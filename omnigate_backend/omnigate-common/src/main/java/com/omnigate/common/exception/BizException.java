package com.omnigate.common.exception;

import com.omnigate.common.error.BaseErrorInfo;
import lombok.Getter;

import java.io.Serial;

/**
 * 业务层运行时异常。
 */
@Getter
public class BizException extends RuntimeException {

    @Serial
    private static final long serialVersionUID = 1L;

    private final Integer code;

    /**
     * 通过标准错误码构造业务异常。
     *
     * @param errorInfo 错误码定义
     */
    public BizException(BaseErrorInfo errorInfo) {
        super(errorInfo.getMessage());
        this.code = errorInfo.getCode();
    }

    /**
     * 通过标准错误码和自定义消息构造业务异常。
     *
     * @param errorInfo 错误码定义
     * @param message 自定义异常消息
     */
    public BizException(BaseErrorInfo errorInfo, String message) {
        super(message);
        this.code = errorInfo.getCode();
    }

    /**
     * 通过状态码和消息构造业务异常。
     *
     * @param code 状态码
     * @param message 异常消息
     */
    public BizException(Integer code, String message) {
        super(message);
        this.code = code;
    }
}
