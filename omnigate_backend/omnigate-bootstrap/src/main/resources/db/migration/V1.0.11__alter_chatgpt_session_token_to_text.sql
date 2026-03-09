ALTER TABLE acc_chatgpt_base
    ALTER COLUMN session_token TYPE TEXT;

COMMENT ON COLUMN acc_chatgpt_base.session_token IS '持久化登录Token（加密存储，使用TEXT兼容长Token）';
