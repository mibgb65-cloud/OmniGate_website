package com.omnigate.google.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import com.omnigate.google.entity.GoogleAccountBase;
import com.omnigate.google.entity.GoogleAccountStatus;
import com.omnigate.google.entity.GoogleFamilyMember;
import com.omnigate.google.entity.GoogleInviteLink;
import com.omnigate.google.mapper.GoogleAccountBaseMapper;
import com.omnigate.google.mapper.GoogleAccountStatusMapper;
import com.omnigate.google.mapper.GoogleFamilyMemberMapper;
import com.omnigate.google.mapper.GoogleInviteLinkMapper;
import com.omnigate.google.model.dto.GoogleAccountImportDTO;
import com.omnigate.google.model.dto.GoogleAccountPageQueryDTO;
import com.omnigate.google.model.dto.GoogleAccountUpdateDTO;
import com.omnigate.google.model.vo.GoogleAccountDetailVO;
import com.omnigate.google.model.vo.GoogleAccountListVO;
import com.omnigate.google.model.vo.GoogleFamilyMemberVO;
import com.omnigate.google.model.vo.GoogleInviteLinkVO;
import com.omnigate.google.service.GoogleAccountService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Google 账号核心资产服务实现。
 */
@Service
@RequiredArgsConstructor
public class GoogleAccountServiceImpl extends ServiceImpl<GoogleAccountBaseMapper, GoogleAccountBase> implements GoogleAccountService {

    private static final String DEFAULT_SUB_TIER = "NONE";

    private final GoogleAccountStatusMapper googleAccountStatusMapper;
    private final GoogleFamilyMemberMapper googleFamilyMemberMapper;
    private final GoogleInviteLinkMapper googleInviteLinkMapper;

    /**
     * 批量导入 Google 账号基础信息，并初始化状态信息。
     *
     * @param importDTOList 导入参数列表
     * @return 导入成功数量
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public int importAccounts(List<GoogleAccountImportDTO> importDTOList) {
        if (importDTOList == null || importDTOList.isEmpty()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "导入数据不能为空");
        }

        List<String> emails = importDTOList.stream().map(this::normalizeEmail).toList();
        assertNoDuplicateEmails(emails);
        assertEmailsNotExists(emails);

        List<GoogleAccountBase> baseList = importDTOList.stream().map(this::toAccountBaseEntity).toList();
        boolean saved = saveBatch(baseList);
        if (!saved) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "账号导入失败");
        }

        for (GoogleAccountBase accountBase : baseList) {
            GoogleAccountStatus status = new GoogleAccountStatus();
            status.setAccountId(accountBase.getId());
            status.setSubTier(DEFAULT_SUB_TIER);
            status.setFamilyStatus(0);
            status.setInviteLinkStatus(0);
            status.setInvitedCount(0);
            googleAccountStatusMapper.insert(status);
        }
        return baseList.size();
    }

    /**
     * 分页查询账号列表。
     *
     * @param queryDTO 分页查询参数
     * @return 账号分页数据
     */
    @Override
    public IPage<GoogleAccountListVO> pageAccounts(GoogleAccountPageQueryDTO queryDTO) {
        String emailKeyword = normalizeText(queryDTO.getEmail());

        LambdaQueryWrapper<GoogleAccountBase> countWrapper = Wrappers.lambdaQuery(GoogleAccountBase.class)
                .like(StringUtils.hasText(emailKeyword), GoogleAccountBase::getEmail, emailKeyword)
                .eq(queryDTO.getSyncStatus() != null, GoogleAccountBase::getSyncStatus, queryDTO.getSyncStatus());
        long total = baseMapper.selectCount(countWrapper);

        long current = queryDTO.getCurrent();
        long size = queryDTO.getSize();
        long offset = (current - 1) * size;

        LambdaQueryWrapper<GoogleAccountBase> listWrapper = Wrappers.lambdaQuery(GoogleAccountBase.class)
                .like(StringUtils.hasText(emailKeyword), GoogleAccountBase::getEmail, emailKeyword)
                .eq(queryDTO.getSyncStatus() != null, GoogleAccountBase::getSyncStatus, queryDTO.getSyncStatus())
                .orderByDesc(GoogleAccountBase::getCreatedAt)
                .last("LIMIT " + size + " OFFSET " + offset);
        List<GoogleAccountBase> accountBases = baseMapper.selectList(listWrapper);

        List<Long> accountIds = accountBases.stream().map(GoogleAccountBase::getId).toList();
        Map<Long, GoogleAccountStatus> statusMap = loadStatusMap(accountIds);

        Page<GoogleAccountListVO> result = new Page<>(current, size, total);
        result.setRecords(accountBases.stream()
                .map(base -> toAccountListVO(base, statusMap.get(base.getId())))
                .toList());
        return result;
    }

    /**
     * 查询账号详情（基础信息 + 状态信息聚合）。
     *
     * @param id 账号 ID
     * @return 账号详情
     */
    @Override
    public GoogleAccountDetailVO getAccountDetail(Long id) {
        GoogleAccountBase accountBase = getRequiredAccount(id);
        GoogleAccountStatus accountStatus = googleAccountStatusMapper.selectById(id);
        return toAccountDetailVO(accountBase, accountStatus);
    }

    /**
     * 更新账号基础信息。
     *
     * @param id 账号 ID
     * @param updateDTO 更新参数
     */
    @Override
    public void updateAccountBase(Long id, GoogleAccountUpdateDTO updateDTO) {
        GoogleAccountBase accountBase = getRequiredAccount(id);

        boolean changed = false;
        if (updateDTO.getPassword() != null) {
            String password = normalizeText(updateDTO.getPassword());
            if (!StringUtils.hasText(password)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "密码不能为空字符串");
            }
            accountBase.setPassword(password);
            changed = true;
        }
        if (updateDTO.getRecoveryEmail() != null) {
            accountBase.setRecoveryEmail(normalizeText(updateDTO.getRecoveryEmail()));
            changed = true;
        }
        if (updateDTO.getTotpSecret() != null) {
            String totpSecret = normalizeText(updateDTO.getTotpSecret());
            if (!StringUtils.hasText(totpSecret)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "TOTP密钥不能为空字符串");
            }
            accountBase.setTotpSecret(totpSecret);
            changed = true;
        }
        if (updateDTO.getRegion() != null) {
            accountBase.setRegion(normalizeText(updateDTO.getRegion()));
            changed = true;
        }
        if (updateDTO.getRemark() != null) {
            accountBase.setRemark(normalizeText(updateDTO.getRemark()));
            changed = true;
        }

        if (!changed) {
            return;
        }

        boolean updated = updateById(accountBase);
        if (!updated) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新账号信息失败");
        }
    }

    /**
     * 查询账号下的家庭成员列表。
     *
     * @param accountId 账号 ID
     * @return 家庭成员列表
     */
    @Override
    public List<GoogleFamilyMemberVO> listFamilyMembers(Long accountId) {
        getRequiredAccount(accountId);
        LambdaQueryWrapper<GoogleFamilyMember> queryWrapper = Wrappers.lambdaQuery(GoogleFamilyMember.class)
                .eq(GoogleFamilyMember::getAccountId, accountId)
                .orderByAsc(GoogleFamilyMember::getInviteDate);
        return googleFamilyMemberMapper.selectList(queryWrapper).stream().map(this::toFamilyMemberVO).toList();
    }

    /**
     * 查询账号下的福利邀请链接列表。
     *
     * @param accountId 账号 ID
     * @return 邀请链接列表
     */
    @Override
    public List<GoogleInviteLinkVO> listInviteLinks(Long accountId) {
        getRequiredAccount(accountId);
        LambdaQueryWrapper<GoogleInviteLink> queryWrapper = Wrappers.lambdaQuery(GoogleInviteLink.class)
                .eq(GoogleInviteLink::getAccountId, accountId)
                .orderByDesc(GoogleInviteLink::getCreatedAt);
        return googleInviteLinkMapper.selectList(queryWrapper).stream().map(this::toInviteLinkVO).toList();
    }

    /**
     * 校验导入数据中邮箱不重复。
     *
     * @param emails 邮箱列表
     */
    private void assertNoDuplicateEmails(List<String> emails) {
        Set<String> emailSet = new HashSet<>();
        for (String email : emails) {
            if (!emailSet.add(email)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "导入数据存在重复邮箱: " + email);
            }
        }
    }

    /**
     * 校验数据库中不存在将要导入的邮箱。
     *
     * @param emails 邮箱列表
     */
    private void assertEmailsNotExists(List<String> emails) {
        long count = lambdaQuery().in(GoogleAccountBase::getEmail, emails).count();
        if (count > 0) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "存在已注册邮箱，导入失败");
        }
    }

    /**
     * 根据账号 ID 查询账户，不存在时抛出业务异常。
     *
     * @param id 账号 ID
     * @return 账号基础信息
     */
    private GoogleAccountBase getRequiredAccount(Long id) {
        GoogleAccountBase accountBase = getById(id);
        if (accountBase == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "账号不存在");
        }
        return accountBase;
    }

    /**
     * 批量加载账号状态并按 accountId 建立映射。
     *
     * @param accountIds 账号 ID 列表
     * @return 状态映射
     */
    private Map<Long, GoogleAccountStatus> loadStatusMap(List<Long> accountIds) {
        if (accountIds == null || accountIds.isEmpty()) {
            return Map.of();
        }
        return googleAccountStatusMapper.selectBatchIds(accountIds).stream()
                .filter(Objects::nonNull)
                .collect(Collectors.toMap(GoogleAccountStatus::getAccountId, Function.identity(), (a, b) -> a));
    }

    /**
     * 导入参数转基础信息实体。
     *
     * @param importDTO 导入参数
     * @return 基础信息实体
     */
    private GoogleAccountBase toAccountBaseEntity(GoogleAccountImportDTO importDTO) {
        GoogleAccountBase accountBase = new GoogleAccountBase();
        accountBase.setEmail(normalizeEmail(importDTO));
        accountBase.setPassword(normalizeText(importDTO.getPassword()));
        accountBase.setRecoveryEmail(normalizeText(importDTO.getRecoveryEmail()));
        accountBase.setTotpSecret(normalizeText(importDTO.getTotpSecret()));
        accountBase.setRegion(normalizeText(importDTO.getRegion()));
        accountBase.setRemark(normalizeText(importDTO.getRemark()));
        accountBase.setSyncStatus(0);
        return accountBase;
    }

    /**
     * 基础信息和状态聚合为列表视图对象。
     *
     * @param accountBase 基础信息
     * @param accountStatus 状态信息
     * @return 列表视图对象
     */
    private GoogleAccountListVO toAccountListVO(GoogleAccountBase accountBase, GoogleAccountStatus accountStatus) {
        GoogleAccountListVO vo = new GoogleAccountListVO();
        vo.setId(accountBase.getId());
        vo.setEmail(accountBase.getEmail());
        vo.setPassword(accountBase.getPassword());
        vo.setRecoveryEmail(accountBase.getRecoveryEmail());
        vo.setTotpSecret(accountBase.getTotpSecret());
        vo.setRegion(accountBase.getRegion());
        vo.setRemark(accountBase.getRemark());
        vo.setSyncStatus(accountBase.getSyncStatus());
        vo.setCreatedAt(accountBase.getCreatedAt());
        vo.setUpdatedAt(accountBase.getUpdatedAt());

        if (accountStatus != null) {
            vo.setSubTier(accountStatus.getSubTier());
            vo.setFamilyStatus(accountStatus.getFamilyStatus());
            vo.setExpireDate(accountStatus.getExpireDate());
            vo.setInviteLinkStatus(accountStatus.getInviteLinkStatus());
            vo.setInvitedCount(accountStatus.getInvitedCount());
        }
        return vo;
    }

    /**
     * 基础信息和状态聚合为详情视图对象。
     *
     * @param accountBase 基础信息
     * @param accountStatus 状态信息
     * @return 详情视图对象
     */
    private GoogleAccountDetailVO toAccountDetailVO(GoogleAccountBase accountBase, GoogleAccountStatus accountStatus) {
        GoogleAccountDetailVO vo = new GoogleAccountDetailVO();
        vo.setId(accountBase.getId());
        vo.setEmail(accountBase.getEmail());
        vo.setPassword(accountBase.getPassword());
        vo.setRecoveryEmail(accountBase.getRecoveryEmail());
        vo.setTotpSecret(accountBase.getTotpSecret());
        vo.setRegion(accountBase.getRegion());
        vo.setRemark(accountBase.getRemark());
        vo.setSyncStatus(accountBase.getSyncStatus());
        vo.setCreatedAt(accountBase.getCreatedAt());
        vo.setUpdatedAt(accountBase.getUpdatedAt());

        if (accountStatus != null) {
            vo.setSubTier(accountStatus.getSubTier());
            vo.setFamilyStatus(accountStatus.getFamilyStatus());
            vo.setExpireDate(accountStatus.getExpireDate());
            vo.setInviteLinkStatus(accountStatus.getInviteLinkStatus());
            vo.setStudentLink(accountStatus.getStudentLink());
            vo.setInvitedCount(accountStatus.getInvitedCount());
        }
        return vo;
    }

    /**
     * 成员实体转视图对象。
     *
     * @param entity 成员实体
     * @return 成员视图对象
     */
    private GoogleFamilyMemberVO toFamilyMemberVO(GoogleFamilyMember entity) {
        GoogleFamilyMemberVO vo = new GoogleFamilyMemberVO();
        vo.setId(entity.getId());
        vo.setAccountId(entity.getAccountId());
        vo.setMemberName(entity.getMemberName());
        vo.setMemberEmail(entity.getMemberEmail());
        vo.setInviteDate(entity.getInviteDate());
        vo.setMemberRole(entity.getMemberRole());
        return vo;
    }

    /**
     * 邀请链接实体转视图对象。
     *
     * @param entity 邀请链接实体
     * @return 邀请链接视图对象
     */
    private GoogleInviteLinkVO toInviteLinkVO(GoogleInviteLink entity) {
        GoogleInviteLinkVO vo = new GoogleInviteLinkVO();
        vo.setId(entity.getId());
        vo.setAccountId(entity.getAccountId());
        vo.setInviteUrl(entity.getInviteUrl());
        vo.setUsedCount(entity.getUsedCount());
        return vo;
    }

    /**
     * 标准化邮箱文本。
     *
     * @param importDTO 导入参数
     * @return 标准化后的邮箱
     */
    private String normalizeEmail(GoogleAccountImportDTO importDTO) {
        String email = normalizeText(importDTO.getEmail());
        if (!StringUtils.hasText(email)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "邮箱不能为空");
        }
        return email.toLowerCase();
    }

    /**
     * 标准化文本，去除首尾空白。
     *
     * @param text 原始文本
     * @return 标准化文本
     */
    private String normalizeText(String text) {
        return text == null ? null : text.trim();
    }
}
