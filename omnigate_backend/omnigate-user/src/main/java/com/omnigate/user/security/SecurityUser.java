package com.omnigate.user.security;

import com.omnigate.user.entity.SysRole;
import com.omnigate.user.entity.SysUser;
import lombok.Getter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.io.Serial;
import java.util.Collection;
import java.util.List;
import java.util.Objects;

/**
 * Spring Security 用户主体对象。
 */
@Getter
public class SecurityUser implements UserDetails {

    @Serial
    private static final long serialVersionUID = 1L;

    private static final String ROLE_PREFIX = "ROLE_";

    private final SysUser sysUser;
    private final Collection<? extends GrantedAuthority> authorities;

    public SecurityUser(SysUser sysUser, List<SysRole> roles) {
        this.sysUser = sysUser;
        this.authorities = toAuthorities(roles);
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return authorities;
    }

    @Override
    public String getPassword() {
        return sysUser.getPasswordHash();
    }

    @Override
    public String getUsername() {
        return sysUser.getUsername();
    }

    @Override
    public boolean isAccountNonExpired() {
        return true;
    }

    @Override
    public boolean isAccountNonLocked() {
        return true;
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return true;
    }

    @Override
    public boolean isEnabled() {
        return Objects.equals(sysUser.getStatus(), 1);
    }

    /**
     * 将角色集合转换为 Spring Security 权限集合。
     *
     * @param roles 角色集合
     * @return 权限集合
     */
    private Collection<? extends GrantedAuthority> toAuthorities(List<SysRole> roles) {
        if (CollectionUtils.isEmpty(roles)) {
            return List.of();
        }
        return roles.stream()
                .map(SysRole::getRoleCode)
                .filter(StringUtils::hasText)
                .map(this::normalizeRoleCode)
                .map(SimpleGrantedAuthority::new)
                .distinct()
                .toList();
    }

    /**
     * 统一角色编码前缀，确保符合 Spring Security 角色规范。
     *
     * @param roleCode 原始角色编码
     * @return 规范化角色编码
     */
    private String normalizeRoleCode(String roleCode) {
        return roleCode.startsWith(ROLE_PREFIX) ? roleCode : ROLE_PREFIX + roleCode;
    }
}
