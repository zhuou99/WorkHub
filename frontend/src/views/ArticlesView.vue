<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Article, Project } from '@/types'
import { formatDateTime, label } from '@/utils'

const loading = ref(true)
const error = ref('')
const items = ref<Article[]>([])
const projects = ref<Project[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 20
const kw = ref('')
const keyword = ref('')
const projectId = ref('')

const editing = ref(false)
const isNew = ref(false)
const edit = ref<Article | null>(null)

const ARTICLE_STATUS: Record<string, string> = { draft: '草稿', layout: '排版中', done: '已发布', failed: '已失败' }
const STATUS_OPTIONS = Object.entries(ARTICLE_STATUS).map(([value, text]) => ({ value, text }))

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

function preview(article: Article): string {
  const summary = (article.summary ?? '').trim()
  if (summary) return summary
  const text = (article.content ?? '').replace(/\r/g, '').replace(/\n/g, ' ').trim()
  if (!text) return '暂无正文'
  return text + ((article.content ?? '').length >= 120 ? '…' : '')
}

function projName(id: string | null): string {
  if (!id) return '—'
  return projects.value.find((p) => p.id === id)?.name ?? '项目已删除'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await api.page<Article>(`/api/articles/page?pageIndex=${page.value}&pageSize=${PAGE_SIZE}&keyword=${encodeURIComponent(keyword.value)}&projectId=${encodeURIComponent(projectId.value)}`)
    total.value = result.total
    items.value = result.rows
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载文章失败'
  } finally {
    loading.value = false
  }
}

function applySearch() { keyword.value = kw.value.trim(); page.value = 1; load() }
function goPage(p: number) { page.value = Math.max(1, p); load() }
function changeProject(v: string) { projectId.value = v; page.value = 1; load() }

async function loadProjects() {
  try { projects.value = await api.get<Project[]>('/api/projects') } catch { /* 项目加载失败不阻塞文章 */ }
}

function openAdd() {
  edit.value = { id: '', title: '', summary: null, cover: null, tags: null, projectId: null, content: null, status: 'draft', publishTime: null, createTime: null, modifyTime: null }
  isNew.value = true
  editing.value = true
}
function openEdit(article: Article) { edit.value = { ...article }; isNew.value = false; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.title.trim()) return
  edit.value.title = edit.value.title.trim()
  await api.post<Article>('/api/articles', edit.value)
  editing.value = false
  await load()
}

async function setStatus(article: Article, status: string) {
  await api.post(`/api/articles/${article.id}/status`, { status })
  await load()
}

async function remove(article: Article) {
  await api.del(`/api/articles/${article.id}`)
  await load()
}

onMounted(() => { load(); loadProjects() })
</script>

<template>
  <div v-if="loading" class="loading"><div class="spinner" /></div>
  <div v-else-if="error" class="card"><div class="empty">{{ error }}</div></div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">文章</div>
        <div class="page-sub">文章写作与发布：状态从草稿推进到已发布，正文走 Markdown。</div>
      </div>
      <div class="page-actions">
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建文章</button>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="search" style="position: relative">
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索标题 / 摘要 / 内容 / 标签" @keyup.enter="applySearch" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <button class="btn" @click="applySearch"><AppIcon name="search" :size="13" /> 查询</button>
      <select :value="projectId" class="input" style="width: 160px" @change="changeProject(($event.target as HTMLSelectElement).value)">
        <option value="">全部项目</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}{{ p.status === 'done' ? '（已完结）' : '' }}</option>
      </select>
    </div>

    <div v-if="!items.length" class="page-empty">
      <p>{{ keyword || projectId ? '没有匹配的文章。' : '还没有文章，点右上角「新建文章」开一篇。' }}</p>
    </div>

    <table v-else class="table">
      <thead><tr><th>标题 / 摘要</th><th>状态</th><th>项目</th><th>发布时间</th><th class="right">操作</th></tr></thead>
      <tbody>
        <tr v-for="article in items" :key="article.id">
          <td>
            <b style="cursor: pointer" @click="openEdit(article)">{{ article.title || '未命名' }}</b>
            <div class="tax">{{ preview(article) }}</div>
          </td>
          <td><span class="pill" :class="'st-' + (article.status || 'draft')">{{ label(ARTICLE_STATUS, article.status, '草稿') }}</span></td>
          <td>{{ projName(article.projectId) }}</td>
          <td>{{ article.publishTime ? formatDateTime(article.publishTime) : '—' }}</td>
          <td class="right"><div class="row-actions">
            <button v-if="article.status !== 'done'" class="btn" style="height: 26px; font-size: 12px; color: var(--success-color)" @click="setStatus(article, 'done')"><AppIcon name="check" :size="13" /> 发布</button>
            <button class="btn" style="height: 26px; font-size: 12px" @click="openEdit(article)"><AppIcon name="edit" :size="13" /></button>
            <button class="btn" style="height: 26px; font-size: 12px; color: var(--danger-color)" @click="remove(article)"><AppIcon name="trash" :size="13" /></button>
          </div></td>
        </tr>
      </tbody>
    </table>

    <div v-if="pageCount > 1" class="pager">
      <button class="btn" :disabled="page <= 1" @click="goPage(page - 1)"><AppIcon name="chevron-left" :size="13" /></button>
      <span>{{ page }} / {{ pageCount }}（共 {{ total }} 条）</span>
      <button class="btn" :disabled="page >= pageCount" @click="goPage(page + 1)"><AppIcon name="chevron-right" :size="13" /></button>
    </div>

    <Modal v-if="editing && edit" :title="isNew ? '新建文章' : '编辑文章'" icon="file-text" wide @close="editing = false">
      <div class="form-grid">
        <div class="field full"><label>标题 <span class="req">*</span></label><input v-model="edit.title" class="input" maxlength="300" /></div>
        <div class="field full"><label>摘要</label><input v-model="edit.summary" class="input" maxlength="1000" /></div>
        <div class="field full"><label>正文（Markdown）</label><textarea v-model="edit.content" class="input" rows="16" placeholder="支持 Markdown" /></div>
        <div class="field"><label>标签</label><input v-model="edit.tags" class="input" maxlength="300" placeholder="逗号分隔" /></div>
        <div class="field"><label>项目</label>
          <select v-model="edit.projectId" class="input"><option :value="null">不挂项目</option><option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option></select>
        </div>
        <div class="field"><label>状态</label>
          <select v-model="edit.status" class="input"><option v-for="o in STATUS_OPTIONS" :key="o.value" :value="o.value">{{ o.text }}</option></select>
        </div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
    </Modal>
  </template>
</template>
