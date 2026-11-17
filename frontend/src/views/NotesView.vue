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
  <div v-if="loading" class="loading"><div class="spinner" /></div>
  <div v-else-if="error" class="card"><div class="empty">{{ error }}</div></div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">笔记</div>
        <div class="page-sub">Markdown 笔记与灵感收件箱：每页 20 条，点击标题进入编辑。</div>
      </div>
      <div class="page-actions">
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建笔记</button>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="search" style="position: relative">
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索标题 / 内容 / 标签" @keyup.enter="applySearch" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <button class="btn" @click="applySearch"><AppIcon name="search" :size="13" /> 查询</button>
      <button class="btn" @click="clearSearch">清除</button>
      <div class="quick" style="flex: 1 1 300px">
        <div class="quick-in">
          <AppIcon name="zap" :size="15" />
          <input v-model="quick" class="input" placeholder="灵感收件箱：想到什么先记一句，回车入库" @keyup.enter="quickAdd" />
        </div>
        <button class="btn" :disabled="adding || !quick.trim()" @click="quickAdd"><AppIcon name="plus" :size="13" /> 记下</button>
      </div>
    </div>

    <div v-if="!items.length" class="page-empty">
      <p>{{ keyword ? '没有匹配的笔记。' : '还没有笔记，用上面的收件箱记第一条。' }}</p>
    </div>

    <table v-else class="table">
      <thead><tr><th>标题 / 正文预览</th><th>标签</th><th>置顶</th><th>创建时间</th><th class="right">操作</th></tr></thead>
      <tbody>
        <tr v-for="note in items" :key="note.id">
          <td>
            <b style="cursor: pointer" @click="openEdit(note)">{{ note.title || '未命名' }}</b>
            <div class="tax">{{ preview(note) }}</div>
          </td>
          <td>{{ note.tags || '—' }}</td>
          <td>{{ note.pinned ? '置顶' : '—' }}</td>
          <td>{{ formatDateTime(note.createTime) }}</td>
          <td class="right"><div class="row-actions">
            <button class="btn" style="height: 26px; font-size: 12px" @click="openEdit(note)"><AppIcon name="edit" :size="13" /></button>
            <button class="btn" style="height: 26px; font-size: 12px; color: var(--danger-color)" @click="remove(note)"><AppIcon name="trash" :size="13" /></button>
          </div></td>
        </tr>
      </tbody>
    </table>

    <div v-if="pageCount > 1" class="pager">
      <button class="btn" :disabled="page <= 1" @click="goPage(page - 1)"><AppIcon name="chevron-left" :size="13" /></button>
      <span>{{ page }} / {{ pageCount }}（共 {{ total }} 条）</span>
      <button class="btn" :disabled="page >= pageCount" @click="goPage(page + 1)"><AppIcon name="chevron-right" :size="13" /></button>
    </div>

    <Modal v-if="editing && edit" :title="isNew ? '新建笔记' : '编辑笔记'" icon="notepad" wide @close="editing = false">
      <div class="form-grid">
        <div class="field full"><label>标题 <span class="req">*</span></label><input v-model="edit.title" class="input" maxlength="300" /></div>
        <div class="field full"><label>正文（Markdown）</label><textarea v-model="edit.content" class="input" rows="14" placeholder="支持 Markdown" /></div>
        <div class="field"><label>标签</label><input v-model="edit.tags" class="input" maxlength="300" placeholder="逗号分隔" /></div>
        <div class="field" style="align-self: end"><label style="display: flex; align-items: center; gap: 8px; font-weight: 500"><input v-model="edit.pinned" type="checkbox" /> 置顶</label></div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
    </Modal>
  </template>
</template>
