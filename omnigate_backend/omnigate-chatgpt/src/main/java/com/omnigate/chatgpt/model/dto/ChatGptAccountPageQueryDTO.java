package com.omnigate.chatgpt.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * ChatGPT 账号分页查询参数。
 */
@Data
public class ChatGptAccountPageQueryDTO {

    /**
     * 页码，从 1 开始。
     */
    @Min(value = 1, message = "页码不能小于1")
    private Long current = 1L;

    /**
     * 每页条数。
     */
    @Min(value = 1, message = "每页条数不能小于1")
    @Max(value = 200, message = "每页条数不能超过200")
    private Long size = 10L;

    /**
     * 邮箱关键字（模糊搜索）。
     */
    @Size(max = 128, message = "邮箱关键字长度不能超过128")
    private String email;

    /**
     * 订阅层级过滤。
     */
    @Pattern(regexp = "free|plus|team|go", message = "订阅层级仅支持 free/plus/team/go")
    private String subTier;

    /**
     * 账号状态过滤。
     */
    @Pattern(regexp = "active|locked|banned", message = "账号状态仅支持 active/locked/banned")
    private String accountStatus;
}
