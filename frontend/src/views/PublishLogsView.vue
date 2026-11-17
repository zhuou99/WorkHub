<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { api } from '@/api'
import type { PublishLog } from '@/types'
import { formatDateTime } from '@/utils'

const loading = ref(true)
const error = ref('')
const items = ref<PublishLog[]>([])
const kw = ref('')
const result = ref('all')

const CHANNEL_TEXT: Record<string, string> = { cnblogs: '博客园', wechat: '公众号', manual: '手动' }

function match(l: PublishLog, k: string): boolean {
  if (!k.trim()) return true
  const needle = k.trim().toLowerCase()
  return [l.articleTitle, l.channel, l.detail].some((v) => v && v.toLowerCase().includes(needle))
}

const shown = computed(() =>
  items.value.filter((l) => (result.value === 'all' || l.result === result.value) && match(l, kw.value)),
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = await api.get<PublishLog[]>('/api/publish/logs')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载发布记录失败'
  } finally {
    loading.value = false
  }
}

async function clearAll() {
  await api.del('/api/publish/logs')
  items.value = []
}

async function remove(log: PublishLog) {
  await api.del(`/api/publish/logs/${log.id}`)
  items.value = items.value.filter((x) => x.id !== log.id)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading"><div class="spinner" /></div>
  <div v-else-if="error" class="card"><div class="empty">{{ error }}</div></div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">发布记录</div>
        <div class="page-sub">博客园 / 公众号每次导出的留痕：成功失败一眼看清。</div>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="!items.length" @click="clearAll"><AppIcon name="trash" :size="14" /> 清空</button>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="search" style="position: relative">
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索文章标题 / 渠道 / 详情" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <select v-model="result" class="input" style="width: 120px">
        <option value="all">成功与失败</option>
        <option value="success">只看成功</option>
        <option value="failure">只看失败</option>
      </select>
    </div>

    <div v-if="!shown.length" class="page-empty">
      <p>还没有发布记录。去「文章」页导出到博客园或公众号，这里就会留下痕迹。</p>
    </div>

    <table v-else class="table">
      <thead><tr><th>文章</th><th>渠道</th><th>结果</th><th>详情</th><th>时间</th><th class="right">操作</th></tr></thead>
      <tbody>
        <tr v-for="l in shown" :key="l.id">
          <td>{{ l.articleTitle || '—' }}</td>
          <td><span class="pill st-talking">{{ CHANNEL_TEXT[l.channel] || l.channel }}</span></td>
          <td><span class="pill" :class="l.result === 'success' ? 'st-done' : 'st-void'">{{ l.result === 'success' ? '成功' : '失败' }}</span></td>
          <td class="muted">{{ l.detail || '' }}</td>
          <td>{{ formatDateTime(l.createTime) }}</td>
          <td class="right"><button class="btn" style="height: 26px; font-size: 12px; color: var(--danger-color)" @click="remove(l)"><AppIcon name="trash" :size="13" /></button></td>
        </tr>
      </tbody>
    </table>
  </template>
</template>
