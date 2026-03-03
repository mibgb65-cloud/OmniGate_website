package com.omnigate.user.model.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 创建用户请求参数。
 */
@Data
public class UserCreateDTO {

    /**
     * 用户名。
     */
    @NotBlank(message = "用户名不能为空")
    @Size(max = 64, message = "用户名长度不能超过64")
    private String username;

    /**
     * 邮箱。
     */
    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    @Size(max = 128, message = "邮箱长度不能超过128")
    private String email;

    /**
     * 明文密码（服务端会进行加密存储）。
     */
    @NotBlank(message = "密码不能为空")
    @Size(min = 8, max = 64, message = "密码长度必须在8到64之间")
    private String password;

    /**
     * 昵称。
     */
    @Size(max = 64, message = "昵称长度不能超过64")
    private String nickname;

    /**
     * 头像地址。
     */
    @Size(max = 255, message = "头像地址长度不能超过255")
    private String avatarUrl;
}
