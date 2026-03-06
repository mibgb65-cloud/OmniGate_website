package com.omnigate.google.controller;

import com.omnigate.common.response.Result;
import com.omnigate.google.model.dto.GoogleTaskStatusBatchQueryDTO;
import com.omnigate.google.model.vo.GoogleTaskRunStatusVO;
import com.omnigate.google.service.GoogleAccountTaskService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * Worker 任务状态查询控制器。
 */
@Validated
@RestController
@RequestMapping("/api/google/tasks")
@RequiredArgsConstructor
public class GoogleTaskController {

    private final GoogleAccountTaskService googleAccountTaskService;

    /**
     * 按 taskRunId 查询任务状态。
     *
     * @param taskRunId 执行记录 ID
     * @return 任务状态
     */
    @GetMapping("/{taskRunId}")
    public Result<GoogleTaskRunStatusVO> getTaskStatus(@PathVariable @NotBlank(message = "taskRunId 不能为空") String taskRunId) {
        return Result.success(googleAccountTaskService.getTaskRunStatus(taskRunId));
    }

    /**
     * 按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunId 根任务 ID
     * @return 最新任务状态
     */
    @GetMapping("/root/{rootRunId}")
    public Result<GoogleTaskRunStatusVO> getLatestTaskStatusByRootRunId(
            @PathVariable @NotBlank(message = "rootRunId 不能为空") String rootRunId) {
        return Result.success(googleAccountTaskService.getLatestTaskRunStatusByRootRunId(rootRunId));
    }

    /**
     * 批量按 rootRunId 查询当前最新任务状态。
     *
     * @param queryDTO 批量查询参数
     * @return 最新任务状态列表
     */
    @PostMapping("/root/status/batch")
    public Result<List<GoogleTaskRunStatusVO>> batchGetLatestTaskStatusByRootRunIds(
            @RequestBody @Valid GoogleTaskStatusBatchQueryDTO queryDTO) {
        return Result.success(googleAccountTaskService.listLatestTaskRunStatusesByRootRunIds(queryDTO.getRootRunIds()));
    }
}
