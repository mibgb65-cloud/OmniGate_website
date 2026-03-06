package com.omnigate.google.service;

import com.omnigate.google.model.vo.GoogleTaskRunStatusVO;
import com.omnigate.google.model.vo.GoogleTaskDispatchVO;

import java.util.List;

/**
 * Google 账号自动化任务投递服务。
 */
public interface GoogleAccountTaskService {

    /**
     * 投递单账号特征同步任务。
     *
     * @param accountId 账号 ID
     * @return 投递结果
     */
    GoogleTaskDispatchVO dispatchFeatureSyncTask(Long accountId);

    /**
     * 投递批量账号特征同步任务。
     *
     * @param accountIds 账号 ID 列表
     * @return 投递结果列表
     */
    List<GoogleTaskDispatchVO> dispatchFeatureSyncBatchTasks(List<Long> accountIds);

    /**
     * 投递学生资格链接同步任务。
     *
     * @param accountId 账号 ID
     * @return 投递结果
     */
    GoogleTaskDispatchVO dispatchStudentEligibilityTask(Long accountId);

    /**
     * 投递家庭组邀请任务。
     *
     * @param accountId 母号账号 ID
     * @param invitedAccountEmail 被邀请邮箱
     * @return 投递结果
     */
    GoogleTaskDispatchVO dispatchFamilyInviteTask(Long accountId, String invitedAccountEmail);

    /**
     * 按 taskRunId 查询任务状态。
     *
     * @param taskRunId 执行记录 ID
     * @return 任务状态
     */
    GoogleTaskRunStatusVO getTaskRunStatus(String taskRunId);

    /**
     * 按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunId 根任务 ID
     * @return 最新任务状态
     */
    GoogleTaskRunStatusVO getLatestTaskRunStatusByRootRunId(String rootRunId);

    /**
     * 批量按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunIds 根任务 ID 列表
     * @return 最新任务状态列表
     */
    List<GoogleTaskRunStatusVO> listLatestTaskRunStatusesByRootRunIds(List<String> rootRunIds);
}
