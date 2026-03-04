package com.omnigate.chatgpt.config;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Configuration;

/**
 * ChatGPT 模块 MyBatis Mapper 扫描配置。
 */
@Configuration
@MapperScan("com.omnigate.chatgpt.mapper")
public class ChatGptMybatisMapperScanConfig {
}
