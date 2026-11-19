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
  <div v-if="loading" v-loading="true" style="min-height: 240px" />
  <el-alert v-else-if="error" type="error" :title="error" :closable="false" show-icon />

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">文章</div>
        <div class="page-sub">文章写作与发布：状态从草稿推进到已发布，正文走 Markdown。</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建文章</el-button>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="search">
        <el-input v-model="kw" placeholder="搜索标题 / 摘要 / 内容 / 标签" @keyup.enter="applySearch">
          <template #prefix><AppIcon name="search" :size="15" /></template>
        </el-input>
      </div>
      <el-button @click="applySearch"><AppIcon name="search" :size="13" /> 查询</el-button>
      <el-select :empty-values="[]" :model-value="projectId" style="width: 160px" @update:model-value="changeProject">
        <el-option value="" label="全部项目" />
        <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name + (p.status === 'done' ? '（已完结）' : '')" />
      </el-select>
    </div>

    <el-empty v-if="!items.length" :description="keyword || projectId ? '没有匹配的文章。' : '还没有文章，点右上角「新建文章」开一篇。'" />

    <el-table v-else :data="items">
      <el-table-column label="标题 / 摘要">
        <template #default="{ row }">
          <b style="cursor: pointer" @click="openEdit(row as Article)">{{ row.title || '未命名' }}</b>
          <div class="tax">{{ preview(row as Article) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="状态">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'done' ? 'success' : 'info'">{{ label(ARTICLE_STATUS, row.status, '草稿') }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="项目">
        <template #default="{ row }">{{ projName(row.projectId) }}</template>
      </el-table-column>
      <el-table-column label="发布时间">
        <template #default="{ row }">{{ row.publishTime ? formatDateTime(row.publishTime) : '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" align="right">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button v-if="row.status !== 'done'" size="small" type="success" plain @click="setStatus(row as Article, 'done')"><AppIcon name="check" :size="13" /> 发布</el-button>
            <el-button size="small" @click="openEdit(row as Article)"><AppIcon name="edit" :size="13" /></el-button>
            <el-button size="small" type="danger" plain @click="remove(row as Article)"><AppIcon name="trash" :size="13" /></el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-if="pageCount > 1" layout="prev, pager, next" :total="total" :page-size="PAGE_SIZE" :current-page="page" @current-change="goPage" />

    <Modal v-if="editing && edit" :title="isNew ? '新建文章' : '编辑文章'" icon="file-text" wide @close="editing = false">
      <div class="form-grid">
        <div class="field full"><label>标题 <span class="req">*</span></label><el-input v-model="edit.title" maxlength="300" /></div>
        <div class="field full"><label>摘要</label><el-input v-model="edit.summary" maxlength="1000" /></div>
        <div class="field full"><label>正文（Markdown）</label><el-input v-model="edit.content" type="textarea" :rows="16" placeholder="支持 Markdown" /></div>
        <div class="field"><label>标签</label><el-input v-model="edit.tags" maxlength="300" placeholder="逗号分隔" /></div>
        <div class="field"><label>项目</label>
          <el-select :empty-values="[]" v-model="edit.projectId" style="width: 100%">
            <el-option :value="(null as any)" label="不挂项目" />
            <el-option v-for="p in projects" :key="p.id" :value="p.id" :label="p.name" />
          </el-select>
        </div>
        <div class="field"><label>状态</label>
          <el-select v-model="edit.status" style="width: 100%">
            <el-option v-for="o in STATUS_OPTIONS" :key="o.value" :value="o.value" :label="o.text" />
          </el-select>
        </div>
      </div>
      <template #footer>
        <el-button @click="editing = false">取消</el-button>
        <el-button type="primary" @click="save"><AppIcon name="check" :size="14" /> 保存</el-button>
      </template>
    </Modal>
  </template>
</template>
