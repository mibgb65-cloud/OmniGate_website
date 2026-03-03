package com.omnigate.google.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.google.entity.GoogleAccountBase;
import org.apache.ibatis.annotations.Mapper;

/**
 * Google 账号基础信息 Mapper。
 */
@Mapper
public interface GoogleAccountBaseMapper extends BaseMapper<GoogleAccountBase> {
}
