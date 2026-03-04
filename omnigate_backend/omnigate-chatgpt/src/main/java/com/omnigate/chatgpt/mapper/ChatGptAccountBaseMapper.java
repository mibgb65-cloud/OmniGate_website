package com.omnigate.chatgpt.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.omnigate.chatgpt.entity.ChatGptAccountBase;
import org.apache.ibatis.annotations.Mapper;

/**
 * ChatGPT 账号基础信息 Mapper。
 */
@Mapper
public interface ChatGptAccountBaseMapper extends BaseMapper<ChatGptAccountBase> {
}
