<script setup lang="ts">
import AppIcon from './AppIcon.vue'

/** 基于 el-dialog 的弹窗封装。
 *  保持旧版 API（title / icon / wide / @close / 默认插槽 / #footer），
 *  调用方仍用 v-if 控制挂载即打开。 */
withDefaults(defineProps<{
  title: string
  icon?: string
  wide?: boolean
}>(), { icon: '', wide: false })

const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <el-dialog
    :model-value="true"
    :width="wide ? 900 : 560"
    append-to-body
    destroy-on-close
    class="wh-modal"
    @close="emit('close')"
  >
    <template #header>
      <span class="modal-title">
        <AppIcon v-if="icon" :name="icon" :size="16" />
        {{ title }}
      </span>
    </template>
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </el-dialog>
</template>
