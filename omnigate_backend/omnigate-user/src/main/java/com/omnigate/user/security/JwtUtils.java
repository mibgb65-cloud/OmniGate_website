package com.omnigate.user.security;

import com.omnigate.user.config.JwtProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jws;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.util.Assert;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * JWT 工具类，负责 Token 的签发、解析与校验。
 */
@Component
@RequiredArgsConstructor
public class JwtUtils {

    private static final String CLAIM_USER_ID = "uid";
    private static final String CLAIM_AUTHORITIES = "authorities";
    private static final String CLAIM_TOKEN_TYPE = "tokenType";

    private static final String TOKEN_TYPE_ACCESS = "access";
    private static final String TOKEN_TYPE_REFRESH = "refresh";

    private final JwtProperties jwtProperties;

    /**
     * 生成 Access Token。
     *
     * @param userId 用户 ID
     * @param username 用户名
     * @param authorities 权限集合
     * @return Access Token
     */
    public String generateAccessToken(Long userId, String username, List<String> authorities) {
        Instant now = Instant.now();
        Instant expireAt = now.plus(Duration.ofMinutes(jwtProperties.getAccessExpireMinutes()));
        List<String> authorityList = CollectionUtils.isEmpty(authorities) ? List.of() : authorities;
        return Jwts.builder()
                .issuer(jwtProperties.getIssuer())
                .subject(username)
                .issuedAt(Date.from(now))
                .expiration(Date.from(expireAt))
                .claim(CLAIM_USER_ID, userId)
                .claim(CLAIM_AUTHORITIES, authorityList)
                .claim(CLAIM_TOKEN_TYPE, TOKEN_TYPE_ACCESS)
                .signWith(signingKey())
                .compact();
    }

    /**
     * 生成 Refresh Token。
     *
     * @param userId 用户 ID
     * @return Refresh Token
     */
    public String generateRefreshToken(Long userId) {
        Instant now = Instant.now();
        Instant expireAt = now.plus(Duration.ofDays(jwtProperties.getRefreshExpireDays()));
        return Jwts.builder()
                .issuer(jwtProperties.getIssuer())
                .subject(String.valueOf(userId))
                .issuedAt(Date.from(now))
                .expiration(Date.from(expireAt))
                .claim(CLAIM_USER_ID, userId)
                .claim(CLAIM_TOKEN_TYPE, TOKEN_TYPE_REFRESH)
                .signWith(signingKey())
                .compact();
    }

    /**
     * 解析并校验 Access Token。
     *
     * @param token Access Token
     * @return Access Token 声明
     */
    public AccessTokenClaims parseAccessToken(String token) {
        Claims claims = parseAndValidate(token);
        ensureTokenType(claims, TOKEN_TYPE_ACCESS);
        Long userId = claims.get(CLAIM_USER_ID, Long.class);
        String username = claims.getSubject();
        List<?> authorityList = claims.get(CLAIM_AUTHORITIES, List.class);
        List<String> authorities = authorityList == null
                ? List.of()
                : authorityList.stream().filter(Objects::nonNull).map(String::valueOf).toList();
        return new AccessTokenClaims(userId, username, authorities);
    }

    /**
     * 解析并校验 Refresh Token。
     *
     * @param token Refresh Token
     * @return Refresh Token 声明
     */
    public RefreshTokenClaims parseRefreshToken(String token) {
        Claims claims = parseAndValidate(token);
        ensureTokenType(claims, TOKEN_TYPE_REFRESH);
        Long userId = claims.get(CLAIM_USER_ID, Long.class);
        return new RefreshTokenClaims(userId);
    }

    /**
     * 校验 Token 是否有效（签名、格式、过期）。
     *
     * @param token JWT
     * @return true-有效，false-无效
     */
    public boolean validateToken(String token) {
        try {
            parseAndValidate(token);
            return true;
        } catch (JwtException | IllegalArgumentException ex) {
            return false;
        }
    }

    /**
     * 获取 Access Token 过期秒数。
     *
     * @return 过期秒数
     */
    public long accessTokenExpireSeconds() {
        return Duration.ofMinutes(jwtProperties.getAccessExpireMinutes()).toSeconds();
    }

    /**
     * 获取 Refresh Token 过期秒数。
     *
     * @return 过期秒数
     */
    public long refreshTokenExpireSeconds() {
        return Duration.ofDays(jwtProperties.getRefreshExpireDays()).toSeconds();
    }

    private Claims parseAndValidate(String token) {
        Assert.hasText(token, "JWT token 不能为空");
        Jws<Claims> claimsJws = Jwts.parser()
                .verifyWith(signingKey())
                .build()
                .parseSignedClaims(token);
        return claimsJws.getPayload();
    }

    private void ensureTokenType(Claims claims, String expectedType) {
        String tokenType = claims.get(CLAIM_TOKEN_TYPE, String.class);
        if (!StringUtils.hasText(tokenType) || !expectedType.equals(tokenType)) {
            throw new JwtException("Token 类型非法");
        }
    }

    private SecretKey signingKey() {
        Assert.hasText(jwtProperties.getSecret(), "JWT 密钥未配置");
        byte[] keyBytes = sha256(jwtProperties.getSecret());
        return Keys.hmacShaKeyFor(keyBytes);
    }

    private byte[] sha256(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return digest.digest(text.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("无法初始化 SHA-256 算法", ex);
        }
    }

    /**
     * Access Token 声明载荷。
     *
     * @param userId 用户 ID
     * @param username 用户名
     * @param authorities 权限集合
     */
    public record AccessTokenClaims(Long userId, String username, List<String> authorities) {
    }

    /**
     * Refresh Token 声明载荷。
     *
     * @param userId 用户 ID
     */
    public record RefreshTokenClaims(Long userId) {
    }
}
