package com.omnigate.github.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.omnigate.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

/**
 * GitHub 仓库交互记录实体。
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("acc_github_repo_interaction")
public class GithubRepoInteraction extends BaseEntity {

    /**
     * 主键 ID。
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * GitHub 账号 ID。
     */
    private Long accountId;

    /**
     * 仓库所有者。
     */
    private String repoOwner;

    /**
     * 仓库名称。
     */
    private String repoName;

    /**
     * 规范化仓库地址。
     */
    private String repoUrl;

    /**
     * 是否已 Star。
     */
    private Integer starred;

    /**
     * Star 时间。
     */
    private LocalDateTime starredAt;

    /**
     * 是否已 Fork。
     */
    private Integer forked;

    /**
     * Fork 时间。
     */
    private LocalDateTime forkedAt;

    /**
     * 是否已 Watch。
     */
    private Integer watched;

    /**
     * Watch 时间。
     */
    private LocalDateTime watchedAt;

    /**
     * 是否已关注仓库 Owner。
     */
    private Integer followed;

    /**
     * 关注 Owner 时间。
     */
    private LocalDateTime followedAt;
}
