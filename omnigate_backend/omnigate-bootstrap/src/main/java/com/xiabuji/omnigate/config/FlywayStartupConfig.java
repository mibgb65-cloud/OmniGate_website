package com.xiabuji.omnigate.config;

import org.flywaydb.core.api.MigrationInfo;
import org.springframework.boot.flyway.autoconfigure.FlywayMigrationStrategy;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Flyway 启动迁移策略配置。
 */
@Configuration
public class FlywayStartupConfig {

    private static final Logger log = LoggerFactory.getLogger(FlywayStartupConfig.class);

    /**
     * 每次应用启动时检测待执行迁移并自动执行。
     *
     * @return FlywayMigrationStrategy
     */
    @Bean
    public FlywayMigrationStrategy flywayMigrationStrategy() {
        return flyway -> {
            MigrationInfo[] pendingMigrations = flyway.info().pending();
            int pendingCount = pendingMigrations == null ? 0 : pendingMigrations.length;
            if (pendingCount > 0) {
                log.info("检测到 {} 个待执行迁移版本，开始自动迁移。", pendingCount);
            } else {
                log.info("未检测到待执行迁移版本。");
            }
            flyway.migrate();
        };
    }
}
