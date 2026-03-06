package com.omnigate.google.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.omnigate.common.response.Result;
import com.omnigate.google.model.dto.GoogleAccountImportDTO;
import com.omnigate.google.model.dto.GoogleAccountPageQueryDTO;
import com.omnigate.google.model.dto.GoogleAccountUpdateDTO;
import com.omnigate.google.model.dto.GoogleBatchSyncRequestDTO;
import com.omnigate.google.model.dto.GoogleInviteFamilyMemberTaskDTO;
import com.omnigate.google.model.vo.GoogleAccountDetailVO;
import com.omnigate.google.model.vo.GoogleAccountListVO;
import com.omnigate.google.model.vo.GoogleFamilyMemberVO;
import com.omnigate.google.model.vo.GoogleInviteLinkVO;
import com.omnigate.google.model.vo.GoogleTaskDispatchVO;
import com.omnigate.google.service.GoogleAccountService;
import com.omnigate.google.service.GoogleAccountTaskService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Positive;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.DeleteMapping;

import java.util.List;

/**
 * Google 账号核心资产控制器。
 */
@Validated
@RestController
@RequestMapping("/api/google/accounts")
@RequiredArgsConstructor
public class GoogleAccountController {

    private final GoogleAccountService googleAccountService;
    private final GoogleAccountTaskService googleAccountTaskService;

    /**
     * 导入 Google 账号（单条/批量）。
     *
     * @param importDTOList 导入参数列表
     * @return 导入成功条数
     */
    @PostMapping("/import")
    public Result<Integer> importAccounts(@RequestBody @NotEmpty(message = "导入数据不能为空") @Valid List<GoogleAccountImportDTO> importDTOList) {
        return Result.success(googleAccountService.importAccounts(importDTOList));
    }

    /**
     * 分页查询账号列表（脱敏）。
     *
     * @param queryDTO 查询参数
     * @return 分页数据
     */
    @GetMapping
    public Result<IPage<GoogleAccountListVO>> pageAccounts(@Valid GoogleAccountPageQueryDTO queryDTO) {
        return Result.success(googleAccountService.pageAccounts(queryDTO));
    }

    /**
     * 查询账号详情（脱敏）。
     *
     * @param id 账号 ID
     * @return 账号详情
     */
    @GetMapping("/{id}")
    public Result<GoogleAccountDetailVO> getAccountDetail(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        return Result.success(googleAccountService.getAccountDetail(id));
    }

    /**
     * 更新账号基础信息。
     *
     * @param id 账号 ID
     * @param updateDTO 更新参数
     * @return 成功响应
     */
    @PutMapping("/{id}")
    public Result<Void> updateAccountBase(@PathVariable @Positive(message = "账号ID必须大于0") Long id,
                                          @RequestBody @Valid GoogleAccountUpdateDTO updateDTO) {
        googleAccountService.updateAccountBase(id, updateDTO);
        return Result.success();
    }

    /**
     * 查询家庭组成员列表（只读）。
     *
     * @param id 账号 ID
     * @return 家庭成员列表
     */
    @GetMapping("/{id}/family-members")
    public Result<List<GoogleFamilyMemberVO>> listFamilyMembers(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        return Result.success(googleAccountService.listFamilyMembers(id));
    }

    /**
     * 查询福利邀请链接列表（只读）。
     *
     * @param id 账号 ID
     * @return 邀请链接列表
     */
    @GetMapping("/{id}/invite-links")
    public Result<List<GoogleInviteLinkVO>> listInviteLinks(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        return Result.success(googleAccountService.listInviteLinks(id));
    }

    /**
     * 逻辑删除账号及其关联信息。
     *
     * @param id 账号 ID
     * @return 成功响应
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteAccount(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        googleAccountService.deleteAccount(id);
        return Result.success();
    }

    /**
     * 投递单个账号信息同步任务。
     *
     * @param id 账号 ID
     * @return 任务投递结果
     */
    @PostMapping("/{id}/sync")
    public Result<GoogleTaskDispatchVO> syncAccount(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        return Result.success(googleAccountTaskService.dispatchFeatureSyncTask(id));
    }

    /**
     * 投递批量账号信息同步任务。
     *
     * @param requestDTO 批量请求参数
     * @return 任务投递结果列表
     */
    @PostMapping("/sync/batch")
    public Result<List<GoogleTaskDispatchVO>> syncAccountsBatch(@RequestBody @Valid GoogleBatchSyncRequestDTO requestDTO) {
        return Result.success(googleAccountTaskService.dispatchFeatureSyncBatchTasks(requestDTO.getAccountIds()));
    }

    /**
     * 投递学生认证链接同步任务。
     *
     * @param id 账号 ID
     * @return 任务投递结果
     */
    @PostMapping("/{id}/student-eligibility/sync")
    public Result<GoogleTaskDispatchVO> syncStudentEligibility(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        return Result.success(googleAccountTaskService.dispatchStudentEligibilityTask(id));
    }

    /**
     * 投递家庭组邀请任务。
     *
     * @param id 母号账号 ID
     * @param requestDTO 邀请参数
     * @return 任务投递结果
     */
    @PostMapping("/{id}/family-members/invite")
    public Result<GoogleTaskDispatchVO> inviteFamilyMember(@PathVariable @Positive(message = "账号ID必须大于0") Long id,
                                                            @RequestBody @Valid GoogleInviteFamilyMemberTaskDTO requestDTO) {
        return Result.success(googleAccountTaskService.dispatchFamilyInviteTask(id, requestDTO.getInvitedAccountEmail()));
    }
}
