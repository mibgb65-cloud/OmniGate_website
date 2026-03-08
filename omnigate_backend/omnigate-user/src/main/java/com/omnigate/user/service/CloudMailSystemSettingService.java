package com.omnigate.user.service;

import com.omnigate.user.model.dto.CloudMailSystemSettingUpdateDTO;
import com.omnigate.user.model.vo.CloudMailSystemSettingVO;

/**
 * CloudMail 系统配置服务。
 */
public interface CloudMailSystemSettingService {

    /**
     * 读取 CloudMail 系统配置。
     *
     * @return CloudMail 配置
     */
    CloudMailSystemSettingVO getSettings();

    /**
     * 更新 CloudMail 系统配置。
     *
     * @param updateDTO 更新参数
     */
    void updateSettings(CloudMailSystemSettingUpdateDTO updateDTO);
}
