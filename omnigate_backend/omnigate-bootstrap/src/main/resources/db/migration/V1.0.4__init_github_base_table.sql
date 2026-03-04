-- GitHub 资产模块基础表初始化

CREATE TABLE IF NOT EXISTS acc_github_base
(
    id             BIGSERIAL PRIMARY KEY,
    username       VARCHAR(128) NOT NULL,
    email          VARCHAR(128) NOT NULL,
    password       VARCHAR(255) NOT NULL,
    totp_secret    VARCHAR(255) NOT NULL,
    proxy_ip       VARCHAR(64),
    account_status VARCHAR(32)  NOT NULL DEFAULT 'active',
    created_by     BIGINT,
    updated_by     BIGINT,
    deleted        INTEGER      NOT NULL DEFAULT 0,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc_github_base IS 'GitHub账号基础信息表';
COMMENT ON COLUMN acc_github_base.id IS '主键ID';
COMMENT ON COLUMN acc_github_base.username IS 'GitHub用户名';
COMMENT ON COLUMN acc_github_base.email IS '绑定邮箱';
COMMENT ON COLUMN acc_github_base.password IS '登录密码（加密存储）';
COMMENT ON COLUMN acc_github_base.totp_secret IS '二次验证TOTP密钥（加密存储）';
COMMENT ON COLUMN acc_github_base.proxy_ip IS '固定代理IP';
COMMENT ON COLUMN acc_github_base.account_status IS '账号状态：active, locked, banned';
COMMENT ON COLUMN acc_github_base.created_by IS '创建人';
COMMENT ON COLUMN acc_github_base.updated_by IS '更新人';
COMMENT ON COLUMN acc_github_base.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_github_base.created_at IS '创建时间';
COMMENT ON COLUMN acc_github_base.updated_at IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_acc_github_base_username ON acc_github_base (username);
CREATE INDEX IF NOT EXISTS idx_acc_github_base_email ON acc_github_base (email);
CREATE INDEX IF NOT EXISTS idx_acc_github_base_account_status ON acc_github_base (account_status);
CREATE INDEX IF NOT EXISTS idx_acc_github_base_deleted ON acc_github_base (deleted);
