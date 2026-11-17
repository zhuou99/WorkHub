<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppIcon from './AppIcon.vue'
import type { NavModule } from '@/nav'

defineProps<{ module: NavModule }>()
const emit = defineEmits<{ (e: 'navigate', path: string): void }>()

const route = useRoute()
</script>

<template>
  <aside class="app-sub">
    <h4>{{ module.name }}</h4>
    <button
      v-for="child in module.children"
      :key="child.path"
      type="button"
      class="app-sitem"
      :class="{ on: route.path === child.path }"
      @click="emit('navigate', child.path)"
    >
      <AppIcon :name="child.icon" :size="15" />
      <span>{{ child.name }}</span>
    </button>
  </aside>
</template>
