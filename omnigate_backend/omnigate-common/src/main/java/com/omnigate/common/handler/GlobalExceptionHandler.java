package com.omnigate.common.handler;

import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import com.omnigate.common.response.Result;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

/**
 * 全局异常处理器，统一转换 MVC 接口异常响应。
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * 处理业务异常。
     *
     * @param ex 业务异常
     * @param request 当前请求
     * @return 统一响应对象
     */
    @ExceptionHandler(BizException.class)
    public Result<Void> handleBizException(BizException ex, HttpServletRequest request) {
        log.warn("Business exception, path={}, code={}, message={}", request.getRequestURI(), ex.getCode(), ex.getMessage());
        return Result.error(ex.getCode(), ex.getMessage());
    }

    /**
     * 处理参数校验异常。
     *
     * @param ex 参数校验异常
     * @param request 当前请求
     * @return 统一响应对象
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleMethodArgumentNotValidException(MethodArgumentNotValidException ex, HttpServletRequest request) {
        String message = ex.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(this::buildFieldErrorMessage)
                .collect(Collectors.joining("; "));

        if (message.isBlank()) {
            message = BizErrorCodeEnum.BAD_REQUEST.getMessage();
        }

        log.warn("Validation exception, path={}, message={}", request.getRequestURI(), message);
        return Result.error(BizErrorCodeEnum.BAD_REQUEST.getCode(), message);
    }

    /**
     * 处理未捕获的系统异常。
     *
     * @param ex 系统异常
     * @param request 当前请求
     * @return 统一响应对象
     */
    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception ex, HttpServletRequest request) {
        log.error("Unhandled exception, path={}", request.getRequestURI(), ex);
        return Result.error(BizErrorCodeEnum.INTERNAL_SERVER_ERROR);
    }

    /**
     * 组装字段级校验错误信息。
     *
     * @param fieldError 字段错误
     * @return 错误描述
     */
    private String buildFieldErrorMessage(FieldError fieldError) {
        String defaultMessage = fieldError.getDefaultMessage() == null ? "invalid" : fieldError.getDefaultMessage();
        return fieldError.getField() + ": " + defaultMessage;
    }
}
