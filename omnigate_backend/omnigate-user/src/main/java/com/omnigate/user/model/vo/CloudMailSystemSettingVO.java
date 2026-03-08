package com.omnigate.user.model.vo;

import lombok.Data;

/**
 * CloudMail 系统配置视图对象。
 */
@Data
public class CloudMailSystemSettingVO {

    /**
     * CloudMail 登录账号（邮箱）。
     */
    private String accountEmail;

    /**
     * CloudMail 登录密码。
     */
    private String password;

    /**
     * CloudMail 登录网址。
     */
    private String authUrl;

    /**
     * ChatGPT 注册邮箱后缀。
     */
    private String registrationEmailSuffix;
}
