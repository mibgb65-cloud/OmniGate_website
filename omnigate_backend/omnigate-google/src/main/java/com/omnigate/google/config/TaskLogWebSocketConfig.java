package com.omnigate.google.config;

import com.omnigate.google.websocket.TaskLogWebSocketHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * 任务日志 WebSocket 配置。
 */
@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class TaskLogWebSocketConfig implements WebSocketConfigurer {

    private final TaskLogWebSocketHandler taskLogWebSocketHandler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(taskLogWebSocketHandler, "/ws/task-log")
                .setAllowedOriginPatterns("*");
    }
}
