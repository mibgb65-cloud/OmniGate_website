-- Google 资产模块初始化表结构

-- Google 账号基础信息表
CREATE TABLE IF NOT EXISTS acc_google_base
(
    id             BIGSERIAL PRIMARY KEY,
    email          VARCHAR(128) NOT NULL,
    password       VARCHAR(255) NOT NULL,
    recovery_email VARCHAR(128),
    totp_secret    VARCHAR(255) NOT NULL,
    region         VARCHAR(64),
    remark         VARCHAR(255),
    sync_status    SMALLINT     NOT NULL DEFAULT 0,
    created_by     BIGINT,
    updated_by     BIGINT,
    deleted        INTEGER      NOT NULL DEFAULT 0,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc_google_base IS 'Google账号基础信息表';
COMMENT ON COLUMN acc_google_base.id IS '主键ID';
COMMENT ON COLUMN acc_google_base.email IS 'Google账号邮箱（唯一）';
COMMENT ON COLUMN acc_google_base.password IS '账号密码（加密后存储）';
COMMENT ON COLUMN acc_google_base.recovery_email IS '辅助恢复邮箱';
COMMENT ON COLUMN acc_google_base.totp_secret IS '二次验证TOTP密钥';
COMMENT ON COLUMN acc_google_base.region IS '账号所属地区';
COMMENT ON COLUMN acc_google_base.remark IS '备注信息';
COMMENT ON COLUMN acc_google_base.sync_status IS '同步状态：0-未开始，1-等待，2-处理中，3-成功，4-失败';
COMMENT ON COLUMN acc_google_base.created_by IS '创建人';
COMMENT ON COLUMN acc_google_base.updated_by IS '更新人';
COMMENT ON COLUMN acc_google_base.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_google_base.created_at IS '创建时间';
COMMENT ON COLUMN acc_google_base.updated_at IS '更新时间';

CREATE UNIQUE INDEX IF NOT EXISTS uk_acc_google_base_email ON acc_google_base (email);
CREATE INDEX IF NOT EXISTS idx_acc_google_base_sync_status ON acc_google_base (sync_status);
CREATE INDEX IF NOT EXISTS idx_acc_google_base_deleted ON acc_google_base (deleted);

-- Google 账号状态信息表
CREATE TABLE IF NOT EXISTS acc_google_status
(
    account_id          BIGINT PRIMARY KEY,
    sub_tier            VARCHAR(32) NOT NULL DEFAULT 'NONE',
    family_status       SMALLINT    NOT NULL DEFAULT 0,
    expire_date         DATE,
    invite_link_status  SMALLINT    NOT NULL DEFAULT 0,
    student_link        VARCHAR(512),
    invited_count       SMALLINT    NOT NULL DEFAULT 0,
    created_by          BIGINT,
    updated_by          BIGINT,
    deleted             INTEGER     NOT NULL DEFAULT 0,
    created_at          TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_acc_google_status_invited_count CHECK (invited_count BETWEEN 0 AND 5)
);

COMMENT ON TABLE acc_google_status IS 'Google账号状态信息表';
COMMENT ON COLUMN acc_google_status.account_id IS '账号ID（关联acc_google_base.id）';
COMMENT ON COLUMN acc_google_status.sub_tier IS '订阅类型：NONE，AI_PLUS，AI_PRO，AI_ULTRA';
COMMENT ON COLUMN acc_google_status.family_status IS '家庭组状态：0-未开通，1-已开通';
COMMENT ON COLUMN acc_google_status.expire_date IS '订阅到期日期（年月日）';
COMMENT ON COLUMN acc_google_status.invite_link_status IS '邀请链接状态：0-无，1-有';
COMMENT ON COLUMN acc_google_status.student_link IS '学生认证链接';
COMMENT ON COLUMN acc_google_status.invited_count IS '已邀请成员人数（最大5）';
COMMENT ON COLUMN acc_google_status.created_by IS '创建人';
COMMENT ON COLUMN acc_google_status.updated_by IS '更新人';
COMMENT ON COLUMN acc_google_status.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_google_status.created_at IS '创建时间';
COMMENT ON COLUMN acc_google_status.updated_at IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_acc_google_status_sub_tier ON acc_google_status (sub_tier);
CREATE INDEX IF NOT EXISTS idx_acc_google_status_family_status ON acc_google_status (family_status);
CREATE INDEX IF NOT EXISTS idx_acc_google_status_deleted ON acc_google_status (deleted);

-- Google 家庭组成员表
CREATE TABLE IF NOT EXISTS acc_google_family_member
(
    id           BIGSERIAL PRIMARY KEY,
    account_id   BIGINT       NOT NULL,
    member_name  VARCHAR(128) NOT NULL,
    member_email VARCHAR(128) NOT NULL,
    invite_date  DATE,
    member_role  SMALLINT     NOT NULL,
    created_by   BIGINT,
    updated_by   BIGINT,
    deleted      INTEGER      NOT NULL DEFAULT 0,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc_google_family_member IS 'Google家庭组成员表';
COMMENT ON COLUMN acc_google_family_member.id IS '主键ID';
COMMENT ON COLUMN acc_google_family_member.account_id IS '账号ID（关联acc_google_base.id）';
COMMENT ON COLUMN acc_google_family_member.member_name IS '家庭组成员名称';
COMMENT ON COLUMN acc_google_family_member.member_email IS '家庭组成员邮箱';
COMMENT ON COLUMN acc_google_family_member.invite_date IS '邀请日期（年月日）';
COMMENT ON COLUMN acc_google_family_member.member_role IS '成员身份：1-管理员，2-成员';
COMMENT ON COLUMN acc_google_family_member.created_by IS '创建人';
COMMENT ON COLUMN acc_google_family_member.updated_by IS '更新人';
COMMENT ON COLUMN acc_google_family_member.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_google_family_member.created_at IS '创建时间';
COMMENT ON COLUMN acc_google_family_member.updated_at IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_acc_google_family_member_account_id ON acc_google_family_member (account_id);
CREATE INDEX IF NOT EXISTS idx_acc_google_family_member_member_email ON acc_google_family_member (member_email);
CREATE INDEX IF NOT EXISTS idx_acc_google_family_member_deleted ON acc_google_family_member (deleted);
CREATE UNIQUE INDEX IF NOT EXISTS uk_acc_google_family_member_acc_email_deleted
    ON acc_google_family_member (account_id, member_email, deleted);

-- Google 邀请链接表（4个月免费链接）
CREATE TABLE IF NOT EXISTS acc_google_invite_link
(
    id         BIGSERIAL PRIMARY KEY,
    account_id BIGINT        NOT NULL,
    invite_url VARCHAR(1024) NOT NULL,
    used_count SMALLINT      NOT NULL DEFAULT 0,
    created_by BIGINT,
    updated_by BIGINT,
    deleted    INTEGER       NOT NULL DEFAULT 0,
    created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE acc_google_invite_link IS 'Google账号邀请链接表（4个月免费链接）';
COMMENT ON COLUMN acc_google_invite_link.id IS '主键ID';
COMMENT ON COLUMN acc_google_invite_link.account_id IS '账号ID（关联acc_google_base.id）';
COMMENT ON COLUMN acc_google_invite_link.invite_url IS '邀请链接URL';
COMMENT ON COLUMN acc_google_invite_link.used_count IS '邀请链接已使用次数';
COMMENT ON COLUMN acc_google_invite_link.created_by IS '创建人';
COMMENT ON COLUMN acc_google_invite_link.updated_by IS '更新人';
COMMENT ON COLUMN acc_google_invite_link.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_google_invite_link.created_at IS '创建时间';
COMMENT ON COLUMN acc_google_invite_link.updated_at IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_acc_google_invite_link_account_id ON acc_google_invite_link (account_id);
CREATE INDEX IF NOT EXISTS idx_acc_google_invite_link_deleted ON acc_google_invite_link (deleted);
CREATE UNIQUE INDEX IF NOT EXISTS uk_acc_google_invite_link_account_url_deleted
    ON acc_google_invite_link (account_id, invite_url, deleted);

DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_acc_google_status_account_id') THEN
        ALTER TABLE acc_google_status
            ADD CONSTRAINT fk_acc_google_status_account_id
                FOREIGN KEY (account_id) REFERENCES acc_google_base (id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_acc_google_family_member_account_id') THEN
        ALTER TABLE acc_google_family_member
            ADD CONSTRAINT fk_acc_google_family_member_account_id
                FOREIGN KEY (account_id) REFERENCES acc_google_base (id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_acc_google_invite_link_account_id') THEN
        ALTER TABLE acc_google_invite_link
            ADD CONSTRAINT fk_acc_google_invite_link_account_id
                FOREIGN KEY (account_id) REFERENCES acc_google_base (id);
    END IF;
END
$$;
