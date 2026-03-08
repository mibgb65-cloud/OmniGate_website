package com.omnigate.user.model.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * CloudMail 系统配置更新请求。
 */
@Data
public class CloudMailSystemSettingUpdateDTO {

    /**
     * CloudMail 登录账号（邮箱）。
     */
    @NotBlank(message = "CloudMail 账号不能为空")
    @Email(message = "CloudMail 账号邮箱格式不正确")
    @Size(max = 255, message = "CloudMail 账号长度不能超过255")
    private String accountEmail;

    /**
     * CloudMail 登录密码。
     */
    @NotBlank(message = "CloudMail 密码不能为空")
    @Size(max = 255, message = "CloudMail 密码长度不能超过255")
    private String password;

    /**
     * CloudMail 登录网址。
     */
    @NotBlank(message = "CloudMail 登录网址不能为空")
    @Size(max = 512, message = "CloudMail 登录网址长度不能超过512")
    private String authUrl;

    /**
     * ChatGPT 注册邮箱后缀。
     */
    @NotBlank(message = "ChatGPT 注册邮箱后缀不能为空")
    @Size(max = 255, message = "ChatGPT 注册邮箱后缀长度不能超过255")
    private String registrationEmailSuffix;
}
