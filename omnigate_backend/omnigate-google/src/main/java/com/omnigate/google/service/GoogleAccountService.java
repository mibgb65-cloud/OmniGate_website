package com.omnigate.google.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.omnigate.google.entity.GoogleAccountBase;
import com.omnigate.google.model.dto.GoogleAccountImportDTO;
import com.omnigate.google.model.dto.GoogleAccountPageQueryDTO;
import com.omnigate.google.model.dto.GoogleAccountUpdateDTO;
import com.omnigate.google.model.vo.GoogleAccountDetailVO;
import com.omnigate.google.model.vo.GoogleAccountListVO;
import com.omnigate.google.model.vo.GoogleFamilyMemberVO;
import com.omnigate.google.model.vo.GoogleInviteLinkVO;

import java.util.List;

/**
 * Google 账号核心资产服务接口。
 */
public interface GoogleAccountService extends IService<GoogleAccountBase> {

    /**
     * 导入账号（支持单条/批量）。
     *
     * @param importDTOList 导入参数列表
     * @return 导入成功条数
     */
    int importAccounts(List<GoogleAccountImportDTO> importDTOList);

    /**
     * 分页查询账号列表。
     *
     * @param queryDTO 分页查询参数
     * @return 分页列表
     */
    IPage<GoogleAccountListVO> pageAccounts(GoogleAccountPageQueryDTO queryDTO);

    /**
     * 查询账号详情。
     *
     * @param id 账号 ID
     * @return 账号详情
     */
    GoogleAccountDetailVO getAccountDetail(Long id);

    /**
     * 更新账号基础信息。
     *
     * @param id 账号 ID
     * @param updateDTO 更新参数
     */
    void updateAccountBase(Long id, GoogleAccountUpdateDTO updateDTO);

    /**
     * 查询家庭成员列表。
     *
     * @param accountId 账号 ID
     * @return 家庭成员列表
     */
    List<GoogleFamilyMemberVO> listFamilyMembers(Long accountId);

    /**
     * 查询邀请链接列表。
     *
     * @param accountId 账号 ID
     * @return 邀请链接列表
     */
    List<GoogleInviteLinkVO> listInviteLinks(Long accountId);
}
