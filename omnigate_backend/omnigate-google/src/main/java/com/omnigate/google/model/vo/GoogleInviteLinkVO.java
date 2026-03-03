package com.omnigate.google.model.vo;

import lombok.Data;

/**
 * Google 邀请链接视图对象。
 */
@Data
public class GoogleInviteLinkVO {

    /**
     * 主键 ID。
     */
    private Long id;

    /**
     * 账号 ID。
     */
    private Long accountId;

    /**
     * 邀请链接。
     */
    private String inviteUrl;

    /**
     * 已使用次数。
     */
    private Integer usedCount;
}
