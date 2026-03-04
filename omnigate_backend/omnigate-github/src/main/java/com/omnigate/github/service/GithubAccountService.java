package com.omnigate.github.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.omnigate.github.entity.GithubAccountBase;
import com.omnigate.github.model.dto.GithubAccountImportDTO;
import com.omnigate.github.model.dto.GithubAccountPageQueryDTO;
import com.omnigate.github.model.dto.GithubAccountStatusDTO;
import com.omnigate.github.model.dto.GithubAccountUpdateDTO;
import com.omnigate.github.model.vo.GithubAccountVO;

import java.util.List;

/**
 * GitHub 账号基础管理服务接口。
 */
public interface GithubAccountService extends IService<GithubAccountBase> {

    /**
     * 导入账号（单条/批量）。
     *
     * @param importDTOList 导入参数列表
     * @return 导入成功数量
     */
    int importAccounts(List<GithubAccountImportDTO> importDTOList);

    /**
     * 分页查询账号池。
     *
     * @param queryDTO 查询参数
     * @return 分页数据
     */
    IPage<GithubAccountVO> pageAccounts(GithubAccountPageQueryDTO queryDTO);

    /**
     * 获取账号详情。
     *
     * @param id 主键 ID
     * @return 账号视图对象
     */
    GithubAccountVO getAccount(Long id);

    /**
     * 修改基础信息。
     *
     * @param id 主键 ID
     * @param updateDTO 更新参数
     */
    void updateAccount(Long id, GithubAccountUpdateDTO updateDTO);

    /**
     * 快捷更新账号状态。
     *
     * @param id 主键 ID
     * @param statusDTO 状态参数
     */
    void updateAccountStatus(Long id, GithubAccountStatusDTO statusDTO);

    /**
     * 逻辑删除账号。
     *
     * @param id 主键 ID
     */
    void deleteAccount(Long id);
}
