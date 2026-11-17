<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SideRail from '@/components/SideRail.vue'
import SideSub from '@/components/SideSub.vue'
import TopBar from '@/components/TopBar.vue'
import { api, setUnauthorizedHandler } from '@/api'
import { moduleOf } from '@/nav'
import type { UserInfo } from '@/types'

const route = useRoute()
const router = useRouter()

const user = ref<UserInfo | null>(null)
const booting = ref(true)

const TITLES: Record<string, string> = {
  '/': '工作台',
  '/clients': '客户',
  '/projects': '项目列表',
  '/tasks': '任务看板',
  '/invoices': '发票台账',
  '/plans': '回款计划',
  '/stats': '收支统计',
  '/notes': '笔记',
  '/bookmarks': '我的收藏',
  '/snippets': '代码片段',
  '/articles': '文章',
  '/publish': '发布记录',
  '/search': '全文检索',
  '/rss': 'RSS 订阅',
  '/toolbox': '万能工具台',
  '/repos': '开源项目',
  '/settings': '偏好设置',
}

const title = computed(() => TITLES[route.path] ?? '工作台')
const activeModule = computed(() => moduleOf(route.path))
const railKey = computed(() => activeModule.value?.key ?? 'home')

async function refreshUser(): Promise<boolean> {
  try {
    user.value = await api.get<UserInfo>('/api/auth/me')
    return true
  } catch {
    user.value = null
    return false
  }
}

async function logout() {
  try {
    await api.post('/api/auth/logout')
  } catch {
    // 登出失败也要把本地状态清掉
  }
  user.value = null
  router.push('/login')
}

/** 路由变化时刷新登录态：登录页跳回 / 之后，靠这里把 user 拉起来。 */
watch(
  () => route.path,
  async (path) => {
    if (booting.value) return
    if (path === '/login') {
      user.value = null
      return
    }
    if (!user.value) {
      const ok = await refreshUser()
      if (!ok) router.push('/login')
    }
  },
)

onMounted(async () => {
  setUnauthorizedHandler(() => {
    user.value = null
    if (route.path !== '/login') router.push('/login')
  })
  const ok = await refreshUser()
  // 先完成跳转再结束启动态，避免未登录时 Dashboard 抢跑发一堆 401
  if (!ok && route.path !== '/login') {
    await router.push('/login')
  }
  booting.value = false
})
</script>

<template>
  <div v-if="booting" class="loading"><div class="spinner" /></div>

  <!-- 未登录：渲染登录页（无外壳） -->
  <RouterView v-else-if="!user" />

  <!-- 已登录：完整外壳 -->
  <div v-else class="app-shell">
    <TopBar :title="title" :user="user" @home="router.push('/')" @logout="logout" />
    <div class="app-below">
      <SideRail :active="railKey" @select="(m) => router.push(m.path)" />
      <SideSub
        v-if="activeModule && activeModule.children.length > 1"
        :module="activeModule"
        @navigate="(path) => router.push(path)"
      />
      <main class="app-main">
        <div class="app-scroll">
          <RouterView :user="user" />
        </div>
      </main>
    </div>
  </div>
</template>
