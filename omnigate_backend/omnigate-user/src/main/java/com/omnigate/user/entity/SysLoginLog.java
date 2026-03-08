package com.omnigate.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.handler.JsonbStringTypeHandler;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

/**
 * 系统登录日志实体。
 */
@Getter
@Setter
@TableName(value = "sys_login_log", autoResultMap = true)
public class SysLoginLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;

    private String loginAccount;

    private String loginType;

    private String clientIp;

    private String userAgent;

    /**
     * 登录状态：1-成功，0-失败。
     */
    private Integer loginStatus;

    private String failReason;

    private LocalDateTime loginAt;

    @TableField(typeHandler = JsonbStringTypeHandler.class)
    private String extInfo;
}
