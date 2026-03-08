INSERT INTO system_settings (key, value, description)
VALUES ('cloudmail.account_email', NULL, 'CloudMail 登录账号（邮箱）')
ON CONFLICT (key) DO NOTHING;

INSERT INTO system_settings (key, value, description)
VALUES ('cloudmail.password', NULL, 'CloudMail 登录密码')
ON CONFLICT (key) DO NOTHING;

INSERT INTO system_settings (key, value, description)
VALUES ('cloudmail.auth_url', NULL, 'CloudMail 登录网址')
ON CONFLICT (key) DO NOTHING;
