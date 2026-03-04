package com.omnigate.github.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.github.entity.GithubAccountBase;
import org.apache.ibatis.annotations.Mapper;

/**
 * GitHub 账号基础信息 Mapper。
 */
@Mapper
public interface GithubAccountBaseMapper extends BaseMapper<GithubAccountBase> {
}
