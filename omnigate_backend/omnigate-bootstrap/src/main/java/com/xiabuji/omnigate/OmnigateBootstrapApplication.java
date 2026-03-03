package com.xiabuji.omnigate;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {"com.xiabuji.omnigate", "com.omnigate"})
public class OmnigateBootstrapApplication {

    public static void main(String[] args) {
        SpringApplication.run(OmnigateBootstrapApplication.class, args);
    }
}
