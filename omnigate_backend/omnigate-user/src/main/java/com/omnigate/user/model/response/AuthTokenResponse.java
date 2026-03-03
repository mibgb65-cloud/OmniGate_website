package com.omnigate.user.model.response;

import lombok.Builder;
import lombok.Data;

/**
 * 认证成功后的 Token 响应体。
 */
@Data
@Builder
public class AuthTokenResponse {

    /**
     * Access Token。
     */
    private String accessToken;

    /**
     * Refresh Token。
     */
    private String refreshToken;

    /**
     * Token 类型，固定 Bearer。
     */
    private String tokenType;

    /**
     * Access Token 过期秒数。
     */
    private Long accessExpireSeconds;

    /**
     * Refresh Token 过期秒数。
     */
    private Long refreshExpireSeconds;
}
