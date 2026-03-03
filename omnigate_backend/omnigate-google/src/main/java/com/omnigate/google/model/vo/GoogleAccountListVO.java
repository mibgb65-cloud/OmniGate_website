package com.omnigate.google.model.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * Google 账号列表视图对象。
 */
@Data
public class GoogleAccountListVO {

    /**
     * 账号 ID。
     */
    private Long id;

    /**
     * 邮箱。
     */
    private String email;

    /**
     * 账号密码。
     */
    private String password;

    /**
     * 辅助邮箱。
     */
    private String recoveryEmail;

    /**
     * 二次验证密钥。
     */
    private String totpSecret;

    /**
     * 地区。
     */
    private String region;

    /**
     * 备注。
     */
    private String remark;

    /**
     * 同步状态。
     */
    private Integer syncStatus;

    /**
     * 订阅类型。
     */
    private String subTier;

    /**
     * 家庭组状态：0-未开通，1-已开通。
     */
    private Integer familyStatus;

    /**
     * 到期日期。
     */
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate expireDate;

    /**
     * 邀请链接状态：0-无，1-有。
     */
    private Integer inviteLinkStatus;

    /**
     * 已邀请人数。
     */
    private Integer invitedCount;

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
}
