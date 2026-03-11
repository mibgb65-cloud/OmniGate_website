package com.omnigate.chatgpt.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.omnigate.chatgpt.entity.ChatGptAccountBase;
import com.omnigate.chatgpt.mapper.ChatGptAccountBaseMapper;
import com.omnigate.chatgpt.model.dto.ChatGptAccountBatchSoldDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountBatchStatusDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountCreateDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountPageQueryDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountStatusDTO;
import com.omnigate.chatgpt.model.dto.ChatGptAccountUpdateDTO;
import com.omnigate.chatgpt.model.vo.ChatGptAccountVO;
import com.omnigate.chatgpt.service.ChatGptAccountService;
import com.omnigate.common.error.BizErrorCodeEnum;
import com.omnigate.common.exception.BizException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * ChatGPT 账号管理服务实现。
 */
@Service
@RequiredArgsConstructor
public class ChatGptAccountServiceImpl extends ServiceImpl<ChatGptAccountBaseMapper, ChatGptAccountBase>
        implements ChatGptAccountService {

    private static final String DEFAULT_SUB_TIER = "free";
    private static final String DEFAULT_ACCOUNT_STATUS = "active";
    private static final boolean DEFAULT_SOLD = false;

    /**
     * 新增单个账号。
     *
     * @param createDTO 新增参数
     * @return 新增账号 ID
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createAccount(ChatGptAccountCreateDTO createDTO) {
        String email = normalizeEmail(createDTO.getEmail());
        assertEmailUnique(email, null);

        ChatGptAccountBase entity = toEntity(createDTO, email);
        if (!save(entity)) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "新增账号失败");
        }
        return entity.getId();
    }

    /**
     * 批量新增账号。
     *
     * @param createDTOList 新增参数列表
     * @return 新增成功数量
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public int createAccountsBatch(List<ChatGptAccountCreateDTO> createDTOList) {
        if (createDTOList == null || createDTOList.isEmpty()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "新增数据不能为空");
        }

        List<String> emails = new ArrayList<>(createDTOList.size());
        List<ChatGptAccountBase> entities = new ArrayList<>(createDTOList.size());
        for (ChatGptAccountCreateDTO createDTO : createDTOList) {
            String email = normalizeEmail(createDTO.getEmail());
            emails.add(email);
            entities.add(toEntity(createDTO, email));
        }

        assertNoDuplicateEmails(emails);
        assertEmailsNotExists(emails);

        if (!saveBatch(entities)) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "批量新增账号失败");
        }
        return entities.size();
    }

    /**
     * 分页查询账号。
     *
     * @param queryDTO 查询参数
     * @return 分页数据
     */
    @Override
    public IPage<ChatGptAccountVO> pageAccounts(ChatGptAccountPageQueryDTO queryDTO) {
        String emailKeyword = normalize(queryDTO.getEmail());
        String subTier = normalize(queryDTO.getSubTier());
        String accountStatus = normalize(queryDTO.getAccountStatus());
        Boolean sold = queryDTO.getSold();

        LambdaQueryWrapper<ChatGptAccountBase> countWrapper = Wrappers.lambdaQuery(ChatGptAccountBase.class)
                .like(StringUtils.hasText(emailKeyword), ChatGptAccountBase::getEmail, emailKeyword)
                .eq(StringUtils.hasText(subTier), ChatGptAccountBase::getSubTier, subTier)
                .eq(StringUtils.hasText(accountStatus), ChatGptAccountBase::getAccountStatus, accountStatus)
                .eq(sold != null, ChatGptAccountBase::getSold, sold);
        long total = baseMapper.selectCount(countWrapper);

        long current = queryDTO.getCurrent();
        long size = queryDTO.getSize();
        long offset = (current - 1) * size;

        LambdaQueryWrapper<ChatGptAccountBase> listWrapper = Wrappers.lambdaQuery(ChatGptAccountBase.class)
                .like(StringUtils.hasText(emailKeyword), ChatGptAccountBase::getEmail, emailKeyword)
                .eq(StringUtils.hasText(subTier), ChatGptAccountBase::getSubTier, subTier)
                .eq(StringUtils.hasText(accountStatus), ChatGptAccountBase::getAccountStatus, accountStatus)
                .eq(sold != null, ChatGptAccountBase::getSold, sold)
                .orderByDesc(ChatGptAccountBase::getCreatedAt)
                .last("LIMIT " + size + " OFFSET " + offset);
        List<ChatGptAccountBase> records = baseMapper.selectList(listWrapper);

        Page<ChatGptAccountVO> page = new Page<>(current, size, total);
        page.setRecords(records.stream().map(this::toVO).toList());
        return page;
    }

    /**
     * 查询账号详情。
     *
     * @param id 账号 ID
     * @return 账号详情
     */
    @Override
    public ChatGptAccountVO getAccount(Long id) {
        return toVO(getRequiredById(id));
    }

    /**
     * 更新账号基础信息。
     *
     * @param id 账号 ID
     * @param updateDTO 更新参数
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAccount(Long id, ChatGptAccountUpdateDTO updateDTO) {
        ChatGptAccountBase entity = getRequiredById(id);

        boolean changed = false;
        if (updateDTO.getEmail() != null) {
            String email = normalizeEmail(updateDTO.getEmail());
            if (!email.equals(entity.getEmail())) {
                assertEmailUnique(email, id);
                entity.setEmail(email);
                changed = true;
            }
        }
        if (updateDTO.getPassword() != null) {
            String password = normalize(updateDTO.getPassword());
            if (!StringUtils.hasText(password)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "密码不能为空字符串");
            }
            entity.setPassword(password);
            changed = true;
        }
        if (updateDTO.getSessionToken() != null) {
            entity.setSessionToken(normalize(updateDTO.getSessionToken()));
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
        if (updateDTO.getSubTier() != null) {
            String subTier = normalize(updateDTO.getSubTier());
            if (!StringUtils.hasText(subTier)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "订阅层级不能为空字符串");
            }
            entity.setSubTier(subTier);
            changed = true;
        }
        if (updateDTO.getAccountStatus() != null) {
            String accountStatus = normalize(updateDTO.getAccountStatus());
            if (!StringUtils.hasText(accountStatus)) {
                throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "账号状态不能为空字符串");
            }
            entity.setAccountStatus(accountStatus);
            changed = true;
        }
        if (updateDTO.getSold() != null) {
            entity.setSold(updateDTO.getSold());
            changed = true;
        }
        if (updateDTO.getExpireDate() != null) {
            entity.setExpireDate(updateDTO.getExpireDate());
            changed = true;
        }

        if (!changed) {
            return;
        }
        if (!updateById(entity)) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新账号失败");
        }
    }

    /**
     * 更新单个账号状态。
     *
     * @param id 账号 ID
     * @param statusDTO 状态参数
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateAccountStatus(Long id, ChatGptAccountStatusDTO statusDTO) {
        ChatGptAccountBase entity = getRequiredById(id);
        entity.setAccountStatus(normalize(statusDTO.getAccountStatus()));
        if (!updateById(entity)) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "更新账号状态失败");
        }
    }

    /**
     * 批量更新账号状态。
     *
     * @param batchStatusDTO 批量状态参数
     * @return 更新成功数量
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public int batchUpdateAccountStatus(ChatGptAccountBatchStatusDTO batchStatusDTO) {
        List<Long> ids = distinctIds(batchStatusDTO.getIds());
        assertIdsNotEmpty(ids);
        assertAllExists(ids);

        boolean updated = lambdaUpdate()
                .in(ChatGptAccountBase::getId, ids)
                .set(ChatGptAccountBase::getAccountStatus, normalize(batchStatusDTO.getAccountStatus()))
                .update();
        if (!updated) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "批量更新账号状态失败");
        }
        return ids.size();
    }

    /**
     * 批量更新账号出售状态。
     *
     * @param batchSoldDTO 批量出售状态参数
     * @return 更新成功数量
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public int batchUpdateAccountSold(ChatGptAccountBatchSoldDTO batchSoldDTO) {
        List<Long> ids = distinctIds(batchSoldDTO.getIds());
        assertIdsNotEmpty(ids);
        assertAllExists(ids);

        boolean updated = lambdaUpdate()
                .in(ChatGptAccountBase::getId, ids)
                .set(ChatGptAccountBase::getSold, batchSoldDTO.getSold())
                .update();
        if (!updated) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "批量更新账号出售状态失败");
        }
        return ids.size();
    }

    /**
     * 删除单个账号。
     *
     * @param id 账号 ID
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
     * 批量删除账号。
     *
     * @param ids 账号 ID 列表
     * @return 删除成功数量
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public int batchDeleteAccounts(List<Long> ids) {
        List<Long> distinctIds = distinctIds(ids);
        assertIdsNotEmpty(distinctIds);
        assertAllExists(distinctIds);

        if (!removeByIds(distinctIds)) {
            throw new BizException(BizErrorCodeEnum.INTERNAL_SERVER_ERROR, "批量删除账号失败");
        }
        return distinctIds.size();
    }

    /**
     * 校验请求中的邮箱不重复。
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
     * 校验数据库中邮箱不存在。
     *
     * @param emails 邮箱列表
     */
    private void assertEmailsNotExists(List<String> emails) {
        long count = lambdaQuery().in(ChatGptAccountBase::getEmail, emails).count();
        if (count > 0) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "存在已注册邮箱，新增失败");
        }
    }

    /**
     * 校验单个邮箱唯一性。
     *
     * @param email 邮箱
     * @param excludeId 需要排除的账号 ID
     */
    private void assertEmailUnique(String email, Long excludeId) {
        LambdaQueryWrapper<ChatGptAccountBase> queryWrapper = Wrappers.lambdaQuery(ChatGptAccountBase.class)
                .eq(ChatGptAccountBase::getEmail, email);
        if (excludeId != null) {
            queryWrapper.ne(ChatGptAccountBase::getId, excludeId);
        }
        long count = baseMapper.selectCount(queryWrapper);
        if (count > 0) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "邮箱已存在: " + email);
        }
    }

    /**
     * 校验账号 ID 列表不为空。
     *
     * @param ids 账号 ID 列表
     */
    private void assertIdsNotEmpty(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "账号ID列表不能为空");
        }
    }

    /**
     * 校验账号都存在。
     *
     * @param ids 账号 ID 列表
     */
    private void assertAllExists(List<Long> ids) {
        long count = lambdaQuery().in(ChatGptAccountBase::getId, ids).count();
        if (count != ids.size()) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "存在不存在的账号，批量操作失败");
        }
    }

    /**
     * DTO 转实体对象。
     *
     * @param createDTO 新增参数
     * @param email 标准化后的邮箱
     * @return 实体对象
     */
    private ChatGptAccountBase toEntity(ChatGptAccountCreateDTO createDTO, String email) {
        ChatGptAccountBase entity = new ChatGptAccountBase();
        entity.setEmail(email);

        String password = normalize(createDTO.getPassword());
        if (!StringUtils.hasText(password)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "密码不能为空");
        }
        entity.setPassword(password);

        entity.setSessionToken(normalize(createDTO.getSessionToken()));
        entity.setTotpSecret(normalize(createDTO.getTotpSecret()));

        String subTier = normalize(createDTO.getSubTier());
        entity.setSubTier(StringUtils.hasText(subTier) ? subTier : DEFAULT_SUB_TIER);

        String accountStatus = normalize(createDTO.getAccountStatus());
        entity.setAccountStatus(StringUtils.hasText(accountStatus) ? accountStatus : DEFAULT_ACCOUNT_STATUS);

        entity.setSold(createDTO.getSold() != null ? createDTO.getSold() : DEFAULT_SOLD);
        entity.setExpireDate(createDTO.getExpireDate());
        return entity;
    }

    /**
     * 实体转视图对象。
     *
     * @param entity 实体对象
     * @return 视图对象
     */
    private ChatGptAccountVO toVO(ChatGptAccountBase entity) {
        ChatGptAccountVO vo = new ChatGptAccountVO();
        vo.setId(entity.getId());
        vo.setEmail(entity.getEmail());
        vo.setPassword(entity.getPassword());
        vo.setSessionToken(entity.getSessionToken());
        vo.setTotpSecret(entity.getTotpSecret());
        vo.setSubTier(entity.getSubTier());
        vo.setAccountStatus(entity.getAccountStatus());
        vo.setSold(Boolean.TRUE.equals(entity.getSold()));
        vo.setExpireDate(entity.getExpireDate());
        vo.setCreatedAt(entity.getCreatedAt());
        vo.setUpdatedAt(entity.getUpdatedAt());
        return vo;
    }

    /**
     * 根据 ID 查询账号，不存在则抛异常。
     *
     * @param id 账号 ID
     * @return 账号实体
     */
    private ChatGptAccountBase getRequiredById(Long id) {
        ChatGptAccountBase entity = getById(id);
        if (entity == null) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "账号不存在");
        }
        return entity;
    }

    /**
     * 标准化邮箱。
     *
     * @param email 原始邮箱
     * @return 标准化邮箱
     */
    private String normalizeEmail(String email) {
        String normalizedEmail = normalize(email);
        if (!StringUtils.hasText(normalizedEmail)) {
            throw new BizException(BizErrorCodeEnum.BAD_REQUEST, "邮箱不能为空");
        }
        return normalizedEmail.toLowerCase();
    }

    /**
     * 对账号 ID 去重。
     *
     * @param ids 原始 ID 列表
     * @return 去重后的 ID 列表
     */
    private List<Long> distinctIds(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return List.of();
        }
        return ids.stream().distinct().toList();
    }

    /**
     * 标准化文本。
     *
     * @param value 原始值
     * @return 去空白后的值
     */
    private String normalize(String value) {
        return value == null ? null : value.trim();
    }
}
