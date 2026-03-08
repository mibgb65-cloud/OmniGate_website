INSERT INTO system_settings (key, value, description)
VALUES ('chatgpt.registration_email_suffix', NULL, 'ChatGPT 注册邮箱后缀（仅域名部分）')
ON CONFLICT (key) DO NOTHING;
