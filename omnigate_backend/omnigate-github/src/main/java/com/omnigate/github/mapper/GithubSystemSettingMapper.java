package com.omnigate.github.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * GitHub 模块系统配置 Mapper。
 */
@Mapper
public interface GithubSystemSettingMapper {

    /**
     * 根据 key 查询配置值。
     *
     * @param key 配置键
     * @return 配置值
     */
    @Select("""
            SELECT value
            FROM system_settings
            WHERE key = #{key}
            LIMIT 1
            """)
    String selectValueByKey(@Param("key") String key);
}
