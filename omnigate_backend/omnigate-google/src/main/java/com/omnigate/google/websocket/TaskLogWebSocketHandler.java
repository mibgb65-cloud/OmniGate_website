package com.omnigate.google.websocket;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.omnigate.google.model.vo.GoogleTaskRunStatusVO;
import com.omnigate.google.service.GoogleAccountTaskService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.ReadOffset;
import org.springframework.data.redis.connection.stream.StreamOffset;
import org.springframework.data.redis.connection.stream.StreamReadOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import org.springframework.web.util.UriComponentsBuilder;

import jakarta.annotation.PreDestroy;
import java.net.URI;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;

/**
 * 将 Redis Stream 中的任务日志桥接到前端 WebSocket。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class TaskLogWebSocketHandler extends TextWebSocketHandler {

    private static final Duration LOG_READ_BLOCK = Duration.ofSeconds(2);
    private static final long BACKLOG_LOOKBACK_MS = 2_000L;

    private final StringRedisTemplate stringRedisTemplate;
    private final GoogleAccountTaskService googleAccountTaskService;
    private final ObjectMapper objectMapper;

    @Value("${omnigate.worker.task-log-stream:task_log_stream}")
    private String taskLogStream;

    private final ExecutorService sessionExecutor = java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor();
    private final Map<String, Future<?>> sessionWorkers = new ConcurrentHashMap<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        TaskLogSubscription subscription = TaskLogSubscription.from(session.getUri());
        if (!subscription.isValid()) {
            session.close(CloseStatus.BAD_DATA.withReason("Missing task identifier"));
            return;
        }

        session.getAttributes().put(TaskLogSubscription.ATTRIBUTE_KEY, subscription);
        GoogleTaskRunStatusVO initialStatus = resolveStatusSnapshot(subscription);
        if (initialStatus != null) {
            sendStatusSnapshot(session, initialStatus);
        }

        String startId = toStreamStartId(initialStatus);
        Future<?> worker = sessionExecutor.submit(() -> streamTaskLogs(session, subscription, startId, initialStatus));
        sessionWorkers.put(session.getId(), worker);
    }

    @Override
    public void handleTextMessage(WebSocketSession session, TextMessage message) {
        // 前端发送的 subscribe 指令仅用于兼容，服务端在建连时已完成订阅。
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        stopWorker(session.getId());
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        log.warn("Task log websocket transport error. sessionId={} message={}", session.getId(), exception.getMessage());
        stopWorker(session.getId());
        if (session.isOpen()) {
            session.close(CloseStatus.SERVER_ERROR);
        }
    }

    @PreDestroy
    public void shutdown() {
        sessionWorkers.keySet().forEach(this::stopWorker);
        sessionExecutor.shutdownNow();
    }

    private void streamTaskLogs(WebSocketSession session,
                                TaskLogSubscription subscription,
                                String startId,
                                GoogleTaskRunStatusVO initialStatus) {
        String lastSeenId = startId;
        GoogleTaskRunStatusVO latestStatus = initialStatus;

        while (session.isOpen()) {
            try {
                List<MapRecord<String, Object, Object>> records = readTaskLogRecords(lastSeenId);
                for (MapRecord<String, Object, Object> record : records) {
                    lastSeenId = record.getId().getValue();
                    Map<String, Object> payload = normalizeRecordPayload(record);
                    if (!subscription.matches(payload)) {
                        continue;
                    }
                    sendPayload(session, payload);
                }

                GoogleTaskRunStatusVO nextStatus = resolveStatusSnapshot(subscription);
                if (hasStatusChanged(latestStatus, nextStatus)) {
                    latestStatus = nextStatus;
                    if (nextStatus != null) {
                        sendStatusSnapshot(session, nextStatus);
                    }
                }
            } catch (InterruptedException interruptedException) {
                Thread.currentThread().interrupt();
                return;
            } catch (Exception ex) {
                log.warn("Task log websocket stream loop failed. sessionId={} message={}", session.getId(), ex.getMessage());
                try {
                    if (session.isOpen()) {
                        session.sendMessage(new TextMessage("{\"level\":\"ERROR\",\"message\":\"日志流读取失败\"}"));
                    }
                } catch (Exception sendEx) {
                    log.debug("Failed to send websocket error message. sessionId={}", session.getId(), sendEx);
                }
                return;
            }
        }
    }

    private List<MapRecord<String, Object, Object>> readTaskLogRecords(String lastSeenId) {
        StreamReadOptions readOptions = StreamReadOptions.empty().count(100).block(LOG_READ_BLOCK);
        List<MapRecord<String, Object, Object>> records = stringRedisTemplate.opsForStream().read(
                readOptions,
                StreamOffset.create(taskLogStream, ReadOffset.from(lastSeenId))
        );
        return records == null ? List.of() : records;
    }

    private Map<String, Object> normalizeRecordPayload(MapRecord<String, Object, Object> record) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("stream_id", record.getId().getValue());
        record.getValue().forEach((key, value) -> payload.put(String.valueOf(key), parseFieldValue(value)));
        return payload;
    }

    private Object parseFieldValue(Object rawValue) {
        if (!(rawValue instanceof String rawText)) {
            return rawValue;
        }

        String trimmed = rawText.trim();
        if (!StringUtils.hasText(trimmed)) {
            return trimmed;
        }
        if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) {
            return trimmed;
        }

        try {
            return objectMapper.readValue(trimmed, new TypeReference<Object>() {
            });
        } catch (Exception ignore) {
            return trimmed;
        }
    }

    private GoogleTaskRunStatusVO resolveStatusSnapshot(TaskLogSubscription subscription) {
        if (StringUtils.hasText(subscription.rootRunId())) {
            return googleAccountTaskService.getLatestTaskRunStatusByRootRunId(subscription.rootRunId());
        }
        if (StringUtils.hasText(subscription.taskRunId())) {
            return googleAccountTaskService.getTaskRunStatus(subscription.taskRunId());
        }
        return null;
    }

    private void sendStatusSnapshot(WebSocketSession session, GoogleTaskRunStatusVO status) throws Exception {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("taskRunId", status.getTaskRunId());
        payload.put("task_run_id", status.getTaskRunId());
        payload.put("rootRunId", status.getRootRunId());
        payload.put("root_run_id", status.getRootRunId());
        payload.put("status", status.getStatus());
        payload.put("attemptNo", status.getAttemptNo());
        payload.put("attempt_no", status.getAttemptNo());
        payload.put("maxAttempts", status.getMaxAttempts());
        payload.put("max_attempts", status.getMaxAttempts());
        payload.put("errorCode", status.getErrorCode());
        payload.put("error_code", status.getErrorCode());
        payload.put("errorMessage", status.getErrorMessage());
        payload.put("error_message", status.getErrorMessage());
        payload.put("lastCheckpoint", status.getLastCheckpoint());
        payload.put("last_checkpoint", status.getLastCheckpoint());
        sendPayload(session, payload);
    }

    private void sendPayload(WebSocketSession session, Map<String, Object> payload) throws Exception {
        if (!session.isOpen()) {
            return;
        }
        session.sendMessage(new TextMessage(objectMapper.writeValueAsString(payload)));
    }

    private boolean hasStatusChanged(GoogleTaskRunStatusVO previous, GoogleTaskRunStatusVO next) {
        if (previous == null) {
            return next != null;
        }
        if (next == null) {
            return true;
        }
        return !Objects.equals(previous.getTaskRunId(), next.getTaskRunId())
                || !Objects.equals(previous.getStatus(), next.getStatus())
                || !Objects.equals(previous.getAttemptNo(), next.getAttemptNo())
                || !Objects.equals(previous.getErrorMessage(), next.getErrorMessage())
                || !Objects.equals(previous.getUpdatedAt(), next.getUpdatedAt());
    }

    private String toStreamStartId(GoogleTaskRunStatusVO initialStatus) {
        if (initialStatus == null || initialStatus.getCreatedAt() == null) {
            return "0-0";
        }

        long epochMillis = initialStatus.getCreatedAt().toInstant().toEpochMilli();
        long startMillis = Math.max(0L, epochMillis - BACKLOG_LOOKBACK_MS);
        return startMillis + "-0";
    }

    private void stopWorker(String sessionId) {
        Future<?> worker = sessionWorkers.remove(sessionId);
        if (worker != null) {
            worker.cancel(true);
        }
    }

    private record TaskLogSubscription(String taskRunId, String rootRunId) {

        private static final String ATTRIBUTE_KEY = "taskLogSubscription";

        static TaskLogSubscription from(URI uri) {
            if (uri == null) {
                return new TaskLogSubscription(null, null);
            }

            Map<String, List<String>> queryParams = UriComponentsBuilder.fromUri(uri).build().getQueryParams();
            String taskRunId = firstNonBlank(
                    queryParams.get("task_run_id"),
                    queryParams.get("taskRunId"),
                    queryParams.get("task_id"),
                    queryParams.get("taskId")
            );
            String rootRunId = firstNonBlank(
                    queryParams.get("root_run_id"),
                    queryParams.get("rootRunId")
            );
            return new TaskLogSubscription(taskRunId, rootRunId);
        }

        boolean isValid() {
            return StringUtils.hasText(taskRunId) || StringUtils.hasText(rootRunId);
        }

        boolean matches(Map<String, Object> payload) {
            if (CollectionUtils.isEmpty(payload)) {
                return false;
            }

            String payloadTaskRunId = firstNonBlank(payload.get("task_run_id"), payload.get("taskRunId"), payload.get("task_id"), payload.get("taskId"));
            String payloadRootRunId = firstNonBlank(payload.get("root_run_id"), payload.get("rootRunId"));

            if (StringUtils.hasText(rootRunId) && StringUtils.hasText(payloadRootRunId) && !rootRunId.equals(payloadRootRunId)) {
                return false;
            }
            if (StringUtils.hasText(taskRunId) && StringUtils.hasText(payloadTaskRunId) && !taskRunId.equals(payloadTaskRunId)) {
                return false;
            }
            if (StringUtils.hasText(rootRunId)) {
                return StringUtils.hasText(payloadRootRunId) || !StringUtils.hasText(taskRunId) || taskRunId.equals(payloadTaskRunId);
            }
            return StringUtils.hasText(payloadTaskRunId);
        }

        private static String firstNonBlank(List<String>... values) {
            for (List<String> items : values) {
                String value = firstNonBlank(items == null ? null : items.toArray());
                if (StringUtils.hasText(value)) {
                    return value;
                }
            }
            return null;
        }

        private static String firstNonBlank(Object... values) {
            if (values == null) {
                return null;
            }
            for (Object item : values) {
                if (item == null) {
                    continue;
                }
                String value = String.valueOf(item).trim();
                if (StringUtils.hasText(value)) {
                    return value;
                }
            }
            return null;
        }
    }
}
