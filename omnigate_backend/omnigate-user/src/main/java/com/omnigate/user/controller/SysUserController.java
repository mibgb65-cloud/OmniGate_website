package com.omnigate.user.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.omnigate.common.response.Result;
import com.omnigate.user.model.dto.UserCreateDTO;
import com.omnigate.user.model.dto.UserPageQueryDTO;
import com.omnigate.user.model.dto.UserPasswordUpdateDTO;
import com.omnigate.user.model.dto.UserRoleAssignDTO;
import com.omnigate.user.model.dto.UserUpdateDTO;
import com.omnigate.user.model.vo.UserInfoVO;
import com.omnigate.user.service.SysUserService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Positive;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 系统用户管理控制器。
 */
@Validated
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN')")
public class SysUserController {

    private final SysUserService sysUserService;

    /**
     * 分页查询用户列表。
     *
     * @param queryDTO 分页查询参数
     * @return 用户分页数据
     */
    @GetMapping
    public Result<IPage<UserInfoVO>> pageUsers(@Valid UserPageQueryDTO queryDTO) {
        return Result.success(sysUserService.pageUsers(queryDTO));
    }

    /**
     * 查询用户详情。
     *
     * @param userId 用户 ID
     * @return 用户详情
     */
    @GetMapping("/{userId}")
    public Result<UserInfoVO> getUserInfo(@PathVariable @Positive(message = "用户ID必须大于0") Long userId) {
        return Result.success(sysUserService.getUserInfo(userId));
    }

    /**
     * 新增用户。
     *
     * @param createDTO 创建参数
     * @return 新增后的用户信息
     */
    @PostMapping
    public Result<UserInfoVO> createUser(@RequestBody @Valid UserCreateDTO createDTO) {
        return Result.success(sysUserService.createUser(createDTO));
    }

    /**
     * 更新用户基础信息（不包含密码）。
     *
     * @param userId 用户 ID
     * @param updateDTO 更新参数
     * @return 更新后的用户信息
     */
    @PutMapping("/{userId}")
    public Result<UserInfoVO> updateUser(@PathVariable @Positive(message = "用户ID必须大于0") Long userId,
                                         @RequestBody @Valid UserUpdateDTO updateDTO) {
        return Result.success(sysUserService.updateUser(userId, updateDTO));
    }

    /**
     * 单独修改用户密码。
     *
     * @param userId 用户 ID
     * @param updateDTO 密码更新参数
     * @return 成功响应
     */
    @PutMapping("/{userId}/password")
    public Result<Void> updatePassword(@PathVariable @Positive(message = "用户ID必须大于0") Long userId,
                                       @RequestBody @Valid UserPasswordUpdateDTO updateDTO) {
        sysUserService.updatePassword(userId, updateDTO);
        return Result.success();
    }

    /**
     * 更新用户状态（启用/禁用）。
     *
     * @param userId 用户 ID
     * @param status 状态值：1-启用，0-禁用
     * @return 成功响应
     */
    @PutMapping("/{userId}/status/{status}")
    public Result<Void> updateStatus(@PathVariable @Positive(message = "用户ID必须大于0") Long userId,
                                     @PathVariable @Min(value = 0, message = "状态值只能是0或1")
                                     @Max(value = 1, message = "状态值只能是0或1") Integer status) {
        sysUserService.updateStatus(userId, status);
        return Result.success();
    }

    /**
     * 为用户分配角色。
     *
     * @param userId 用户 ID
     * @param assignDTO 角色分配参数
     * @return 成功响应
     */
    @PutMapping("/{userId}/roles")
    public Result<Void> assignRoles(@PathVariable @Positive(message = "用户ID必须大于0") Long userId,
                                    @RequestBody @Valid UserRoleAssignDTO assignDTO) {
        sysUserService.assignRoles(userId, assignDTO);
        return Result.success();
    }

    /**
     * 逻辑删除用户。
     *
     * @param userId 用户 ID
     * @return 成功响应
     */
    @DeleteMapping("/{userId}")
    public Result<Void> removeUser(@PathVariable @Positive(message = "用户ID必须大于0") Long userId) {
        sysUserService.removeUser(userId);
        return Result.success();
    }
}
