package com.omnigate.user.security;

import lombok.AllArgsConstructor;
import lombok.Getter;
import org.springframework.security.core.GrantedAuthority;

import java.io.Serial;
import java.io.Serializable;
import java.util.Collection;

/**
 * Access Token 验签成功后的上下文用户主体。
 */
@Getter
@AllArgsConstructor
public class JwtUserPrincipal implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    private final Long userId;
    private final String username;
    private final Collection<? extends GrantedAuthority> authorities;
}
