package com.omnigate.google.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

/**
 * 批量查询任务状态请求。
 */
@Data
public class GoogleTaskStatusBatchQueryDTO {

    @NotEmpty(message = "rootRunIds 不能为空")
    private List<@NotBlank(message = "rootRunId 不能为空") String> rootRunIds;
}
