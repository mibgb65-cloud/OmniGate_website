package com.omnigate.user.config;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Configuration;

/**
 * MyBatis Mapper 扫描配置。
 */
@Configuration
@MapperScan("com.omnigate.user.mapper")
public class MybatisMapperScanConfig {
}
