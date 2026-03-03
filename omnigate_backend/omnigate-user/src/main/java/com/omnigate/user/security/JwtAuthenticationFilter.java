package com.omnigate.user.security;

import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * JWT 鉴权过滤器。
 * 仅对 Access Token 做本地验签，不访问 Redis 或数据库。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    /**
     * 请求中保存鉴权异常信息的属性名。
     */
    public static final String REQUEST_ATTRIBUTE_AUTH_ERROR = "jwt.auth.error";

    private static final String AUTHORIZATION_HEADER = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

    private final JwtUtils jwtUtils;

    /**
     * 放行登录、刷新、登出等认证开放接口。
     *
     * @param request 当前请求
     * @return true-不执行过滤，false-执行过滤
     */
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String uri = request.getRequestURI();
        if (HttpMethod.OPTIONS.matches(request.getMethod())) {
            return true;
        }
        return "/api/auth/login".equals(uri)
                || "/api/auth/refresh".equals(uri)
                || "/error".equals(uri);
    }

    /**
     * 从请求头读取 Access Token，验签成功后写入安全上下文。
     *
     * @param request 当前请求
     * @param response 当前响应
     * @param filterChain 过滤链
     * @throws ServletException Servlet 异常
     * @throws IOException IO 异常
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String accessToken = resolveAccessToken(request);
        if (StringUtils.hasText(accessToken)) {
            try {
                JwtUtils.AccessTokenClaims claims = jwtUtils.parseAccessToken(accessToken);
                if (claims.userId() != null && StringUtils.hasText(claims.username())) {
                    List<GrantedAuthority> authorities = claims.authorities()
                            .stream()
                            .filter(StringUtils::hasText)
                            .map(SimpleGrantedAuthority::new)
                            .map(GrantedAuthority.class::cast)
                            .toList();

                    JwtUserPrincipal principal = new JwtUserPrincipal(claims.userId(), claims.username(), authorities);
                    UsernamePasswordAuthenticationToken authentication =
                            UsernamePasswordAuthenticationToken.authenticated(principal, null, authorities);
                    authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    SecurityContextHolder.getContext().setAuthentication(authentication);
                }
            } catch (JwtException | IllegalArgumentException ex) {
                SecurityContextHolder.clearContext();
                request.setAttribute(REQUEST_ATTRIBUTE_AUTH_ERROR, "Access Token 无效或已过期");
                log.debug("Access Token 验签失败，path={}, message={}", request.getRequestURI(), ex.getMessage());
            }
        }
        filterChain.doFilter(request, response);
    }

    /**
     * 从 Authorization 请求头中提取 Bearer Token。
     *
     * @param request 当前请求
     * @return Access Token，不存在时返回 null
     */
    private String resolveAccessToken(HttpServletRequest request) {
        String authorization = request.getHeader(AUTHORIZATION_HEADER);
        if (!StringUtils.hasText(authorization) || !authorization.startsWith(BEARER_PREFIX)) {
            return null;
        }
        return authorization.substring(BEARER_PREFIX.length()).trim();
    }
}
