package com.omnigate.user.model.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 登录请求体。
 */
@Data
public class LoginRequest {

    /**
     * 登录账号（用户名或邮箱）。
     */
    @NotBlank(message = "登录账号不能为空")
    private String loginAccount;

    /**
     * 登录密码。
     */
    @NotBlank(message = "登录密码不能为空")
    private String password;
}
