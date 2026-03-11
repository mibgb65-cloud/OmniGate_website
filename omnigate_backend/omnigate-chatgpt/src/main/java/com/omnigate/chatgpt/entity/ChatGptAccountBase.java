package com.omnigate.chatgpt.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import com.omnigate.common.handler.AesEncryptTypeHandler;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDate;

/**
 * ChatGPT 账号基础信息实体。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName(value = "acc_chatgpt_base", autoResultMap = true)
public class ChatGptAccountBase extends BaseEntity {

    /**
     * 主键 ID。
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 账号邮箱（唯一）。
     */
    private String email;

    /**
     * 登录密码（加密存储）。
     */
    @TableField(typeHandler = AesEncryptTypeHandler.class)
    private String password;

    /**
     * 持久化登录 Token（加密存储）。
     */
    @TableField(typeHandler = AesEncryptTypeHandler.class)
    private String sessionToken;

    /**
     * 二次验证 TOTP 密钥（加密存储）。
     */
    @TableField(typeHandler = AesEncryptTypeHandler.class)
    private String totpSecret;

    /**
     * 订阅层级：free, plus, team, go。
     */
    private String subTier;

    /**
     * 账号状态：active, locked, banned。
     */
    private String accountStatus;

    /**
     * 是否已出售。
     */
    @TableField("is_sold")
    private Boolean sold;

    /**
     * 订阅到期日期。
     */
    private LocalDate expireDate;
}
