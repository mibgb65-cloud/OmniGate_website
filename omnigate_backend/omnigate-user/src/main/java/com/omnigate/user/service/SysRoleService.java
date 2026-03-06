package com.omnigate.user.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.omnigate.user.entity.SysRole;
import com.omnigate.user.model.vo.RoleInfoVO;

import java.util.List;

/**
 * 系统角色服务接口。
 */
public interface SysRoleService extends IService<SysRole> {

    /**
     * 查询可分配的启用角色列表。
     *
     * @return 角色列表
     */
    List<RoleInfoVO> listActiveRoles();
}
