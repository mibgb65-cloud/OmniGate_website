package com.omnigate.common.error;

/**
 * 标准化错误码定义的基础契约。
 */
public interface BaseErrorInfo {

    /**
     * 获取错误码。
     *
     * @return 错误码
     */
    Integer getCode();

    /**
     * 获取错误提示信息。
     *
     * @return 错误提示
     */
    String getMessage();
}
