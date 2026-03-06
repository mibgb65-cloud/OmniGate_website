package com.omnigate.google.service.impl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import com.omnigate.google.entity.GoogleAccountBase;
import com.omnigate.google.mapper.GoogleAccountBaseMapper;
import com.omnigate.google.mapper.GoogleFamilyMemberMapper;
import com.omnigate.google.mapper.SystemSettingMapper;
import com.omnigate.google.mapper.WorkerTaskRunMapper;
import com.omnigate.google.model.vo.GoogleTaskRunStatusVO;
import com.omnigate.google.model.vo.GoogleTaskDispatchVO;
import com.omnigate.google.service.GoogleAccountTaskService;
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

import java.lang.reflect.Method;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Google 账号自动化任务投递服务实现。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GoogleAccountTaskServiceImpl implements GoogleAccountTaskService {

    private static final String MODULE_GOOGLE = "google";
    private static final String STATUS_QUEUED = "queued";
    private static final String DEFAULT_TRIGGERED_BY = "system";
    private static final String RETRY_MAX_ATTEMPTS_KEY = "task.retry_max_attempts";
    private static final int DEFAULT_MAX_ATTEMPTS = 3;

    private static final String ACTION_FEATURE_SYNC = "get_google_account_feature_by_account_id";
    private static final String ACTION_STUDENT_ELIGIBILITY = "get_google_account_student_eligibility_by_account_id";
    private static final String ACTION_FAMILY_INVITE = "invite_google_family_member_by_account_id";
    private static final int ACCOUNT_SYNC_STATUS_WAITING = 1;

    private final GoogleAccountBaseMapper googleAccountBaseMapper;
    private final GoogleFamilyMemberMapper googleFamilyMemberMapper;
    private final WorkerTaskRunMapper workerTaskRunMapper;
    private final SystemSettingMapper systemSettingMapper;
    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    @Value("${omnigate.worker.task-stream:task_stream}")
    private String taskStream;

    @Override
    public GoogleTaskDispatchVO dispatchFeatureSyncTask(Long accountId) {
        GoogleAccountBase accountBase = getRequiredAccount(accountId);
        return dispatchFeatureSyncTaskInternal(accountBase);
    }

    @Override
    public List<GoogleTaskDispatchVO> dispatchFeatureSyncBatchTasks(List<Long> accountIds) {
        List<Long> distinctIds = distinctIds(accountIds);
        assertIdsNotEmpty(distinctIds);
        assertAllAccountsExists(distinctIds);

        List<GoogleTaskDispatchVO> result = new ArrayList<>(distinctIds.size());
        for (Long accountId : distinctIds) {
            result.add(dispatchFeatureSyncTaskInternal(getRequiredAccount(accountId)));
        }
        return result;
    }

    @Override
    public GoogleTaskDispatchVO dispatchStudentEligibilityTask(Long accountId) {
        getRequiredAccount(accountId);
        Map<String, Object> bizPayload = Map.of("google_account_id", accountId);
        return dispatchTask(accountId, ACTION_STUDENT_ELIGIBILITY, bizPayload, null);
    }

    @Override
    public GoogleTaskDispatchVO dispatchFamilyInviteTask(Long accountId, String invitedAccountEmail) {
        GoogleAccountBase ownerAccount = getRequiredAccount(accountId);
        String invitedEmail = normalizeEmail(invitedAccountEmail);

        if (StringUtils.hasText(ownerAccount.getEmail()) && ownerAccount.getEmail().equalsIgnoreCase(invitedEmail)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "不能邀请当前母号账号自身");
        }
        GoogleAccountBase invitedAccount = googleAccountBaseMapper.selectActiveByEmailIgnoreCase(invitedEmail);
        if (invitedAccount == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "被邀请邮箱不在账号池中");
        }
        long existingCount = googleFamilyMemberMapper.countActiveByAccountIdAndEmail(accountId, invitedEmail);
        if (existingCount > 0) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "该邮箱已在家庭组成员中");
        }

        Map<String, Object> bizPayload = new LinkedHashMap<>();
        bizPayload.put("google_account_id", accountId);
        bizPayload.put("invited_account_email", invitedEmail);
        return dispatchTask(accountId, ACTION_FAMILY_INVITE, bizPayload, invitedEmail);
    }

    @Override
    public GoogleTaskRunStatusVO getTaskRunStatus(String taskRunId) {
        UUID taskRunUuid = parseUuid(taskRunId, "taskRunId");
        GoogleTaskRunStatusVO status = workerTaskRunMapper.selectStatusById(taskRunUuid);
        if (status == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "任务不存在: " + taskRunId);
        }
        return status;
    }

    @Override
    public GoogleTaskRunStatusVO getLatestTaskRunStatusByRootRunId(String rootRunId) {
        UUID rootRunUuid = parseUuid(rootRunId, "rootRunId");
        GoogleTaskRunStatusVO status = workerTaskRunMapper.selectLatestStatusByRootRunId(rootRunUuid);
        if (status == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "任务不存在: " + rootRunId);
        }
        return status;
    }

    @Override
    public List<GoogleTaskRunStatusVO> listLatestTaskRunStatusesByRootRunIds(List<String> rootRunIds) {
        if (rootRunIds == null || rootRunIds.isEmpty()) {
            return List.of();
        }
        List<UUID> rootUuidList = rootRunIds.stream()
                .filter(StringUtils::hasText)
                .map(rootRunId -> parseUuid(rootRunId, "rootRunId"))
                .distinct()
                .toList();
        if (rootUuidList.isEmpty()) {
            return List.of();
        }
        return workerTaskRunMapper.selectLatestStatusesByRootRunIds(rootUuidList);
    }

    private GoogleTaskDispatchVO dispatchFeatureSyncTaskInternal(GoogleAccountBase accountBase) {
        Long accountId = accountBase.getId();
        Integer previousStatus = accountBase.getSyncStatus();
        updateFeatureSyncStatus(accountId, ACCOUNT_SYNC_STATUS_WAITING);
        try {
            Map<String, Object> bizPayload = Map.of("google_account_id", accountId);
            return dispatchTask(accountId, ACTION_FEATURE_SYNC, bizPayload, null);
        } catch (RuntimeException ex) {
            updateFeatureSyncStatus(accountId, previousStatus);
            throw ex;
        }
    }

    protected GoogleTaskDispatchVO dispatchTask(Long accountId,
                                                String action,
                                                Map<String, Object> bizPayload,
                                                String invitedAccountEmail) {
        UUID taskRunId = UUID.randomUUID();
        UUID rootRunId = UUID.randomUUID();
        String payloadJson = buildTaskPayloadJson(action, bizPayload);
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
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "创建任务记录失败");
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
                throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "投递任务到队列失败");
            }
        } catch (BizException ex) {
            throw ex;
        } catch (Exception ex) {
            cleanupTaskRun(taskRunId);
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "投递任务到队列异常: " + ex.getMessage());
        }

        GoogleTaskDispatchVO vo = new GoogleTaskDispatchVO();
        vo.setTaskRunId(taskRunId.toString());
        vo.setRootRunId(rootRunId.toString());
        vo.setModule(MODULE_GOOGLE);
        vo.setAction(action);
        vo.setStatus(STATUS_QUEUED);
        vo.setAccountId(accountId);
        vo.setInvitedAccountEmail(invitedAccountEmail);
        return vo;
    }

    private void cleanupTaskRun(UUID taskRunId) {
        try {
            workerTaskRunMapper.deleteById(taskRunId);
        } catch (Exception cleanupEx) {
            log.error("清理失败任务记录异常, taskRunId={}", taskRunId, cleanupEx);
        }
    }

    private GoogleAccountBase getRequiredAccount(Long accountId) {
        GoogleAccountBase accountBase = googleAccountBaseMapper.selectById(accountId);
        if (accountBase == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "账号不存在");
        }
        return accountBase;
    }

    private void assertAllAccountsExists(List<Long> accountIds) {
        if (accountIds.isEmpty()) {
            return;
        }
        List<GoogleAccountBase> existing = googleAccountBaseMapper.selectList(
                Wrappers.lambdaQuery(GoogleAccountBase.class)
                        .select(GoogleAccountBase::getId)
                        .in(GoogleAccountBase::getId, accountIds)
        );
        Set<Long> existingIdSet = existing.stream().map(GoogleAccountBase::getId).collect(Collectors.toSet());
        List<Long> missingIds = accountIds.stream().filter(id -> !existingIdSet.contains(id)).toList();
        if (!missingIds.isEmpty()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "以下账号不存在: " + missingIds);
        }
    }

    private void assertIdsNotEmpty(List<Long> accountIds) {
        if (accountIds == null || accountIds.isEmpty()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "账号ID列表不能为空");
        }
    }

    private List<Long> distinctIds(List<Long> accountIds) {
        if (accountIds == null || accountIds.isEmpty()) {
            return List.of();
        }
        LinkedHashSet<Long> idSet = new LinkedHashSet<>(accountIds);
        return new ArrayList<>(idSet);
    }

    private String buildTaskPayloadJson(String action, Map<String, Object> bizPayload) {
        Map<String, Object> taskPayload = new LinkedHashMap<>();
        taskPayload.put("module", MODULE_GOOGLE);
        taskPayload.put("action", action);
        taskPayload.put("payload", bizPayload);
        try {
            return objectMapper.writeValueAsString(taskPayload);
        } catch (JsonProcessingException ex) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "序列化任务参数失败: " + ex.getMessage());
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

    private String normalizeEmail(String email) {
        String normalized = email == null ? null : email.trim();
        if (!StringUtils.hasText(normalized)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "被邀请邮箱不能为空");
        }
        return normalized.toLowerCase();
    }

    private void updateFeatureSyncStatus(Long accountId, Integer syncStatus) {
        if (accountId == null || syncStatus == null) {
            return;
        }
        int updated = googleAccountBaseMapper.updateSyncStatusById(accountId, syncStatus);
        if (updated <= 0) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新账号同步状态失败");
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
