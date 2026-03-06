package com.omnigate.google.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.google.entity.GoogleAccountBase;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

/**
 * Google 账号基础信息 Mapper。
 */
@Mapper
public interface GoogleAccountBaseMapper extends BaseMapper<GoogleAccountBase> {

    /**
     * 按邮箱（忽略大小写）查询有效账号。
     *
     * @param email 邮箱
     * @return 账号基础信息（仅返回主键和邮箱）
     */
    @Select("""
            SELECT id, email
            FROM acc_google_base
            WHERE deleted = 0
              AND LOWER(email) = LOWER(#{email})
            LIMIT 1
            """)
    GoogleAccountBase selectActiveByEmailIgnoreCase(@Param("email") String email);

    /**
     * 更新账号同步状态。
     *
     * @param id 账号 ID
     * @param syncStatus 同步状态
     * @return 影响行数
     */
    @Update("""
            UPDATE acc_google_base
            SET sync_status = #{syncStatus},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = #{id}
              AND deleted = 0
            """)
    int updateSyncStatusById(@Param("id") Long id, @Param("syncStatus") Integer syncStatus);
}
