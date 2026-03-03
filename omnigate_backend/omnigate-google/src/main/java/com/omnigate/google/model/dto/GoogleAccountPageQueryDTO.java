package com.omnigate.google.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * Google 账号分页查询参数。
 */
@Data
public class GoogleAccountPageQueryDTO {

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
     * 邮箱关键字。
     */
    @Size(max = 128, message = "邮箱关键字长度不能超过128")
    private String email;

    /**
     * 同步状态。
     */
    private Integer syncStatus;
}
