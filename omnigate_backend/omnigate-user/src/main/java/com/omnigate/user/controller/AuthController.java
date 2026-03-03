package com.omnigate.user.controller;

import com.omnigate.common.response.Result;
import com.omnigate.user.model.request.LoginRequest;
import com.omnigate.user.model.request.LogoutRequest;
import com.omnigate.user.model.request.RefreshTokenRequest;
import com.omnigate.user.model.response.AuthTokenResponse;
import com.omnigate.user.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证控制器，提供登录、刷新和登出接口。
 */
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private static final String BEARER_PREFIX = "Bearer ";

    private final AuthService authService;

    /**
     * 账号密码登录并签发 Access/Refresh 双 Token。
     *
     * @param request 登录请求体
     * @return Token 响应
     */
    @PostMapping("/login")
    public Result<AuthTokenResponse> login(@Valid @RequestBody LoginRequest request) {
        AuthTokenResponse tokenResponse = authService.login(request.getLoginAccount(), request.getPassword());
        return Result.success(tokenResponse);
    }

    /**
     * 使用 Refresh Token 刷新 Access Token。
     *
     * @param request 刷新请求体
     * @return Token 响应
     */
    @PostMapping("/refresh")
    public Result<AuthTokenResponse> refresh(@Valid @RequestBody RefreshTokenRequest request) {
        AuthTokenResponse tokenResponse = authService.refresh(request.getRefreshToken());
        return Result.success(tokenResponse);
    }

    /**
     * 退出登录并删除 Redis 中的 Refresh Token。
     *
     * @param request 登出请求体（可选）
     * @param authorization Authorization 请求头（可选）
     * @return 成功响应
     */
    @PostMapping("/logout")
    public Result<Void> logout(@RequestBody(required = false) LogoutRequest request,
                               @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization) {
        String refreshToken = request == null ? null : request.getRefreshToken();
        if (!StringUtils.hasText(refreshToken)) {
            refreshToken = extractBearerToken(authorization);
        }
        authService.logout(refreshToken);
        return Result.success();
    }

    /**
     * 从 Authorization 请求头提取 Bearer Token。
     *
     * @param authorization Authorization 请求头值
     * @return Token 内容，不存在时返回 null
     */
    private String extractBearerToken(String authorization) {
        if (!StringUtils.hasText(authorization) || !authorization.startsWith(BEARER_PREFIX)) {
            return null;
        }
        return authorization.substring(BEARER_PREFIX.length()).trim();
    }
}
