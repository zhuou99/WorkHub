<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import { formatDate, label } from '@/utils'
import { marked } from 'marked'
import type { Bookmark } from '@/types'

function renderMarkdown(text: string): string {
  try { return marked.parse(text ?? '') as string } catch { return text ?? '' }
}

const loading = ref(true)
const error = ref('')
const items = ref<Bookmark[]>([])
const kw = ref('')
const status = ref('')
const onlyFav = ref(false)
const tagFilter = ref('')
const page = ref(1)
const PAGE_SIZE = 12

const clipping = ref(false)
const clipVisible = ref(false)
const clipUrl = ref('')
const clipError = ref('')

const editing = ref(false)
const isNew = ref(false)
const edit = ref<Bookmark | null>(null)

const viewing = ref(false)
const view = ref<Bookmark | null>(null)

const BOOKMARK_STATUS: Record<string, string> = { unread: '未读', reading: '在读', read: '已读' }
const STATUS_OPTIONS = Object.entries(BOOKMARK_STATUS).map(([value, text]) => ({ value, text }))

function match(b: Bookmark, k: string): boolean {
  if (!k.trim()) return true
  const needle = k.trim().toLowerCase()
  return [b.title, b.summary, b.tags, b.content].some((v) => v && v.toLowerCase().includes(needle))
}

function tagList(b: Bookmark): string[] {
  return b.tags ? [...new Set(b.tags.split(',').map((t) => t.trim()).filter(Boolean))] : []
}

const allTags = computed(() => [...new Set(items.value.flatMap(tagList))].sort())

const shown = computed(() =>
  items.value.filter((b) => {
    if (status.value && b.status !== status.value) return false
    if (onlyFav.value && !b.favorite) return false
    if (tagFilter.value && !tagList(b).includes(tagFilter.value)) return false
    return match(b, kw.value)
  }),
)

const maxPage = computed(() => Math.max(1, Math.ceil(shown.value.length / PAGE_SIZE)))
const paged = computed(() => shown.value.slice((Math.min(page.value, maxPage.value) - 1) * PAGE_SIZE, Math.min(page.value, maxPage.value) * PAGE_SIZE))

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = await api.get<Bookmark[]>('/api/bookmarks')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载收藏失败'
  } finally {
    loading.value = false
  }
}

function nextStatus(s: string | null): string {
  return s === 'unread' ? 'reading' : s === 'reading' ? 'read' : 'unread'
}

async function cycle(b: Bookmark) {
  await api.post<Bookmark>('/api/bookmarks', { ...b, status: nextStatus(b.status) })
  await load()
}

async function toggleFav(b: Bookmark) {
  await api.post<Bookmark>('/api/bookmarks', { ...b, favorite: !b.favorite })
  await load()
}

function openClip() { clipUrl.value = ''; clipError.value = ''; clipVisible.value = true }

async function doClip() {
  if (!clipUrl.value.trim() || clipping.value) return
  clipping.value = true
  clipError.value = ''
  try {
    await api.post<Bookmark>(`/api/bookmarks/clip?url=${encodeURIComponent(clipUrl.value.trim())}`)
    clipVisible.value = false
    await load()
  } catch (e) {
    clipError.value = `抓取失败：${e instanceof Error ? e.message : '未知错误'}。可点「手动添加」自己填。`
  } finally {
    clipping.value = false
  }
}

function openAdd() {
  edit.value = { id: '', title: '', url: '', site: null, summary: null, content: null, tags: null, status: 'unread', favorite: false, snapshot: null, createTime: null }
  isNew.value = true
  editing.value = true
}
function openEdit(b: Bookmark) { edit.value = { ...b }; isNew.value = false; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.title.trim() || !edit.value.url.trim()) return
  edit.value.title = edit.value.title.trim()
  edit.value.url = edit.value.url.trim()
  await api.post<Bookmark>('/api/bookmarks', edit.value)
  editing.value = false
  await load()
}

function openView(b: Bookmark) { view.value = b; viewing.value = true }

async function remove(b: Bookmark) {
  await api.del(`/api/bookmarks/${b.id}`)
  items.value = items.value.filter((x) => x.id !== b.id)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading"><div class="spinner" /></div>
  <div v-else-if="error" class="card"><div class="empty">{{ error }}</div></div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">我的收藏</div>
        <div class="page-sub">链接收藏与网页快照：剪藏一条链接，自动抓标题、摘要和正文。</div>
      </div>
      <div class="page-actions">
        <button class="btn" @click="openClip"><AppIcon name="bookmark" :size="14" /> 剪藏链接</button>
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 手动添加</button>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="search" style="position: relative">
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索标题 / 摘要 / 标签" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <select v-model="status" class="input" style="width: 100px"><option value="">全部状态</option><option v-for="o in STATUS_OPTIONS" :key="o.value" :value="o.value">{{ o.text }}</option></select>
      <button class="btn" :class="{ primary: onlyFav }" @click="onlyFav = !onlyFav"><AppIcon name="bookmark" :size="13" /> 只看收藏</button>
      <select v-if="allTags.length" v-model="tagFilter" class="input" style="width: 110px"><option value="">全部标签</option><option v-for="t in allTags" :key="t" :value="t">{{ t }}</option></select>
    </div>

    <div v-if="!shown.length" class="page-empty">
      <p>{{ kw.trim() || status || onlyFav || tagFilter ? '没有匹配的收藏。' : '还没有收藏，点「剪藏链接」贴一个链接试试。' }}</p>
    </div>

    <div v-else class="card-grid">
      <div v-for="b in paged" :key="b.id" class="ent-card">
        <div class="ent-top">
          <b class="ent-name" @click="openView(b)">{{ b.title }}</b>
          <span class="dot" :class="{ read: b.status !== 'unread' }" :title="label(BOOKMARK_STATUS, b.status, '未读')" />
          <button class="icon-btn" type="button" @click="toggleFav(b)">
            <AppIcon name="bookmark" :size="14" :style="b.favorite ? 'color: var(--warning-color); fill: currentColor' : ''" />
          </button>
        </div>
        <div v-if="b.summary" class="ent-note">{{ b.summary }}</div>
        <div v-if="tagList(b).length" class="ent-tags">
          <span v-for="t in tagList(b)" :key="t" class="tag">{{ t }}</span>
        </div>
        <div class="ent-meta">
          <span><AppIcon name="calendar" :size="12" /> {{ formatDate(b.createTime) }}</span>
          <span v-if="b.site"><AppIcon name="globe" :size="12" /> {{ b.site }}</span>
        </div>
        <div class="ent-acts">
          <button class="btn" style="height: 28px; font-size: 12px" @click="cycle(b)"><AppIcon name="check" :size="13" /> {{ label(BOOKMARK_STATUS, nextStatus(b.status), '未读') }}</button>
          <button class="btn" style="height: 28px; font-size: 12px" @click="openView(b)"><AppIcon name="file-text" :size="13" /> 正文</button>
          <button class="btn" style="height: 28px; font-size: 12px" @click="openEdit(b)"><AppIcon name="edit" :size="13" /></button>
          <button class="btn" style="height: 28px; font-size: 12px; color: var(--danger-color)" @click="remove(b)"><AppIcon name="trash" :size="13" /></button>
        </div>
      </div>
    </div>

    <div v-if="maxPage > 1" class="pager">
      <button class="btn" :disabled="page <= 1" @click="page--"><AppIcon name="chevron-left" :size="13" /></button>
      <span>{{ Math.min(page, maxPage) }} / {{ maxPage }}</span>
      <button class="btn" :disabled="page >= maxPage" @click="page++"><AppIcon name="chevron-right" :size="13" /></button>
    </div>

    <!-- 剪藏 -->
    <Modal v-if="clipVisible" title="剪藏链接" icon="bookmark" @close="clipVisible = false">
      <div class="field">
        <label>文章链接</label>
        <input v-model="clipUrl" class="input" placeholder="https://…" @keyup.enter="doClip" />
      </div>
      <div v-if="clipError" class="auth-error">{{ clipError }}</div>
      <template #footer>
        <button class="btn" @click="clipVisible = false">取消</button>
        <button class="btn primary" :disabled="clipping || !clipUrl.trim()" @click="doClip"><AppIcon name="bookmark" :size="14" /> {{ clipping ? '抓取中…' : '剪藏' }}</button>
      </template>
    </Modal>

    <!-- 编辑 -->
    <Modal v-if="editing && edit" :title="isNew ? '手动添加' : '编辑收藏'" icon="bookmark" wide @close="editing = false">
      <div class="form-grid">
        <div class="field full"><label>标题 <span class="req">*</span></label><input v-model="edit.title" class="input" maxlength="300" /></div>
        <div class="field full"><label>原文链接 <span class="req">*</span></label><input v-model="edit.url" class="input" maxlength="1000" /></div>
        <div class="field"><label>站点</label><input v-model="edit.site" class="input" maxlength="200" /></div>
        <div class="field"><label>状态</label><select v-model="edit.status" class="input"><option v-for="o in STATUS_OPTIONS" :key="o.value" :value="o.value">{{ o.text }}</option></select></div>
        <div class="field"><label>标签</label><input v-model="edit.tags" class="input" maxlength="300" placeholder="逗号分隔" /></div>
        <div class="field full"><label>摘要</label><input v-model="edit.summary" class="input" maxlength="500" /></div>
        <div class="field full"><label>正文（Markdown）</label><textarea v-model="edit.content" class="input" rows="8" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
    </Modal>

    <!-- 查看正文 -->
    <Modal v-if="viewing && view" :title="view.title" icon="file-text" wide @close="viewing = false">
      <a v-if="view.url" :href="view.url" target="_blank" rel="noopener" class="muted" style="font-size: 12.5px">{{ view.url }}</a>
      <div v-if="view.content" class="markdown-body" style="margin-top: 14px" v-html="renderMarkdown(view.content)" />
      <div v-else class="empty" style="margin-top: 14px">这条收藏没有抓到正文。</div>
    </Modal>
  </template>
</template>
