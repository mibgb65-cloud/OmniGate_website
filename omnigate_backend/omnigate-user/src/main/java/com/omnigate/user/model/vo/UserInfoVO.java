package com.omnigate.user.model.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 用户信息视图对象。
 */
@Data
public class UserInfoVO {

    /**
     * 用户 ID。
     */
    private Long id;

    /**
     * 用户名。
     */
    private String username;

    /**
     * 邮箱。
     */
    private String email;

    /**
     * 昵称。
     */
    private String nickname;

    /**
     * 头像地址。
     */
    private String avatarUrl;

    /**
     * 用户状态：1-启用，0-禁用。
     */
    private Integer status;

    /**
     * 最近登录 IP。
     */
    private String lastLoginIp;

    /**
     * 最近登录时间。
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime lastLoginAt;

    /**
     * 创建时间。
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createdAt;

    /**
     * 更新时间。
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime updatedAt;

    /**
     * 角色 ID 列表（详情接口可用）。
     */
    private List<Long> roleIds;

    /**
     * 角色编码列表（详情接口可用）。
     */
    private List<String> roleCodes;
}
