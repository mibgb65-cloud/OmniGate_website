package com.omnigate.chatgpt.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDate;

/**
 * ChatGPT Team 车队实体。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("acc_chatgpt_team")
public class ChatGptTeam extends BaseEntity {

    /**
     * 主键 ID。
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 团队名称。
     */
    private String teamName;

    /**
     * 车头账号 ID（关联 acc_chatgpt_base.id）。
     */
    private Long ownerId;

    /**
     * 最大成员数。
     */
    private Integer maxMembers;

    /**
     * 车队到期日期。
     */
    private LocalDate expireDate;
}
