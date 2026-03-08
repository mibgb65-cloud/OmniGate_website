package com.omnigate.github.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * GitHub 仓库 Star 任务请求参数。
 */
@Data
public class GithubStarRepoTaskDTO {

    /**
     * 目标仓库 URL。
     */
    @NotBlank(message = "repoUrl 不能为空")
    @Size(max = 1024, message = "repoUrl 长度不能超过1024")
    private String repoUrl;
}
