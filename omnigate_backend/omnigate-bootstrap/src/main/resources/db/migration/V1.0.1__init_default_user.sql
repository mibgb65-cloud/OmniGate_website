-- 默认管理员初始化数据
-- 初始账号：admin
-- 初始密码：ChangeMe123!
-- 请在首次登录后立即修改默认密码。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) 初始化默认管理员角色
INSERT INTO sys_role (role_code, role_name, description, status, sort, ext_info, created_by, updated_by, deleted)
VALUES ('ADMIN', '超级管理员', '系统默认超级管理员角色', 1, 0, '{}'::jsonb, 0, 0, 0)
ON CONFLICT (role_code) DO NOTHING;

-- 2) 初始化默认管理员用户（密码采用 BCrypt）
INSERT INTO sys_user (username,
                      email,
                      password_hash,
                      nickname,
                      status,
                      ext_info,
                      created_by,
                      updated_by,
                      deleted)
SELECT 'admin',
       'admin@omnigate.local',
       crypt('ChangeMe123!', gen_salt('bf', 10)),
       '系统管理员',
       1,
       '{}'::jsonb,
       0,
       0,
       0
WHERE NOT EXISTS (
    SELECT 1
    FROM sys_user
    WHERE username = 'admin'
       OR email = 'admin@omnigate.local'
);

-- 3) 绑定管理员用户与管理员角色
INSERT INTO sys_user_role (user_id, role_id, created_by, updated_by, deleted)
SELECT u.id, r.id, 0, 0, 0
FROM sys_user u
         JOIN sys_role r ON r.role_code = 'ADMIN'
WHERE u.username = 'admin'
  AND NOT EXISTS (
    SELECT 1
    FROM sys_user_role ur
    WHERE ur.user_id = u.id
      AND ur.role_id = r.id
      AND ur.deleted = 0
);
