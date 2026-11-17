<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { RssFeed, RssItem } from '@/types'
import { formatDate } from '@/utils'

const loading = ref(true)
const error = ref('')
const feeds = ref<RssFeed[]>([])
const items = ref<RssItem[]>([])
const unread = ref<Record<string, number>>({})
const starredCount = ref(0)
const feedId = ref('')
const kw = ref('')
const filter = ref('')
const busy = ref(false)

const addVisible = ref(false)
const addUrl = ref('')
const addError = ref('')

const PRESETS = [
  { name: '.NET 博客', url: 'https://devblogs.microsoft.com/dotnet/feed' },
  { name: 'Go 博客', url: 'https://go.dev/blog/feed.atom' },
  { name: 'Cloudflare 博客', url: 'https://blog.cloudflare.com/rss/' },
]

const stats = computed(() => [
  { icon: 'rss', color: '#4f7cff', value: feeds.value.length, label: '订阅源' },
  { icon: 'mail', color: '#f5a623', value: unread.value[''] ?? 0, label: '未读条目' },
  { icon: 'bookmark', color: '#7c5cff', value: starredCount.value, label: '已标记' },
  { icon: 'calendar', color: '#22c58e', value: items.value.filter((i) => new Date(i.publishedAt ?? 0) > new Date(Date.now() - 7 * 86400000)).length, label: '近 7 天' },
])

const shown = computed(() =>
  items.value.filter((i) => {
    if (filter.value === 'unread' && i.read) return false
    if (filter.value === 'star' && !i.starred) return false
    if (!kw.value.trim()) return true
    const needle = kw.value.trim().toLowerCase()
    return `${i.title} ${i.summary ?? ''} ${i.author ?? ''}`.toLowerCase().includes(needle)
  }).slice(0, itemLimit.value),
)

const itemLimit = ref(30)
function moreItems() { itemLimit.value += 30 }

function feedName(id: string): string { return feeds.value.find((f) => f.id === id)?.title ?? '未知源' }

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [board, list] = await Promise.all([
      api.get<{ feeds: RssFeed[]; unread: Record<string, number>; starred: number }>('/api/rss/board'),
      api.get<RssItem[]>(`/api/rss/items?feedId=${feedId.value}`),
    ])
    feeds.value = board.feeds
    unread.value = board.unread
    starredCount.value = board.starred
    items.value = list
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载订阅源失败'
  } finally {
    loading.value = false
  }
}

async function reload() { await load() }

function pickFeed(id: string) { feedId.value = feedId.value === id ? '' : id; itemLimit.value = 30; reload() }

function openAdd() { addUrl.value = ''; addError.value = ''; addVisible.value = true }

async function addFeed() {
  if (!addUrl.value.trim() || busy.value) return
  busy.value = true
  addError.value = ''
  try {
    await api.post('/api/rss/feeds', { url: addUrl.value.trim() })
    addVisible.value = false
    await reload()
  } catch (e) {
    addError.value = e instanceof Error ? e.message : '添加失败'
  } finally {
    busy.value = false
  }
}

async function syncOne(f: RssFeed) {
  busy.value = true
  try { await api.post(`/api/rss/feeds/${f.id}/sync`); await reload() }
  catch (e) { error.value = e instanceof Error ? e.message : '同步失败' }
  finally { busy.value = false }
}

async function syncAll() {
  busy.value = true
  try { await api.post('/api/rss/sync-all'); await reload() }
  catch (e) { error.value = e instanceof Error ? e.message : '同步失败' }
  finally { busy.value = false }
}

async function togglePause(f: RssFeed) {
  await api.post(`/api/rss/feeds/${f.id}/pause`)
  await reload()
}

async function deleteFeed(f: RssFeed) {
  await api.del(`/api/rss/feeds/${f.id}`)
  if (feedId.value === f.id) feedId.value = ''
  await reload()
}

async function setRead(i: RssItem) {
  await api.post(`/api/rss/items/${i.id}/read?read=${!i.read}`)
  await reload()
}

async function readAll() {
  await api.post('/api/rss/read-all', { feedId: feedId.value })
  await reload()
}

async function toggleStar(i: RssItem) {
  await api.post(`/api/rss/items/${i.id}/star`)
  await reload()
}

async function deleteItem(i: RssItem) {
  await api.del(`/api/rss/items/${i.id}`)
  items.value = items.value.filter((x) => x.id !== i.id)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading"><div class="spinner" /></div>
  <div v-else-if="error" class="card"><div class="empty">{{ error }}</div></div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">RSS 订阅</div>
        <div class="page-sub">订阅博客与技术动态：条件请求省流量，判重去重，未读一目了然。</div>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="busy || !feeds.length" @click="syncAll"><AppIcon name="refresh" :size="14" /> 同步全部</button>
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 添加订阅</button>
      </div>
    </div>

    <div class="stat-grid" style="grid-template-columns: repeat(4, minmax(0, 1fr))">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
          <div class="stat-icon" :style="{ background: s.color + '22', color: s.color }"><AppIcon :name="s.icon" :size="15" /></div>
        </div>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="search" style="position: relative">
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索条目" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <button class="btn" :class="{ primary: filter === 'unread' }" @click="filter = filter === 'unread' ? '' : 'unread'">未读</button>
      <button class="btn" :class="{ primary: filter === 'star' }" @click="filter = filter === 'star' ? '' : 'star'">已标记</button>
      <button class="btn" @click="readAll">全部已读</button>
    </div>

    <div class="cols" style="grid-template-columns: 240px 1fr; align-items: start">
      <!-- 订阅源 -->
      <div class="col">
        <div class="card" style="padding: 12px">
          <button class="app-sitem" :class="{ on: feedId === '' }" style="width: 100%" @click="pickFeed('')">
            <AppIcon name="rss" :size="15" /><span>全部源</span><span class="kb-count" style="margin-left: auto">{{ unread[''] ?? 0 }}</span>
          </button>
          <div v-for="f in feeds" :key="f.id" style="display: flex; align-items: center; gap: 4px">
            <button class="app-sitem" :class="{ on: feedId === f.id }" style="flex: 1; min-width: 0" :title="f.title" @click="pickFeed(f.id)">
              <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ f.title }}</span>
              <span v-if="unread[f.id]" class="kb-count">{{ unread[f.id] }}</span>
            </button>
            <button class="icon-btn" type="button" title="同步" @click="syncOne(f)"><AppIcon name="refresh" :size="13" /></button>
            <button class="icon-btn" type="button" :title="f.paused ? '恢复' : '暂停'" @click="togglePause(f)"><AppIcon :name="f.paused ? 'circle' : 'check'" :size="13" /></button>
            <button class="icon-btn" type="button" title="退订" @click="deleteFeed(f)"><AppIcon name="trash" :size="13" /></button>
          </div>
        </div>
      </div>

      <!-- 条目 -->
      <div class="col">
        <div v-if="!shown.length" class="page-empty" style="padding: 40px 20px">
          <p>{{ kw.trim() || filter ? '没有符合条件的条目。' : feedId ? '这个源还没有抓到条目，点「同步」试一次。' : '还没有条目，先添加一个订阅源。' }}</p>
        </div>
        <div v-else class="card" style="padding: 0; overflow: hidden">
          <div v-for="i in shown" :key="i.id" class="rel" style="padding: 11px 14px">
            <span class="dot" :class="{ read: i.read }" style="cursor: pointer" :title="i.read ? '标未读' : '标已读'" @click="setRead(i)" />
            <div style="flex: 1; min-width: 0">
              <a :href="i.url || '#'" target="_blank" rel="noopener" style="font-weight: 600; font-size: 13.5px; color: var(--text-primary)" :class="{ muted: i.read }">{{ i.title }}</a>
              <div class="tax" style="margin-top: 2px">{{ i.summary ? i.summary.slice(0, 120) : '' }}</div>
              <div class="muted" style="font-size: 11px; margin-top: 3px">{{ feedName(i.feedId) }}{{ i.author ? ' · ' + i.author : '' }} · {{ formatDate(i.publishedAt) }}</div>
            </div>
            <button class="icon-btn" type="button" :title="i.starred ? '取消标记' : '标记'" @click="toggleStar(i)">
              <AppIcon name="bookmark" :size="14" :style="i.starred ? 'color: var(--warning-color)' : ''" />
            </button>
            <button class="icon-btn" type="button" title="删除" @click="deleteItem(i)"><AppIcon name="trash" :size="13" /></button>
          </div>
          <div v-if="shown.length === itemLimit" style="text-align: center; padding: 12px">
            <button class="btn" @click="moreItems">更多条目</button>
          </div>
        </div>
      </div>
    </div>

    <Modal v-if="addVisible" title="添加订阅" icon="rss" @close="addVisible = false">
      <div class="field" style="margin-bottom: 12px">
        <label>订阅地址（feed 链接或站点首页都行）</label>
        <input v-model="addUrl" class="input" placeholder="https://…" @keyup.enter="addFeed" />
      </div>
      <div v-if="addError" class="auth-error">{{ addError }}</div>
      <div class="sec" style="margin-top: 4px">预设</div>
      <div v-for="preset in PRESETS" :key="preset.url" class="rel" style="cursor: pointer" @click="addUrl = preset.url">
        <span class="rel-t">{{ preset.name }}</span>
        <span class="rel-a muted">{{ preset.url }}</span>
      </div>
      <template #footer>
        <button class="btn" @click="addVisible = false">取消</button>
        <button class="btn primary" :disabled="busy || !addUrl.trim()" @click="addFeed"><AppIcon name="plus" :size="14" /> {{ busy ? '订阅中…' : '订阅' }}</button>
      </template>
    </Modal>
  </template>
</template>
