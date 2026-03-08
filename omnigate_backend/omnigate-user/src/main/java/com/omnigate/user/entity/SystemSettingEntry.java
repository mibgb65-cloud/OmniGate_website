package com.omnigate.user.entity;

import lombok.Data;

/**
 * 系统配置表记录。
 */
@Data
public class SystemSettingEntry {

    /**
     * 配置键。
     */
    private String key;

    /**
     * 配置值。
     */
    private String value;

    /**
     * 配置说明。
     */
    private String description;
}
