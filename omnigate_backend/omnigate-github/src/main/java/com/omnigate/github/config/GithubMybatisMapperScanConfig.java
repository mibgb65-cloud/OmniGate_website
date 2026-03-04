package com.omnigate.github.config;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Configuration;

/**
 * GitHub 模块 MyBatis Mapper 扫描配置。
 */
@Configuration
@MapperScan("com.omnigate.github.mapper")
public class GithubMybatisMapperScanConfig {
}
