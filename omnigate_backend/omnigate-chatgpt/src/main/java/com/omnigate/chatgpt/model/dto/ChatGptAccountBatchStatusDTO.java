package com.omnigate.chatgpt.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import lombok.Data;

import java.util.List;

/**
 * ChatGPT 账号批量状态更新参数。
 */
@Data
public class ChatGptAccountBatchStatusDTO {

    /**
     * 账号 ID 列表。
     */
    @NotEmpty(message = "账号ID列表不能为空")
    private List<@Positive(message = "账号ID必须大于0") Long> ids;

    /**
     * 批量更新目标状态：active, locked, banned。
     */
    @NotBlank(message = "账号状态不能为空")
    @Pattern(regexp = "active|locked|banned", message = "账号状态仅支持 active/locked/banned")
    private String accountStatus;
}
