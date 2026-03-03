package com.omnigate.user.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * JWT 配置项。
 */
@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "omnigate.security.jwt")
public class JwtProperties {

    /**
     * 签发方。
     */
    private String issuer = "omnigate";

    /**
     * Access Token 过期时间（分钟）。
     */
    private Long accessExpireMinutes = 30L;

    /**
     * Refresh Token 过期时间（天）。
     */
    private Long refreshExpireDays = 7L;

    /**
     * JWT 密钥。
     */
    private String secret;
}
