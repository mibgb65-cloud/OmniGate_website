package com.omnigate.user.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 管理员修改用户密码请求参数。
 */
@Data
public class UserPasswordUpdateDTO {

    /**
     * 新密码明文，服务端会进行加密存储。
     */
    @NotBlank(message = "密码不能为空")
    @Size(min = 8, max = 64, message = "密码长度必须在8到64之间")
    private String password;
}
