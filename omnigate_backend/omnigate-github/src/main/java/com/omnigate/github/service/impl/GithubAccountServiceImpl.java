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
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * GitHub 账号基础管理服务实现。
 */
@Service
@RequiredArgsConstructor
public class GithubAccountServiceImpl extends ServiceImpl<GithubAccountBaseMapper, GithubAccountBase> implements GithubAccountService {

    private static final String STATUS_ACTIVE = "active";

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

        assertNoRequestDuplicates(importDTOList);
        assertDbUnique(importDTOList);

        List<GithubAccountBase> entities = importDTOList.stream().map(this::toEntity).toList();
        boolean saved = saveBatch(entities);
        if (!saved) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "导入账号失败");
        }
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
        return toVO(getRequiredById(id));
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

        boolean changed = false;
        if (updateDTO.getPassword() != null) {
            String password = normalize(updateDTO.getPassword());
            if (!StringUtils.hasText(password)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "密码不能为空字符串");
            }
            entity.setPassword(password);
            changed = true;
        }
        if (updateDTO.getTotpSecret() != null) {
            String totpSecret = normalize(updateDTO.getTotpSecret());
            if (!StringUtils.hasText(totpSecret)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "TOTP密钥不能为空字符串");
            }
            entity.setTotpSecret(totpSecret);
            changed = true;
        }
        if (updateDTO.getProxyIp() != null) {
            entity.setProxyIp(normalize(updateDTO.getProxyIp()));
            changed = true;
        }

        if (!changed) {
            return;
        }
        if (!updateById(entity)) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新账号信息失败");
        }
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
        entity.setAccountStatus(normalize(statusDTO.getAccountStatus()));
        if (!updateById(entity)) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新账号状态失败");
        }
    }

    /**
     * 逻辑删除账号。
     *
     * @param id 主键 ID
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteAccount(Long id) {
        getRequiredById(id);
        if (!removeById(id)) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "删除账号失败");
        }
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
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "导入数据存在重复用户名: " + username);
            }
            if (!emails.add(email)) {
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
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "用户名已存在，导入失败");
        }

        long emailCount = lambdaQuery().in(GithubAccountBase::getEmail, emails).count();
        if (emailCount > 0) {
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
}
