package com.omnigate.github.model.vo;

import lombok.Data;

/**
 * GitHub Worker 任务投递结果。
 */
@Data
public class GithubTaskDispatchVO {

    /**
     * 当前执行记录 ID（task_runs.id）。
     */
    private String taskRunId;

    /**
     * 根任务 ID（task_runs.root_run_id）。
     */
    private String rootRunId;

    /**
     * 任务模块。
     */
    private String module;

    /**
     * 任务动作。
     */
    private String action;

    /**
     * 任务状态（默认 queued）。
     */
    private String status;

    /**
     * 关联 GitHub 账号 ID。
     */
    private Long accountId;

    /**
     * 关联仓库 URL（Star 任务时返回）。
     */
    private String repoUrl;
}
