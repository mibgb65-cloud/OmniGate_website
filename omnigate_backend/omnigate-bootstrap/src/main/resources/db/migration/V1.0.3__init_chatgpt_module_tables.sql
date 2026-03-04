-- ChatGPT 资产模块初始化表结构

-- ChatGPT 账号基础信息表
CREATE TABLE IF NOT EXISTS acc_chatgpt_base
(
    id             BIGSERIAL PRIMARY KEY,
    email          VARCHAR(128) NOT NULL,
    password       VARCHAR(255),
    session_token  VARCHAR(1024),
    sub_tier       VARCHAR(32)  NOT NULL DEFAULT 'free',
    account_status VARCHAR(32)  NOT NULL DEFAULT 'active',
    expire_date    DATE,
    created_by     BIGINT,
    updated_by     BIGINT,
    deleted        INTEGER      NOT NULL DEFAULT 0,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc_chatgpt_base IS 'ChatGPT账号基础信息表';
COMMENT ON COLUMN acc_chatgpt_base.id IS '主键ID';
COMMENT ON COLUMN acc_chatgpt_base.email IS '账号邮箱（唯一）';
COMMENT ON COLUMN acc_chatgpt_base.password IS '登录密码（加密存储）';
COMMENT ON COLUMN acc_chatgpt_base.session_token IS '持久化登录Token（加密存储）';
COMMENT ON COLUMN acc_chatgpt_base.sub_tier IS '订阅层级：free, plus, team, go';
COMMENT ON COLUMN acc_chatgpt_base.account_status IS '账号状态：active, locked, banned';
COMMENT ON COLUMN acc_chatgpt_base.expire_date IS '订阅到期日期';
COMMENT ON COLUMN acc_chatgpt_base.created_by IS '创建人';
COMMENT ON COLUMN acc_chatgpt_base.updated_by IS '更新人';
COMMENT ON COLUMN acc_chatgpt_base.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_chatgpt_base.created_at IS '创建时间';
COMMENT ON COLUMN acc_chatgpt_base.updated_at IS '更新时间';

CREATE UNIQUE INDEX IF NOT EXISTS uk_acc_chatgpt_base_email ON acc_chatgpt_base (email);
CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_base_sub_tier ON acc_chatgpt_base (sub_tier);
CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_base_account_status ON acc_chatgpt_base (account_status);
CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_base_deleted ON acc_chatgpt_base (deleted);

-- ChatGPT Team 车队表
CREATE TABLE IF NOT EXISTS acc_chatgpt_team
(
    id          BIGSERIAL PRIMARY KEY,
    team_name   VARCHAR(128) NOT NULL,
    owner_id    BIGINT       NOT NULL,
    max_members SMALLINT     NOT NULL DEFAULT 5,
    expire_date DATE,
    created_by  BIGINT,
    updated_by  BIGINT,
    deleted     INTEGER      NOT NULL DEFAULT 0,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc_chatgpt_team IS 'ChatGPT Team车队表';
COMMENT ON COLUMN acc_chatgpt_team.id IS '主键ID';
COMMENT ON COLUMN acc_chatgpt_team.team_name IS '团队名称';
COMMENT ON COLUMN acc_chatgpt_team.owner_id IS '车头账号ID（关联acc_chatgpt_base.id）';
COMMENT ON COLUMN acc_chatgpt_team.max_members IS '最大成员数，默认5';
COMMENT ON COLUMN acc_chatgpt_team.expire_date IS '车队到期日期';
COMMENT ON COLUMN acc_chatgpt_team.created_by IS '创建人';
COMMENT ON COLUMN acc_chatgpt_team.updated_by IS '更新人';
COMMENT ON COLUMN acc_chatgpt_team.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_chatgpt_team.created_at IS '创建时间';
COMMENT ON COLUMN acc_chatgpt_team.updated_at IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_team_owner_id ON acc_chatgpt_team (owner_id);
CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_team_expire_date ON acc_chatgpt_team (expire_date);
CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_team_deleted ON acc_chatgpt_team (deleted);

-- ChatGPT Team 成员关联表
CREATE TABLE IF NOT EXISTS acc_chatgpt_team_member
(
    id          BIGSERIAL PRIMARY KEY,
    team_id     BIGINT      NOT NULL,
    member_id   BIGINT      NOT NULL,
    member_role VARCHAR(32) NOT NULL,
    join_time   TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  BIGINT,
    updated_by  BIGINT,
    deleted     INTEGER     NOT NULL DEFAULT 0,
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc_chatgpt_team_member IS 'ChatGPT Team成员关联表';
COMMENT ON COLUMN acc_chatgpt_team_member.id IS '主键ID';
COMMENT ON COLUMN acc_chatgpt_team_member.team_id IS '车队ID（关联acc_chatgpt_team.id）';
COMMENT ON COLUMN acc_chatgpt_team_member.member_id IS '成员账号ID（关联acc_chatgpt_base.id）';
COMMENT ON COLUMN acc_chatgpt_team_member.member_role IS '成员角色：owner, member';
COMMENT ON COLUMN acc_chatgpt_team_member.join_time IS '加入时间';
COMMENT ON COLUMN acc_chatgpt_team_member.created_by IS '创建人';
COMMENT ON COLUMN acc_chatgpt_team_member.updated_by IS '更新人';
COMMENT ON COLUMN acc_chatgpt_team_member.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_chatgpt_team_member.created_at IS '创建时间';
COMMENT ON COLUMN acc_chatgpt_team_member.updated_at IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_team_member_team_id ON acc_chatgpt_team_member (team_id);
CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_team_member_member_id ON acc_chatgpt_team_member (member_id);
CREATE INDEX IF NOT EXISTS idx_acc_chatgpt_team_member_deleted ON acc_chatgpt_team_member (deleted);
CREATE UNIQUE INDEX IF NOT EXISTS uk_acc_chatgpt_team_member_team_member_deleted
    ON acc_chatgpt_team_member (team_id, member_id, deleted);

DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_acc_chatgpt_team_owner_id') THEN
        ALTER TABLE acc_chatgpt_team
            ADD CONSTRAINT fk_acc_chatgpt_team_owner_id
                FOREIGN KEY (owner_id) REFERENCES acc_chatgpt_base (id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_acc_chatgpt_team_member_team_id') THEN
        ALTER TABLE acc_chatgpt_team_member
            ADD CONSTRAINT fk_acc_chatgpt_team_member_team_id
                FOREIGN KEY (team_id) REFERENCES acc_chatgpt_team (id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_acc_chatgpt_team_member_member_id') THEN
        ALTER TABLE acc_chatgpt_team_member
            ADD CONSTRAINT fk_acc_chatgpt_team_member_member_id
                FOREIGN KEY (member_id) REFERENCES acc_chatgpt_base (id);
    END IF;
END
$$;
