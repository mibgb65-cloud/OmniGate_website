package com.omnigate.github.model.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * GitHub 账号导入参数。
 */
@Data
public class GithubAccountImportDTO {

    /**
     * GitHub 用户名。
     */
    @NotBlank(message = "用户名不能为空")
    @Size(max = 128, message = "用户名长度不能超过128")
    private String username;

    /**
     * 绑定邮箱。
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
     * 二次验证密钥。
     */
    @NotBlank(message = "TOTP密钥不能为空")
    @Size(max = 255, message = "TOTP密钥长度不能超过255")
    private String totpSecret;

    /**
     * 代理 IP。
     */
    @Size(max = 64, message = "代理IP长度不能超过64")
    private String proxyIp;

    /**
     * 账号状态：active, locked, banned。
     */
    @Pattern(regexp = "active|locked|banned", message = "账号状态仅支持 active/locked/banned")
    private String accountStatus;
}
