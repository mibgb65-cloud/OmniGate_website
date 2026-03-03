package com.omnigate.common.error;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 通用业务与系统响应码定义。
 */
@Getter
@AllArgsConstructor
public enum BizErrorCodeEnum implements BaseErrorInfo {

    SUCCESS(200, "Success"),
    BAD_REQUEST(400, "Bad Request"),
    UNAUTHORIZED(401, "Unauthorized"),
    FORBIDDEN(403, "Forbidden"),
    INTERNAL_SERVER_ERROR(500, "Internal Server Error");

    private final Integer code;
    private final String message;
}
