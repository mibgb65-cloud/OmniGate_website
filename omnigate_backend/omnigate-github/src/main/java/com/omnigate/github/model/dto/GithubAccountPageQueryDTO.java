package com.omnigate.github.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * GitHub 账号分页查询参数。
 */
@Data
public class GithubAccountPageQueryDTO {

    /**
     * 页码，从 1 开始。
     */
    @Min(value = 1, message = "页码不能小于1")
    private Long current = 1L;

    /**
     * 每页条数。
     */
    @Min(value = 1, message = "每页条数不能小于1")
    @Max(value = 200, message = "每页条数不能超过200")
    private Long size = 10L;

    /**
     * 用户名关键字（模糊搜索）。
     */
    @Size(max = 128, message = "用户名关键字长度不能超过128")
    private String username;

    /**
     * 账号状态过滤。
     */
    @Pattern(regexp = "active|locked|banned", message = "账号状态仅支持 active/locked/banned")
    private String accountStatus;

    /**
     * 代理 IP 精确过滤。
     */
    @Size(max = 64, message = "代理IP长度不能超过64")
    private String proxyIp;
}
