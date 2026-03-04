package com.omnigate.chatgpt.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

/**
 * ChatGPT Team 成员关联实体。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("acc_chatgpt_team_member")
public class ChatGptTeamMember extends BaseEntity {

    /**
     * 主键 ID。
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 车队 ID（关联 acc_chatgpt_team.id）。
     */
    private Long teamId;

    /**
     * 成员账号 ID（关联 acc_chatgpt_base.id）。
     */
    private Long memberId;

    /**
     * 成员角色：owner, member。
     */
    private String memberRole;

    /**
     * 加入时间。
     */
    private LocalDateTime joinTime;
}
