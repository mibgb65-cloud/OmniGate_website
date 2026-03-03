package com.omnigate.common.response;

import com.omnigate.common.error.BaseErrorInfo;
import com.omnigate.common.error.BizErrorCodeEnum;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serial;
import java.io.Serializable;

/**
 * 统一接口响应体。
 *
 * @param <T> 数据载荷类型
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Result<T> implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    private Integer code;
    private String message;
    private T data;

    /**
     * 返回成功响应（无数据）。
     *
     * @param <T> 数据载荷类型
     * @return 统一响应对象
     */
    public static <T> Result<T> success() {
        return success(null);
    }

    /**
     * 返回成功响应（携带数据）。
     *
     * @param data 返回数据
     * @param <T> 数据载荷类型
     * @return 统一响应对象
     */
    public static <T> Result<T> success(T data) {
        return new Result<>(BizErrorCodeEnum.SUCCESS.getCode(), BizErrorCodeEnum.SUCCESS.getMessage(), data);
    }

    /**
     * 返回成功响应（自定义提示信息）。
     *
     * @param message 提示信息
     * @param data 返回数据
     * @param <T> 数据载荷类型
     * @return 统一响应对象
     */
    public static <T> Result<T> success(String message, T data) {
        return new Result<>(BizErrorCodeEnum.SUCCESS.getCode(), message, data);
    }

    /**
     * 返回失败响应（使用标准错误码定义）。
     *
     * @param errorInfo 错误码定义
     * @param <T> 数据载荷类型
     * @return 统一响应对象
     */
    public static <T> Result<T> error(BaseErrorInfo errorInfo) {
        return new Result<>(errorInfo.getCode(), errorInfo.getMessage(), null);
    }

    /**
     * 返回失败响应（使用标准错误码 + 自定义提示信息）。
     *
     * @param errorInfo 错误码定义
     * @param message 自定义提示信息
     * @param <T> 数据载荷类型
     * @return 统一响应对象
     */
    public static <T> Result<T> error(BaseErrorInfo errorInfo, String message) {
        return new Result<>(errorInfo.getCode(), message, null);
    }

    /**
     * 返回失败响应（直接指定状态码和提示信息）。
     *
     * @param code 状态码
     * @param message 提示信息
     * @param <T> 数据载荷类型
     * @return 统一响应对象
     */
    public static <T> Result<T> error(Integer code, String message) {
        return new Result<>(code, message, null);
    }
}
