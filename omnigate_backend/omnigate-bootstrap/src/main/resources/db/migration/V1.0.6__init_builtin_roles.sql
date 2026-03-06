-- 初始化内置角色数据
-- 为用户管理页提供可分配的标准角色集合

INSERT INTO sys_role (role_code, role_name, description, status, sort, ext_info, created_by, updated_by, deleted)
VALUES ('OPERATOR', '运营管理员', '可执行日常业务操作与账号维护', 1, 10, '{}'::jsonb, 0, 0, 0)
ON CONFLICT (role_code) DO NOTHING;

INSERT INTO sys_role (role_code, role_name, description, status, sort, ext_info, created_by, updated_by, deleted)
VALUES ('VIEWER', '只读观察者', '仅可查看数据，不可执行修改操作', 1, 20, '{}'::jsonb, 0, 0, 0)
ON CONFLICT (role_code) DO NOTHING;
