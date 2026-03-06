package com.omnigate.google.mapper;

import com.omnigate.google.model.vo.GoogleTaskRunStatusVO;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.UUID;

/**
 * Worker 任务执行记录 Mapper。
 */
@Mapper
public interface WorkerTaskRunMapper {

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
    GoogleTaskRunStatusVO selectStatusById(@Param("id") UUID id);

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
    GoogleTaskRunStatusVO selectLatestStatusByRootRunId(@Param("rootRunId") UUID rootRunId);

    /**
     * 批量按 rootRunId 查询当前最新任务状态。
     *
     * @param rootRunIds 根任务 ID 列表
     * @return 最新任务状态列表
     */
    @Select({
            "<script>",
            "SELECT CAST(latest.id AS VARCHAR) AS taskRunId,",
            "       CAST(latest.root_run_id AS VARCHAR) AS rootRunId,",
            "       latest.attempt_no AS attemptNo,",
            "       latest.max_attempts AS maxAttempts,",
            "       latest.input_payload ->> 'module' AS module,",
            "       latest.input_payload ->> 'action' AS action,",
            "       latest.status AS status,",
            "       latest.error_code AS errorCode,",
            "       latest.error_message AS errorMessage,",
            "       latest.last_checkpoint AS lastCheckpoint,",
            "       latest.started_at AS startedAt,",
            "       latest.finished_at AS finishedAt,",
            "       latest.created_at AS createdAt,",
            "       latest.updated_at AS updatedAt",
            "FROM (",
            "    SELECT id, root_run_id, attempt_no, max_attempts, input_payload, status, error_code, error_message,",
            "           last_checkpoint, started_at, finished_at, created_at, updated_at,",
            "           ROW_NUMBER() OVER (PARTITION BY root_run_id ORDER BY attempt_no DESC, created_at DESC) AS rn",
            "    FROM task_runs",
            "    WHERE root_run_id IN",
            "    <foreach collection='rootRunIds' item='rootRunId' open='(' separator=',' close=')'>",
            "        CAST(#{rootRunId} AS uuid)",
            "    </foreach>",
            ") latest",
            "WHERE latest.rn = 1",
            "</script>"
    })
    List<GoogleTaskRunStatusVO> selectLatestStatusesByRootRunIds(@Param("rootRunIds") List<String> rootRunIds);
}
