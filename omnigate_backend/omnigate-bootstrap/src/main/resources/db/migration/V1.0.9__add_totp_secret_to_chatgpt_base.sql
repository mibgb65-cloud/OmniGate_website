ALTER TABLE acc_chatgpt_base
    ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255);

COMMENT ON COLUMN acc_chatgpt_base.totp_secret IS '二次验证TOTP密钥（加密存储）';
