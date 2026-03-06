package com.omnigate.google.model.vo;

import lombok.Data;

import java.time.OffsetDateTime;

/**
 * Worker 任务运行状态视图。
 */
@Data
public class GoogleTaskRunStatusVO {

    private String taskRunId;

    private String rootRunId;

    private Integer attemptNo;

    private Integer maxAttempts;

    private String module;

    private String action;

    private String status;

    private String errorCode;

    private String errorMessage;

    private String lastCheckpoint;

    private OffsetDateTime startedAt;

    private OffsetDateTime finishedAt;

    private OffsetDateTime createdAt;

    private OffsetDateTime updatedAt;
}
