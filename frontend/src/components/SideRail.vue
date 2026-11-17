<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import { NAV, type NavModule } from '@/nav'

defineProps<{ active: string }>()
const emit = defineEmits<{ (e: 'select', module: NavModule): void }>()
</script>

<template>
  <nav class="app-rail">
    <button
      v-for="m in NAV"
      :key="m.key"
      type="button"
      class="rail-item"
      :class="{ on: active === m.key }"
      :title="m.name"
      @click="emit('select', m)"
    >
      <AppIcon :name="m.icon" :size="19" />
      <span>{{ m.name }}</span>
    </button>
  </nav>
</template>
