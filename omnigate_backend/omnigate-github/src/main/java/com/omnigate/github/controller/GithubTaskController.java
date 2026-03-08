package com.omnigate.github.controller;

import com.omnigate.common.response.Result;
import com.omnigate.github.model.vo.GithubTaskRunStatusVO;
import com.omnigate.github.service.GithubAccountTaskService;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * GitHub Worker 任务状态查询控制器。
 */
@Validated
@RestController
@RequestMapping("/api/github/tasks")
@RequiredArgsConstructor
public class GithubTaskController {

    private final GithubAccountTaskService githubAccountTaskService;

    /**
     * 按 taskRunId 查询任务状态。
     *
     * @param taskRunId 执行记录 ID
     * @return 任务状态
     */
    @GetMapping("/{taskRunId}")
    public Result<GithubTaskRunStatusVO> getTaskStatus(
            @PathVariable @NotBlank(message = "taskRunId 不能为空") String taskRunId) {
        return Result.success(githubAccountTaskService.getTaskRunStatus(taskRunId));
    }

    /**
     * 按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunId 根任务 ID
     * @return 最新任务状态
     */
    @GetMapping("/root/{rootRunId}")
    public Result<GithubTaskRunStatusVO> getLatestTaskStatusByRootRunId(
            @PathVariable @NotBlank(message = "rootRunId 不能为空") String rootRunId) {
        return Result.success(githubAccountTaskService.getLatestTaskRunStatusByRootRunId(rootRunId));
    }
}
