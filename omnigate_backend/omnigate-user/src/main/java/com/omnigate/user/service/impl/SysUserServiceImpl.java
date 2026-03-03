package com.omnigate.user.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import com.omnigate.user.entity.SysRole;
import com.omnigate.user.entity.SysUser;
import com.omnigate.user.mapper.SysRoleMapper;
import com.omnigate.user.mapper.SysUserMapper;
import com.omnigate.user.mapper.SysUserRoleMapper;
import com.omnigate.user.model.dto.UserCreateDTO;
import com.omnigate.user.model.dto.UserPageQueryDTO;
import com.omnigate.user.model.dto.UserRoleAssignDTO;
import com.omnigate.user.model.dto.UserUpdateDTO;
import com.omnigate.user.model.vo.UserInfoVO;
import com.omnigate.user.service.SysUserService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;

/**
 * 系统用户管理服务实现。
 */
@Service
@RequiredArgsConstructor
public class SysUserServiceImpl extends ServiceImpl<SysUserMapper, SysUser> implements SysUserService {

    private final PasswordEncoder passwordEncoder;
    private final SysRoleMapper sysRoleMapper;
    private final SysUserRoleMapper sysUserRoleMapper;

    /**
     * 分页查询用户，支持用户名模糊匹配与状态过滤。
     *
     * @param queryDTO 分页查询参数
     * @return 用户分页结果
     */
    @Override
    public IPage<UserInfoVO> pageUsers(UserPageQueryDTO queryDTO) {
        String usernameKeyword = normalizeText(queryDTO.getUsername());
        LambdaQueryWrapper<SysUser> countWrapper = Wrappers.lambdaQuery(SysUser.class)
                .like(StringUtils.hasText(usernameKeyword), SysUser::getUsername, usernameKeyword)
                .eq(queryDTO.getStatus() != null, SysUser::getStatus, queryDTO.getStatus())
                .orderByDesc(SysUser::getCreatedAt);
        long total = baseMapper.selectCount(countWrapper);

        long current = queryDTO.getCurrent();
        long size = queryDTO.getSize();
        long offset = (current - 1) * size;

        LambdaQueryWrapper<SysUser> listWrapper = Wrappers.lambdaQuery(SysUser.class)
                .like(StringUtils.hasText(usernameKeyword), SysUser::getUsername, usernameKeyword)
                .eq(queryDTO.getStatus() != null, SysUser::getStatus, queryDTO.getStatus())
                .orderByDesc(SysUser::getCreatedAt)
                .last("LIMIT " + size + " OFFSET " + offset);
        List<SysUser> users = baseMapper.selectList(listWrapper);

        Page<UserInfoVO> result = new Page<>(current, size, total);
        result.setRecords(users.stream().map(this::toUserInfoVO).toList());
        return result;
    }

    /**
     * 查询用户详情并附带角色信息。
     *
     * @param userId 用户 ID
     * @return 用户详情
     */
    @Override
    public UserInfoVO getUserInfo(Long userId) {
        SysUser sysUser = getRequiredUser(userId);
        UserInfoVO userInfoVO = toUserInfoVO(sysUser);
        fillRoleInfo(userInfoVO, userId);
        return userInfoVO;
    }

    /**
     * 新增用户并完成密码加密存储。
     *
     * @param createDTO 创建参数
     * @return 新增后的用户信息
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserInfoVO createUser(UserCreateDTO createDTO) {
        String username = normalizeText(createDTO.getUsername());
        String email = normalizeText(createDTO.getEmail());
        assertUsernameUnique(username, null);
        assertEmailUnique(email, null);

        SysUser sysUser = new SysUser();
        sysUser.setUsername(username);
        sysUser.setEmail(email);
        sysUser.setPasswordHash(passwordEncoder.encode(createDTO.getPassword()));
        sysUser.setNickname(normalizeText(createDTO.getNickname()));
        sysUser.setAvatarUrl(normalizeText(createDTO.getAvatarUrl()));
        sysUser.setStatus(1);

        boolean saved = save(sysUser);
        if (!saved) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "新增用户失败");
        }
        return toUserInfoVO(sysUser);
    }

    /**
     * 更新用户基础信息（不含密码）。
     *
     * @param userId 用户 ID
     * @param updateDTO 更新参数
     * @return 更新后的用户信息
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserInfoVO updateUser(Long userId, UserUpdateDTO updateDTO) {
        SysUser sysUser = getRequiredUser(userId);
        String username = normalizeText(updateDTO.getUsername());
        String email = normalizeText(updateDTO.getEmail());

        assertUsernameUnique(username, userId);
        assertEmailUnique(email, userId);

        sysUser.setUsername(username);
        sysUser.setEmail(email);
        sysUser.setNickname(normalizeText(updateDTO.getNickname()));
        sysUser.setAvatarUrl(normalizeText(updateDTO.getAvatarUrl()));

        boolean updated = updateById(sysUser);
        if (!updated) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新用户失败");
        }
        return getUserInfo(userId);
    }

    /**
     * 更新用户启用状态。
     *
     * @param userId 用户 ID
     * @param status 状态：1-启用，0-禁用
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateStatus(Long userId, Integer status) {
        if (!Objects.equals(status, 1) && !Objects.equals(status, 0)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "状态值非法，仅支持 0 或 1");
        }

        SysUser sysUser = getRequiredUser(userId);
        sysUser.setStatus(status);
        boolean updated = updateById(sysUser);
        if (!updated) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新用户状态失败");
        }
    }

    /**
     * 先清理用户原有角色，再批量写入新角色关联。
     *
     * @param userId 用户 ID
     * @param assignDTO 角色分配参数
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void assignRoles(Long userId, UserRoleAssignDTO assignDTO) {
        getRequiredUser(userId);

        List<Long> roleIds = assignDTO.getRoleIds();
        if (roleIds == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "角色ID列表不能为空");
        }
        if (roleIds.stream().anyMatch(Objects::isNull)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "角色ID列表不能包含空值");
        }

        List<Long> distinctRoleIds = new LinkedHashSet<>(roleIds).stream().toList();
        if (!distinctRoleIds.isEmpty()) {
            assertAllRolesValid(distinctRoleIds);
        }

        sysUserRoleMapper.logicalDeleteByUserId(userId);
        if (!distinctRoleIds.isEmpty()) {
            sysUserRoleMapper.batchInsert(userId, distinctRoleIds);
        }
    }

    /**
     * 逻辑删除用户，并清理其角色关联关系。
     *
     * @param userId 用户 ID
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void removeUser(Long userId) {
        getRequiredUser(userId);
        boolean removed = removeById(userId);
        if (!removed) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "删除用户失败");
        }
        sysUserRoleMapper.logicalDeleteByUserId(userId);
    }

    /**
     * 按 ID 加载用户，不存在时抛出业务异常。
     *
     * @param userId 用户 ID
     * @return 用户实体
     */
    private SysUser getRequiredUser(Long userId) {
        SysUser sysUser = getById(userId);
        if (sysUser == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "用户不存在");
        }
        return sysUser;
    }

    /**
     * 校验用户名唯一性。
     *
     * @param username 用户名
     * @param excludeUserId 排除的用户 ID
     */
    private void assertUsernameUnique(String username, Long excludeUserId) {
        long count = lambdaQuery()
                .eq(SysUser::getUsername, username)
                .ne(excludeUserId != null, SysUser::getId, excludeUserId)
                .count();
        if (count > 0) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "用户名已存在");
        }
    }

    /**
     * 校验邮箱唯一性。
     *
     * @param email 邮箱
     * @param excludeUserId 排除的用户 ID
     */
    private void assertEmailUnique(String email, Long excludeUserId) {
        long count = lambdaQuery()
                .eq(SysUser::getEmail, email)
                .ne(excludeUserId != null, SysUser::getId, excludeUserId)
                .count();
        if (count > 0) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "邮箱已存在");
        }
    }

    /**
     * 校验角色是否全部存在且为启用状态。
     *
     * @param roleIds 角色 ID 列表
     */
    private void assertAllRolesValid(List<Long> roleIds) {
        List<SysRole> roles = sysRoleMapper.selectBatchIds(roleIds)
                .stream()
                .filter(role -> Objects.equals(role.getStatus(), 1))
                .toList();
        if (roles.size() != roleIds.size()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "角色不存在或已禁用");
        }
    }

    /**
     * 为用户视图对象填充角色信息。
     *
     * @param userInfoVO 用户视图对象
     * @param userId 用户 ID
     */
    private void fillRoleInfo(UserInfoVO userInfoVO, Long userId) {
        List<SysRole> roles = sysRoleMapper.selectByUserId(userId);
        userInfoVO.setRoleIds(roles.stream().map(SysRole::getId).toList());
        userInfoVO.setRoleCodes(roles.stream().map(SysRole::getRoleCode).toList());
    }

    /**
     * 实体转用户视图对象。
     *
     * @param sysUser 用户实体
     * @return 用户视图对象
     */
    private UserInfoVO toUserInfoVO(SysUser sysUser) {
        UserInfoVO userInfoVO = new UserInfoVO();
        userInfoVO.setId(sysUser.getId());
        userInfoVO.setUsername(sysUser.getUsername());
        userInfoVO.setEmail(sysUser.getEmail());
        userInfoVO.setNickname(sysUser.getNickname());
        userInfoVO.setAvatarUrl(sysUser.getAvatarUrl());
        userInfoVO.setStatus(sysUser.getStatus());
        userInfoVO.setLastLoginIp(sysUser.getLastLoginIp());
        userInfoVO.setLastLoginAt(sysUser.getLastLoginAt());
        userInfoVO.setCreatedAt(sysUser.getCreatedAt());
        userInfoVO.setUpdatedAt(sysUser.getUpdatedAt());
        return userInfoVO;
    }

    /**
     * 统一去除字符串首尾空白。
     *
     * @param text 原始文本
     * @return 去空白后的文本
     */
    private String normalizeText(String text) {
        return text == null ? null : text.trim();
    }
}
