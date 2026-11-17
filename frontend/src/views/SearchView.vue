<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { api } from '@/api'
import type { SearchHit, SearchIndex, SearchResult } from '@/types'

const kw = ref('')
const kind = ref('')
const hits = ref<SearchHit[]>([])
const kinds = ref<Record<string, number>>({})
const engine = ref('')
const index = ref<SearchIndex | null>(null)
const busy = ref(false)
const searched = ref(false)

const KIND_NAMES: Record<string, string> = { note: '笔记', article: '文章', bookmark: '收藏', snippet: '片段', rss: '订阅' }
const KIND_ROUTES: Record<string, string> = { note: '/notes', article: '/articles', bookmark: '/bookmarks', snippet: '/snippets', rss: '/rss' }

async function loadIndex() {
  try { index.value = await api.get<SearchIndex>('/api/search/index') } catch { /* 索引读不到不阻塞 */ }
}

async function search() {
  searched.value = true
  if (!kw.value.trim()) { hits.value = []; kinds.value = {}; engine.value = ''; return }
  busy.value = true
  try {
    const r = await api.get<SearchResult>(`/api/search?kw=${encodeURIComponent(kw.value)}&kind=${kind.value}`)
    hits.value = r.hits
    kinds.value = r.kinds
    engine.value = r.engine
  } catch (e) {
    hits.value = []
  } finally {
    busy.value = false
  }
}

async function rebuild() {
  busy.value = true
  try {
    await api.post('/api/search/rebuild')
    await loadIndex()
    if (kw.value.trim()) await search()
  } finally {
    busy.value = false
  }
}

function pick(k: string) { kind.value = kind.value === k ? '' : k; if (kw.value.trim()) search() }

function go(hit: SearchHit) {
  const url = KIND_ROUTES[hit.kind]
  if (url) window.location.href = url
}

onMounted(loadIndex)
</script>

<template>
  <div class="page-head">
    <div>
      <div class="page-greet">全文检索</div>
      <div class="page-sub">SQLite FTS5 索引笔记、文章、收藏、片段与订阅，改存即进索引。</div>
    </div>
  </div>

  <div class="page-toolbar" style="margin-bottom: 14px">
    <div class="search" style="position: relative; flex: 1 1 360px">
      <input v-model="kw" class="input" style="padding-left: 36px; height: 40px" placeholder="搜索内容…（回车）" @keyup.enter="search" />
      <AppIcon name="search" :size="16" style="position: absolute; left: 12px; top: 12px; color: var(--text-muted)" />
    </div>
    <button class="btn primary" :disabled="busy" @click="search">搜索</button>
    <button class="btn" :disabled="busy" @click="rebuild"><AppIcon name="refresh" :size="14" /> 重建索引</button>
  </div>

  <div v-if="index" class="muted" style="font-size: 12px; margin-bottom: 14px">
    索引 {{ index.count }} 条 · 源 {{ index.source }} 条
    <template v-if="index.gap > 0"> · <span style="color: var(--warning-color)">相差 {{ index.gap }} 条，点「重建索引」补齐</span></template>
    · 引擎 {{ index.engine }}
  </div>

  <div v-if="!searched" class="page-empty">
    <p>输入关键词开始搜索。新写的内容存下就自动进索引，只有索引和源对不上时才需要重建。</p>
  </div>

  <template v-else>
    <div class="page-toolbar" style="margin-bottom: 12px">
      <button class="btn" :class="{ primary: kind === '' }" @click="pick('')">全部</button>
      <button v-for="(name, k) in KIND_NAMES" :key="k" class="btn" :class="{ primary: kind === k }" @click="pick(k)">
        {{ name }}{{ kinds[k] ? ` (${kinds[k]})` : '' }}
      </button>
      <span v-if="engine" class="muted" style="font-size: 12px; margin-left: auto">{{ engine }}</span>
    </div>

    <div v-if="!hits.length" class="page-empty">
      <p>没有搜到「{{ kw }}」。可以换个说法、少打几个字。</p>
    </div>

    <div v-else class="card" style="padding: 0; overflow: hidden">
      <div v-for="hit in hits" :key="hit.id + hit.kind" class="rel" style="padding: 13px 16px; cursor: pointer; border-bottom: 1px solid var(--border-light)" @click="go(hit)">
        <span class="pill st-talking">{{ KIND_NAMES[hit.kind] || hit.kind }}</span>
        <div style="flex: 1; min-width: 0">
          <div style="font-weight: 600; font-size: 13.5px">
            <template v-for="(part, i) in hit.titleParts" :key="i">
              <mark v-if="part.mark" style="background: var(--warning-soft); color: var(--warning-color)">{{ part.text }}</mark>
              <template v-else>{{ part.text }}</template>
            </template>
          </div>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 3px">
            <template v-for="(part, i) in hit.parts" :key="i">
              <mark v-if="part.mark" style="background: var(--warning-soft); color: var(--warning-color)">{{ part.text }}</mark>
              <template v-else>{{ part.text }}</template>
            </template>
          </div>
        </div>
        <span class="muted" style="font-size: 11.5px; white-space: nowrap">{{ hit.time }}</span>
      </div>
    </div>
  </template>
</template>
