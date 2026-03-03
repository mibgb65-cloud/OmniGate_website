package com.omnigate.user.model.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 用户分页查询参数。
 */
@Data
public class UserPageQueryDTO {

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
     * 用户名模糊搜索关键字。
     */
    @Size(max = 64, message = "用户名关键字长度不能超过64")
    private String username;

    /**
     * 状态过滤：1-启用，0-禁用。
     */
    private Integer status;
}
