package com.omnigate.github.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.omnigate.common.response.Result;
import com.omnigate.github.model.dto.GithubAccountImportDTO;
import com.omnigate.github.model.dto.GithubAccountPageQueryDTO;
import com.omnigate.github.model.dto.GithubAccountStatusDTO;
import com.omnigate.github.model.dto.GithubAccountUpdateDTO;
import com.omnigate.github.model.vo.GithubAccountVO;
import com.omnigate.github.service.GithubAccountService;
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
 * GitHub 账号基础管理控制器。
 */
@Validated
@RestController
@RequestMapping("/api/github/accounts")
@RequiredArgsConstructor
public class GithubAccountController {

    private final GithubAccountService githubAccountService;

    /**
     * 导入账号（单条/批量）。
     *
     * @param importDTOList 导入参数列表
     * @return 导入成功数量
     */
    @PostMapping("/import")
    public Result<Integer> importAccounts(@RequestBody @NotEmpty(message = "导入数据不能为空")
                                          List<@Valid GithubAccountImportDTO> importDTOList) {
        return Result.success(githubAccountService.importAccounts(importDTOList));
    }

    /**
     * 分页查询账号池。
     *
     * @param queryDTO 分页查询参数
     * @return 分页结果
     */
    @GetMapping
    public Result<IPage<GithubAccountVO>> pageAccounts(@Valid GithubAccountPageQueryDTO queryDTO) {
        return Result.success(githubAccountService.pageAccounts(queryDTO));
    }

    /**
     * 获取账号详情。
     *
     * @param id 主键 ID
     * @return 账号详情
     */
    @GetMapping("/{id}")
    public Result<GithubAccountVO> getAccount(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        return Result.success(githubAccountService.getAccount(id));
    }

    /**
     * 修改基础信息。
     *
     * @param id 主键 ID
     * @param updateDTO 更新参数
     * @return 成功响应
     */
    @PutMapping("/{id}")
    public Result<Void> updateAccount(@PathVariable @Positive(message = "账号ID必须大于0") Long id,
                                      @RequestBody @Valid GithubAccountUpdateDTO updateDTO) {
        githubAccountService.updateAccount(id, updateDTO);
        return Result.success();
    }

    /**
     * 快捷更新账号状态。
     *
     * @param id 主键 ID
     * @param statusDTO 状态参数
     * @return 成功响应
     */
    @PatchMapping("/{id}/status")
    public Result<Void> updateAccountStatus(@PathVariable @Positive(message = "账号ID必须大于0") Long id,
                                            @RequestBody @Valid GithubAccountStatusDTO statusDTO) {
        githubAccountService.updateAccountStatus(id, statusDTO);
        return Result.success();
    }

    /**
     * 逻辑删除账号。
     *
     * @param id 主键 ID
     * @return 成功响应
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteAccount(@PathVariable @Positive(message = "账号ID必须大于0") Long id) {
        githubAccountService.deleteAccount(id);
        return Result.success();
    }
}
