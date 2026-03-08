package com.omnigate.user.service.impl;

import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import com.omnigate.user.entity.SystemSettingEntry;
import com.omnigate.user.mapper.CloudMailSystemSettingMapper;
import com.omnigate.user.model.dto.CloudMailSystemSettingUpdateDTO;
import com.omnigate.user.model.vo.CloudMailSystemSettingVO;
import com.omnigate.user.service.CloudMailSystemSettingService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * CloudMail 系统配置服务实现。
 */
@Service
@RequiredArgsConstructor
public class CloudMailSystemSettingServiceImpl implements CloudMailSystemSettingService {

    private static final String ACCOUNT_EMAIL_KEY = "cloudmail.account_email";
    private static final String PASSWORD_KEY = "cloudmail.password";
    private static final String AUTH_URL_KEY = "cloudmail.auth_url";
    private static final String REGISTRATION_EMAIL_SUFFIX_KEY = "chatgpt.registration_email_suffix";

    private static final String ACCOUNT_EMAIL_DESCRIPTION = "CloudMail 登录账号（邮箱）";
    private static final String PASSWORD_DESCRIPTION = "CloudMail 登录密码";
    private static final String AUTH_URL_DESCRIPTION = "CloudMail 登录网址";
    private static final String REGISTRATION_EMAIL_SUFFIX_DESCRIPTION = "ChatGPT 注册邮箱后缀";

    private static final List<String> CLOUDMAIL_SETTING_KEYS = List.of(
            ACCOUNT_EMAIL_KEY,
            PASSWORD_KEY,
            AUTH_URL_KEY,
            REGISTRATION_EMAIL_SUFFIX_KEY
    );

    private final CloudMailSystemSettingMapper cloudMailSystemSettingMapper;

    /**
     * 读取 CloudMail 配置。
     *
     * @return CloudMail 配置
     */
    @Override
    public CloudMailSystemSettingVO getSettings() {
        Map<String, SystemSettingEntry> settingMap = cloudMailSystemSettingMapper.selectByKeys(CLOUDMAIL_SETTING_KEYS)
                .stream()
                .collect(Collectors.toMap(SystemSettingEntry::getKey, Function.identity(), (left, right) -> right));

        CloudMailSystemSettingVO result = new CloudMailSystemSettingVO();
        result.setAccountEmail(normalizeText(settingMap.get(ACCOUNT_EMAIL_KEY) == null ? null : settingMap.get(ACCOUNT_EMAIL_KEY).getValue()));
        result.setPassword(normalizeText(settingMap.get(PASSWORD_KEY) == null ? null : settingMap.get(PASSWORD_KEY).getValue()));
        result.setAuthUrl(normalizeText(settingMap.get(AUTH_URL_KEY) == null ? null : settingMap.get(AUTH_URL_KEY).getValue()));
        result.setRegistrationEmailSuffix(normalizeEmailSuffix(settingMap.get(REGISTRATION_EMAIL_SUFFIX_KEY) == null
                ? null
                : settingMap.get(REGISTRATION_EMAIL_SUFFIX_KEY).getValue()));
        return result;
    }

    /**
     * 保存 CloudMail 配置。
     *
     * @param updateDTO 更新参数
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateSettings(CloudMailSystemSettingUpdateDTO updateDTO) {
        String accountEmail = normalizeRequiredText(updateDTO.getAccountEmail(), "CloudMail 账号不能为空");
        String password = normalizeRequiredText(updateDTO.getPassword(), "CloudMail 密码不能为空");
        String authUrl = normalizeRequiredText(updateDTO.getAuthUrl(), "CloudMail 登录网址不能为空");
        String registrationEmailSuffix = normalizeRequiredText(updateDTO.getRegistrationEmailSuffix(), "ChatGPT 注册邮箱后缀不能为空");
        validateAuthUrl(authUrl);
        registrationEmailSuffix = normalizeEmailSuffix(registrationEmailSuffix);

        cloudMailSystemSettingMapper.upsert(ACCOUNT_EMAIL_KEY, accountEmail, ACCOUNT_EMAIL_DESCRIPTION);
        cloudMailSystemSettingMapper.upsert(PASSWORD_KEY, password, PASSWORD_DESCRIPTION);
        cloudMailSystemSettingMapper.upsert(AUTH_URL_KEY, authUrl, AUTH_URL_DESCRIPTION);
        cloudMailSystemSettingMapper.upsert(
                REGISTRATION_EMAIL_SUFFIX_KEY,
                registrationEmailSuffix,
                REGISTRATION_EMAIL_SUFFIX_DESCRIPTION
        );
    }

    /**
     * 统一去除首尾空白。
     *
     * @param text 原始文本
     * @return 去空白后的文本
     */
    private String normalizeText(String text) {
        return text == null ? null : text.trim();
    }

    /**
     * 规范化必填文本。
     *
     * @param text 原始文本
     * @param message 为空时的提示信息
     * @return 规范化后的文本
     */
    private String normalizeRequiredText(String text, String message) {
        String normalized = normalizeText(text);
        if (normalized == null || normalized.isBlank()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, message);
        }
        return normalized;
    }

    /**
     * 校验登录网址是否合法。
     *
     * @param authUrl 登录网址
     */
    private void validateAuthUrl(String authUrl) {
        try {
            URI uri = new URI(authUrl);
            String scheme = uri.getScheme();
            String host = uri.getHost();
            if (scheme == null || host == null || (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme))) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "CloudMail 登录网址必须是合法的 http/https URL");
            }
        } catch (URISyntaxException ex) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "CloudMail 登录网址格式不正确");
        }
    }

    /**
     * 规范化并校验 ChatGPT 注册邮箱后缀。
     *
     * @param emailSuffix 邮箱后缀
     * @return 规范化后的域名
     */
    private String normalizeEmailSuffix(String emailSuffix) {
        String normalized = normalizeText(emailSuffix);
        if (normalized == null || normalized.isBlank()) {
            return normalized;
        }

        if (normalized.startsWith("@")) {
            normalized = normalized.substring(1);
        }
        if (normalized.contains("@")) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "邮箱后缀只能填写域名，不要填写完整邮箱");
        }
        if (normalized.chars().anyMatch(Character::isWhitespace)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "邮箱后缀不能包含空白字符");
        }
        if (!normalized.contains(".")) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "邮箱后缀格式不正确，至少应包含一个点");
        }
        return normalized.toLowerCase();
    }
}
