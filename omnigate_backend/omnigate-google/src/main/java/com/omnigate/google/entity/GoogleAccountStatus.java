package com.omnigate.google.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDate;

/**
 * Google 账号状态实体。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("acc_google_status")
public class GoogleAccountStatus extends BaseEntity {

    /**
     * 账号 ID（主键且关联 acc_google_base.id）。
     */
    @TableId(type = IdType.INPUT)
    private Long accountId;

    /**
     * 订阅类型：NONE，AI_PLUS，AI_PRO，AI_ULTRA。
     */
    private String subTier;

    /**
     * 家庭组状态：0-未开通，1-已开通。
     */
    private Integer familyStatus;

    /**
     * 到期日期（年月日）。
     */
    private LocalDate expireDate;

    /**
     * 邀请链接状态：0-无，1-有。
     */
    private Integer inviteLinkStatus;

    /**
     * 学生认证链接。
     */
    private String studentLink;

    /**
     * 已邀请人数（最大 5）。
     */
    private Integer invitedCount;
}
