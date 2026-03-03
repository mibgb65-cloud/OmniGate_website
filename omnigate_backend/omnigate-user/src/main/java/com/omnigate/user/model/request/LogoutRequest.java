package com.omnigate.user.model.request;

import lombok.Data;

/**
 * 登出请求体。
 */
@Data
public class LogoutRequest {

    /**
     * 可选：Refresh Token。
     */
    private String refreshToken;
}
