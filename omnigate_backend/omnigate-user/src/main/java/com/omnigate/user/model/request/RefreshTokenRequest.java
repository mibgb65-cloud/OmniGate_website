package com.omnigate.user.model.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 刷新 Token 请求体。
 */
@Data
public class RefreshTokenRequest {

    /**
     * Refresh Token。
     */
    @NotBlank(message = "RefreshToken 不能为空")
    private String refreshToken;
}
