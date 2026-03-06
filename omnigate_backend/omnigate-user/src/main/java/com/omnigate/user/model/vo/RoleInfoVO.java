package com.omnigate.user.model.vo;

import lombok.Data;

/**
 * 角色信息视图对象。
 */
@Data
public class RoleInfoVO {

    /**
     * 角色 ID。
     */
    private Long id;

    /**
     * 角色编码。
     */
    private String roleCode;

    /**
     * 角色名称。
     */
    private String roleName;

    /**
     * 角色描述。
     */
    private String description;

    /**
     * 角色状态：1-启用，0-禁用。
     */
    private Integer status;

    /**
     * 排序值。
     */
    private Integer sort;
}
