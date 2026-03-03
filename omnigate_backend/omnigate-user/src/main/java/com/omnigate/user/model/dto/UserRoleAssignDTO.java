package com.omnigate.user.model.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * 用户角色分配请求参数。
 */
@Data
public class UserRoleAssignDTO {

    /**
     * 角色 ID 列表。传空数组表示清空角色。
     */
    @NotNull(message = "角色ID列表不能为空")
    private List<Long> roleIds;
}
