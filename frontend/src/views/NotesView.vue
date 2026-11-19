<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Note } from '@/types'
import { formatDateTime } from '@/utils'

const loading = ref(true)
const error = ref('')
const items = ref<Note[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 20
const kw = ref('')
const keyword = ref('')
const quick = ref('')
const adding = ref(false)

const editing = ref(false)
const isNew = ref(false)
const edit = ref<Note | null>(null)

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function preview(note: Note): string {
  const text = (note.content ?? '').replace(/\r/g, '').replace(/\n/g, ' ').trim()
  if (!text) return '暂无正文'
  return text + ((note.content ?? '').length >= 120 ? '…' : '')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await api.page<Note>(`/api/notes/page?pageIndex=${page.value}&pageSize=${PAGE_SIZE}&keyword=${encodeURIComponent(keyword.value)}`)
    total.value = result.total
    items.value = result.rows
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载笔记失败'
  } finally {
    loading.value = false
  }
}

function applySearch() { keyword.value = kw.value.trim(); page.value = 1; load() }
function clearSearch() { kw.value = ''; keyword.value = ''; page.value = 1; load() }
function goPage(p: number) { page.value = Math.max(1, p); load() }

async function quickAdd() {
  if (adding.value) return
  const text = quick.value.trim()
  if (!text) return
  adding.value = true
  try {
    await api.post<Note>('/api/notes', { title: text.length > 30 ? text.slice(0, 30) + '…' : text, content: text, tags: '收件箱' })
    quick.value = ''
    await load()
  } finally {
    adding.value = false
  }
}

function openAdd() {
  edit.value = { id: '', title: '', content: null, tags: null, pinned: false, createTime: null, modifyTime: null }
  isNew.value = true
  editing.value = true
}
function openEdit(note: Note) { edit.value = { ...note }; isNew.value = false; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.title.trim()) return
  edit.value.title = edit.value.title.trim()
  await api.post<Note>('/api/notes', edit.value)
  editing.value = false
  await load()
}

async function remove(note: Note) {
  await api.del(`/api/notes/${note.id}`)
  await load()
}

onMounted(load)
</script>

<template>
  <div v-if="loading" v-loading="true" style="min-height: 240px" />
  <el-alert v-else-if="error" type="error" :title="error" :closable="false" show-icon />

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">笔记</div>
        <div class="page-sub">Markdown 笔记与灵感收件箱：每页 20 条，点击标题进入编辑。</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建笔记</el-button>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="search">
        <el-input v-model="kw" placeholder="搜索标题 / 内容 / 标签" @keyup.enter="applySearch">
          <template #prefix><AppIcon name="search" :size="15" /></template>
        </el-input>
      </div>
      <el-button @click="applySearch"><AppIcon name="search" :size="13" /> 查询</el-button>
      <el-button @click="clearSearch">清除</el-button>
      <div class="quick" style="flex: 1 1 300px">
        <div class="quick-in">
          <el-input v-model="quick" placeholder="灵感收件箱：想到什么先记一句，回车入库" @keyup.enter="quickAdd">
            <template #prefix><AppIcon name="zap" :size="15" /></template>
          </el-input>
        </div>
        <el-button :disabled="adding || !quick.trim()" @click="quickAdd"><AppIcon name="plus" :size="13" /> 记下</el-button>
      </div>
    </div>

    <el-empty v-if="!items.length" :description="keyword ? '没有匹配的笔记。' : '还没有笔记，用上面的收件箱记第一条。'" />

    <el-table v-else :data="items">
      <el-table-column label="标题 / 正文预览">
        <template #default="{ row }">
          <b style="cursor: pointer" @click="openEdit(row as Note)">{{ row.title || '未命名' }}</b>
          <div class="tax">{{ preview(row as Note) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="标签">
        <template #default="{ row }">{{ row.tags || '—' }}</template>
      </el-table-column>
      <el-table-column label="置顶">
        <template #default="{ row }">{{ row.pinned ? '置顶' : '—' }}</template>
      </el-table-column>
      <el-table-column label="创建时间">
        <template #default="{ row }">{{ formatDateTime(row.createTime) }}</template>
      </el-table-column>
      <el-table-column label="操作" align="right">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button size="small" @click="openEdit(row as Note)"><AppIcon name="edit" :size="13" /></el-button>
            <el-button size="small" type="danger" plain @click="remove(row as Note)"><AppIcon name="trash" :size="13" /></el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-if="pageCount > 1" layout="prev, pager, next" :total="total" :page-size="PAGE_SIZE" :current-page="page" @current-change="goPage" />

    <Modal v-if="editing && edit" :title="isNew ? '新建笔记' : '编辑笔记'" icon="notepad" wide @close="editing = false">
      <div class="form-grid">
        <div class="field full"><label>标题 <span class="req">*</span></label><el-input v-model="edit.title" maxlength="300" /></div>
        <div class="field full"><label>正文（Markdown）</label><el-input v-model="edit.content" type="textarea" :rows="14" placeholder="支持 Markdown" /></div>
        <div class="field"><label>标签</label><el-input v-model="edit.tags" maxlength="300" placeholder="逗号分隔" /></div>
        <div class="field" style="align-self: end"><label style="display: flex; align-items: center; gap: 8px; font-weight: 500"><el-checkbox v-model="edit.pinned" /> 置顶</label></div>
      </div>
      <template #footer>
        <el-button @click="editing = false">取消</el-button>
        <el-button type="primary" @click="save"><AppIcon name="check" :size="14" /> 保存</el-button>
      </template>
    </Modal>
  </template>
</template>
