<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { ReleasePlan, Repo } from '@/types'
import { formatDate } from '@/utils'

const loading = ref(true)
const error = ref('')
const repos = ref<Repo[]>([])
const plans = ref<ReleasePlan[]>([])
const hasToken = ref(false)
const kw = ref('')
const busy = ref(false)

const editing = ref(false)
const isNew = ref(false)
const edit = ref<Repo | null>(null)

const planVisible = ref(false)
const planRepo = ref<Repo | null>(null)
const planTag = ref('')
const planDate = ref<string | null>(null)
const planNotes = ref('')

const shown = computed(() =>
  !kw.value.trim()
    ? repos.value
    : repos.value.filter((r) => `${r.owner} ${r.name} ${r.description ?? ''} ${r.topics ?? ''} ${r.note ?? ''}`.toLowerCase().includes(kw.value.trim().toLowerCase())),
)

const stats = computed(() => [
  { icon: 'package', color: '#4f7cff', value: repos.value.length, label: '镜像仓库' },
  { icon: 'bookmark', color: '#f5a623', value: repos.value.reduce((s, r) => s + (r.stars || 0), 0), label: 'Star 合计' },
  { icon: 'alert-circle', color: '#ff5c5c', value: repos.value.reduce((s, r) => s + (r.openIssues || 0), 0), label: '未关 Issue' },
  { icon: 'calendar-clock', color: '#7c5cff', value: plans.value.filter((p) => !p.released).length, label: '待发布版本' },
])

function plansOf(repoId: string): ReleasePlan[] { return plans.value.filter((p) => p.repoId === repoId) }

async function load() {
  loading.value = true
  error.value = ''
  try {
    const board = await api.get<{ repos: Repo[]; snapshots: unknown[]; plans: ReleasePlan[]; hasToken: boolean }>('/api/repos/board')
    repos.value = board.repos
    plans.value = board.plans
    hasToken.value = board.hasToken
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载开源看板失败'
  } finally {
    loading.value = false
  }
}

function openAdd() {
  edit.value = { id: '', owner: '', name: '', description: null, url: null, language: null, topics: null, homepage: null, stars: 0, forks: 0, openIssues: 0, syncTime: null, pushedAt: null, lastRelease: null, lastReleaseAt: null, projectId: null, note: null }
  isNew.value = true
  editing.value = true
}
function openEdit(r: Repo) { edit.value = { ...r }; isNew.value = false; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.owner.trim() || !edit.value.name.trim()) return
  edit.value.owner = edit.value.owner.trim().trim()
  edit.value.name = edit.value.name.trim().trim()
  await api.post('/api/repos', edit.value)
  editing.value = false
  await load()
}

async function syncOne(r: Repo) {
  busy.value = true
  try { await api.post(`/api/repos/${r.id}/sync`); await load() }
  catch (e) { error.value = e instanceof Error ? e.message : '同步失败' }
  finally { busy.value = false }
}

async function syncAll() {
  busy.value = true
  try { await api.post('/api/repos/sync-all'); await load() }
  catch (e) { error.value = e instanceof Error ? e.message : '同步失败' }
  finally { busy.value = false }
}

async function remove(r: Repo) {
  await api.del(`/api/repos/${r.id}`)
  await load()
}

function openPlans(r: Repo) { planRepo.value = r; planTag.value = ''; planDate.value = null; planNotes.value = ''; planVisible.value = true }

async function addPlan() {
  if (!planRepo.value || !planTag.value.trim()) return
  await api.post('/api/repos/plans', { repoId: planRepo.value.id, tag: planTag.value.trim(), planDate: planDate.value, notes: planNotes.value })
  planTag.value = ''
  planDate.value = null
  planNotes.value = ''
  await load()
}

async function togglePlan(p: ReleasePlan) {
  await api.post(`/api/repos/plans/${p.id}/toggle`)
  await load()
}

async function deletePlan(p: ReleasePlan) {
  await api.del(`/api/repos/plans/${p.id}`)
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
        <div class="page-greet">开源项目</div>
        <div class="page-sub">GitHub 仓库镜像：拉 Star / Fork / Issue 与最近发版，Token 加密存本机。</div>
      </div>
      <div class="page-actions">
        <button class="btn" :disabled="busy || !repos.length" @click="syncAll"><AppIcon name="refresh" :size="14" /> 同步全部</button>
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 添加仓库</button>
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
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索 owner / 仓库名 / 描述 / 备注" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <span v-if="!hasToken" class="muted" style="font-size: 12px">未配 GitHub Token，走匿名额度（60 次/小时）</span>
    </div>

    <div v-if="!shown.length" class="page-empty">
      <p>还没有镜像仓库。填 owner/name 添加一个，点「同步」拉最新数据。</p>
    </div>

    <div v-else class="card-grid">
      <div v-for="r in shown" :key="r.id" class="ent-card">
        <div class="ent-top">
          <b class="ent-name">{{ r.owner }}/{{ r.name }}</b>
          <span v-if="r.language" class="pill st-talking">{{ r.language }}</span>
        </div>
        <div v-if="r.description" class="ent-note">{{ r.description }}</div>
        <div class="ent-meta">
          <span><AppIcon name="bookmark" :size="12" /> {{ (r.stars || 0).toLocaleString('zh-CN') }} ★</span>
          <span><AppIcon name="git-branch" :size="12" /> {{ r.forks || 0 }}</span>
          <span v-if="r.syncTime"><AppIcon name="calendar" :size="12" /> {{ formatDate(r.syncTime) }} 同步</span>
        </div>
        <div v-if="r.lastRelease" class="ent-flags">
          <span class="flag link">发版 {{ r.lastRelease }}</span>
        </div>
        <div v-if="plansOf(r.id).length" class="ent-flags">
          <span v-for="p in plansOf(r.id).filter((x) => !x.released)" :key="p.id" class="flag warn">{{ p.tag }} 待发</span>
        </div>
        <div class="ent-acts">
          <button class="btn" style="height: 28px; font-size: 12px" @click="openPlans(r)"><AppIcon name="calendar-clock" :size="13" /> 计划</button>
          <button class="btn" style="height: 28px; font-size: 12px" :disabled="busy" @click="syncOne(r)"><AppIcon name="refresh" :size="13" /> 同步</button>
          <button class="btn" style="height: 28px; font-size: 12px" @click="openEdit(r)"><AppIcon name="edit" :size="13" /></button>
          <button class="btn" style="height: 28px; font-size: 12px; color: var(--danger-color)" @click="remove(r)"><AppIcon name="trash" :size="13" /></button>
        </div>
      </div>
    </div>

    <Modal v-if="editing && edit" :title="isNew ? '添加仓库' : '编辑仓库'" icon="package" @close="editing = false">
      <div class="form-grid">
        <div class="field"><label>Owner <span class="req">*</span></label><input v-model="edit.owner" class="input" maxlength="100" placeholder="knownliu" /></div>
        <div class="field"><label>仓库名 <span class="req">*</span></label><input v-model="edit.name" class="input" maxlength="100" placeholder="eims" /></div>
        <div class="field full"><label>备注</label><input v-model="edit.note" class="input" maxlength="1000" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
    </Modal>

    <Modal v-if="planVisible && planRepo" :title="planRepo.owner + '/' + planRepo.name + ' · 发布计划'" icon="calendar-clock" @close="planVisible = false">
      <div v-for="p in plansOf(planRepo.id)" :key="p.id" class="ms-item">
        <span class="pill" :class="p.released ? 'st-done' : 'st-hold'">{{ p.released ? '已发布' : '待发布' }}</span>
        <div class="ms-t">
          <div style="font-weight: 600">{{ p.tag }}</div>
          <div class="muted" style="font-size: 12px">{{ p.notes || '' }}</div>
        </div>
        <div class="ms-dates">
          <span v-if="p.planDate" class="muted">{{ formatDate(p.planDate) }}</span>
          <button class="icon-btn" type="button" :title="p.released ? '退回待发' : '标记发布'" @click="togglePlan(p)"><AppIcon :name="p.released ? 'refresh' : 'check'" :size="13" /></button>
          <button class="icon-btn" type="button" @click="deletePlan(p)"><AppIcon name="trash" :size="13" /></button>
        </div>
      </div>
      <div class="form-grid" style="margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border-light)">
        <div class="field"><label>版本号 <span class="req">*</span></label><input v-model="planTag" class="input" maxlength="50" placeholder="v1.2.0" /></div>
        <div class="field"><label>计划日期</label><input v-model="planDate" class="input" type="date" /></div>
        <div class="field full"><label>版本说明</label><input v-model="planNotes" class="input" maxlength="500" /></div>
        <div class="field full" style="text-align: right"><button class="btn primary" @click="addPlan"><AppIcon name="plus" :size="14" /> 加计划</button></div>
      </div>
    </Modal>
  </template>
</template>
