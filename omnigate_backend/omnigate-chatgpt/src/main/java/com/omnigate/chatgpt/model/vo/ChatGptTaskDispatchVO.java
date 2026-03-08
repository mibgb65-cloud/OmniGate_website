package com.omnigate.chatgpt.model.vo;

import lombok.Data;

/**
 * ChatGPT Worker 任务投递结果。
 */
@Data
public class ChatGptTaskDispatchVO {

    /**
     * 当前执行记录 ID。
     */
    private String taskRunId;

    /**
     * 根任务 ID。
     */
    private String rootRunId;

    /**
     * Worker 模块名。
     */
    private String module;

    /**
     * Worker 动作名。
     */
    private String action;

    /**
     * 当前任务状态。
     */
    private String status;

    /**
     * 请求自动注册数量。
     */
    private Integer requestedCount;
}
