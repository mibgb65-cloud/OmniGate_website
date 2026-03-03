package com.omnigate.user.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.user.entity.SysUser;
import org.apache.ibatis.annotations.Mapper;

/**
 * 系统用户 Mapper。
 */
@Mapper
public interface SysUserMapper extends BaseMapper<SysUser> {
}
