package com.omnigate.user.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 用户角色关联 Mapper。
 */
@Mapper
public interface SysUserRoleMapper {

    /**
     * 逻辑清除用户原有角色关联。
     *
     * @param userId 用户 ID
     * @return 影响行数
     */
    int logicalDeleteByUserId(@Param("userId") Long userId);

    /**
     * 批量插入用户角色关联。
     *
     * @param userId 用户 ID
     * @param roleIds 角色 ID 列表
     * @return 影响行数
     */
    int batchInsert(@Param("userId") Long userId, @Param("roleIds") List<Long> roleIds);
}
