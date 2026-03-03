package com.omnigate.user.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.omnigate.user.entity.SysRole;
import com.omnigate.user.entity.SysUser;
import com.omnigate.user.mapper.SysRoleMapper;
import com.omnigate.user.mapper.SysUserMapper;
import com.omnigate.user.security.SecurityUser;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.List;

/**
 * 自定义用户认证查询实现。
 */
@Service
@RequiredArgsConstructor
public class UserDetailsServiceImpl implements UserDetailsService {

    private final SysUserMapper sysUserMapper;
    private final SysRoleMapper sysRoleMapper;

    /**
     * 按登录账号加载用户，支持用户名或邮箱。
     *
     * @param loginAccount 登录账号
     * @return Security 用户主体
     * @throws UsernameNotFoundException 用户不存在时抛出
     */
    @Override
    public UserDetails loadUserByUsername(String loginAccount) throws UsernameNotFoundException {
        if (!StringUtils.hasText(loginAccount)) {
            throw new UsernameNotFoundException("登录账号不能为空");
        }

        LambdaQueryWrapper<SysUser> wrapper = Wrappers.lambdaQuery(SysUser.class)
                .eq(SysUser::getDeleted, 0)
                .and(query -> query.eq(SysUser::getUsername, loginAccount)
                        .or()
                        .eq(SysUser::getEmail, loginAccount))
                .last("LIMIT 1");

        SysUser sysUser = sysUserMapper.selectOne(wrapper);
        if (sysUser == null) {
            throw new UsernameNotFoundException("用户不存在");
        }

        List<SysRole> roles = sysRoleMapper.selectByUserId(sysUser.getId());
        return new SecurityUser(sysUser, roles);
    }
}
