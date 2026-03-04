package com.omnigate.user.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.user.entity.SysLoginLog;
import org.apache.ibatis.annotations.Mapper;

/**
 * 系统登录日志 Mapper。
 */
@Mapper
public interface SysLoginLogMapper extends BaseMapper<SysLoginLog> {
}
