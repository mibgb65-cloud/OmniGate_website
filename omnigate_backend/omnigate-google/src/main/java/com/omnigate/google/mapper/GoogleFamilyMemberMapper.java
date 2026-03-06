package com.omnigate.google.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.google.entity.GoogleFamilyMember;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * Google 家庭组成员 Mapper。
 */
@Mapper
public interface GoogleFamilyMemberMapper extends BaseMapper<GoogleFamilyMember> {

    /**
     * 查询指定账号下某邮箱成员是否已存在（忽略大小写）。
     *
     * @param accountId 账号 ID
     * @param memberEmail 成员邮箱
     * @return 已存在数量
     */
    @Select("""
            SELECT COUNT(1)
            FROM acc_google_family_member
            WHERE deleted = 0
              AND account_id = #{accountId}
              AND LOWER(member_email) = LOWER(#{memberEmail})
            """)
    long countActiveByAccountIdAndEmail(@Param("accountId") Long accountId, @Param("memberEmail") String memberEmail);
}
