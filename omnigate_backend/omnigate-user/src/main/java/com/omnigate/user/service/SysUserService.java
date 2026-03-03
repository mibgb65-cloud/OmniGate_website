package com.omnigate.user.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.omnigate.user.entity.SysUser;
import com.omnigate.user.model.dto.UserCreateDTO;
import com.omnigate.user.model.dto.UserPageQueryDTO;
import com.omnigate.user.model.dto.UserRoleAssignDTO;
import com.omnigate.user.model.dto.UserUpdateDTO;
import com.omnigate.user.model.vo.UserInfoVO;

/**
 * 系统用户管理服务接口。
 */
public interface SysUserService extends IService<SysUser> {

    /**
     * 分页查询用户列表。
     *
     * @param queryDTO 分页查询参数
     * @return 用户分页数据
     */
    IPage<UserInfoVO> pageUsers(UserPageQueryDTO queryDTO);

    /**
     * 查询用户详情。
     *
     * @param userId 用户 ID
     * @return 用户详情
     */
    UserInfoVO getUserInfo(Long userId);

    /**
     * 新增用户。
     *
     * @param createDTO 创建参数
     * @return 新增后的用户信息
     */
    UserInfoVO createUser(UserCreateDTO createDTO);

    /**
     * 更新用户信息（不含密码）。
     *
     * @param userId 用户 ID
     * @param updateDTO 更新参数
     * @return 更新后的用户信息
     */
    UserInfoVO updateUser(Long userId, UserUpdateDTO updateDTO);

    /**
     * 更新用户状态。
     *
     * @param userId 用户 ID
     * @param status 状态：1-启用，0-禁用
     */
    void updateStatus(Long userId, Integer status);

    /**
     * 为用户分配角色。
     *
     * @param userId 用户 ID
     * @param assignDTO 角色分配参数
     */
    void assignRoles(Long userId, UserRoleAssignDTO assignDTO);

    /**
     * 逻辑删除用户。
     *
     * @param userId 用户 ID
     */
    void removeUser(Long userId);
}
