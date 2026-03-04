<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ArrowRight, Expand, Fold, SwitchButton, UserFilled } from '@element-plus/icons-vue'

const props = defineProps({
  isCollapse: {
    type: Boolean,
    default: false,
  },
  breadcrumbs: {
    type: Array,
    default: () => [],
  },
  username: {
    type: String,
    default: 'Admin',
  },
  role: {
    type: String,
    default: 'ADMIN',
  },
})

const emit = defineEmits(['toggle-collapse', 'logout'])
const router = useRouter()

const roleLabel = computed(() => {
  const roleMap = {
    ADMIN: '超级管理员',
    OPERATOR: '运营管理员',
    VIEWER: '只读观察者',
  }
  return roleMap[props.role] || props.role || '管理员'
})

const avatarText = computed(() => props.username?.charAt(0)?.toUpperCase() || 'A')

async function handleUserCommand(command) {
  if (command === 'profile') {
    await router.push('/profile')
    return
  }

  if (command !== 'logout') return

  try {
    await ElMessageBox.confirm('确认要退出当前管理会话吗？', '安全退出', {
      type: 'warning',
      confirmButtonText: '确认退出',
      cancelButtonText: '取消',
      confirmButtonClass: 'el-button--danger',
      center: true,
      roundButton: true,
    })
  } catch {
    return
  }

  emit('logout')
}
</script>

<template>
  <el-header class="top-bar">
    <div class="top-bar-left">
      <el-button class="collapse-btn" text @click="emit('toggle-collapse')">
        <el-icon><component :is="isCollapse ? Expand : Fold" /></el-icon>
      </el-button>

      <el-breadcrumb :separator-icon="ArrowRight" class="breadcrumb">
        <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item v-for="(item, index) in breadcrumbs" :key="`${item.path}-${index}`">
          {{ item.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="top-bar-right">
      <el-dropdown trigger="click" @command="handleUserCommand">
        <div class="user-profile">
          <div class="user-info">
            <span class="name">{{ username || 'Admin' }}</span>
            <span class="role">{{ roleLabel }}</span>
          </div>
          <el-avatar :size="38" class="user-avatar">{{ avatarText }}</el-avatar>
        </div>
        <template #dropdown>
          <el-dropdown-menu class="user-dropdown">
            <el-dropdown-item :icon="UserFilled" command="profile">个人中心</el-dropdown-item>
            <el-dropdown-item divided :icon="SwitchButton" command="logout" class="logout-item">
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<style scoped>
.top-bar {
  height: 72px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border-bottom: 1px solid rgba(22, 38, 48, 0.08);
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  color: var(--og-slate-700);
  transition: all 0.3s ease;
}

.collapse-btn:hover {
  background: #eef3f1;
  color: var(--og-emerald-700);
}

:deep(.breadcrumb .el-breadcrumb__inner) {
  color: var(--og-slate-600);
  font-weight: 500;
  transition: all 0.3s ease;
}

:deep(.breadcrumb .el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--og-slate-900);
  font-weight: 700;
}

.top-bar-right .user-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 8px 6px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.top-bar-right .user-profile:hover {
  background: #f3f7f5;
  border-color: rgba(18, 161, 115, 0.18);
  box-shadow: 0 8px 18px rgba(18, 30, 42, 0.08);
}

.top-bar-right .user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.top-bar-right .name {
  font-size: 0.94rem;
  font-weight: 700;
  color: var(--og-slate-900);
  line-height: 1.2;
}

.top-bar-right .role {
  font-size: 0.76rem;
  color: var(--og-slate-500);
  line-height: 1.2;
}

.top-bar-right .user-avatar {
  background: linear-gradient(135deg, #1b2a35 0%, #253541 100%);
  color: #e8fff7;
  font-weight: 700;
  border: 2px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 4px 12px rgba(13, 23, 32, 0.18);
  transition: all 0.3s ease;
}

.user-dropdown {
  padding: 8px;
  border-radius: 12px;
  border: 1px solid rgba(27, 41, 53, 0.12);
  box-shadow: 0 16px 40px rgba(16, 26, 35, 0.16);
}

:deep(.user-dropdown .el-dropdown-menu__item) {
  border-radius: 9px;
  margin: 3px 0;
  padding: 9px 14px;
  transition: all 0.3s ease;
}

:deep(.user-dropdown .logout-item) {
  color: var(--el-color-danger);
}

:deep(.user-dropdown .logout-item:hover) {
  background: var(--el-color-danger-light-9);
}

@media (max-width: 768px) {
  .top-bar {
    padding: 0 14px;
    height: 66px;
  }

  .breadcrumb {
    max-width: 45vw;
    overflow: hidden;
  }

  :deep(.breadcrumb .el-breadcrumb__inner) {
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
    display: inline-block;
    max-width: 100%;
  }

  .top-bar-right .user-info {
    display: none;
  }
}
</style>
