package com.omnigate.google.model.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * Google 家庭组邀请任务请求参数。
 */
@Data
public class GoogleInviteFamilyMemberTaskDTO {

    /**
     * 被邀请账号邮箱。
     */
    @NotBlank(message = "被邀请邮箱不能为空")
    @Email(message = "被邀请邮箱格式不正确")
    @Size(max = 128, message = "被邀请邮箱长度不能超过128")
    private String invitedAccountEmail;
}
