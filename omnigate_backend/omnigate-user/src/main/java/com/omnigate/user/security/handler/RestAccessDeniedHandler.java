package com.omnigate.user.security.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.response.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * 无权限访问统一响应处理器，返回标准 JSON 结构。
 */
@Component
public class RestAccessDeniedHandler implements AccessDeniedHandler {

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 处理已认证但权限不足场景。
     *
     * @param request 当前请求
     * @param response 当前响应
     * @param accessDeniedException 拒绝访问异常
     * @throws IOException IO 异常
     */
    @Override
    public void handle(HttpServletRequest request,
                       HttpServletResponse response,
                       AccessDeniedException accessDeniedException) throws IOException {
        Result<Void> result = Result.error(BizErrorCodeEnum.FORBIDDEN);

        response.setStatus(HttpServletResponse.SC_FORBIDDEN);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getWriter(), result);
    }
}
