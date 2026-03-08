package com.omnigate.user.controller;

import com.omnigate.common.response.Result;
import com.omnigate.user.model.dto.CloudMailSystemSettingUpdateDTO;
import com.omnigate.user.model.vo.CloudMailSystemSettingVO;
import com.omnigate.user.service.CloudMailSystemSettingService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * CloudMail 系统配置控制器。
 */
@Validated
@RestController
@RequestMapping("/api/system-settings/cloudmail")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN')")
public class CloudMailSystemSettingController {

    private final CloudMailSystemSettingService cloudMailSystemSettingService;

    /**
     * 读取 CloudMail 系统配置。
     *
     * @return CloudMail 配置
     */
    @GetMapping
    public Result<CloudMailSystemSettingVO> getSettings() {
        return Result.success(cloudMailSystemSettingService.getSettings());
    }

    /**
     * 更新 CloudMail 系统配置。
     *
     * @param updateDTO 更新参数
     * @return 成功响应
     */
    @PutMapping
    public Result<Void> updateSettings(@RequestBody @Valid CloudMailSystemSettingUpdateDTO updateDTO) {
        cloudMailSystemSettingService.updateSettings(updateDTO);
        return Result.success();
    }
}
