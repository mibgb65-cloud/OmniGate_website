-- 系统用户表
CREATE TABLE IF NOT EXISTS sys_user (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    email VARCHAR(128) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(64),
    avatar_url VARCHAR(255),
    status SMALLINT NOT NULL DEFAULT 1,
    last_login_ip VARCHAR(64),
    last_login_at TIMESTAMP,
    ext_info JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by BIGINT,
    updated_by BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER NOT NULL DEFAULT 0
);

COMMENT ON TABLE sys_user IS '系统用户表';
COMMENT ON COLUMN sys_user.id IS '主键 ID';
COMMENT ON COLUMN sys_user.username IS '用户名';
COMMENT ON COLUMN sys_user.email IS '邮箱';
COMMENT ON COLUMN sys_user.password_hash IS '密码哈希';
COMMENT ON COLUMN sys_user.nickname IS '昵称';
COMMENT ON COLUMN sys_user.avatar_url IS '头像地址';
COMMENT ON COLUMN sys_user.status IS '状态：1-正常，0-禁用';
COMMENT ON COLUMN sys_user.last_login_ip IS '最后登录 IP';
COMMENT ON COLUMN sys_user.last_login_at IS '最后登录时间';
COMMENT ON COLUMN sys_user.ext_info IS '扩展信息（JSONB）';
COMMENT ON COLUMN sys_user.created_by IS '创建人';
COMMENT ON COLUMN sys_user.updated_by IS '更新人';
COMMENT ON COLUMN sys_user.created_at IS '创建时间';
COMMENT ON COLUMN sys_user.updated_at IS '更新时间';
COMMENT ON COLUMN sys_user.deleted IS '逻辑删除标记：0-未删，1-已删';

CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_user_username ON sys_user (username);
CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_user_email ON sys_user (email);
CREATE INDEX IF NOT EXISTS idx_sys_user_status ON sys_user (status);
CREATE INDEX IF NOT EXISTS idx_sys_user_deleted ON sys_user (deleted);

-- 系统角色表
CREATE TABLE IF NOT EXISTS sys_role (
    id BIGSERIAL PRIMARY KEY,
    role_code VARCHAR(64) NOT NULL,
    role_name VARCHAR(64) NOT NULL,
    description VARCHAR(255),
    status SMALLINT NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0,
    ext_info JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by BIGINT,
    updated_by BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER NOT NULL DEFAULT 0
);

COMMENT ON TABLE sys_role IS '系统角色表';
COMMENT ON COLUMN sys_role.id IS '主键 ID';
COMMENT ON COLUMN sys_role.role_code IS '角色编码';
COMMENT ON COLUMN sys_role.role_name IS '角色名称';
COMMENT ON COLUMN sys_role.description IS '角色描述';
COMMENT ON COLUMN sys_role.status IS '状态：1-正常，0-禁用';
COMMENT ON COLUMN sys_role.sort IS '排序值';
COMMENT ON COLUMN sys_role.ext_info IS '扩展信息（JSONB）';
COMMENT ON COLUMN sys_role.created_by IS '创建人';
COMMENT ON COLUMN sys_role.updated_by IS '更新人';
COMMENT ON COLUMN sys_role.created_at IS '创建时间';
COMMENT ON COLUMN sys_role.updated_at IS '更新时间';
COMMENT ON COLUMN sys_role.deleted IS '逻辑删除标记：0-未删，1-已删';

CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_role_role_code ON sys_role (role_code);
CREATE INDEX IF NOT EXISTS idx_sys_role_status ON sys_role (status);
CREATE INDEX IF NOT EXISTS idx_sys_role_deleted ON sys_role (deleted);

-- 用户角色关联表
CREATE TABLE IF NOT EXISTS sys_user_role (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    created_by BIGINT,
    updated_by BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER NOT NULL DEFAULT 0
);

COMMENT ON TABLE sys_user_role IS '用户角色关联表';
COMMENT ON COLUMN sys_user_role.id IS '主键 ID';
COMMENT ON COLUMN sys_user_role.user_id IS '用户 ID';
COMMENT ON COLUMN sys_user_role.role_id IS '角色 ID';
COMMENT ON COLUMN sys_user_role.created_by IS '创建人';
COMMENT ON COLUMN sys_user_role.updated_by IS '更新人';
COMMENT ON COLUMN sys_user_role.created_at IS '创建时间';
COMMENT ON COLUMN sys_user_role.updated_at IS '更新时间';
COMMENT ON COLUMN sys_user_role.deleted IS '逻辑删除标记：0-未删，1-已删';

CREATE UNIQUE INDEX IF NOT EXISTS uk_sys_user_role_user_role_deleted ON sys_user_role (user_id, role_id, deleted);
CREATE INDEX IF NOT EXISTS idx_sys_user_role_user_id ON sys_user_role (user_id);
CREATE INDEX IF NOT EXISTS idx_sys_user_role_role_id ON sys_user_role (role_id);

DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sys_user_role_user_id') THEN
        ALTER TABLE sys_user_role
            ADD CONSTRAINT fk_sys_user_role_user_id
                FOREIGN KEY (user_id) REFERENCES sys_user (id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sys_user_role_role_id') THEN
        ALTER TABLE sys_user_role
            ADD CONSTRAINT fk_sys_user_role_role_id
                FOREIGN KEY (role_id) REFERENCES sys_role (id);
    END IF;
END
$$;

-- 登录日志表
CREATE TABLE IF NOT EXISTS sys_login_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    login_account VARCHAR(128) NOT NULL,
    login_type VARCHAR(32) NOT NULL DEFAULT 'PASSWORD',
    client_ip VARCHAR(64),
    user_agent VARCHAR(512),
    login_status SMALLINT NOT NULL DEFAULT 1,
    fail_reason VARCHAR(255),
    login_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ext_info JSONB NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE sys_login_log IS '系统登录日志表';
COMMENT ON COLUMN sys_login_log.id IS '主键 ID';
COMMENT ON COLUMN sys_login_log.user_id IS '用户 ID';
COMMENT ON COLUMN sys_login_log.login_account IS '登录账号（用户名或邮箱）';
COMMENT ON COLUMN sys_login_log.login_type IS '登录类型';
COMMENT ON COLUMN sys_login_log.client_ip IS '客户端 IP';
COMMENT ON COLUMN sys_login_log.user_agent IS '客户端 User-Agent';
COMMENT ON COLUMN sys_login_log.login_status IS '登录状态：1-成功，0-失败';
COMMENT ON COLUMN sys_login_log.fail_reason IS '失败原因';
COMMENT ON COLUMN sys_login_log.login_at IS '登录时间';
COMMENT ON COLUMN sys_login_log.ext_info IS '扩展信息（JSONB）';

CREATE INDEX IF NOT EXISTS idx_sys_login_log_user_id ON sys_login_log (user_id);
CREATE INDEX IF NOT EXISTS idx_sys_login_log_login_at ON sys_login_log (login_at DESC);
CREATE INDEX IF NOT EXISTS idx_sys_login_log_login_status ON sys_login_log (login_status);
