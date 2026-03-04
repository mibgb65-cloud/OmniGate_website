package com.omnigate.google.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * Google 邀请链接实体（4个月免费链接）。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("acc_google_invite_link")
public class GoogleInviteLink extends BaseEntity {

    /**
     * 主键 ID。
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 账号 ID（关联 acc_google_base.id）。
     */
    private Long accountId;

    /**
     * 邀请链接 URL。
     */
    private String inviteUrl;

    /**
     * 已使用次数。
     */
    private Integer usedCount;
}
