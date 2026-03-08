package com.omnigate.chatgpt.service;

import com.omnigate.chatgpt.model.dto.ChatGptBatchRegisterTaskCreateDTO;
import com.omnigate.chatgpt.model.vo.ChatGptTaskDispatchVO;
import com.omnigate.chatgpt.model.vo.ChatGptTaskRunStatusVO;

/**
 * ChatGPT 自动注册任务投递服务。
 */
public interface ChatGptAccountTaskService {

    /**
     * 投递批量自动注册任务。
     *
     * @param createDTO 任务参数
     * @return 投递结果
     */
    ChatGptTaskDispatchVO dispatchBatchRegisterTask(ChatGptBatchRegisterTaskCreateDTO createDTO);

    /**
     * 按 taskRunId 查询任务状态。
     *
     * @param taskRunId 任务执行记录 ID
     * @return 任务状态
     */
    ChatGptTaskRunStatusVO getTaskRunStatus(String taskRunId);

    /**
     * 按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunId 根任务 ID
     * @return 最新任务状态
     */
    ChatGptTaskRunStatusVO getLatestTaskRunStatusByRootRunId(String rootRunId);
}
