package com.omnigate.github.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

/**
 * GitHub 账号状态更新参数。
 */
@Data
public class GithubAccountStatusDTO {

    /**
     * 账号状态：active, locked, banned。
     */
    @NotBlank(message = "账号状态不能为空")
    @Pattern(regexp = "active|locked|banned", message = "账号状态仅支持 active/locked/banned")
    private String accountStatus;
}
