ALTER TABLE acc_chatgpt_base
    ADD COLUMN IF NOT EXISTS is_sold BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN acc_chatgpt_base.is_sold IS '是否已出售：false-未出售，true-已出售';
