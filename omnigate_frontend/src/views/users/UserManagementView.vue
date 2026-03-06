<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Lock, Plus, Refresh, Search } from '@element-plus/icons-vue'

import { listRoles } from '@/api/roles'
import {
  assignUserRoles,
  createUser,
  deleteUser,
  getUserInfo,
  pageUsers,
  updateUser,
  updateUserPassword,
  updateUserStatus,
} from '@/api/users'

const loading = ref(false)
const users = ref([])
const detailLoading = ref(false)
const detailVisible = ref(false)
const currentUserDetail = ref(null)
const dialogVisible = ref(false)
const dialogMode = ref('create')
const passwordDialogVisible = ref(false)
const roleDialogVisible = ref(false)
const editingUserId = ref(null)
const passwordTarget = ref(null)
const roleTarget = ref(null)
const saving = ref(false)
const passwordSaving = ref(false)
const roleSaving = ref(false)
const roleCatalogLoading = ref(false)
const roleDialogLoading = ref(false)
const statusUpdatingId = ref(null)
const deletingId = ref(null)
const roleOptions = ref([])

const userFormRef = ref()
const passwordFormRef = ref()

const queryForm = reactive({
  username: '',
  status: undefined,
})

const pager = reactive({
  current: 1,
  size: 10,
  total: 0,
})

const statusOptions = [
  { label: '全部状态', value: undefined },
  { label: '启用', value: 1 },
  { label: '禁用', value: 0 },
]

function createEmptyUserForm() {
  return {
    username: '',
    email: '',
    password: '',
    nickname: '',
    avatarUrl: '',
  }
}

const userForm = reactive(createEmptyUserForm())

const passwordForm = reactive({
  password: '',
  confirmPassword: '',
})

const roleForm = reactive({
  roleIds: [],
})

const formTitle = computed(() => (dialogMode.value === 'create' ? '新增系统用户' : '编辑用户信息'))
const formSubtitle = computed(() =>
  dialogMode.value === 'create'
    ? '新建账号时直接设置初始密码，创建后会立刻出现在列表顶部。'
    : '这里只维护基础资料，密码和角色都通过独立操作入口处理，避免误改。',
)

const activeStatusKey = computed(() => {
  if (queryForm.status === 1) return 'enabled'
  if (queryForm.status === 0) return 'disabled'
  return 'all'
})

const dashboardStats = computed(() => {
  const enabledCount = users.value.filter((item) => item.status === 1).length
  const disabledCount = users.value.filter((item) => item.status === 0).length
  const neverLoggedInCount = users.value.filter((item) => !item.lastLoginAt).length

  return [
    {
      key: 'all',
      label: '全部用户',
      value: pager.total,
      hint: '查看所有后台账号',
      status: undefined,
      interactive: true,
    },
    {
      key: 'enabled',
      label: '当前页启用',
      value: enabledCount,
      hint: '可正常登录后台',
      status: 1,
      interactive: true,
    },
    {
      key: 'disabled',
      label: '当前页禁用',
      value: disabledCount,
      hint: '已冻结登录权限',
      status: 0,
      interactive: true,
    },
    {
      key: 'never-login',
      label: '当前页未登录',
      value: neverLoggedInCount,
      hint: '还没有登录记录',
      interactive: false,
    },
  ]
})

const hasActiveFilters = computed(() => Boolean(trimRequiredText(queryForm.username)) || queryForm.status !== undefined)

const activeFilters = computed(() => {
  const filters = []
  const keyword = trimRequiredText(queryForm.username)

  if (keyword) {
    filters.push(`用户名：${keyword}`)
  }
  if (queryForm.status === 1) {
    filters.push('状态：启用')
  }
  if (queryForm.status === 0) {
    filters.push('状态：禁用')
  }

  return filters
})

const listSummary = computed(() => {
  if (loading.value) {
    return '正在同步最新用户数据。'
  }
  if (!pager.total) {
    return hasActiveFilters.value ? '当前筛选条件下没有匹配用户。' : '当前还没有系统用户，可先创建一个后台账号。'
  }

  const from = (pager.current - 1) * pager.size + 1
  const to = Math.min(pager.current * pager.size, pager.total)
  return `当前展示第 ${from}-${to} 位，共 ${pager.total} 位用户。可直接在列表内处理状态、密码与角色。`
})

const roleMap = computed(() => new Map(roleOptions.value.map((item) => [item.id, item])))
const roleLoading = computed(() => roleCatalogLoading.value || roleDialogLoading.value)

function trimRequiredText(value) {
  return String(value || '').trim()
}

function normalizeOptionalText(value) {
  const nextValue = String(value || '').trim()
  return nextValue || undefined
}

function resetUserForm() {
  Object.assign(userForm, createEmptyUserForm())
}

function resetPasswordForm() {
  passwordForm.password = ''
  passwordForm.confirmPassword = ''
}

function resetRoleForm() {
  roleForm.roleIds = []
}

function validateCreatePassword(rule, value, callback) {
  if (dialogMode.value !== 'create') {
    callback()
    return
  }

  const password = trimRequiredText(value)
  if (!password) {
    callback(new Error('请输入初始密码'))
    return
  }
  if (password.length < 8 || password.length > 64) {
    callback(new Error('密码长度必须在 8 到 64 位之间'))
    return
  }
  callback()
}

function validateConfirmPassword(rule, value, callback) {
  const password = trimRequiredText(passwordForm.password)
  const confirmPassword = trimRequiredText(value)
  if (!confirmPassword) {
    callback(new Error('请再次输入新密码'))
    return
  }
  if (password !== confirmPassword) {
    callback(new Error('两次输入的密码不一致'))
    return
  }
  callback()
}

const userFormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 1, max: 64, message: '用户名长度不能超过 64 位', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
    { min: 1, max: 128, message: '邮箱长度不能超过 128 位', trigger: 'blur' },
  ],
  password: [{ validator: validateCreatePassword, trigger: 'blur' }],
  nickname: [{ min: 0, max: 64, message: '昵称长度不能超过 64 位', trigger: 'blur' }],
  avatarUrl: [{ min: 0, max: 255, message: '头像地址长度不能超过 255 位', trigger: 'blur' }],
}

const passwordFormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度必须在 8 到 64 位之间', trigger: 'blur' },
  ],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
}

async function fetchUsers() {
  loading.value = true
  try {
    const pageData = await pageUsers({
      current: pager.current,
      size: pager.size,
      username: trimRequiredText(queryForm.username) || undefined,
      status: queryForm.status,
    })

    users.value = Array.isArray(pageData?.records) ? pageData.records : []
    pager.total = Number(pageData?.total || 0)
    pager.current = Number(pageData?.current || pager.current)
    pager.size = Number(pageData?.size || pager.size)
  } finally {
    loading.value = false
  }
}

async function fetchRoleOptions() {
  roleCatalogLoading.value = true
  try {
    const data = await listRoles()
    roleOptions.value = Array.isArray(data) ? data : []
  } finally {
    roleCatalogLoading.value = false
  }
}

function handleSearch() {
  pager.current = 1
  fetchUsers()
}

function handleReset() {
  queryForm.username = ''
  queryForm.status = undefined
  pager.current = 1
  fetchUsers()
}

function handleQuickFilter(status) {
  queryForm.status = status
  pager.current = 1
  fetchUsers()
}

function handleCurrentChange(page) {
  pager.current = page
  fetchUsers()
}

function handleSizeChange(size) {
  pager.current = 1
  pager.size = size
  fetchUsers()
}

function handleDialogClosed() {
  resetUserForm()
  editingUserId.value = null
  dialogMode.value = 'create'
  nextTick(() => userFormRef.value?.clearValidate())
}

function handlePasswordDialogClosed() {
  resetPasswordForm()
  passwordTarget.value = null
  nextTick(() => passwordFormRef.value?.clearValidate())
}

function handleRoleDialogClosed() {
  resetRoleForm()
  roleTarget.value = null
}

function openCreateDialog() {
  dialogMode.value = 'create'
  editingUserId.value = null
  resetUserForm()
  dialogVisible.value = true
}

async function openEditDialog(userId) {
  const detail = await getUserInfo(userId)
  dialogMode.value = 'edit'
  editingUserId.value = userId
  userForm.username = detail?.username || ''
  userForm.email = detail?.email || ''
  userForm.password = ''
  userForm.nickname = detail?.nickname || ''
  userForm.avatarUrl = detail?.avatarUrl || ''
  dialogVisible.value = true
}

function openPasswordDialog(row) {
  passwordTarget.value = {
    id: row.id,
    username: row.username,
  }
  resetPasswordForm()
  passwordDialogVisible.value = true
}

async function openRoleDialog(row) {
  roleDialogLoading.value = true
  try {
    if (!roleOptions.value.length) {
      await fetchRoleOptions()
    }

    if (!roleOptions.value.length) {
      ElMessage.warning('暂无可分配角色，请先初始化角色数据')
      return
    }

    const detail = await getUserInfo(row.id)
    roleTarget.value = {
      id: row.id,
      username: row.username,
      email: row.email,
    }
    roleForm.roleIds = Array.isArray(detail?.roleIds) ? [...detail.roleIds] : []
    roleDialogVisible.value = true
  } finally {
    roleDialogLoading.value = false
  }
}

async function refreshCurrentDetail(userId) {
  if (currentUserDetail.value?.id !== userId) return
  currentUserDetail.value = await getUserInfo(userId)
}

async function openDetail(userId) {
  detailVisible.value = true
  detailLoading.value = true
  currentUserDetail.value = null

  try {
    currentUserDetail.value = await getUserInfo(userId)
  } catch {
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function handleSubmit() {
  if (!userFormRef.value || saving.value) return
  await userFormRef.value.validate()

  saving.value = true
  try {
    const payload = {
      username: trimRequiredText(userForm.username),
      email: trimRequiredText(userForm.email),
      nickname: normalizeOptionalText(userForm.nickname),
      avatarUrl: normalizeOptionalText(userForm.avatarUrl),
    }

    let targetUserId = editingUserId.value

    if (dialogMode.value === 'create') {
      payload.password = trimRequiredText(userForm.password)
      const createdUser = await createUser(payload)
      targetUserId = createdUser?.id || null
      pager.current = 1
      ElMessage.success('用户已创建')
    } else {
      await updateUser(editingUserId.value, payload)
      ElMessage.success('用户信息已更新')
    }

    dialogVisible.value = false
    await fetchUsers()

    if (targetUserId) {
      await refreshCurrentDetail(targetUserId)
    }
  } finally {
    saving.value = false
  }
}

async function handlePasswordSave() {
  if (!passwordFormRef.value || !passwordTarget.value || passwordSaving.value) return
  await passwordFormRef.value.validate()

  passwordSaving.value = true
  try {
    await updateUserPassword(passwordTarget.value.id, {
      password: trimRequiredText(passwordForm.password),
    })
    ElMessage.success('密码已更新')
    passwordDialogVisible.value = false
    await refreshCurrentDetail(passwordTarget.value.id)
  } finally {
    passwordSaving.value = false
  }
}

async function handleRoleSave() {
  if (!roleTarget.value || roleSaving.value) return

  roleSaving.value = true
  try {
    await assignUserRoles(roleTarget.value.id, {
      roleIds: [...roleForm.roleIds],
    })
    ElMessage.success('角色分配已更新')
    roleDialogVisible.value = false
    await fetchUsers()
    await refreshCurrentDetail(roleTarget.value.id)
  } finally {
    roleSaving.value = false
  }
}

async function handleStatusChange(row, value) {
  const nextStatus = value ? 1 : 0
  const previousStatus = row.status

  row.status = nextStatus
  statusUpdatingId.value = row.id
  try {
    await updateUserStatus(row.id, nextStatus)
    if (currentUserDetail.value?.id === row.id) {
      currentUserDetail.value.status = nextStatus
    }
    ElMessage.success(nextStatus === 1 ? '用户已启用' : '用户已禁用')
  } catch (error) {
    row.status = previousStatus
    if (currentUserDetail.value?.id === row.id) {
      currentUserDetail.value.status = previousStatus
    }
  } finally {
    statusUpdatingId.value = null
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除用户「${row.username}」吗？`, '危险操作确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
    })
  } catch {
    return
  }

  deletingId.value = row.id
  try {
    await deleteUser(row.id)
    ElMessage.success('用户已删除')

    if (currentUserDetail.value?.id === row.id) {
      detailVisible.value = false
      currentUserDetail.value = null
    }

    if (users.value.length === 1 && pager.current > 1) {
      pager.current -= 1
    }
    await fetchUsers()
  } finally {
    deletingId.value = null
  }
}

function resolveStatusLabel(status) {
  return status === 1 ? '启用中' : '已禁用'
}

function resolveStatusType(status) {
  return status === 1 ? 'success' : 'info'
}

function resolveStatusCaption(status) {
  return status === 1 ? '允许后台登录与管理操作' : '该账号已停止登录权限'
}

function resolveRoleType(roleCode) {
  if (roleCode === 'ADMIN') return 'danger'
  if (roleCode === 'OPERATOR') return 'warning'
  if (roleCode === 'VIEWER') return 'info'
  return 'success'
}

function resolveRoleBadges(user) {
  const roleNames = Array.isArray(user?.roleNames) ? user.roleNames : []
  const roleCodes = Array.isArray(user?.roleCodes) ? user.roleCodes : []

  if (roleNames.length || roleCodes.length) {
    const size = Math.max(roleNames.length, roleCodes.length)
    return Array.from({ length: size }, (_, index) => {
      const code = roleCodes[index] || roleNames[index] || `ROLE-${index}`
      return {
        key: `${user?.id || 'role'}-${code}-${index}`,
        code,
        label: roleNames[index] || roleCodes[index] || '未命名角色',
      }
    })
  }

  const roleIds = Array.isArray(user?.roleIds) ? user.roleIds : []
  if (roleIds.length) {
    return roleIds
      .map((roleId) => roleMap.value.get(roleId))
      .filter(Boolean)
      .map((role) => ({
        key: `${user?.id || 'role'}-${role.id}`,
        code: role.roleCode,
        label: role.roleName,
      }))
  }

  return []
}

function getUserInitials(user) {
  const seed = trimRequiredText(user?.nickname) || trimRequiredText(user?.username)
  return seed ? seed.slice(0, 2).toUpperCase() : 'OG'
}

function resolveUserDisplayName(user) {
  return trimRequiredText(user?.nickname) || trimRequiredText(user?.username) || '未命名用户'
}

function formatDateTime(value, fallback = '-') {
  return value || fallback
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="page-shell">
    <section class="hero-card">
      <div class="hero-copy">
        <span class="hero-kicker">Access Directory</span>
        <h1>系统用户列表</h1>
        <p>把账号资料、角色权限和登录状态收拢到一个工作台里，先看全局，再决定是否进入详情或继续编辑。</p>
      </div>

      <div class="hero-side">
        <div class="hero-actions">
          <el-button :icon="Refresh" @click="fetchUsers">刷新列表</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增用户</el-button>
        </div>

        <div class="stats-grid">
          <component
            :is="item.interactive ? 'button' : 'article'"
            v-for="item in dashboardStats"
            :key="item.key"
            :type="item.interactive ? 'button' : undefined"
            class="stat-item"
            :class="{
              'is-active': item.interactive && activeStatusKey === item.key,
              'is-static': !item.interactive,
            }"
            @click="item.interactive ? handleQuickFilter(item.status) : undefined"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.hint }}</p>
          </component>
        </div>
      </div>
    </section>

    <el-card class="workspace-card" shadow="never">
      <div class="workspace-head">
        <div>
          <span class="section-kicker">Directory Workspace</span>
          <h2>用户列表</h2>
          <p>{{ listSummary }}</p>
        </div>
      </div>

      <div class="control-strip">
        <el-form :model="queryForm" class="query-form" label-position="top" @submit.prevent>
          <el-form-item label="用户名关键字">
            <el-input v-model="queryForm.username" clearable placeholder="输入用户名模糊搜索" @keyup.enter="handleSearch" />
          </el-form-item>

          <el-form-item label="用户状态">
            <el-select v-model="queryForm.status" placeholder="全部状态" clearable>
              <el-option v-for="item in statusOptions.slice(1)" :key="String(item.value)" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>

          <el-form-item class="actions">
            <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
            <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>

        <div class="active-filters">
          <span>{{ activeFilters.length ? '当前筛选' : '快捷提示' }}</span>
          <div v-if="activeFilters.length" class="filter-tags">
            <el-tag v-for="item in activeFilters" :key="item" effect="plain" round>{{ item }}</el-tag>
          </div>
          <p v-else>点击上方统计卡可以快速切换“启用 / 禁用”视图，减少手动选择成本。</p>
        </div>
      </div>

      <div class="desktop-list">
        <el-table :data="users" v-loading="loading" row-key="id" class="user-table">
          <el-table-column label="用户信息" min-width="290">
            <template #default="{ row }">
              <button type="button" class="identity-cell" @click="openDetail(row.id)">
                <span class="identity-avatar">{{ getUserInitials(row) }}</span>
                <span class="identity-copy">
                  <strong>{{ resolveUserDisplayName(row) }}</strong>
                  <span>@{{ row.username }}</span>
                  <span>{{ row.email }}</span>
                </span>
              </button>
            </template>
          </el-table-column>

          <el-table-column label="角色权限" min-width="240">
            <template #default="{ row }">
              <div class="role-column">
                <div v-if="resolveRoleBadges(row).length" class="role-stack">
                  <el-tag
                    v-for="role in resolveRoleBadges(row).slice(0, 3)"
                    :key="role.key"
                    :type="resolveRoleType(role.code)"
                    effect="plain"
                  >
                    {{ role.label }}
                  </el-tag>
                </div>
                <span v-else class="empty-inline">未分配角色</span>

                <small>{{ resolveRoleBadges(row).length ? '保存后权限立即生效' : '建议至少分配一个权限角色' }}</small>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="170">
            <template #default="{ row }">
              <div class="status-cell">
                <el-tag :type="resolveStatusType(row.status)" effect="light">
                  {{ resolveStatusLabel(row.status) }}
                </el-tag>
                <span>{{ resolveStatusCaption(row.status) }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="最近活动" min-width="220">
            <template #default="{ row }">
              <div class="activity-cell">
                <strong>{{ formatDateTime(row.lastLoginAt, '尚未登录') }}</strong>
                <span>{{ row.lastLoginIp || '暂无登录 IP' }}</span>
                <small>创建于 {{ formatDateTime(row.createdAt) }}</small>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="280" fixed="right" align="center">
            <template #default="{ row }">
              <div class="action-cluster">
                <div class="toggle-line">
                  <span>{{ row.status === 1 ? '允许登录' : '禁止登录' }}</span>
                  <el-switch
                    :model-value="row.status === 1"
                    :loading="statusUpdatingId === row.id"
                    inline-prompt
                    active-text="启用"
                    inactive-text="禁用"
                    @change="(value) => handleStatusChange(row, value)"
                  />
                </div>

                <div class="row-actions">
                  <el-button link type="primary" @click="openEditDialog(row.id)">编辑</el-button>
                  <el-button link type="success" @click="openRoleDialog(row)">角色</el-button>
                  <el-button link type="warning" @click="openPasswordDialog(row)">改密码</el-button>
                  <el-button link type="danger" :loading="deletingId === row.id" @click="handleDelete(row)">删除</el-button>
                </div>
              </div>
            </template>
          </el-table-column>

          <template #empty>
            <el-empty :description="hasActiveFilters ? '当前筛选没有匹配用户' : '还没有系统用户'">
              <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增第一个用户</el-button>
            </el-empty>
          </template>
        </el-table>
      </div>

      <div class="mobile-list" v-loading="loading">
        <template v-if="users.length">
          <article v-for="row in users" :key="row.id" class="user-card">
            <div class="user-card-head">
              <button type="button" class="identity-cell identity-card-trigger" @click="openDetail(row.id)">
                <span class="identity-avatar">{{ getUserInitials(row) }}</span>
                <span class="identity-copy">
                  <strong>{{ resolveUserDisplayName(row) }}</strong>
                  <span>@{{ row.username }}</span>
                  <span>{{ row.email }}</span>
                </span>
              </button>

              <el-tag :type="resolveStatusType(row.status)" effect="light">
                {{ resolveStatusLabel(row.status) }}
              </el-tag>
            </div>

            <div class="user-card-body">
              <div class="mobile-section">
                <span class="mobile-section-title">角色权限</span>
                <div v-if="resolveRoleBadges(row).length" class="role-stack">
                  <el-tag
                    v-for="role in resolveRoleBadges(row).slice(0, 3)"
                    :key="role.key"
                    :type="resolveRoleType(role.code)"
                    effect="plain"
                  >
                    {{ role.label }}
                  </el-tag>
                </div>
                <span v-else class="empty-inline">未分配角色</span>
              </div>

              <div class="mobile-meta-grid">
                <div class="mobile-meta-item">
                  <span>最近登录</span>
                  <strong>{{ formatDateTime(row.lastLoginAt, '尚未登录') }}</strong>
                </div>
                <div class="mobile-meta-item">
                  <span>登录 IP</span>
                  <strong>{{ row.lastLoginIp || '暂无记录' }}</strong>
                </div>
                <div class="mobile-meta-item">
                  <span>创建时间</span>
                  <strong>{{ formatDateTime(row.createdAt) }}</strong>
                </div>
                <div class="mobile-meta-item">
                  <span>登录状态</span>
                  <strong>{{ row.status === 1 ? '允许登录后台' : '已禁止登录' }}</strong>
                </div>
              </div>
            </div>

            <div class="user-card-foot">
              <div class="toggle-line">
                <span>{{ row.status === 1 ? '允许登录' : '禁止登录' }}</span>
                <el-switch
                  :model-value="row.status === 1"
                  :loading="statusUpdatingId === row.id"
                  inline-prompt
                  active-text="启用"
                  inactive-text="禁用"
                  @change="(value) => handleStatusChange(row, value)"
                />
              </div>

              <div class="row-actions row-actions-mobile">
                <el-button link type="primary" @click="openEditDialog(row.id)">编辑</el-button>
                <el-button link type="success" @click="openRoleDialog(row)">角色</el-button>
                <el-button link type="warning" @click="openPasswordDialog(row)">改密码</el-button>
                <el-button link type="danger" :loading="deletingId === row.id" @click="handleDelete(row)">删除</el-button>
              </div>
            </div>
          </article>
        </template>

        <el-empty v-else-if="!loading" :description="hasActiveFilters ? '当前筛选没有匹配用户' : '还没有系统用户'">
          <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增第一个用户</el-button>
        </el-empty>
      </div>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pager.current"
          v-model:page-size="pager.size"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[10, 20, 50, 100]"
          :total="pager.total"
          @current-change="handleCurrentChange"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="formTitle"
      width="720px"
      destroy-on-close
      @closed="handleDialogClosed"
    >
      <div class="dialog-intro">
        <strong>{{ formTitle }}</strong>
        <span>{{ formSubtitle }}</span>
      </div>

      <el-form ref="userFormRef" :model="userForm" :rules="userFormRules" class="user-form" label-position="top" @submit.prevent>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" placeholder="请输入用户名" autocomplete="off" />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="请输入邮箱地址" autocomplete="off" />
        </el-form-item>

        <el-form-item v-if="dialogMode === 'create'" label="初始密码" prop="password">
          <el-input
            v-model="userForm.password"
            type="password"
            show-password
            placeholder="请输入 8 到 64 位密码"
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="userForm.nickname" placeholder="选填，用于列表展示" />
        </el-form-item>

        <el-form-item label="头像地址" prop="avatarUrl" class="full-span">
          <el-input v-model="userForm.avatarUrl" placeholder="选填，例如 https://example.com/avatar.png" />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSubmit">
            {{ dialogMode === 'create' ? '创建用户' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="passwordDialogVisible"
      title="修改登录密码"
      width="460px"
      destroy-on-close
      @closed="handlePasswordDialogClosed"
    >
      <el-alert type="warning" :closable="false" show-icon>
        <template #title>
          即将修改用户「{{ passwordTarget?.username || '-' }}」的登录密码，保存后立即生效。
        </template>
      </el-alert>

      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordFormRules"
        class="password-form"
        label-position="top"
        @submit.prevent
      >
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="passwordForm.password"
            type="password"
            show-password
            placeholder="请输入新密码"
            autocomplete="new-password"
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入新密码"
            autocomplete="new-password"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="passwordDialogVisible = false">取消</el-button>
          <el-button type="primary" :icon="Lock" :loading="passwordSaving" @click="handlePasswordSave">确认修改</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="roleDialogVisible"
      title="分配角色"
      width="680px"
      destroy-on-close
      @closed="handleRoleDialogClosed"
    >
      <div class="dialog-intro">
        <strong>角色分配</strong>
        <span>正在为用户「{{ roleTarget?.username || '-' }}」分配权限角色。保存后会直接影响该账号可访问的后台能力。</span>
      </div>

      <div class="role-meta">
        <span>当前用户</span>
        <strong>{{ roleTarget?.username || '-' }}</strong>
        <span>{{ roleTarget?.email || '-' }}</span>
      </div>

      <div v-loading="roleLoading" class="role-selector">
        <template v-if="roleOptions.length">
          <el-checkbox-group v-model="roleForm.roleIds" class="role-grid">
            <label
              v-for="role in roleOptions"
              :key="role.id"
              class="role-card"
              :class="{ 'is-active': roleForm.roleIds.includes(role.id) }"
            >
              <el-checkbox :value="role.id">
                <div class="role-card-body">
                  <div class="role-card-head">
                    <strong>{{ role.roleName }}</strong>
                    <span>{{ role.roleCode }}</span>
                  </div>
                  <p>{{ role.description || '暂无角色说明' }}</p>
                </div>
              </el-checkbox>
            </label>
          </el-checkbox-group>
        </template>

        <el-empty v-else description="暂无可分配角色" />
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="roleDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="roleSaving" :disabled="roleLoading" @click="handleRoleSave">保存角色分配</el-button>
        </div>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" size="480px" :with-header="false">
      <div class="detail-panel" v-loading="detailLoading">
        <template v-if="currentUserDetail">
          <div class="detail-hero">
            <div>
              <span class="detail-pill">User Detail</span>
              <h2>{{ resolveUserDisplayName(currentUserDetail) }}</h2>
              <p>{{ currentUserDetail.email }}</p>
            </div>
            <el-tag :type="resolveStatusType(currentUserDetail.status)" effect="light">
              {{ resolveStatusLabel(currentUserDetail.status) }}
            </el-tag>
          </div>

          <section class="detail-card">
            <h3>基础资料</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span>用户名</span>
                <strong>{{ currentUserDetail.username || '-' }}</strong>
              </div>
              <div class="detail-item">
                <span>昵称</span>
                <strong>{{ currentUserDetail.nickname || '-' }}</strong>
              </div>
              <div class="detail-item detail-item-wide">
                <span>已分配角色</span>
                <div v-if="resolveRoleBadges(currentUserDetail).length" class="role-tag-list">
                  <el-tag
                    v-for="role in resolveRoleBadges(currentUserDetail)"
                    :key="role.key"
                    :type="resolveRoleType(role.code)"
                    effect="light"
                  >
                    {{ role.label }}
                  </el-tag>
                </div>
                <strong v-else>未分配</strong>
              </div>
              <div class="detail-item detail-item-wide">
                <span>头像地址</span>
                <strong class="break-all">{{ currentUserDetail.avatarUrl || '-' }}</strong>
              </div>
            </div>
          </section>

          <section class="detail-card">
            <h3>登录与时间</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span>最近登录 IP</span>
                <strong>{{ currentUserDetail.lastLoginIp || '暂无记录' }}</strong>
              </div>
              <div class="detail-item">
                <span>最近登录时间</span>
                <strong>{{ formatDateTime(currentUserDetail.lastLoginAt, '暂无记录') }}</strong>
              </div>
              <div class="detail-item">
                <span>创建时间</span>
                <strong>{{ formatDateTime(currentUserDetail.createdAt) }}</strong>
              </div>
              <div class="detail-item">
                <span>更新时间</span>
                <strong>{{ formatDateTime(currentUserDetail.updatedAt) }}</strong>
              </div>
            </div>
          </section>
        </template>

        <el-empty v-else description="暂无用户详情" />
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.page-shell {
  --user-ink: #13212b;
  --user-muted: #607280;
  --user-border: rgba(19, 33, 43, 0.08);
  --user-border-strong: rgba(16, 140, 108, 0.22);
  --user-panel: rgba(255, 255, 255, 0.9);
  --user-accent: #108c6c;
  display: grid;
  gap: 18px;
}

.hero-card {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 18px;
  padding: 24px;
  border-radius: 24px;
  border: 1px solid var(--user-border-strong);
  background:
    radial-gradient(circle at 84% 18%, rgba(16, 140, 108, 0.22), transparent 32%),
    linear-gradient(135deg, #f3fbf8 0%, #eef7f5 44%, #f7fbfc 100%);
  box-shadow: 0 18px 40px rgba(16, 24, 40, 0.06);
}

.hero-copy {
  display: grid;
  align-content: start;
  gap: 10px;
}

.hero-kicker,
.section-kicker {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(19, 33, 43, 0.06);
  color: #325362;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-copy h1,
.workspace-head h2 {
  margin: 0;
  font-family: 'Space Grotesk', 'PingFang SC', sans-serif;
  color: var(--user-ink);
}

.hero-copy h1 {
  font-size: 1.5rem;
}

.hero-copy p,
.workspace-head p {
  margin: 0;
  color: var(--user-muted);
  line-height: 1.7;
}

.hero-side {
  display: grid;
  gap: 14px;
}

.hero-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.stat-item {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(19, 33, 43, 0.08);
  background: rgba(255, 255, 255, 0.8);
  text-align: left;
  cursor: pointer;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease;
}

.stat-item:hover {
  transform: translateY(-1px);
  border-color: rgba(16, 140, 108, 0.24);
  box-shadow: 0 12px 20px rgba(16, 24, 40, 0.06);
}

.stat-item.is-active {
  border-color: rgba(16, 140, 108, 0.34);
  background: rgba(16, 140, 108, 0.1);
  box-shadow: 0 12px 24px rgba(16, 140, 108, 0.08);
}

.stat-item.is-static {
  cursor: default;
}

.stat-item.is-static:hover {
  transform: none;
  border-color: rgba(19, 33, 43, 0.08);
  box-shadow: none;
}

.stat-item span {
  color: #587181;
  font-size: 0.82rem;
}

.stat-item strong {
  font-family: 'Space Grotesk', 'PingFang SC', sans-serif;
  color: var(--user-ink);
  font-size: 1.36rem;
}

.stat-item p {
  margin: 0;
  color: var(--user-muted);
  font-size: 0.84rem;
  line-height: 1.55;
}

.workspace-card {
  border-radius: 22px;
  border: 1px solid var(--user-border);
  background: var(--user-panel);
  box-shadow: 0 14px 32px rgba(16, 24, 40, 0.06);
}

.workspace-card :deep(.el-card__body) {
  display: grid;
  gap: 18px;
  padding: 22px;
}

.workspace-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.control-strip {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(19, 33, 43, 0.06);
  background: linear-gradient(180deg, rgba(247, 250, 249, 0.96), rgba(252, 254, 253, 0.98));
}

.query-form {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) minmax(180px, 0.9fr) auto;
  gap: 14px;
  align-items: end;
}

.query-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.query-form .actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.active-filters {
  display: grid;
  gap: 10px;
}

.active-filters > span {
  color: #46606f;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.active-filters p {
  margin: 0;
  color: var(--user-muted);
  line-height: 1.6;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.desktop-list {
  display: block;
}

.mobile-list {
  display: none;
}

.user-table {
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid rgba(19, 33, 43, 0.08);
}

.workspace-card :deep(.user-table .el-table__header-wrapper th) {
  background: linear-gradient(180deg, #edf8f3 0%, #e8f4ef 100%);
  color: #285366;
  font-weight: 700;
}

.workspace-card :deep(.user-table .el-table__cell) {
  padding: 15px 0;
  border-bottom-color: rgba(148, 163, 184, 0.16);
}

.workspace-card :deep(.user-table .el-table__row:hover td) {
  background: rgba(16, 140, 108, 0.03);
}

.identity-cell {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.identity-avatar {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: linear-gradient(135deg, rgba(16, 140, 108, 0.18), rgba(19, 33, 43, 0.08));
  color: #1d5b57;
  font-family: 'Space Grotesk', 'PingFang SC', sans-serif;
  font-weight: 700;
}

.identity-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.identity-copy strong {
  color: var(--user-ink);
  font-size: 0.98rem;
  line-height: 1.4;
}

.identity-copy span {
  color: var(--user-muted);
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.role-column,
.status-cell,
.activity-cell,
.action-cluster {
  display: grid;
  gap: 8px;
}

.role-column small,
.activity-cell span,
.activity-cell small,
.status-cell span,
.toggle-line span {
  color: var(--user-muted);
  line-height: 1.5;
}

.role-stack,
.role-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty-inline {
  color: var(--user-muted);
  font-size: 0.9rem;
}

.status-cell {
  align-content: start;
}

.activity-cell strong {
  color: var(--user-ink);
  line-height: 1.5;
}

.toggle-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(16, 140, 108, 0.05);
}

.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-start;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
}

.user-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(19, 33, 43, 0.08);
  background: #ffffff;
  box-shadow: 0 12px 24px rgba(16, 24, 40, 0.05);
}

.user-card-head,
.user-card-foot {
  display: grid;
  gap: 12px;
}

.identity-card-trigger {
  align-items: flex-start;
}

.user-card-body {
  display: grid;
  gap: 14px;
}

.mobile-section {
  display: grid;
  gap: 8px;
}

.mobile-section-title {
  color: #46606f;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.mobile-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.mobile-meta-item {
  display: grid;
  gap: 6px;
  padding: 12px;
  border-radius: 14px;
  background: #f7faf9;
  border: 1px solid rgba(19, 33, 43, 0.06);
}

.mobile-meta-item span {
  color: var(--user-muted);
  font-size: 0.82rem;
}

.mobile-meta-item strong {
  color: var(--user-ink);
  line-height: 1.5;
}

.row-actions-mobile {
  justify-content: flex-start;
}

.dialog-intro {
  display: grid;
  gap: 6px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(16, 140, 108, 0.08);
  border: 1px solid rgba(16, 140, 108, 0.14);
}

.dialog-intro strong {
  color: var(--user-ink);
}

.dialog-intro span {
  color: var(--user-muted);
  line-height: 1.6;
}

.user-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.user-form .full-span {
  grid-column: 1 / -1;
}

.user-form :deep(.el-form-item__label),
.password-form :deep(.el-form-item__label) {
  font-weight: 700;
  color: #3b5361;
}

.user-form :deep(.el-input__wrapper),
.password-form :deep(.el-input__wrapper) {
  border-radius: 12px;
}

.password-form {
  margin-top: 16px;
}

.role-meta {
  display: grid;
  gap: 4px;
  margin: 16px 0 0;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(19, 33, 43, 0.08);
  background: #f7faf9;
}

.role-meta span:first-child {
  font-size: 0.76rem;
  color: var(--user-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.role-meta strong {
  color: var(--user-ink);
}

.role-meta span:last-child {
  color: var(--user-muted);
}

.role-selector {
  margin-top: 16px;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.role-card {
  display: block;
  border-radius: 16px;
  border: 1px solid rgba(19, 33, 43, 0.08);
  background: #ffffff;
  padding: 14px 16px;
  cursor: pointer;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

.role-card:hover {
  border-color: rgba(16, 140, 108, 0.24);
  box-shadow: 0 10px 20px rgba(16, 24, 40, 0.06);
}

.role-card.is-active {
  border-color: rgba(16, 140, 108, 0.34);
  background: rgba(16, 140, 108, 0.05);
  box-shadow: 0 12px 24px rgba(16, 140, 108, 0.08);
}

.role-card :deep(.el-checkbox) {
  width: 100%;
  align-items: flex-start;
  gap: 10px;
}

.role-card :deep(.el-checkbox__label) {
  width: 100%;
  padding-left: 0;
}

.role-card-body {
  display: grid;
  gap: 8px;
}

.role-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.role-card-head strong {
  color: var(--user-ink);
}

.role-card-head span {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(16, 140, 108, 0.08);
  color: #0e785d;
  font-size: 0.76rem;
  font-weight: 700;
}

.role-card-body p {
  margin: 0;
  color: var(--user-muted);
  line-height: 1.6;
  font-size: 0.88rem;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.detail-panel {
  min-height: 100%;
  display: grid;
  align-content: start;
  gap: 16px;
}

.detail-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 20px;
  border-radius: 20px;
  color: #eff7f5;
  background:
    radial-gradient(circle at 80% 18%, rgba(16, 140, 108, 0.25), transparent 34%),
    linear-gradient(145deg, #13212b, #1e3643);
}

.detail-pill {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 0.73rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #dff6ef;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(223, 246, 239, 0.16);
}

.detail-hero h2 {
  margin: 14px 0 0;
  font-family: 'Space Grotesk', 'PingFang SC', sans-serif;
  font-size: 1.56rem;
}

.detail-hero p {
  margin: 6px 0 0;
  color: rgba(239, 247, 245, 0.78);
}

.detail-card {
  border-radius: 18px;
  border: 1px solid rgba(19, 33, 43, 0.08);
  background: #ffffff;
  padding: 18px;
}

.detail-card h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--user-ink);
}

.detail-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-item {
  border-radius: 14px;
  border: 1px solid rgba(19, 33, 43, 0.08);
  background: #f7faf9;
  padding: 12px 14px;
  display: grid;
  gap: 6px;
}

.detail-item-wide {
  grid-column: 1 / -1;
}

.detail-item span {
  color: var(--user-muted);
  font-size: 0.82rem;
}

.detail-item strong {
  color: var(--user-ink);
  line-height: 1.6;
}

.break-all {
  word-break: break-all;
}

@media (max-width: 1180px) {
  .hero-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .query-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .query-form .actions {
    grid-column: 1 / -1;
  }

  .desktop-list {
    display: none;
  }

  .mobile-list {
    display: grid;
    gap: 12px;
  }
}

@media (max-width: 760px) {
  .page-shell {
    gap: 14px;
  }

  .hero-card,
  .workspace-card :deep(.el-card__body) {
    padding: 16px;
  }

  .stats-grid,
  .query-form,
  .user-form,
  .role-grid,
  .mobile-meta-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .hero-actions,
  .pagination-wrap {
    justify-content: stretch;
  }

  .hero-actions :deep(.el-button),
  .query-form .actions :deep(.el-button) {
    flex: 1;
  }

  .row-actions {
    gap: 6px;
  }

  .detail-item-wide {
    grid-column: auto;
  }
}
</style>
