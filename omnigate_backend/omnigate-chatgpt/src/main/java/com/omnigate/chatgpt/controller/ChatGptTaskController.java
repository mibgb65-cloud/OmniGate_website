package com.omnigate.chatgpt.controller;

import com.omnigate.chatgpt.model.dto.ChatGptBatchRegisterTaskCreateDTO;
import com.omnigate.chatgpt.model.vo.ChatGptTaskDispatchVO;
import com.omnigate.chatgpt.model.vo.ChatGptTaskRunStatusVO;
import com.omnigate.chatgpt.service.ChatGptAccountTaskService;
import com.omnigate.common.response.Result;
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

/**
 * ChatGPT 自动注册任务控制器。
 */
@Validated
@RestController
@RequestMapping("/api/chatgpt/tasks")
@RequiredArgsConstructor
public class ChatGptTaskController {

    private final ChatGptAccountTaskService chatGptAccountTaskService;

    /**
     * 投递批量自动注册任务。
     *
     * @param createDTO 任务参数
     * @return 投递结果
     */
    @PostMapping("/batch-register")
    public Result<ChatGptTaskDispatchVO> dispatchBatchRegisterTask(
            @RequestBody @Valid ChatGptBatchRegisterTaskCreateDTO createDTO) {
        return Result.success(chatGptAccountTaskService.dispatchBatchRegisterTask(createDTO));
    }

    /**
     * 按 taskRunId 查询任务状态。
     *
     * @param taskRunId 执行记录 ID
     * @return 任务状态
     */
    @GetMapping("/{taskRunId}")
    public Result<ChatGptTaskRunStatusVO> getTaskStatus(
            @PathVariable @NotBlank(message = "taskRunId 不能为空") String taskRunId) {
        return Result.success(chatGptAccountTaskService.getTaskRunStatus(taskRunId));
    }

    /**
     * 按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunId 根任务 ID
     * @return 最新任务状态
     */
    @GetMapping("/root/{rootRunId}")
    public Result<ChatGptTaskRunStatusVO> getLatestTaskStatusByRootRunId(
            @PathVariable @NotBlank(message = "rootRunId 不能为空") String rootRunId) {
        return Result.success(chatGptAccountTaskService.getLatestTaskRunStatusByRootRunId(rootRunId));
    }
}
