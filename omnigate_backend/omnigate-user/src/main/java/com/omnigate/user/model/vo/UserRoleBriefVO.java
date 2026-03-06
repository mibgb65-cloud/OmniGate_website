package com.omnigate.user.model.vo;

import lombok.Data;

/**
 * 用户角色简要信息，用于批量填充分页列表中的角色展示。
 */
@Data
public class UserRoleBriefVO {

    /**
     * 用户 ID。
     */
    private Long userId;

    /**
     * 角色 ID。
     */
    private Long roleId;

    /**
     * 角色编码。
     */
    private String roleCode;

    /**
     * 角色名称。
     */
    private String roleName;
}
