<script setup lang="ts">
import AppIcon from './AppIcon.vue'

withDefaults(defineProps<{
  title: string
  icon?: string
  wide?: boolean
}>(), { icon: '', wide: false })

const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="emit('close')">
      <div class="modal-panel" :class="{ wide }">
        <header class="modal-head">
          <span class="modal-title">
            <AppIcon v-if="icon" :name="icon" :size="16" />
            {{ title }}
          </span>
          <button class="icon-btn" type="button" title="关闭" @click="emit('close')">
            <AppIcon name="plus" :size="16" />
          </button>
        </header>
        <div class="modal-body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="modal-foot">
          <slot name="footer" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>
