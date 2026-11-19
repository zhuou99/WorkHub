<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'
import { api } from '@/api'
import type { AuthGuardState } from '@/types'

const router = useRouter()

const userName = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')
const guard = ref<AuthGuardState | null>(null)

const FEATURES = [
  { icon: 'puzzle', title: '万能工具箱', desc: '编解码、格式转换、正则、哈希、即时翻译。' },
  { icon: 'bookmark', title: '资料库', desc: '剪藏或文章、标签管理、全文可检索。' },
  { icon: 'file-text', title: '创作与发布', desc: 'Markdown 写作，一键出博客园与公众号稿。' },
  { icon: 'briefcase', title: '生意台账', desc: '客户、项目、发票、回款，一条线串起来。' },
]

onMounted(async () => {
  try {
    guard.value = await api.get<AuthGuardState>('/api/auth/guard')
  } catch {
    // 拿不到保护状态不阻塞登录
  }
})

async function submit() {
  if (busy.value) return
  error.value = ''
  busy.value = true
  try {
    await api.post('/api/auth/login', {
      userName: userName.value,
      password: password.value,
    })
    // 登录成功后跳回工作台，App 的路由监听会重新拉取当前用户
    router.push('/')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <!-- 左侧品牌栏 -->
    <div class="auth-brand">
      <div class="auth-orb auth-orb--1" />
      <div class="auth-orb auth-orb--2" />

      <div class="auth-brand-top">
        <div class="auth-mark">W</div>
        <div class="auth-brand-name">WorkHub</div>
      </div>

      <div class="auth-brand-body">
        <div class="auth-eyebrow">独立开发者 · 一人公司工作台</div>
        <h2>把工具、资料、创作<br />和生意收进同一个空间</h2>
        <p class="auth-lede">
          开发小工具、网络收藏、笔记与文章发布、客户项目与发票——数据全在本机 SQLite，不依赖任何云。
        </p>
        <ul class="auth-features">
          <li v-for="f in FEATURES" :key="f.title" class="auth-feature">
            <div class="auth-feature-ico"><AppIcon :name="f.icon" :size="18" /></div>
            <div>
              <b>{{ f.title }}</b>
              <p>{{ f.desc }}</p>
            </div>
          </li>
        </ul>
      </div>

      <div class="auth-brand-foot">© 2026 WorkHub · 数据都在本机</div>
    </div>

    <!-- 右侧表单 -->
    <div class="auth-form-side">
      <el-button text class="auth-theme" title="深色模式（暂未实现）">
        <AppIcon name="moon" :size="16" />
      </el-button>

      <form class="auth-form" @submit.prevent="submit">
        <h2>欢迎回来</h2>
        <p class="auth-sub">登录以进入你的个人工作空间</p>

        <el-alert v-if="error" type="error" :title="error" :closable="false" class="auth-error" />

        <div class="auth-field">
          <label for="username">用户名</label>
          <div class="auth-wrap">
            <el-input id="username" v-model="userName" size="large" autocomplete="username" placeholder="admin">
              <template #prefix><AppIcon name="user" :size="15" /></template>
            </el-input>
          </div>
        </div>

        <div class="auth-field">
          <label for="password">密码</label>
          <div class="auth-wrap">
            <el-input
              id="password"
              v-model="password"
              size="large"
              type="password"
              show-password
              autocomplete="current-password"
              placeholder="••••••"
            >
              <template #prefix><AppIcon name="lock" :size="15" /></template>
            </el-input>
          </div>
        </div>

        <el-button type="primary" native-type="submit" style="width: 100%; height: 40px" :loading="busy">
          <AppIcon name="log-in" :size="15" />
          {{ busy ? '登录中…' : '登 录' }}
        </el-button>

        <div class="auth-note">
          首次使用 <b>admin</b> · <b>admin123</b>，登录后请在「设置」里改掉
        </div>
        <div class="auth-foot">
          登录状态由本机服务端会话维持，数据不出这台电脑
          <template v-if="guard && guard.locked">
            · 账号已锁定，剩余 {{ guard.remainingSeconds }} 秒
          </template>
        </div>
      </form>
    </div>
  </div>
</template>
