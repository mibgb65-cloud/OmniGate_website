package com.omnigate.chatgpt.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.omnigate.chatgpt.mapper.ChatGptSystemSettingMapper;
import com.omnigate.chatgpt.mapper.ChatGptWorkerTaskRunMapper;
import com.omnigate.chatgpt.model.dto.ChatGptBatchRegisterTaskCreateDTO;
import com.omnigate.chatgpt.model.vo.ChatGptTaskDispatchVO;
import com.omnigate.chatgpt.model.vo.ChatGptTaskRunStatusVO;
import com.omnigate.chatgpt.service.ChatGptAccountTaskService;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.connection.stream.RecordId;
import org.springframework.data.redis.connection.stream.StreamRecords;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.lang.reflect.Method;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * ChatGPT 自动注册任务投递服务实现。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ChatGptAccountTaskServiceImpl implements ChatGptAccountTaskService {

    private static final String MODULE_CHATGPT = "chatgpt";
    private static final String ACTION_BATCH_REGISTER = "batch_register_chatgpt_accounts";
    private static final String STATUS_QUEUED = "queued";
    private static final int SINGLE_SIGNUP_COUNT = 1;
    private static final String DEFAULT_TRIGGERED_BY = "system";
    private static final String RETRY_MAX_ATTEMPTS_KEY = "task.retry_max_attempts";
    private static final int DEFAULT_MAX_ATTEMPTS = 3;
    private static final String CLOUDMAIL_ACCOUNT_EMAIL_KEY = "cloudmail.account_email";
    private static final String CLOUDMAIL_PASSWORD_KEY = "cloudmail.password";
    private static final String CLOUDMAIL_AUTH_URL_KEY = "cloudmail.auth_url";
    private static final String CHATGPT_REGISTRATION_EMAIL_SUFFIX_KEY = "chatgpt.registration_email_suffix";

    private final ChatGptWorkerTaskRunMapper workerTaskRunMapper;
    private final ChatGptSystemSettingMapper systemSettingMapper;
    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    @Value("${omnigate.worker.task-stream:task_stream}")
    private String taskStream;

    @Override
    public ChatGptTaskDispatchVO dispatchBatchRegisterTask(ChatGptBatchRegisterTaskCreateDTO createDTO) {
        int signupCount = normalizeSignupCount(createDTO == null ? null : createDTO.getSignupCount());
        validateBatchRegisterSettings();
        UUID taskRunId = UUID.randomUUID();
        UUID rootRunId = UUID.randomUUID();
        String payloadJson = buildTaskPayloadJson(signupCount, 1);
        String triggeredBy = resolveTriggeredBy();
        int maxAttempts = resolveRetryMaxAttempts();

        int inserted = workerTaskRunMapper.insertTaskRun(
                taskRunId,
                rootRunId,
                1,
                maxAttempts,
                STATUS_QUEUED,
                triggeredBy,
                payloadJson
        );
        if (inserted <= 0) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "创建 ChatGPT 自动注册任务失败");
        }

        Map<String, String> streamFields = new LinkedHashMap<>();
        streamFields.put("task_run_id", taskRunId.toString());
        streamFields.put("root_run_id", rootRunId.toString());
        streamFields.put("payload", payloadJson);
        streamFields.put("created_at", DateTimeFormatter.ISO_INSTANT.format(Instant.now()));

        try {
            RecordId recordId = stringRedisTemplate.opsForStream().add(
                    StreamRecords.mapBacked(streamFields).withStreamKey(taskStream)
            );
            if (recordId == null) {
                cleanupTaskRun(taskRunId);
                throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "投递 ChatGPT 自动注册任务到队列失败");
            }
        } catch (BizException ex) {
            throw ex;
        } catch (Exception ex) {
            cleanupTaskRun(taskRunId);
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "投递 ChatGPT 自动注册任务异常: " + ex.getMessage());
        }

        ChatGptTaskDispatchVO vo = new ChatGptTaskDispatchVO();
        vo.setTaskRunId(taskRunId.toString());
        vo.setRootRunId(rootRunId.toString());
        vo.setModule(MODULE_CHATGPT);
        vo.setAction(ACTION_BATCH_REGISTER);
        vo.setStatus(STATUS_QUEUED);
        vo.setRequestedCount(signupCount);
        return vo;
    }

    @Override
    public ChatGptTaskRunStatusVO getTaskRunStatus(String taskRunId) {
        UUID taskRunUuid = parseUuid(taskRunId, "taskRunId");
        ChatGptTaskRunStatusVO status = workerTaskRunMapper.selectStatusById(taskRunUuid);
        if (status == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "任务不存在: " + taskRunId);
        }
        return status;
    }

    @Override
    public ChatGptTaskRunStatusVO getLatestTaskRunStatusByRootRunId(String rootRunId) {
        UUID rootRunUuid = parseUuid(rootRunId, "rootRunId");
        ChatGptTaskRunStatusVO status = workerTaskRunMapper.selectLatestStatusByRootRunId(rootRunUuid);
        if (status == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "任务不存在: " + rootRunId);
        }
        return status;
    }

    private void validateBatchRegisterSettings() {
        List<String> invalidItems = new ArrayList<>();

        String cloudMailAccountEmail = normalizeSettingValue(systemSettingMapper.selectValueByKey(CLOUDMAIL_ACCOUNT_EMAIL_KEY));
        if (!StringUtils.hasText(cloudMailAccountEmail)) {
            invalidItems.add("CloudMail 登录账号（邮箱）未配置");
        }

        String cloudMailPassword = normalizeSettingValue(systemSettingMapper.selectValueByKey(CLOUDMAIL_PASSWORD_KEY));
        if (!StringUtils.hasText(cloudMailPassword)) {
            invalidItems.add("CloudMail 登录密码未配置");
        }

        String cloudMailAuthUrl = normalizeSettingValue(systemSettingMapper.selectValueByKey(CLOUDMAIL_AUTH_URL_KEY));
        if (!StringUtils.hasText(cloudMailAuthUrl)) {
            invalidItems.add("CloudMail 登录网址未配置");
        } else if (!isValidCloudMailAuthUrl(cloudMailAuthUrl)) {
            invalidItems.add("CloudMail 登录网址格式不正确");
        }

        String registrationEmailSuffix = normalizeSettingValue(
                systemSettingMapper.selectValueByKey(CHATGPT_REGISTRATION_EMAIL_SUFFIX_KEY)
        );
        if (!StringUtils.hasText(registrationEmailSuffix)) {
            invalidItems.add("ChatGPT 注册邮箱后缀未配置");
        } else if (!isValidRegistrationEmailSuffix(registrationEmailSuffix)) {
            invalidItems.add("ChatGPT 注册邮箱后缀格式不正确");
        }

        if (!invalidItems.isEmpty()) {
            throw new BizException(
                    BizErrorCodeEnum.BAD_REQUEST,
                    "自动注册前请先完成或修正以下设置：" + String.join("、", invalidItems)
            );
        }
    }

    private int normalizeSignupCount(Integer signupCount) {
        if (signupCount == null || signupCount <= 0) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "signupCount 必须大于 0");
        }
        return signupCount;
    }

    private String buildTaskPayloadJson(int requestedCount, int currentIndex) {
        Map<String, Object> bizPayload = new LinkedHashMap<>();
        bizPayload.put("signup_count", SINGLE_SIGNUP_COUNT);
        bizPayload.put("requested_count", requestedCount);
        bizPayload.put("current_index", currentIndex);
        Map<String, Object> taskPayload = new LinkedHashMap<>();
        taskPayload.put("module", MODULE_CHATGPT);
        taskPayload.put("action", ACTION_BATCH_REGISTER);
        taskPayload.put("payload", bizPayload);
        try {
            return objectMapper.writeValueAsString(taskPayload);
        } catch (JsonProcessingException ex) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "序列化 ChatGPT 自动注册任务参数失败: " + ex.getMessage());
        }
    }

    private int resolveRetryMaxAttempts() {
        String raw = systemSettingMapper.selectValueByKey(RETRY_MAX_ATTEMPTS_KEY);
        if (!StringUtils.hasText(raw)) {
            return DEFAULT_MAX_ATTEMPTS;
        }
        try {
            return Math.max(1, Integer.parseInt(raw.trim()));
        } catch (NumberFormatException ex) {
            log.warn("系统配置 task.retry_max_attempts 非法，使用默认值 {}, raw={}", DEFAULT_MAX_ATTEMPTS, raw);
            return DEFAULT_MAX_ATTEMPTS;
        }
    }

    private String resolveTriggeredBy() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null) {
            return DEFAULT_TRIGGERED_BY;
        }

        String principalUsername = tryExtractPrincipalUsername(authentication.getPrincipal());
        if (StringUtils.hasText(principalUsername) && !"anonymousUser".equalsIgnoreCase(principalUsername)) {
            return principalUsername;
        }

        String fallbackName = authentication.getName();
        if (StringUtils.hasText(fallbackName) && !"anonymousUser".equalsIgnoreCase(fallbackName)) {
            return fallbackName.trim();
        }
        return DEFAULT_TRIGGERED_BY;
    }

    private String normalizeSettingValue(String value) {
        return value == null ? null : value.trim();
    }

    private boolean isValidCloudMailAuthUrl(String authUrl) {
        try {
            URI uri = new URI(authUrl);
            String scheme = uri.getScheme();
            String host = uri.getHost();
            return scheme != null
                    && host != null
                    && ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme));
        } catch (URISyntaxException ex) {
            return false;
        }
    }

    private boolean isValidRegistrationEmailSuffix(String emailSuffix) {
        String normalized = emailSuffix.startsWith("@") ? emailSuffix.substring(1) : emailSuffix;
        return !normalized.contains("@")
                && !normalized.chars().anyMatch(Character::isWhitespace)
                && normalized.contains(".");
    }

    private String tryExtractPrincipalUsername(Object principal) {
        if (principal == null) {
            return null;
        }
        if (principal instanceof CharSequence chars) {
            return chars.toString().trim();
        }
        try {
            Method getter = principal.getClass().getMethod("getUsername");
            Object result = getter.invoke(principal);
            if (result instanceof String username && StringUtils.hasText(username)) {
                return username.trim();
            }
        } catch (Exception ignore) {
            return null;
        }
        return null;
    }

    private void cleanupTaskRun(UUID taskRunId) {
        try {
            workerTaskRunMapper.deleteById(taskRunId);
        } catch (Exception cleanupEx) {
            log.error("清理失败任务记录异常, taskRunId={}", taskRunId, cleanupEx);
        }
    }

    private UUID parseUuid(String rawUuid, String fieldName) {
        if (!StringUtils.hasText(rawUuid)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, fieldName + " 不能为空");
        }
        try {
            return UUID.fromString(rawUuid.trim());
        } catch (IllegalArgumentException ex) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, fieldName + " 格式非法");
        }
    }
}
