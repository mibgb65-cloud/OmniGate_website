package com.omnigate.user.service;

import com.omnigate.user.model.response.AuthTokenResponse;

/**
 * 认证服务接口。
 */
public interface AuthService {

    /**
     * 登录并签发双 Token。
     *
     * @param loginAccount 登录账号（用户名或邮箱）
     * @param password 登录密码
     * @return Token 响应
     */
    AuthTokenResponse login(String loginAccount, String password);

    /**
     * 刷新 Access Token。
     *
     * @param refreshToken Refresh Token
     * @return Token 响应
     */
    AuthTokenResponse refresh(String refreshToken);

    /**
     * 登出并清理 Refresh Token。
     *
     * @param refreshToken 可选 Refresh Token
     */
    void logout(String refreshToken);
}
