<template>
  <div class="login-container">
    <div class="login-box">
      <div class="settings-bar">
        <!-- 主题切换 -->
        <el-tooltip :content="$t(themeStore.theme === 'light' ? 'theme.switchToDark' : 'theme.switchToLight')" placement="bottom">
          <el-button circle size="small" @click="themeStore.toggleTheme()">
            <el-icon v-if="themeStore.theme === 'light'"><Moon /></el-icon>
            <el-icon v-else><Sunny /></el-icon>
          </el-button>
        </el-tooltip>

        <!-- 语言切换 -->
        <el-select v-model="language" size="small" @change="changeLanguage" style="width: 110px">
          <el-option label="🇨🇳 中文" value="zh-CN" />
          <el-option label="🇺🇸 English" value="en-US" />
        </el-select>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @submit.prevent="handleSubmit"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            :placeholder="$t('auth.username')"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            :placeholder="$t('auth.password')"
            size="large"
            show-password
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleSubmit"
            class="login-button"
          >
            {{ $t('auth.login') }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useLocaleStore } from '@/stores/locale'
import { useThemeStore } from '@/stores/theme'
import { Moon, Sunny } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const userStore = useUserStore()
const localeStore = useLocaleStore()
const themeStore = useThemeStore()

const language = ref(localeStore.locale || 'zh-CN')
const loading = ref(false)
const formRef = ref(null)

// 登录表单
const form = reactive({
  username: '',
  password: ''
})

const rules = computed(() => ({
  username: [
    { required: true, message: t('auth.usernameRequired'), trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('auth.passwordRequired'), trigger: 'blur' }
  ]
}))

const changeLanguage = (lang) => {
  language.value = lang
  localeStore.setLocale(lang)
}

// 登录
const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const success = await userStore.login(
      form.username,
      form.password
    )

    if (success) {
      ElMessage.success(t('auth.loginSuccess'))
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } else {
      ElMessage.error(t('auth.loginFailed'))
    }
  } catch (error) {
    ElMessage.error(t('auth.loginFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: 'Arial', sans-serif;
}

.login-box {
  width: 360px;
  margin: 0 auto;
  background: white;
  padding: 32px;
  border-radius: 8px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  position: relative;
  transition: background-color 0.3s, color 0.3s;
}

html.dark .login-box {
  background: var(--card-bg);
  color: var(--text-primary);
}

.settings-bar {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 40px;
}

.login-button {
  width: 100%;
  padding: 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.3s;
}

.login-button:hover {
  background: #5568d3;
}

:deep(.el-input__inner) {
  padding: 12px;
  font-size: 14px;
}

:deep(.el-form-item) {
  margin-bottom: 20px;
}

:deep(.el-form-item__error) {
  font-size: 12px;
}
</style>
