package com.omnigate.google.model.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.time.LocalDate;

/**
 * Google 家庭成员视图对象。
 */
@Data
public class GoogleFamilyMemberVO {

    /**
     * 主键 ID。
     */
    private Long id;

    /**
     * 账号 ID。
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
     * 邀请日期。
     */
    @JsonFormat(pattern = "yyyy-MM-dd")
    private LocalDate inviteDate;

    /**
     * 成员身份：1-管理员，2-成员。
     */
    private Integer memberRole;
}
