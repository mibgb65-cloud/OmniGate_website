package com.omnigate.common.config;

import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import com.fasterxml.jackson.databind.Module;
import com.fasterxml.jackson.databind.module.SimpleModule;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Jackson 序列化配置：Long 类型按字符串输出，避免前端 Number 精度丢失。
 */
@Configuration
public class JacksonLongToStringConfig {

    /**
     * 全局将 Long/long 输出为字符串。
     */
    @Bean
    public Module jacksonLongToStringModule() {
        SimpleModule module = new SimpleModule();
        module.addSerializer(Long.class, ToStringSerializer.instance);
        module.addSerializer(Long.TYPE, ToStringSerializer.instance);
        return module;
    }
}
