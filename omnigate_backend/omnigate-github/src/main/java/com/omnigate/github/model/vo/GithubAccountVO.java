package com.omnigate.github.model.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * GitHub 账号视图对象。
 */
@Data
public class GithubAccountVO {

    /**
     * 主键 ID。
     */
    private Long id;

    /**
     * GitHub 用户名。
     */
    private String username;

    /**
     * 绑定邮箱。
     */
    private String email;

    /**
     * 登录密码。
     */
    private String password;

    /**
     * 二次验证 TOTP 密钥。
     */
    private String totpSecret;

    /**
     * 代理 IP。
     */
    private String proxyIp;

    /**
     * 账号状态。
     */
    private String accountStatus;

    /**
     * 创建时间。
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createdAt;

    /**
     * 更新时间。
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime updatedAt;
}
