package com.omnigate.chatgpt.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.omnigate.chatgpt.entity.ChatGptAccountBase;
import com.omnigate.chatgpt.model.dto.ChatGptAccountBatchStatusDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountCreateDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountPageQueryDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountStatusDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountUpdateDTO;
import com.omnigate.chatgpt.model.vo.ChatGptAccountVO;

import java.util.List;

/**
 * ChatGPT 账号管理服务接口。
 */
public interface ChatGptAccountService extends IService<ChatGptAccountBase> {

    /**
     * 新增账号。
     *
     * @param createDTO 新增参数
     * @return 新增账号 ID
     */
    Long createAccount(ChatGptAccountCreateDTO createDTO);

    /**
     * 批量新增账号。
     *
     * @param createDTOList 新增参数列表
     * @return 新增成功数量
     */
    int createAccountsBatch(List<ChatGptAccountCreateDTO> createDTOList);

    /**
     * 分页查询账号。
     *
     * @param queryDTO 查询参数
     * @return 分页数据
     */
    IPage<ChatGptAccountVO> pageAccounts(ChatGptAccountPageQueryDTO queryDTO);

    /**
     * 获取账号详情。
     *
     * @param id 账号 ID
     * @return 账号详情
     */
    ChatGptAccountVO getAccount(Long id);

    /**
     * 更新账号基础信息。
     *
     * @param id 账号 ID
     * @param updateDTO 更新参数
     */
    void updateAccount(Long id, ChatGptAccountUpdateDTO updateDTO);

    /**
     * 更新单个账号状态。
     *
     * @param id 账号 ID
     * @param statusDTO 状态参数
     */
    void updateAccountStatus(Long id, ChatGptAccountStatusDTO statusDTO);

    /**
     * 批量更新账号状态。
     *
     * @param batchStatusDTO 批量状态参数
     * @return 更新成功数量
     */
    int batchUpdateAccountStatus(ChatGptAccountBatchStatusDTO batchStatusDTO);

    /**
     * 删除单个账号。
     *
     * @param id 账号 ID
     */
    void deleteAccount(Long id);

    /**
     * 批量删除账号。
     *
     * @param ids 账号 ID 列表
     * @return 删除成功数量
     */
    int batchDeleteAccounts(List<Long> ids);
}
