package com.omnigate.google.model.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * Google 账号基础信息更新参数。
 */
@Data
public class GoogleAccountUpdateDTO {

    /**
     * 账号密码。
     */
    @Size(max = 255, message = "密码长度不能超过255")
    private String password;

    /**
     * 辅助邮箱。
     */
    @Email(message = "辅助邮箱格式不正确")
    @Size(max = 128, message = "辅助邮箱长度不能超过128")
    private String recoveryEmail;

    /**
     * 二次验证密钥。
     */
    @Size(max = 255, message = "TOTP密钥长度不能超过255")
    private String totpSecret;

    /**
     * 地区。
     */
    @Size(max = 64, message = "地区长度不能超过64")
    private String region;

    /**
     * 备注。
     */
    @Size(max = 255, message = "备注长度不能超过255")
    private String remark;
}
