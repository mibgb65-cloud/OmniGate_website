package com.xiabuji.omnigate;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class OmnigateBootstrapApplicationTests {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private UserDetailsService userDetailsService;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Test
    void shouldLoadUserFromSysUserTablesByUsernameAndEmail() {
        String suffix = UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        String username = "it_user_" + suffix;
        String email = username + "@omnigate.test";
        String rawPassword = "P@ssw0rd123!";
        String encodedPassword = passwordEncoder.encode(rawPassword);
        String roleCode = "ADMIN_" + suffix.toUpperCase();

        jdbcTemplate.update(
                "INSERT INTO sys_user (username, email, password_hash, status, deleted) VALUES (?, ?, ?, ?, ?)",
                username, email, encodedPassword, 1, 0
        );

        Long userId = jdbcTemplate.queryForObject(
                "SELECT id FROM sys_user WHERE username = ?",
                Long.class,
                username
        );
        assertThat(userId).isNotNull();

        jdbcTemplate.update(
                "INSERT INTO sys_role (role_code, role_name, status, deleted) VALUES (?, ?, ?, ?)",
                roleCode, "集成测试角色", 1, 0
        );

        Long roleId = jdbcTemplate.queryForObject(
                "SELECT id FROM sys_role WHERE role_code = ?",
                Long.class,
                roleCode
        );
        assertThat(roleId).isNotNull();

        jdbcTemplate.update(
                "INSERT INTO sys_user_role (user_id, role_id, deleted) VALUES (?, ?, ?)",
                userId, roleId, 0
        );

        UserDetails byUsername = userDetailsService.loadUserByUsername(username);
        UserDetails byEmail = userDetailsService.loadUserByUsername(email);

        assertThat(byUsername.getUsername()).isEqualTo(username);
        assertThat(byEmail.getUsername()).isEqualTo(username);
        assertThat(byUsername.isEnabled()).isTrue();
        assertThat(passwordEncoder.matches(rawPassword, byUsername.getPassword())).isTrue();
        assertThat(byUsername.getAuthorities())
                .extracting(GrantedAuthority::getAuthority)
                .contains("ROLE_" + roleCode);
    }
}
