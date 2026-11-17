<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Snippet } from '@/types'

const loading = ref(true)
const error = ref('')
const items = ref<Snippet[]>([])
const kw = ref('')
const lang = ref('')

const editing = ref(false)
const edit = ref<Snippet | null>(null)

const languages = computed(() => [...new Set(items.value.map((s) => s.language).filter((l): l is string => !!l && l.trim() !== ''))].sort())

const shown = computed(() =>
  items.value.filter((s) => {
    if (lang.value && s.language !== lang.value) return false
    if (!kw.value.trim()) return true
    const needle = kw.value.trim().toLowerCase()
    return [s.title, s.description, s.code, s.tags].some((v) => v && v.toLowerCase().includes(needle))
  }),
)

function tagList(s: Snippet): string[] {
  return s.tags ? [...new Set(s.tags.split(',').map((t) => t.trim()).filter(Boolean))] : []
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = await api.get<Snippet[]>('/api/snippets')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载代码片段失败'
  } finally {
    loading.value = false
  }
}

function openAdd() {
  edit.value = { id: '', title: '', language: null, code: null, description: null, tags: null, createTime: null }
  editing.value = true
}
function openEdit(s: Snippet) { edit.value = { ...s }; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.title.trim()) return
  edit.value.title = edit.value.title.trim()
  await api.post<Snippet>('/api/snippets', edit.value)
  editing.value = false
  await load()
}

async function copyCode(s: Snippet) {
  try {
    await navigator.clipboard.writeText(s.code ?? '')
  } catch {
    /* 剪贴板不可用时静默失败 */
  }
}

async function remove(s: Snippet) {
  await api.del(`/api/snippets/${s.id}`)
  items.value = items.value.filter((x) => x.id !== s.id)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading"><div class="spinner" /></div>
  <div v-else-if="error" class="card"><div class="empty">{{ error }}</div></div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">代码片段</div>
        <div class="page-sub">随手记下的小段代码：按语言筛选，复制即用。</div>
      </div>
      <div class="page-actions">
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新增片段</button>
      </div>
    </div>

    <div class="page-toolbar">
      <div class="search" style="position: relative">
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索标题 / 说明 / 代码 / 标签" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <select v-model="lang" class="input" style="width: 130px">
        <option value="">全部语言</option>
        <option v-for="l in languages" :key="l" :value="l">{{ l }}</option>
      </select>
    </div>

    <div v-if="!shown.length" class="page-empty">
      <p>{{ kw.trim() || lang ? '没有匹配的片段。' : '还没有代码片段，点右上角记一条。' }}</p>
    </div>

    <div v-else class="card-grid">
      <div v-for="s in shown" :key="s.id" class="ent-card">
        <div class="ent-top">
          <b class="ent-name">{{ s.title }}</b>
          <span v-if="s.language" class="pill st-active">{{ s.language }}</span>
        </div>
        <div v-if="s.description" class="ent-note">{{ s.description }}</div>
        <pre class="code-preview">{{ (s.code ?? '').slice(0, 300) }}</pre>
        <div v-if="tagList(s).length" class="ent-tags">
          <span v-for="t in tagList(s)" :key="t" class="tag">{{ t }}</span>
        </div>
        <div class="ent-acts">
          <button class="btn" style="height: 28px; font-size: 12px" @click="copyCode(s)"><AppIcon name="clipboard" :size="13" /> 复制</button>
          <button class="btn" style="height: 28px; font-size: 12px" @click="openEdit(s)"><AppIcon name="edit" :size="13" /></button>
          <button class="btn" style="height: 28px; font-size: 12px; color: var(--danger-color)" @click="remove(s)"><AppIcon name="trash" :size="13" /></button>
        </div>
      </div>
    </div>

    <Modal v-if="editing && edit" :title="edit.id ? '编辑片段' : '新增片段'" icon="code" wide @close="editing = false">
      <div class="form-grid">
        <div class="field"><label>标题 <span class="req">*</span></label><input v-model="edit.title" class="input" maxlength="300" /></div>
        <div class="field"><label>语言</label><input v-model="edit.language" class="input" maxlength="50" placeholder="python / js / sql…" /></div>
        <div class="field full"><label>代码</label><textarea v-model="edit.code" class="input" rows="14" style="font-family: Menlo, Consolas, monospace; font-size: 12.5px" /></div>
        <div class="field full"><label>说明</label><input v-model="edit.description" class="input" maxlength="1000" /></div>
        <div class="field full"><label>标签</label><input v-model="edit.tags" class="input" maxlength="300" placeholder="逗号分隔" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
    </Modal>
  </template>
</template>
