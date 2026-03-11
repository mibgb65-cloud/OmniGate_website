package com.omnigate.chatgpt.model.dto;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.Data;

import java.util.List;

/**
 * ChatGPT 账号批量出售状态更新参数。
 */
@Data
public class ChatGptAccountBatchSoldDTO {

    /**
     * 账号 ID 列表。
     */
    @NotEmpty(message = "账号ID列表不能为空")
    private List<@Positive(message = "账号ID必须大于0") Long> ids;

    /**
     * 是否已出售。
     */
    @NotNull(message = "出售状态不能为空")
    private Boolean sold;
}
