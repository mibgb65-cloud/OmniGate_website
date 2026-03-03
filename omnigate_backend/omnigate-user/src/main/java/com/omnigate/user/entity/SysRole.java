package com.omnigate.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import lombok.Getter;
import lombok.Setter;

/**
 * 系统角色实体。
 */
@Getter
@Setter
@TableName("sys_role")
public class SysRole extends BaseEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String roleCode;

    private String roleName;

    private String description;

    /**
     * 角色状态：1-正常，0-禁用。
     */
    private Integer status;

    private Integer sort;

    private String extInfo;
}
