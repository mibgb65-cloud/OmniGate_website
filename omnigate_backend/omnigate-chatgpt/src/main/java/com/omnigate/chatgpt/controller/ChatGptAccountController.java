package com.omnigate.chatgpt.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.omnigate.chatgpt.model.dto.ChatGptAccountBatchStatusDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountCreateDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountPageQueryDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountStatusDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountUpdateDTO;
import com.omnigate.chatgpt.model.vo.ChatGptAccountVO;
import com.omnigate.chatgpt.service.ChatGptAccountService;
import com.omnigate.common.response.Result;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Positive;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * ChatGPT 账号管理控制器。
 */
@Validated
@RestController
@RequestMapping("/api/chatgpt/accounts")
@RequiredArgsConstructor
public class ChatGptAccountController {

    private final ChatGptAccountService chatGptAccountService;

    /**
     * 新增单个账号。
     *
     * @param createDTO 新增参数
     * @return 新增账号 ID
     */
    @PostMapping
    public Result<Long> createAccount(@RequestBody @Valid ChatGptAccountCreateDTO createDTO) {
        return Result.success(chatGptAccountService.createAccount(createDTO));
    }

    /**
     * 批量新增账号。
     *
     * @param createDTOList 新增参数列表
     * @return 新增成功数量
     */
    @PostMapping("/batch")
    public Result<Integer> createAccountsBatch(@RequestBody @NotEmpty(message = "新增数据不能为空")
                                               List<@Valid ChatGptAccountCreateDTO> createDTOList) {
        return Result.success(chatGptAccountService.createAccountsBatch(createDTOList));
    }

    /**
     * 分页查询账号。
     *
     * @param queryDTO 查询参数
     * @return 分页数据
     */
    @GetMapping
    public Result<IPage<ChatGptAccountVO>> pageAccounts(@Valid ChatGptAccountPageQueryDTO queryDTO) {
        return Result.success(chatGptAccountService.pageAccounts(queryDTO));
    }

    /**
     * 查询账号详情。
     *
     * @param id 账号 ID
     * @return 账号详情
     */
    @GetMapping("/{id}")
    public Result<ChatGptAccountVO> getAccount(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        return Result.success(chatGptAccountService.getAccount(id));
    }

    /**
     * 更新账号基础信息。
     *
     * @param id 账号 ID
     * @param updateDTO 更新参数
     * @return 成功响应
     */
    @PutMapping("/{id}")
    public Result<Void> updateAccount(@PathVariable @Positive(message = "账号ID必须大于0") Long id,
                                      @RequestBody @Valid ChatGptAccountUpdateDTO updateDTO) {
        chatGptAccountService.updateAccount(id, updateDTO);
        return Result.success();
    }

    /**
     * 更新单个账号状态。
     *
     * @param id 账号 ID
     * @param statusDTO 状态参数
     * @return 成功响应
     */
    @PatchMapping("/{id}/status")
    public Result<Void> updateAccountStatus(@PathVariable @Positive(message = "账号ID必须大于0") Long id,
                                            @RequestBody @Valid ChatGptAccountStatusDTO statusDTO) {
        chatGptAccountService.updateAccountStatus(id, statusDTO);
        return Result.success();
    }

    /**
     * 批量更新账号状态。
     *
     * @param batchStatusDTO 批量状态参数
     * @return 更新成功数量
     */
    @PatchMapping("/batch/status")
    public Result<Integer> batchUpdateAccountStatus(@RequestBody @Valid ChatGptAccountBatchStatusDTO batchStatusDTO) {
        return Result.success(chatGptAccountService.batchUpdateAccountStatus(batchStatusDTO));
    }

    /**
     * 删除单个账号。
     *
     * @param id 账号 ID
     * @return 成功响应
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteAccount(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        chatGptAccountService.deleteAccount(id);
        return Result.success();
    }

    /**
     * 批量删除账号。
     *
     * @param ids 账号 ID 列表
     * @return 删除成功数量
     */
    @DeleteMapping("/batch")
    public Result<Integer> batchDeleteAccounts(@RequestBody @NotEmpty(message = "账号ID列表不能为空")
                                               List<@Positive(message = "账号ID必须大于0") Long> ids) {
        return Result.success(chatGptAccountService.batchDeleteAccounts(ids));
    }
}
