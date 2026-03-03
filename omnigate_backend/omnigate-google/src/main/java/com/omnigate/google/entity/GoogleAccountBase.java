package com.omnigate.google.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import com.omnigate.common.handler.AesEncryptTypeHandler;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * Google 账号基础信息实体。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName(value = "acc_google_base", autoResultMap = true)
public class GoogleAccountBase extends BaseEntity {

    /**
     * 主键 ID。
     */
    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    /**
     * Google 账号邮箱（唯一）。
     */
    private String email;

    /**
     * 账号密码（加密后存储）。
     */
    @TableField(typeHandler = AesEncryptTypeHandler.class)
    private String password;

    /**
     * 辅助恢复邮箱。
     */
    private String recoveryEmail;

    /**
     * 二次验证 TOTP 密钥。
     */
    @TableField(typeHandler = AesEncryptTypeHandler.class)
    private String totpSecret;

    /**
     * 账号所属地区。
     */
    private String region;

    /**
     * 备注信息。
     */
    private String remark;

    /**
     * 同步状态：0-未开始，1-等待，2-处理中，3-成功，4-失败。
     */
    private Integer syncStatus;
}
