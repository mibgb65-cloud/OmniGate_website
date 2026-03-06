package com.omnigate.google.model.dto;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * Google 账号批量同步任务请求参数。
 */
@Data
public class GoogleBatchSyncRequestDTO {

    /**
     * 待同步账号 ID 列表。
     */
    @NotEmpty(message = "账号ID列表不能为空")
    @Size(max = 50, message = "单次最多提交50个账号")
    private List<@NotNull(message = "账号ID不能为空") @Positive(message = "账号ID必须大于0") Long> accountIds;
}
