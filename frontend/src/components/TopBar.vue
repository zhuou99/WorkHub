<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'
import type { UserInfo } from '@/types'

defineProps<{ title: string; user: UserInfo | null }>()
const emit = defineEmits<{
  (e: 'home'): void
  (e: 'logout'): void
  (e: 'search', keyword: string): void
}>()

const router = useRouter()
const kw = ref('')

function onSearch() {
  if (kw.value.trim()) emit('search', kw.value.trim())
}
</script>

<template>
  <header class="app-top">
    <div class="app-brand" title="WorkHub" @click="emit('home')">
      <div class="app-mark">W</div>
    </div>

    <div class="app-topbar">
      <div class="app-title">{{ title }}</div>

      <div class="app-topbar-right">
        <el-input
          v-model="kw"
          class="app-search"
          placeholder="搜索菜单、页面…"
          clearable
          @keyup.enter="onSearch"
        >
          <template #prefix><AppIcon name="search" :size="15" /></template>
        </el-input>

        <el-button text class="topbar-icon" title="刷新" @click="router.go(0)">
          <AppIcon name="refresh" :size="16" />
        </el-button>
        <el-button text class="topbar-icon" title="全屏">
          <AppIcon name="fullscreen" :size="16" />
        </el-button>
        <el-button text class="topbar-icon" title="通知">
          <AppIcon name="bell" :size="16" />
        </el-button>

        <el-dropdown @command="(cmd: string) => cmd === 'logout' && emit('logout')">
          <div class="app-user">
            <el-avatar :size="30" class="app-avatar">{{ (user?.name ?? '?').slice(0, 1) }}</el-avatar>
            <div class="app-user-meta">
              <div class="app-user-name">{{ user?.name ?? '未登录' }}</div>
              <div class="app-user-role">{{ user?.role ?? '' }}</div>
            </div>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout" divided>
                <AppIcon name="log-in" :size="14" /> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>
