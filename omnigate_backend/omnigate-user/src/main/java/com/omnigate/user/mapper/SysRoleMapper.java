package com.omnigate.user.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.user.entity.SysRole;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 系统角色 Mapper。
 */
@Mapper
public interface SysRoleMapper extends BaseMapper<SysRole> {

    /**
     * 按用户 ID 查询有效角色列表。
     *
     * @param userId 用户 ID
     * @return 角色列表
     */
    List<SysRole> selectByUserId(@Param("userId") Long userId);
}
