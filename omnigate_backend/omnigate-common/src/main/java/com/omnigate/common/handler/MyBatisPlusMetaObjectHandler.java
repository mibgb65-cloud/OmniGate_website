package com.omnigate.common.handler;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import lombok.extern.slf4j.Slf4j;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * 全局 MyBatis-Plus 审计字段自动填充处理器。
 */
@Slf4j
@Component
public class MyBatisPlusMetaObjectHandler implements MetaObjectHandler {

    /**
     * 插入时自动填充创建/更新人和创建/更新时间。
     *
     * @param metaObject 元对象
     */
    @Override
    public void insertFill(MetaObject metaObject) {
        LocalDateTime now = LocalDateTime.now();
        Long operatorId = currentOperatorId();
        strictInsertFill(metaObject, "createdAt", LocalDateTime.class, now);
        strictInsertFill(metaObject, "updatedAt", LocalDateTime.class, now);
        strictInsertFill(metaObject, "createdBy", Long.class, operatorId);
        strictInsertFill(metaObject, "updatedBy", Long.class, operatorId);
        log.debug("Insert fill completed, operatorId={}, now={}", operatorId, now);
    }

    /**
     * 更新时自动填充更新人和更新时间。
     *
     * @param metaObject 元对象
     */
    @Override
    public void updateFill(MetaObject metaObject) {
        LocalDateTime now = LocalDateTime.now();
        Long operatorId = currentOperatorId();
        strictUpdateFill(metaObject, "updatedAt", LocalDateTime.class, now);
        strictUpdateFill(metaObject, "updatedBy", Long.class, operatorId);
        log.debug("Update fill completed, operatorId={}, now={}", operatorId, now);
    }

    /**
     * 预留：从上下文中解析当前操作人 ID。
     * 后续可在上层模块对接安全上下文实现真实取值。
     */
    protected Long currentOperatorId() {
        return 0L;
    }
}
