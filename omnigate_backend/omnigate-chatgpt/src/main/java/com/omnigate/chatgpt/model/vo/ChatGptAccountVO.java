package com.omnigate.chatgpt.model.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * ChatGPT 账号视图对象。
 */
@Data
public class ChatGptAccountVO {

    /**
     * 主键 ID。
     */
    private Long id;

    /**
     * 账号邮箱。
     */
    private String email;

    /**
     * 登录密码。
     */
    private String password;

    /**
     * 会话 Token。
     */
    private String sessionToken;

    /**
     * 二次验证 TOTP 密钥。
     */
    private String totpSecret;

    /**
     * 订阅层级。
     */
    private String subTier;

    /**
     * 账号状态。
     */
    private String accountStatus;

    /**
     * 是否已出售。
     */
    private Boolean sold;

    /**
     * 订阅到期日期。
     */
    private LocalDate expireDate;

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
