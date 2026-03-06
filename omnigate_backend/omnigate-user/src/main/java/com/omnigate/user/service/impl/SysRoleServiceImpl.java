package com.omnigate.user.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.omnigate.user.entity.SysRole;
import com.omnigate.user.mapper.SysRoleMapper;
import com.omnigate.user.model.vo.RoleInfoVO;
import com.omnigate.user.service.SysRoleService;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 系统角色服务实现。
 */
@Service
public class SysRoleServiceImpl extends ServiceImpl<SysRoleMapper, SysRole> implements SysRoleService {

    /**
     * 返回所有启用中的角色，供用户管理页进行角色分配。
     *
     * @return 启用角色列表
     */
    @Override
    public List<RoleInfoVO> listActiveRoles() {
        return lambdaQuery()
                .eq(SysRole::getStatus, 1)
                .orderByAsc(SysRole::getSort)
                .orderByAsc(SysRole::getId)
                .list()
                .stream()
                .map(this::toRoleInfoVO)
                .toList();
    }

    private RoleInfoVO toRoleInfoVO(SysRole sysRole) {
        RoleInfoVO roleInfoVO = new RoleInfoVO();
        roleInfoVO.setId(sysRole.getId());
        roleInfoVO.setRoleCode(sysRole.getRoleCode());
        roleInfoVO.setRoleName(sysRole.getRoleName());
        roleInfoVO.setDescription(sysRole.getDescription());
        roleInfoVO.setStatus(sysRole.getStatus());
        roleInfoVO.setSort(sysRole.getSort());
        return roleInfoVO;
    }
}
