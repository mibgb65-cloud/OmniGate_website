package com.omnigate.github.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import com.omnigate.github.entity.GithubAccountBase;
import com.omnigate.github.mapper.GithubAccountBaseMapper;
import com.omnigate.github.model.dto.GithubAccountImportDTO;
import com.omnigate.github.model.dto.GithubAccountPageQueryDTO;
import com.omnigate.github.model.dto.GithubAccountStatusDTO;
import com.omnigate.github.model.dto.GithubAccountUpdateDTO;
import com.omnigate.github.model.vo.GithubAccountVO;
import com.omnigate.github.service.GithubAccountService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * GitHub 账号基础管理服务实现。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GithubAccountServiceImpl extends ServiceImpl<GithubAccountBaseMapper, GithubAccountBase> implements GithubAccountService {

    private static final String LOG_PREFIX = "[GitHub账号]";
    private static final String STATUS_ACTIVE = "active";
    private static final int LOG_SAMPLE_LIMIT = 3;

    /**
     * 导入账号，支持单条和批量。
     *
     * @param importDTOList 导入参数列表
     * @return 导入成功数量
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public int importAccounts(List<GithubAccountImportDTO> importDTOList) {
        if (importDTOList == null || importDTOList.isEmpty()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "导入数据不能为空");
        }

        log.info("{} 开始导入账号 | count={}", LOG_PREFIX, importDTOList.size());
        assertNoRequestDuplicates(importDTOList);
        assertDbUnique(importDTOList);

        List<GithubAccountBase> entities = importDTOList.stream().map(this::toEntity).toList();
        boolean saved = saveBatch(entities);
        if (!saved) {
            log.error("{} 导入账号失败 | count={}", LOG_PREFIX, importDTOList.size());
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "导入账号失败");
        }
        log.info(
                "{} 导入账号完成 | count={} | usernames={}",
                LOG_PREFIX,
                entities.size(),
                summarizeUsernames(entities)
        );
        return entities.size();
    }

    /**
     * 分页查询账号池。
     *
     * @param queryDTO 查询参数
     * @return 分页数据
     */
    @Override
    public IPage<GithubAccountVO> pageAccounts(GithubAccountPageQueryDTO queryDTO) {
        String usernameKeyword = normalize(queryDTO.getUsername());
        String accountStatus = normalize(queryDTO.getAccountStatus());
        String proxyIp = normalize(queryDTO.getProxyIp());
        log.debug(
                "{} 分页查询账号 | current={} | size={} | usernameKeyword={} | accountStatus={} | proxyIp={}",
                LOG_PREFIX,
                queryDTO.getCurrent(),
                queryDTO.getSize(),
                safeLogText(usernameKeyword),
                safeLogText(accountStatus),
                maskProxyIp(proxyIp)
        );

        LambdaQueryWrapper<GithubAccountBase> countWrapper = Wrappers.lambdaQuery(GithubAccountBase.class)
                .like(StringUtils.hasText(usernameKeyword), GithubAccountBase::getUsername, usernameKeyword)
                .eq(StringUtils.hasText(accountStatus), GithubAccountBase::getAccountStatus, accountStatus)
                .eq(StringUtils.hasText(proxyIp), GithubAccountBase::getProxyIp, proxyIp);
        long total = baseMapper.selectCount(countWrapper);

        long current = queryDTO.getCurrent();
        long size = queryDTO.getSize();
        long offset = (current - 1) * size;

        LambdaQueryWrapper<GithubAccountBase> listWrapper = Wrappers.lambdaQuery(GithubAccountBase.class)
                .like(StringUtils.hasText(usernameKeyword), GithubAccountBase::getUsername, usernameKeyword)
                .eq(StringUtils.hasText(accountStatus), GithubAccountBase::getAccountStatus, accountStatus)
                .eq(StringUtils.hasText(proxyIp), GithubAccountBase::getProxyIp, proxyIp)
                .orderByDesc(GithubAccountBase::getCreatedAt)
                .last("LIMIT " + size + " OFFSET " + offset);
        List<GithubAccountBase> records = baseMapper.selectList(listWrapper);

        Page<GithubAccountVO> page = new Page<>(current, size, total);
        page.setRecords(records.stream().map(this::toVO).toList());
        log.debug(
                "{} 分页查询完成 | current={} | size={} | total={} | returned={}",
                LOG_PREFIX,
                current,
                size,
                total,
                records.size()
        );
        return page;
    }

    /**
     * 获取账号详情。
     *
     * @param id 主键 ID
     * @return 账号视图对象
     */
    @Override
    public GithubAccountVO getAccount(Long id) {
        GithubAccountBase entity = getRequiredById(id);
        log.debug(
                "{} 查询账号详情 | accountId={} | username={} | email={}",
                LOG_PREFIX,
                id,
                safeLogText(entity.getUsername()),
                maskEmail(entity.getEmail())
        );
        return toVO(entity);
    }

    /**
     * 修改基础信息。
     *
     * @param id 主键 ID
     * @param updateDTO 更新参数
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAccount(Long id, GithubAccountUpdateDTO updateDTO) {
        GithubAccountBase entity = getRequiredById(id);
        List<String> changedFields = new ArrayList<>();

        boolean changed = false;
        if (updateDTO.getPassword() != null) {
            String password = normalize(updateDTO.getPassword());
            if (!StringUtils.hasText(password)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "密码不能为空字符串");
            }
            entity.setPassword(password);
            changedFields.add("password");
            changed = true;
        }
        if (updateDTO.getTotpSecret() != null) {
            String totpSecret = normalize(updateDTO.getTotpSecret());
            if (!StringUtils.hasText(totpSecret)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "TOTP密钥不能为空字符串");
            }
            entity.setTotpSecret(totpSecret);
            changedFields.add("totpSecret");
            changed = true;
        }
        if (updateDTO.getProxyIp() != null) {
            entity.setProxyIp(normalize(updateDTO.getProxyIp()));
            changedFields.add("proxyIp");
            changed = true;
        }

        if (!changed) {
            log.info(
                    "{} 跳过更新账号 | accountId={} | username={} | reason=no_changes",
                    LOG_PREFIX,
                    id,
                    safeLogText(entity.getUsername())
            );
            return;
        }
        log.info(
                "{} 开始更新账号 | accountId={} | username={} | email={} | fields={}",
                LOG_PREFIX,
                id,
                safeLogText(entity.getUsername()),
                maskEmail(entity.getEmail()),
                changedFields
        );
        if (!updateById(entity)) {
            log.error("{} 更新账号失败 | accountId={} | fields={}", LOG_PREFIX, id, changedFields);
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新账号信息失败");
        }
        log.info("{} 更新账号完成 | accountId={} | fields={}", LOG_PREFIX, id, changedFields);
    }

    /**
     * 快捷更新账号状态。
     *
     * @param id 主键 ID
     * @param statusDTO 状态参数
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAccountStatus(Long id, GithubAccountStatusDTO statusDTO) {
        GithubAccountBase entity = getRequiredById(id);
        String previousStatus = entity.getAccountStatus();
        String targetStatus = normalize(statusDTO.getAccountStatus());
        log.info(
                "{} 开始更新账号状态 | accountId={} | username={} | from={} | to={}",
                LOG_PREFIX,
                id,
                safeLogText(entity.getUsername()),
                safeLogText(previousStatus),
                safeLogText(targetStatus)
        );
        entity.setAccountStatus(targetStatus);
        if (!updateById(entity)) {
            log.error(
                    "{} 更新账号状态失败 | accountId={} | username={} | targetStatus={}",
                    LOG_PREFIX,
                    id,
                    safeLogText(entity.getUsername()),
                    safeLogText(targetStatus)
            );
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新账号状态失败");
        }
        log.info(
                "{} 更新账号状态完成 | accountId={} | username={} | from={} | to={}",
                LOG_PREFIX,
                id,
                safeLogText(entity.getUsername()),
                safeLogText(previousStatus),
                safeLogText(targetStatus)
        );
    }

    /**
     * 逻辑删除账号。
     *
     * @param id 主键 ID
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteAccount(Long id) {
        GithubAccountBase entity = getRequiredById(id);
        log.info(
                "{} 开始删除账号 | accountId={} | username={} | email={}",
                LOG_PREFIX,
                id,
                safeLogText(entity.getUsername()),
                maskEmail(entity.getEmail())
        );
        if (!removeById(id)) {
            log.error("{} 删除账号失败 | accountId={}", LOG_PREFIX, id);
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "删除账号失败");
        }
        log.info("{} 删除账号完成 | accountId={} | username={}", LOG_PREFIX, id, safeLogText(entity.getUsername()));
    }

    /**
     * 校验请求数据中的用户名和邮箱唯一性。
     *
     * @param importDTOList 导入参数列表
     */
    private void assertNoRequestDuplicates(List<GithubAccountImportDTO> importDTOList) {
        Set<String> usernames = new HashSet<>();
        Set<String> emails = new HashSet<>();
        for (GithubAccountImportDTO dto : importDTOList) {
            String username = normalize(dto.getUsername());
            String email = normalize(dto.getEmail()).toLowerCase();
            if (!usernames.add(username)) {
                log.warn("{} 导入参数校验失败 | reason=duplicate_username | username={}", LOG_PREFIX, safeLogText(username));
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "导入数据存在重复用户名: " + username);
            }
            if (!emails.add(email)) {
                log.warn("{} 导入参数校验失败 | reason=duplicate_email | email={}", LOG_PREFIX, maskEmail(email));
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "导入数据存在重复邮箱: " + email);
            }
        }
    }

    /**
     * 校验数据库中用户名和邮箱唯一性。
     *
     * @param importDTOList 导入参数列表
     */
    private void assertDbUnique(List<GithubAccountImportDTO> importDTOList) {
        List<String> usernames = importDTOList.stream()
                .map(GithubAccountImportDTO::getUsername)
                .map(this::normalize)
                .toList();
        List<String> emails = importDTOList.stream()
                .map(GithubAccountImportDTO::getEmail)
                .map(this::normalize)
                .map(String::toLowerCase)
                .toList();

        long usernameCount = lambdaQuery().in(GithubAccountBase::getUsername, usernames).count();
        if (usernameCount > 0) {
            log.warn(
                    "{} 导入前校验失败 | reason=username_exists | candidateCount={} | existsCount={}",
                    LOG_PREFIX,
                    usernames.size(),
                    usernameCount
            );
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "用户名已存在，导入失败");
        }

        long emailCount = lambdaQuery().in(GithubAccountBase::getEmail, emails).count();
        if (emailCount > 0) {
            log.warn(
                    "{} 导入前校验失败 | reason=email_exists | candidateCount={} | existsCount={}",
                    LOG_PREFIX,
                    emails.size(),
                    emailCount
            );
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "邮箱已存在，导入失败");
        }
    }

    /**
     * 导入 DTO 转实体对象。
     *
     * @param dto 导入参数
     * @return 实体对象
     */
    private GithubAccountBase toEntity(GithubAccountImportDTO dto) {
        GithubAccountBase entity = new GithubAccountBase();
        entity.setUsername(normalize(dto.getUsername()));
        entity.setEmail(normalize(dto.getEmail()).toLowerCase());
        entity.setPassword(normalize(dto.getPassword()));
        entity.setTotpSecret(normalize(dto.getTotpSecret()));
        entity.setProxyIp(normalize(dto.getProxyIp()));
        entity.setAccountStatus(StringUtils.hasText(normalize(dto.getAccountStatus()))
                ? normalize(dto.getAccountStatus())
                : STATUS_ACTIVE);
        return entity;
    }

    /**
     * 实体对象转视图对象。
     *
     * @param entity 实体对象
     * @return 视图对象
     */
    private GithubAccountVO toVO(GithubAccountBase entity) {
        GithubAccountVO vo = new GithubAccountVO();
        vo.setId(entity.getId());
        vo.setUsername(entity.getUsername());
        vo.setEmail(entity.getEmail());
        vo.setPassword(entity.getPassword());
        vo.setTotpSecret(entity.getTotpSecret());
        vo.setAccessToken(entity.getAccessToken());
        vo.setAccessTokenNote(entity.getAccessTokenNote());
        vo.setProxyIp(entity.getProxyIp());
        vo.setAccountStatus(entity.getAccountStatus());
        vo.setCreatedAt(entity.getCreatedAt());
        vo.setUpdatedAt(entity.getUpdatedAt());
        return vo;
    }

    /**
     * 按 ID 获取账号，不存在则抛出业务异常。
     *
     * @param id 主键 ID
     * @return 实体对象
     */
    private GithubAccountBase getRequiredById(Long id) {
        GithubAccountBase entity = getById(id);
        if (entity == null) {
            log.warn("{} 按ID查询账号不存在 | accountId={}", LOG_PREFIX, id);
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "账号不存在");
        }
        return entity;
    }

    /**
     * 标准化字符串文本。
     *
     * @param value 原始值
     * @return 去空白后的值
     */
    private String normalize(String value) {
        return value == null ? null : value.trim();
    }

    private String summarizeUsernames(List<GithubAccountBase> entities) {
        List<String> usernames = entities.stream()
                .map(GithubAccountBase::getUsername)
                .filter(StringUtils::hasText)
                .limit(LOG_SAMPLE_LIMIT)
                .toList();
        if (entities.size() <= LOG_SAMPLE_LIMIT) {
            return usernames.toString();
        }
        return usernames + "...(+" + (entities.size() - LOG_SAMPLE_LIMIT) + ")";
    }

    private String safeLogText(String value) {
        return StringUtils.hasText(value) ? value : "-";
    }

    private String maskEmail(String email) {
        if (!StringUtils.hasText(email) || !email.contains("@")) {
            return "-";
        }
        String normalized = email.trim();
        String[] parts = normalized.split("@", 2);
        String localPart = parts[0];
        String domain = parts[1];
        if (!StringUtils.hasText(localPart) || !StringUtils.hasText(domain)) {
            return "-";
        }
        if (localPart.length() <= 2) {
            return localPart.charAt(0) + "***@" + domain;
        }
        return localPart.substring(0, 2) + "***@" + domain;
    }

    private String maskProxyIp(String proxyIp) {
        if (!StringUtils.hasText(proxyIp)) {
            return "-";
        }
        String normalized = proxyIp.trim();
        String[] parts = normalized.split("\\.");
        if (parts.length == 4) {
            return parts[0] + "." + parts[1] + "." + parts[2] + ".*";
        }
        return normalized;
    }
}
