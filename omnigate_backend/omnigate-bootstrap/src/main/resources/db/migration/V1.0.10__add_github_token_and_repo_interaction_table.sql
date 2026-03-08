-- GitHub 模块补充 Token 字段与仓库交互记录表

ALTER TABLE IF EXISTS acc_github_base
    ADD COLUMN IF NOT EXISTS access_token VARCHAR(1024),
    ADD COLUMN IF NOT EXISTS access_token_note VARCHAR(255);

COMMENT ON COLUMN acc_github_base.access_token IS 'GitHub Personal Access Token（加密存储）';
COMMENT ON COLUMN acc_github_base.access_token_note IS 'GitHub Token 生成时的备注名称';

-- GitHub 仓库交互记录表
CREATE TABLE IF NOT EXISTS acc_github_repo_interaction
(
    id          BIGSERIAL PRIMARY KEY,
    account_id  BIGINT        NOT NULL,
    repo_owner  VARCHAR(128)  NOT NULL,
    repo_name   VARCHAR(255)  NOT NULL,
    repo_url    VARCHAR(1024) NOT NULL,
    starred     SMALLINT      NOT NULL DEFAULT 0,
    starred_at  TIMESTAMP,
    forked      SMALLINT      NOT NULL DEFAULT 0,
    forked_at   TIMESTAMP,
    watched     SMALLINT      NOT NULL DEFAULT 0,
    watched_at  TIMESTAMP,
    followed    SMALLINT      NOT NULL DEFAULT 0,
    followed_at TIMESTAMP,
    created_by  BIGINT,
    updated_by  BIGINT,
    deleted     INTEGER       NOT NULL DEFAULT 0,
    created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_acc_github_repo_interaction_starred CHECK (starred IN (0, 1)),
    CONSTRAINT ck_acc_github_repo_interaction_forked CHECK (forked IN (0, 1)),
    CONSTRAINT ck_acc_github_repo_interaction_watched CHECK (watched IN (0, 1)),
    CONSTRAINT ck_acc_github_repo_interaction_followed CHECK (followed IN (0, 1))
);

COMMENT ON TABLE acc_github_repo_interaction IS 'GitHub仓库交互记录表';
COMMENT ON COLUMN acc_github_repo_interaction.id IS '主键ID';
COMMENT ON COLUMN acc_github_repo_interaction.account_id IS '账号ID（关联acc_github_base.id）';
COMMENT ON COLUMN acc_github_repo_interaction.repo_owner IS '仓库所属者';
COMMENT ON COLUMN acc_github_repo_interaction.repo_name IS '仓库名称';
COMMENT ON COLUMN acc_github_repo_interaction.repo_url IS '规范化后的仓库URL';
COMMENT ON COLUMN acc_github_repo_interaction.starred IS '是否已Star：0-否，1-是';
COMMENT ON COLUMN acc_github_repo_interaction.starred_at IS 'Star时间';
COMMENT ON COLUMN acc_github_repo_interaction.forked IS '是否已Fork：0-否，1-是';
COMMENT ON COLUMN acc_github_repo_interaction.forked_at IS 'Fork时间';
COMMENT ON COLUMN acc_github_repo_interaction.watched IS '是否已Watch：0-否，1-是';
COMMENT ON COLUMN acc_github_repo_interaction.watched_at IS 'Watch时间';
COMMENT ON COLUMN acc_github_repo_interaction.followed IS '是否已关注仓库Owner：0-否，1-是';
COMMENT ON COLUMN acc_github_repo_interaction.followed_at IS '关注Owner时间';
COMMENT ON COLUMN acc_github_repo_interaction.created_by IS '创建人';
COMMENT ON COLUMN acc_github_repo_interaction.updated_by IS '更新人';
COMMENT ON COLUMN acc_github_repo_interaction.deleted IS '逻辑删除标记：0-未删除，1-已删除';
COMMENT ON COLUMN acc_github_repo_interaction.created_at IS '创建时间';
COMMENT ON COLUMN acc_github_repo_interaction.updated_at IS '更新时间';

CREATE INDEX IF NOT EXISTS idx_acc_github_repo_interaction_account_id
    ON acc_github_repo_interaction (account_id);
CREATE INDEX IF NOT EXISTS idx_acc_github_repo_interaction_repo_owner_name
    ON acc_github_repo_interaction (repo_owner, repo_name);
CREATE INDEX IF NOT EXISTS idx_acc_github_repo_interaction_starred
    ON acc_github_repo_interaction (starred);
CREATE INDEX IF NOT EXISTS idx_acc_github_repo_interaction_forked
    ON acc_github_repo_interaction (forked);
CREATE INDEX IF NOT EXISTS idx_acc_github_repo_interaction_watched
    ON acc_github_repo_interaction (watched);
CREATE INDEX IF NOT EXISTS idx_acc_github_repo_interaction_followed
    ON acc_github_repo_interaction (followed);
CREATE INDEX IF NOT EXISTS idx_acc_github_repo_interaction_deleted
    ON acc_github_repo_interaction (deleted);
CREATE UNIQUE INDEX IF NOT EXISTS uk_acc_github_repo_interaction_acc_repo_deleted
    ON acc_github_repo_interaction (account_id, repo_owner, repo_name, deleted);

DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_acc_github_repo_interaction_account_id') THEN
        ALTER TABLE acc_github_repo_interaction
            ADD CONSTRAINT fk_acc_github_repo_interaction_account_id
                FOREIGN KEY (account_id) REFERENCES acc_github_base (id);
    END IF;
END
$$;
