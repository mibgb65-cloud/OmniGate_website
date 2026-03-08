package com.omnigate.user.mapper;

import com.omnigate.user.entity.SystemSettingEntry;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * CloudMail 系统配置 Mapper。
 */
@Mapper
public interface CloudMailSystemSettingMapper {

    /**
     * 按 key 列表查询系统配置。
     *
     * @param keys 配置键列表
     * @return 配置记录
     */
    @Select("""
            <script>
            SELECT key,
                   value,
                   description
            FROM system_settings
            WHERE key IN
            <foreach collection="keys" item="key" open="(" separator="," close=")">
                #{key}
            </foreach>
            </script>
            """)
    List<SystemSettingEntry> selectByKeys(@Param("keys") List<String> keys);

    /**
     * 插入或更新配置值。
     *
     * @param key 配置键
     * @param value 配置值
     * @param description 配置说明
     * @return 影响行数
     */
    @Insert("""
            INSERT INTO system_settings (key, value, description, updated_at)
            VALUES (#{key}, #{value}, #{description}, now())
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value,
                description = EXCLUDED.description,
                updated_at = now()
            """)
    int upsert(@Param("key") String key,
               @Param("value") String value,
               @Param("description") String description);
}
