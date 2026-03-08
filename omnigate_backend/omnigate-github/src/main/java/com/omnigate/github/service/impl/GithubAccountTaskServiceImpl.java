package com.omnigate.github.service.impl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import com.omnigate.github.entity.GithubAccountBase;
import com.omnigate.github.mapper.GithubAccountBaseMapper;
import com.omnigate.github.mapper.GithubSystemSettingMapper;
import com.omnigate.github.mapper.GithubWorkerTaskRunMapper;
import com.omnigate.github.model.vo.GithubTaskDispatchVO;
import com.omnigate.github.model.vo.GithubTaskRunStatusVO;
import com.omnigate.github.service.GithubAccountTaskService;
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
import java.net.URI;
import java.net.URISyntaxException;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/**
 * GitHub 账号自动化任务投递服务实现。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GithubAccountTaskServiceImpl implements GithubAccountTaskService {

    private static final String LOG_PREFIX = "[GitHub任务]";
    private static final String MODULE_GITHUB = "github";
    private static final String STATUS_ACTIVE = "active";
    private static final String STATUS_QUEUED = "queued";
    private static final String DEFAULT_TRIGGERED_BY = "system";
    private static final String RETRY_MAX_ATTEMPTS_KEY = "task.retry_max_attempts";
    private static final int DEFAULT_MAX_ATTEMPTS = 3;

    private static final String ACTION_GENERATE_TOKEN = "generate_github_token_by_account_id";
    private static final String ACTION_STAR_REPO = "star_github_repo_by_account_id";

    private final GithubAccountBaseMapper githubAccountBaseMapper;
    private final GithubWorkerTaskRunMapper workerTaskRunMapper;
    private final GithubSystemSettingMapper systemSettingMapper;
    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    @Value("${omnigate.worker.task-stream:task_stream}")
    private String taskStream;

    @Override
    public GithubTaskDispatchVO dispatchGenerateTokenTask(Long accountId) {
        GithubAccountBase account = getRequiredOperableAccount(accountId);
        Map<String, Object> bizPayload = Map.of("github_account_id", account.getId());
        log.info("{} 投递生成 Token 任务 | accountId={} | username={}", LOG_PREFIX, account.getId(), safeLogText(account.getUsername()));
        return dispatchTask(account.getId(), ACTION_GENERATE_TOKEN, bizPayload, null);
    }

    @Override
    public GithubTaskDispatchVO dispatchStarRepoTask(Long accountId, String repoUrl) {
        GithubAccountBase account = getRequiredOperableAccount(accountId);
        String normalizedRepoUrl = normalizeGithubRepoUrl(repoUrl);
        Map<String, Object> bizPayload = new LinkedHashMap<>();
        bizPayload.put("github_account_id", account.getId());
        bizPayload.put("repo_url", normalizedRepoUrl);
        log.info(
                "{} 投递 Star 仓库任务 | accountId={} | username={} | repoUrl={}",
                LOG_PREFIX,
                account.getId(),
                safeLogText(account.getUsername()),
                normalizedRepoUrl
        );
        return dispatchTask(account.getId(), ACTION_STAR_REPO, bizPayload, normalizedRepoUrl);
    }

    @Override
    public GithubTaskRunStatusVO getTaskRunStatus(String taskRunId) {
        UUID taskRunUuid = parseUuid(taskRunId, "taskRunId");
        GithubTaskRunStatusVO status = workerTaskRunMapper.selectStatusById(taskRunUuid);
        if (status == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "任务不存在: " + taskRunId);
        }
        return status;
    }

    @Override
    public GithubTaskRunStatusVO getLatestTaskRunStatusByRootRunId(String rootRunId) {
        UUID rootRunUuid = parseUuid(rootRunId, "rootRunId");
        GithubTaskRunStatusVO status = workerTaskRunMapper.selectLatestStatusByRootRunId(rootRunUuid);
        if (status == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "任务不存在: " + rootRunId);
        }
        return status;
    }

    private GithubTaskDispatchVO dispatchTask(Long accountId,
                                              String action,
                                              Map<String, Object> bizPayload,
                                              String repoUrl) {
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
            log.error("{} 创建任务记录失败 | accountId={} | action={}", LOG_PREFIX, accountId, action);
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

        GithubTaskDispatchVO vo = new GithubTaskDispatchVO();
        vo.setTaskRunId(taskRunId.toString());
        vo.setRootRunId(rootRunId.toString());
        vo.setModule(MODULE_GITHUB);
        vo.setAction(action);
        vo.setStatus(STATUS_QUEUED);
        vo.setAccountId(accountId);
        vo.setRepoUrl(repoUrl);
        return vo;
    }

    private GithubAccountBase getRequiredOperableAccount(Long accountId) {
        GithubAccountBase account = githubAccountBaseMapper.selectById(accountId);
        if (account == null) {
            log.warn("{} 账号不存在 | accountId={}", LOG_PREFIX, accountId);
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "账号不存在");
        }
        if (!STATUS_ACTIVE.equalsIgnoreCase(normalize(account.getAccountStatus()))) {
            log.warn(
                    "{} 账号状态不允许执行自动化操作 | accountId={} | status={}",
                    LOG_PREFIX,
                    accountId,
                    safeLogText(account.getAccountStatus())
            );
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "仅 active 状态账号可执行 GitHub 自动化操作");
        }
        assertCredentialPresent("邮箱", account.getEmail());
        assertCredentialPresent("密码", account.getPassword());
        assertCredentialPresent("TOTP密钥", account.getTotpSecret());
        return account;
    }

    private void assertCredentialPresent(String fieldLabel, String value) {
        if (!StringUtils.hasText(normalize(value))) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, fieldLabel + "不能为空，无法执行 GitHub 自动化操作");
        }
    }

    private String normalizeGithubRepoUrl(String repoUrl) {
        String raw = normalize(repoUrl);
        if (!StringUtils.hasText(raw)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "repoUrl 不能为空");
        }
        String candidate = raw;
        if (!candidate.matches("(?i)^https?://.*")) {
            candidate = "https://" + candidate;
        }
        URI uri;
        try {
            uri = new URI(candidate);
        } catch (URISyntaxException ex) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "repoUrl 不是合法的 GitHub 仓库地址");
        }

        String host = normalize(uri.getHost());
        if (!StringUtils.hasText(host)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "repoUrl 缺少合法主机名");
        }
        String normalizedHost = host.toLowerCase(Locale.ROOT);
        if (!"github.com".equals(normalizedHost) && !"www.github.com".equals(normalizedHost)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "repoUrl 必须是 github.com 仓库地址");
        }

        String path = normalize(uri.getPath());
        if (!StringUtils.hasText(path)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "repoUrl 缺少 owner/repo 信息");
        }
        List<String> segments = List.of(path.split("/")).stream()
                .filter(StringUtils::hasText)
                .map(String::trim)
                .toList();
        if (segments.size() < 2) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "repoUrl 缺少完整的 owner/repo 信息");
        }

        String owner = segments.get(0);
        String repo = segments.get(1);
        if (repo.endsWith(".git")) {
            repo = repo.substring(0, repo.length() - 4);
        }
        if (!owner.matches("^[A-Za-z0-9_.-]+$") || !repo.matches("^[A-Za-z0-9_.-]+$")) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "repoUrl 包含非法的 owner/repo 名称");
        }
        return "https://github.com/" + owner + "/" + repo;
    }

    private String buildTaskPayloadJson(String action, Map<String, Object> bizPayload) {
        Map<String, Object> taskPayload = new LinkedHashMap<>();
        taskPayload.put("module", MODULE_GITHUB);
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
            log.warn("{} 系统配置 task.retry_max_attempts 非法，使用默认值 {} | raw={}", LOG_PREFIX, DEFAULT_MAX_ATTEMPTS, raw);
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

    private void cleanupTaskRun(UUID taskRunId) {
        try {
            workerTaskRunMapper.deleteById(taskRunId);
        } catch (Exception cleanupEx) {
            log.error("{} 清理失败任务记录异常 | taskRunId={}", LOG_PREFIX, taskRunId, cleanupEx);
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

    private String normalize(String value) {
        return value == null ? null : value.trim();
    }

    private String safeLogText(String value) {
        return StringUtils.hasText(value) ? value.trim() : "-";
    }
}
