package com.omnigate.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

/**
 * 系统用户实体。
 */
@Getter
@Setter
@TableName("sys_user")
public class SysUser extends BaseEntity {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String username;

    private String email;

    private String passwordHash;

    private String nickname;

    private String avatarUrl;

    /**
     * 用户状态：1-正常，0-禁用。
     */
    private Integer status;

    private String lastLoginIp;

    private LocalDateTime lastLoginAt;

    private String extInfo;
}
