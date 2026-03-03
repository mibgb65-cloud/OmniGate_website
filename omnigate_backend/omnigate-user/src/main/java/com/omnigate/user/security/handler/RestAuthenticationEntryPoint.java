package com.omnigate.user.security.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.response.Result;
import com.omnigate.user.security.JwtAuthenticationFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * 认证失败统一响应处理器，返回标准 JSON 结构。
 */
@Component
public class RestAuthenticationEntryPoint implements AuthenticationEntryPoint {

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 处理未认证或 Token 无效场景。
     *
     * @param request 当前请求
     * @param response 当前响应
     * @param authException 认证异常
     * @throws IOException IO 异常
     */
    @Override
    public void commence(HttpServletRequest request,
                         HttpServletResponse response,
                         AuthenticationException authException) throws IOException {
        String message = resolveMessage(request);
        Result<Void> result = Result.error(BizErrorCodeEnum.UNAUTHORIZED.getCode(), message);

        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getWriter(), result);
    }

    /**
     * 解析认证失败提示信息。
     *
     * @param request 当前请求
     * @return 认证失败提示
     */
    private String resolveMessage(HttpServletRequest request) {
        Object authError = request.getAttribute(JwtAuthenticationFilter.REQUEST_ATTRIBUTE_AUTH_ERROR);
        if (authError instanceof String message && StringUtils.hasText(message)) {
            return message;
        }
        return BizErrorCodeEnum.UNAUTHORIZED.getMessage();
    }
}
