package com.omnigate.github.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import com.omnigate.common.handler.AesEncryptTypeHandler;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * GitHub 账号基础信息实体。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName(value = "acc_github_base", autoResultMap = true)
public class GithubAccountBase extends BaseEntity {

    /**
     * 主键 ID。
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * GitHub 用户名。
     */
    private String username;

    /**
     * 绑定邮箱。
     */
    private String email;

    /**
     * 登录密码（加密存储）。
     */
    @TableField(typeHandler = AesEncryptTypeHandler.class)
    private String password;

    /**
     * 二次验证 TOTP 密钥（加密存储）。
     */
    @TableField(typeHandler = AesEncryptTypeHandler.class)
    private String totpSecret;

    /**
     * GitHub Personal Access Token（加密存储）。
     */
    @TableField(typeHandler = AesEncryptTypeHandler.class)
    private String accessToken;

    /**
     * Token 备注名称。
     */
    private String accessTokenNote;

    /**
     * 固定代理 IP。
     */
    private String proxyIp;

    /**
     * 账号状态：active, locked, banned。
     */
    private String accountStatus;
}
