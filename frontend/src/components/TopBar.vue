<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import type { UserInfo } from '@/types'

defineProps<{ title: string; user: UserInfo | null }>()
const emit = defineEmits<{
  (e: 'home'): void
  (e: 'logout'): void
  (e: 'search', keyword: string): void
}>()
</script>

<template>
  <header class="app-top">
    <div class="app-brand" title="WorkHub" @click="emit('home')">
      <div class="app-mark">W</div>
    </div>

    <div class="app-topbar">
      <div class="app-title">{{ title }}</div>

      <div class="app-topbar-right">
        <label class="app-search">
          <AppIcon name="search" :size="15" />
          <input
            placeholder="搜索菜单、页面…"
            @keyup.enter="emit('search', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <button class="icon-btn" type="button" title="刷新" @click="$router.go(0)">
          <AppIcon name="refresh" :size="16" />
        </button>
        <button class="icon-btn" type="button" title="全屏">
          <AppIcon name="fullscreen" :size="16" />
        </button>
        <button class="icon-btn" type="button" title="通知">
          <AppIcon name="bell" :size="16" />
        </button>

        <div class="app-user">
          <div class="app-avatar">{{ (user?.name ?? '?').slice(0, 1) }}</div>
          <div class="app-user-meta">
            <div class="app-user-name">{{ user?.name ?? '未登录' }}</div>
            <div class="app-user-role">{{ user?.role ?? '' }}</div>
          </div>
          <button class="icon-btn" type="button" title="退出登录" @click="emit('logout')">
            <AppIcon name="log-in" :size="16" />
          </button>
        </div>
      </div>
    </div>
  </header>
</template>
