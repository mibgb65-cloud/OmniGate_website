package com.omnigate.chatgpt.model.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDate;

/**
 * ChatGPT 账号新增参数。
 */
@Data
public class ChatGptAccountCreateDTO {

    /**
     * 账号邮箱。
     */
    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    @Size(max = 128, message = "邮箱长度不能超过128")
    private String email;

    /**
     * 登录密码。
     */
    @NotBlank(message = "密码不能为空")
    @Size(max = 255, message = "密码长度不能超过255")
    private String password;

    /**
     * 会话 Token。
     */
    private String sessionToken;

    /**
     * 二次验证 TOTP 密钥。
     */
    @Size(max = 255, message = "TOTP密钥长度不能超过255")
    private String totpSecret;

    /**
     * 订阅层级：free, plus, team, go。
     */
    @Pattern(regexp = "free|plus|team|go", message = "订阅层级仅支持 free/plus/team/go")
    private String subTier;

    /**
     * 账号状态：active, locked, banned。
     */
    @Pattern(regexp = "active|locked|banned", message = "账号状态仅支持 active/locked/banned")
    private String accountStatus;

    /**
     * 是否已出售。
     */
    private Boolean sold;

    /**
     * 订阅到期日期。
     */
    private LocalDate expireDate;
}
