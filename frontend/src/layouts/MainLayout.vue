<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '160px'" class="sidebar">
      <div class="logo">
        <span class="logo-icon" v-if="!isCollapse">₿</span>
        <span v-if="!isCollapse">BTC Watcher</span>
      </div>

      <el-menu
        :default-active="$route.path"
        :collapse="isCollapse"
        router
        background-color="#001529"
        text-color="#fff"
        active-text-color="#1890ff"
      >
        <el-menu-item index="/">
          <el-icon><DataLine /></el-icon>
          <template #title>{{ $t('nav.dashboard') }}</template>
        </el-menu-item>

        <el-menu-item index="/strategies">
          <el-icon><Operation /></el-icon>
          <template #title>{{ $t('nav.strategies') }}</template>
        </el-menu-item>

        <el-menu-item index="/signals">
          <el-icon><Notification /></el-icon>
          <template #title>{{ $t('nav.signals') }}</template>
        </el-menu-item>

        <el-menu-item index="/proxies">
          <el-icon><Connection /></el-icon>
          <template #title>{{ $t('nav.proxies') }}</template>
        </el-menu-item>

        <el-menu-item index="/monitoring">
          <el-icon><Monitor /></el-icon>
          <template #title>{{ $t('nav.monitoring') }}</template>
        </el-menu-item>

        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>{{ $t('nav.settings') }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-icon" @click="toggleCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>

          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">{{ $t('common.home') }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="$route.meta.title">
              {{ $t($route.meta.title) }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 主题切换 -->
          <el-tooltip :content="$t(themeStore.theme === 'light' ? 'theme.switchToDark' : 'theme.switchToLight')" placement="bottom">
            <el-button circle @click="themeStore.toggleTheme()">
              <el-icon v-if="themeStore.theme === 'light'"><Moon /></el-icon>
              <el-icon v-else><Sunny /></el-icon>
            </el-button>
          </el-tooltip>

          <!-- 语言切换 -->
          <el-dropdown @command="handleLanguageChange" trigger="click">
            <el-button circle>
              <el-icon><Platform /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="zh-CN" :disabled="localeStore.locale === 'zh-CN'">
                  <span :style="{ fontWeight: localeStore.locale === 'zh-CN' ? 'bold' : 'normal' }">
                    🇨🇳 中文
                  </span>
                </el-dropdown-item>
                <el-dropdown-item command="en-US" :disabled="localeStore.locale === 'en-US'">
                  <span :style="{ fontWeight: localeStore.locale === 'en-US' ? 'bold' : 'normal' }">
                    🇺🇸 English
                  </span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 容量状态 -->
          <el-badge v-if="capacityUtilization" :value="capacityUtilization" class="capacity-badge">
            <el-button circle>
              <el-icon><Odometer /></el-icon>
            </el-button>
          </el-badge>
          <el-button v-else circle>
            <el-icon><Odometer /></el-icon>
          </el-button>

          <!-- 通知 -->
          <el-badge v-if="notificationCount > 0" :value="notificationCount" :max="99">
            <el-button circle>
              <el-icon><Bell /></el-icon>
            </el-button>
          </el-badge>
          <el-button v-else circle>
            <el-icon><Bell /></el-icon>
          </el-button>

          <!-- 用户菜单 -->
          <el-dropdown @command="handleCommand" trigger="click">
            <el-button text>
              <span class="user-dropdown">
                <el-avatar :size="28">{{ userStore.user?.username?.charAt(0) }}</el-avatar>
                <span class="username">{{ userStore.user?.username }}</span>
              </span>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">{{ $t('user.profile') }}</el-dropdown-item>
                <el-dropdown-item command="password">{{ $t('user.changePassword') }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">{{ $t('auth.logout') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useSystemStore } from '@/stores/system'
import { useLocaleStore } from '@/stores/locale'
import { useThemeStore } from '@/stores/theme'
import {
  DataLine,
  Operation,
  Notification,
  Connection,
  Monitor,
  Setting,
  Fold,
  Expand,
  Odometer,
  Bell,
  Moon,
  Sunny,
  Platform
} from '@element-plus/icons-vue'

const router = useRouter()
const { t } = useI18n()
const userStore = useUserStore()
const systemStore = useSystemStore()
const localeStore = useLocaleStore()
const themeStore = useThemeStore()

const isCollapse = ref(false)
const capacityUtilization = ref('')
const notificationCount = ref(0)
let refreshTimer = null

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const handleCommand = (command) => {
  if (command === 'logout') {
    if (confirm(t('auth.logoutConfirm'))) {
      try {
        userStore.logout()
        router.push('/login')
      } catch (error) {
        console.error('Logout error:', error)
      }
    }
  } else if (command === 'profile') {
    alert(t('user.profileComingSoon'))
  } else if (command === 'password') {
    alert(t('user.changePasswordComingSoon'))
  }
}

const handleLanguageChange = (lang) => {
  localeStore.setLocale(lang)
  ElMessage.success(t('language.switchSuccess'))
}

const fetchCapacity = async () => {
  try {
    const res = await systemStore.fetchCapacity()
    capacityUtilization.value = `${res.utilization_percent.toFixed(1)}%`
  } catch (error) {
    console.error('Failed to fetch capacity:', error)
  }
}

onMounted(() => {
  fetchCapacity()
  // 每30秒刷新一次容量信息
  refreshTimer = setInterval(fetchCapacity, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.main-layout {
  height: 100vh;
}

.sidebar {
  background-color: #001529;
  transition: width 0.3s;
}

.logo {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-icon {
  font-size: 24px;
  margin-right: 8px;
  color: #f7931a;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  padding: 0 12px;
  height: 44px;
  transition: background-color 0.3s, border-color 0.3s;
}

html.dark .header {
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-icon {
  font-size: 16px;
  cursor: pointer;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.capacity-badge {
  margin-right: 4px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 6px;
}

.username {
  font-size: 13px;
}

.main-content {
  background: #f0f2f5;
  padding: 6px;
  overflow-y: auto;
}
</style>
