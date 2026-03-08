package com.omnigate.chatgpt.model.dto;

import jakarta.validation.constraints.Positive;
import lombok.Data;

/**
 * ChatGPT 批量自动注册任务创建参数。
 */
@Data
public class ChatGptBatchRegisterTaskCreateDTO {

    /**
     * 需要自动注册的账号数量。
     */
    @Positive(message = "signupCount 必须大于 0")
    private Integer signupCount;
}
