package com.omnigate.user.controller;

import com.omnigate.common.response.Result;
import com.omnigate.user.model.vo.RoleInfoVO;
import com.omnigate.user.service.SysRoleService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 系统角色控制器。
 */
@RestController
@RequestMapping("/api/roles")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN')")
public class SysRoleController {

    private final SysRoleService sysRoleService;

    /**
     * 查询启用中的角色列表。
     *
     * @return 角色列表
     */
    @GetMapping
    public Result<List<RoleInfoVO>> listRoles() {
        return Result.success(sysRoleService.listActiveRoles());
    }
}
