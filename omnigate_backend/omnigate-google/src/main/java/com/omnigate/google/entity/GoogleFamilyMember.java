package com.omnigate.google.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDate;

/**
 * Google 家庭组成员实体。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("acc_google_family_member")
public class GoogleFamilyMember extends BaseEntity {

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
     * 成员名称。
     */
    private String memberName;

    /**
     * 成员邮箱。
     */
    private String memberEmail;

    /**
     * 邀请日期（年月日）。
     */
    private LocalDate inviteDate;

    /**
     * 成员身份：1-管理员，2-成员。
     */
    private Integer memberRole;
}
