package com.omnigate.chatgpt.mapper;

import com.omnigate.chatgpt.model.vo.ChatGptTaskRunStatusVO;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.UUID;

/**
 * ChatGPT Worker 任务执行记录 Mapper。
 */
@Mapper
public interface ChatGptWorkerTaskRunMapper {

    /**
     * 插入待执行任务记录。
     *
     * @param id 任务执行记录 ID
     * @param rootRunId 根任务 ID
     * @param attemptNo 尝试次数
     * @param maxAttempts 最大重试次数
     * @param status 任务状态
     * @param triggeredBy 触发人
     * @param inputPayload 任务入参 JSON
     * @return 影响行数
     */
    @Insert("""
            INSERT INTO task_runs (
                id,
                root_run_id,
                attempt_no,
                max_attempts,
                status,
                triggered_by,
                input_payload,
                created_at,
                updated_at
            ) VALUES (
                #{id},
                #{rootRunId},
                #{attemptNo},
                #{maxAttempts},
                #{status},
                #{triggeredBy},
                CAST(#{inputPayload} AS jsonb),
                now(),
                now()
            )
            """)
    int insertTaskRun(@Param("id") UUID id,
                      @Param("rootRunId") UUID rootRunId,
                      @Param("attemptNo") Integer attemptNo,
                      @Param("maxAttempts") Integer maxAttempts,
                      @Param("status") String status,
                      @Param("triggeredBy") String triggeredBy,
                      @Param("inputPayload") String inputPayload);

    /**
     * 删除任务执行记录（用于投递失败补偿）。
     *
     * @param id 任务执行记录 ID
     * @return 影响行数
     */
    @Delete("""
            DELETE FROM task_runs
            WHERE id = #{id}
            """)
    int deleteById(@Param("id") UUID id);

    /**
     * 按 taskRunId 查询任务状态。
     *
     * @param id 任务执行记录 ID
     * @return 任务状态
     */
    @Select("""
            SELECT CAST(id AS VARCHAR) AS taskRunId,
                   CAST(root_run_id AS VARCHAR) AS rootRunId,
                   attempt_no AS attemptNo,
                   max_attempts AS maxAttempts,
                   input_payload ->> 'module' AS module,
                   input_payload ->> 'action' AS action,
                   status,
                   error_code AS errorCode,
                   error_message AS errorMessage,
                   last_checkpoint AS lastCheckpoint,
                   started_at AS startedAt,
                   finished_at AS finishedAt,
                   created_at AS createdAt,
                   updated_at AS updatedAt
            FROM task_runs
            WHERE id = #{id}
            LIMIT 1
            """)
    ChatGptTaskRunStatusVO selectStatusById(@Param("id") UUID id);

    /**
     * 按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunId 根任务 ID
     * @return 最新任务状态
     */
    @Select("""
            SELECT CAST(id AS VARCHAR) AS taskRunId,
                   CAST(root_run_id AS VARCHAR) AS rootRunId,
                   attempt_no AS attemptNo,
                   max_attempts AS maxAttempts,
                   input_payload ->> 'module' AS module,
                   input_payload ->> 'action' AS action,
                   status,
                   error_code AS errorCode,
                   error_message AS errorMessage,
                   last_checkpoint AS lastCheckpoint,
                   started_at AS startedAt,
                   finished_at AS finishedAt,
                   created_at AS createdAt,
                   updated_at AS updatedAt
            FROM task_runs
            WHERE root_run_id = #{rootRunId}
            ORDER BY attempt_no DESC, created_at DESC
            LIMIT 1
            """)
    ChatGptTaskRunStatusVO selectLatestStatusByRootRunId(@Param("rootRunId") UUID rootRunId);
}
