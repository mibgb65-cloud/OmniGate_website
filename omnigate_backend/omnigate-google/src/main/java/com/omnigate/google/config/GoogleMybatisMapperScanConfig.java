package com.omnigate.google.config;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Configuration;

/**
 * Google 模块 MyBatis Mapper 扫描配置。
 */
@Configuration
@MapperScan("com.omnigate.google.mapper")
public class GoogleMybatisMapperScanConfig {
}
