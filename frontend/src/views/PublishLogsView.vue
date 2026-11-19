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
  <div v-if="loading" v-loading="true" style="min-height: 240px" />
  <el-alert v-else-if="error" type="error" :title="error" :closable="false" show-icon />

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">发布记录</div>
        <div class="page-sub">博客园 / 公众号每次导出的留痕：成功失败一眼看清。</div>
      </div>
      <div class="page-actions">
        <el-button :disabled="!items.length" @click="clearAll"><AppIcon name="trash" :size="14" /> 清空</el-button>
      </div>
    </div>

    <div class="page-toolbar">
      <el-input v-model="kw" placeholder="搜索文章标题 / 渠道 / 详情">
        <template #prefix><AppIcon name="search" :size="15" /></template>
      </el-input>
      <el-select v-model="result" style="width: 120px">
        <el-option value="all" label="成功与失败" />
        <el-option value="success" label="只看成功" />
        <el-option value="failure" label="只看失败" />
      </el-select>
    </div>

    <el-empty v-if="!shown.length" description="还没有发布记录。去「文章」页导出到博客园或公众号，这里就会留下痕迹。" />

    <el-table v-else :data="shown">
      <el-table-column label="文章">
        <template #default="{ row }">{{ row.articleTitle || '—' }}</template>
      </el-table-column>
      <el-table-column label="渠道">
        <template #default="{ row }"><el-tag size="small" type="info">{{ CHANNEL_TEXT[row.channel] || row.channel }}</el-tag></template>
      </el-table-column>
      <el-table-column label="结果">
        <template #default="{ row }"><el-tag size="small" :type="row.result === 'success' ? 'success' : 'danger'">{{ row.result === 'success' ? '成功' : '失败' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="详情">
        <template #default="{ row }"><span class="muted">{{ row.detail || '' }}</span></template>
      </el-table-column>
      <el-table-column label="时间">
        <template #default="{ row }">{{ formatDateTime(row.createTime) }}</template>
      </el-table-column>
      <el-table-column label="操作" align="right">
        <template #default="{ row }">
          <el-button size="small" type="danger" plain @click="remove(row as PublishLog)"><AppIcon name="trash" :size="13" /></el-button>
        </template>
      </el-table-column>
    </el-table>
  </template>
</template>
