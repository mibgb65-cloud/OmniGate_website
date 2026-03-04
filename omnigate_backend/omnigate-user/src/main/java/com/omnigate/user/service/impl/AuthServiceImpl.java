package com.omnigate.user.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import com.omnigate.user.entity.SysLoginLog;
import com.omnigate.user.entity.SysRole;
import com.omnigate.user.entity.SysUser;
import com.omnigate.user.mapper.SysLoginLogMapper;
import com.omnigate.user.mapper.SysRoleMapper;
import com.omnigate.user.mapper.SysUserMapper;
import com.omnigate.user.model.response.AuthTokenResponse;
import com.omnigate.user.security.JwtUserPrincipal;
import com.omnigate.user.security.JwtUtils;
import com.omnigate.user.security.SecurityUser;
import com.omnigate.user.service.AuthService;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.DisabledException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;

/**
 * 认证服务实现：负责登录签发、刷新与登出。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private static final String TOKEN_TYPE_BEARER = "Bearer";
    private static final String REFRESH_TOKEN_KEY_PREFIX = "auth:refresh:";
    private static final String ROLE_PREFIX = "ROLE_";
    private static final String LOGIN_TYPE_PASSWORD = "PASSWORD";
    private static final Integer LOGIN_STATUS_SUCCESS = 1;
    private static final Integer LOGIN_STATUS_FAIL = 0;
    private static final String UNKNOWN_LOGIN_ACCOUNT = "UNKNOWN";

    private final AuthenticationManager authenticationManager;
    private final JwtUtils jwtUtils;
    private final StringRedisTemplate stringRedisTemplate;
    private final SysUserMapper sysUserMapper;
    private final SysRoleMapper sysRoleMapper;
    private final SysLoginLogMapper sysLoginLogMapper;

    @Override
    public AuthTokenResponse login(String loginAccount, String password) {
        HttpServletRequest request = currentRequest();
        String clientIp = resolveClientIp(request);
        String userAgent = resolveUserAgent(request);

        Authentication authentication;
        try {
            authentication = authenticationManager.authenticate(
                    UsernamePasswordAuthenticationToken.unauthenticated(loginAccount, password)
            );
        } catch (DisabledException ex) {
            log.warn("用户账号已被禁用，loginAccount={}", loginAccount);
            saveLoginLog(findUserIdByLoginAccount(loginAccount), loginAccount, clientIp, userAgent, LOGIN_STATUS_FAIL, "用户已被禁用");
            throw new BizException(BizErrorCodeEnum.FORBIDDEN, "用户已被禁用");
        } catch (AuthenticationException ex) {
            log.warn("登录认证失败，loginAccount={}, message={}", loginAccount, ex.getMessage());
            saveLoginLog(findUserIdByLoginAccount(loginAccount), loginAccount, clientIp, userAgent, LOGIN_STATUS_FAIL, "账号或密码错误");
            throw new BizException(BizErrorCodeEnum.UNAUTHORIZED, "账号或密码错误");
        }

        SecurityUser securityUser = (SecurityUser) authentication.getPrincipal();
        Long userId = securityUser.getSysUser().getId();
        List<String> authorities = securityUser.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .toList();

        String accessToken = jwtUtils.generateAccessToken(userId, securityUser.getUsername(), authorities);
        String refreshToken = jwtUtils.generateRefreshToken(userId);

        cacheRefreshToken(userId, refreshToken);
        updateUserLoginTrace(userId, clientIp);
        saveLoginLog(userId, loginAccount, clientIp, userAgent, LOGIN_STATUS_SUCCESS, null);
        log.info("用户登录成功并签发 Token，userId={}", userId);

        return buildTokenResponse(accessToken, refreshToken);
    }

    @Override
    public AuthTokenResponse refresh(String refreshToken) {
        JwtUtils.RefreshTokenClaims claims = parseRefreshTokenSafely(refreshToken);
        Long userId = claims.userId();
        if (userId == null) {
            throw new BizException(BizErrorCodeEnum.UNAUTHORIZED, "刷新凭证非法，请重新登录");
        }

        String cacheKey = refreshTokenCacheKey(userId);
        String cachedToken = stringRedisTemplate.opsForValue().get(cacheKey);
        if (!StringUtils.hasText(cachedToken) || !cachedToken.equals(refreshToken)) {
            throw new BizException(BizErrorCodeEnum.UNAUTHORIZED, "登录状态已失效，请重新登录");
        }

        SysUser sysUser = sysUserMapper.selectById(userId);
        if (sysUser == null) {
            throw new BizException(BizErrorCodeEnum.UNAUTHORIZED, "用户不存在，请重新登录");
        }
        if (!Objects.equals(sysUser.getStatus(), 1)) {
            throw new BizException(BizErrorCodeEnum.FORBIDDEN, "用户已被禁用");
        }

        List<String> authorities = sysRoleMapper.selectByUserId(userId).stream()
                .map(SysRole::getRoleCode)
                .filter(StringUtils::hasText)
                .map(this::normalizeRoleCode)
                .distinct()
                .toList();

        String accessToken = jwtUtils.generateAccessToken(userId, sysUser.getUsername(), authorities);
        log.info("刷新 AccessToken 成功，userId={}", userId);

        return buildTokenResponse(accessToken, refreshToken);
    }

    @Override
    public void logout(String refreshToken) {
        Long userId = resolveLogoutUserIdSafely(refreshToken);
        if (userId == null) {
            throw new BizException(BizErrorCodeEnum.UNAUTHORIZED, "未获取到有效用户信息，请重新登录");
        }
        stringRedisTemplate.delete(refreshTokenCacheKey(userId));
        SecurityContextHolder.clearContext();
        log.info("用户登出成功，userId={}", userId);
    }

    private AuthTokenResponse buildTokenResponse(String accessToken, String refreshToken) {
        return AuthTokenResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .tokenType(TOKEN_TYPE_BEARER)
                .accessExpireSeconds(jwtUtils.accessTokenExpireSeconds())
                .refreshExpireSeconds(jwtUtils.refreshTokenExpireSeconds())
                .build();
    }

    private void cacheRefreshToken(Long userId, String refreshToken) {
        String cacheKey = refreshTokenCacheKey(userId);
        Duration ttl = Duration.ofSeconds(jwtUtils.refreshTokenExpireSeconds());
        stringRedisTemplate.opsForValue().set(cacheKey, refreshToken, ttl);
    }

    private String refreshTokenCacheKey(Long userId) {
        return REFRESH_TOKEN_KEY_PREFIX + userId;
    }

    private String normalizeRoleCode(String roleCode) {
        return roleCode.startsWith(ROLE_PREFIX) ? roleCode : ROLE_PREFIX + roleCode;
    }

    private void updateUserLoginTrace(Long userId, String clientIp) {
        SysUser updateEntity = new SysUser();
        updateEntity.setId(userId);
        updateEntity.setLastLoginIp(clientIp);
        updateEntity.setLastLoginAt(LocalDateTime.now());
        int updatedRows = sysUserMapper.updateById(updateEntity);
        if (updatedRows <= 0) {
            log.warn("更新用户最后登录信息失败，userId={}", userId);
        }
    }

    private void saveLoginLog(Long userId,
                              String loginAccount,
                              String clientIp,
                              String userAgent,
                              Integer loginStatus,
                              String failReason) {
        SysLoginLog loginLog = new SysLoginLog();
        loginLog.setUserId(userId);
        loginLog.setLoginAccount(safeLoginAccount(loginAccount));
        loginLog.setLoginType(LOGIN_TYPE_PASSWORD);
        loginLog.setClientIp(clientIp);
        loginLog.setUserAgent(userAgent);
        loginLog.setLoginStatus(loginStatus);
        loginLog.setFailReason(failReason);
        loginLog.setLoginAt(LocalDateTime.now());
        sysLoginLogMapper.insert(loginLog);
    }

    private Long findUserIdByLoginAccount(String loginAccount) {
        if (!StringUtils.hasText(loginAccount)) {
            return null;
        }
        String normalizedAccount = loginAccount.trim();
        LambdaQueryWrapper<SysUser> queryWrapper = Wrappers.lambdaQuery(SysUser.class)
                .eq(SysUser::getDeleted, 0)
                .and(query -> query.eq(SysUser::getUsername, normalizedAccount)
                        .or()
                        .eq(SysUser::getEmail, normalizedAccount))
                .last("LIMIT 1");
        SysUser user = sysUserMapper.selectOne(queryWrapper);
        return user == null ? null : user.getId();
    }

    private String safeLoginAccount(String loginAccount) {
        if (!StringUtils.hasText(loginAccount)) {
            return UNKNOWN_LOGIN_ACCOUNT;
        }
        return loginAccount.trim();
    }

    private HttpServletRequest currentRequest() {
        RequestAttributes attributes = RequestContextHolder.getRequestAttributes();
        if (attributes instanceof ServletRequestAttributes servletRequestAttributes) {
            return servletRequestAttributes.getRequest();
        }
        return null;
    }

    private String resolveUserAgent(HttpServletRequest request) {
        if (request == null) {
            return null;
        }
        return request.getHeader("User-Agent");
    }

    private String resolveClientIp(HttpServletRequest request) {
        if (request == null) {
            return null;
        }
        String forwardedFor = request.getHeader("X-Forwarded-For");
        if (StringUtils.hasText(forwardedFor)) {
            return forwardedFor.split(",")[0].trim();
        }

        String realIp = request.getHeader("X-Real-IP");
        if (StringUtils.hasText(realIp)) {
            return realIp.trim();
        }
        return request.getRemoteAddr();
    }

    /**
     * 解析并校验 RefreshToken，统一转换为业务异常。
     *
     * @param refreshToken RefreshToken
     * @return RefreshToken 声明
     */
    private JwtUtils.RefreshTokenClaims parseRefreshTokenSafely(String refreshToken) {
        if (!StringUtils.hasText(refreshToken)) {
            throw new BizException(BizErrorCodeEnum.UNAUTHORIZED, "RefreshToken 不能为空");
        }
        try {
            return jwtUtils.parseRefreshToken(refreshToken);
        } catch (JwtException | IllegalArgumentException ex) {
            log.warn("RefreshToken 验签失败，message={}", ex.getMessage());
            throw new BizException(BizErrorCodeEnum.UNAUTHORIZED, "登录状态已失效，请重新登录");
        }
    }

    /**
     * 登出时解析用户 ID，优先使用 RefreshToken，其次回退到安全上下文。
     *
     * @param refreshToken RefreshToken
     * @return 用户 ID，不存在时返回 null
     */
    private Long resolveLogoutUserIdSafely(String refreshToken) {
        if (StringUtils.hasText(refreshToken)) {
            try {
                return parseRefreshTokenSafely(refreshToken).userId();
            } catch (BizException ex) {
                log.debug("按 RefreshToken 解析登出用户失败，尝试回退安全上下文，message={}", ex.getMessage());
            }
        }

        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null) {
            return null;
        }

        Object principal = authentication.getPrincipal();
        if (principal instanceof JwtUserPrincipal jwtUserPrincipal) {
            return jwtUserPrincipal.getUserId();
        }
        if (principal instanceof SecurityUser securityUser) {
            return securityUser.getSysUser().getId();
        }
        return null;
    }
}
