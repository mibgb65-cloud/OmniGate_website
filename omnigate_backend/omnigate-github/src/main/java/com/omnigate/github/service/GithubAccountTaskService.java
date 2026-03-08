package com.omnigate.github.service;

import com.omnigate.github.model.vo.GithubTaskDispatchVO;
import com.omnigate.github.model.vo.GithubTaskRunStatusVO;

/**
 * GitHub 账号自动化任务投递服务。
 */
public interface GithubAccountTaskService {

    /**
     * 投递 GitHub Token 生成任务。
     *
     * @param accountId 账号 ID
     * @return 投递结果
     */
    GithubTaskDispatchVO dispatchGenerateTokenTask(Long accountId);

    /**
     * 投递 GitHub 仓库 Star 任务。
     *
     * @param accountId 账号 ID
     * @param repoUrl 仓库 URL
     * @return 投递结果
     */
    GithubTaskDispatchVO dispatchStarRepoTask(Long accountId, String repoUrl);

    /**
     * 按 taskRunId 查询任务状态。
     *
     * @param taskRunId 执行记录 ID
     * @return 任务状态
     */
    GithubTaskRunStatusVO getTaskRunStatus(String taskRunId);

    /**
     * 按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunId 根任务 ID
     * @return 最新任务状态
     */
    GithubTaskRunStatusVO getLatestTaskRunStatusByRootRunId(String rootRunId);
}
