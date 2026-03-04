package com.omnigate.github.model.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * GitHub 账号基础信息更新参数。
 */
@Data
public class GithubAccountUpdateDTO {

    /**
     * 登录密码。
     */
    @Size(max = 255, message = "密码长度不能超过255")
    private String password;

    /**
     * 二次验证密钥。
     */
    @Size(max = 255, message = "TOTP密钥长度不能超过255")
    private String totpSecret;

    /**
     * 代理 IP。
     */
    @Size(max = 64, message = "代理IP长度不能超过64")
    private String proxyIp;
}
