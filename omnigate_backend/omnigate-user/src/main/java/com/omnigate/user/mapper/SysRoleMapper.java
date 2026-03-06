package com.omnigate.user.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.user.entity.SysRole;
import com.omnigate.user.model.vo.UserRoleBriefVO;
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

    /**
     * 按用户 ID 列表批量查询有效角色信息。
     *
     * @param userIds 用户 ID 列表
     * @return 用户角色简要信息列表
     */
    List<UserRoleBriefVO> selectByUserIds(@Param("userIds") List<Long> userIds);
}
