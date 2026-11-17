<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Client, DeleteImpact, Invoice, Milestone, Payment, Project } from '@/types'
import { dateOf, formatMd, label, money, PROJECT_STATUS, today } from '@/utils'

const loading = ref(true)
const error = ref('')
const projects = ref<Project[]>([])
const milestones = ref<Milestone[]>([])
const clients = ref<Client[]>([])
const invoices = ref<Invoice[]>([])
const payments = ref<Payment[]>([])

const kw = ref('')
const status = ref('all')
const viewMode = ref<'card' | 'gantt'>('card')

const editing = ref(false)
const isNew = ref(false)
const edit = ref<Project | null>(null)

const msVisible = ref(false)
const msOf = ref<Project | null>(null)
const msTitle = ref('')
const msStart = ref<string | null>(null)
const msDue = ref<string | null>(null)
const renaming = ref<string | null>(null)
const renameTitle = ref('')

const killing = ref(false)
const kill = ref<Project | null>(null)
const killBusy = ref(false)
const killDetach = ref(true)
const impact = ref<DeleteImpact | null>(null)

const STATUS_FILTER = [{ value: 'all', text: '全部状态' }, ...Object.entries(PROJECT_STATUS).map(([value, text]) => ({ value, text }))]

const clientOptions = computed(() => {
  const options = clients.value.filter((c) => !c.archived).map((c) => ({ value: c.id, text: c.name }))
  if (edit.value?.clientId && !clients.value.some((c) => c.id === edit.value!.clientId && !c.archived)) {
    const c = clients.value.find((x) => x.id === edit.value!.clientId)
    if (c) options.push({ value: c.id, text: c.name + '（已归档）' })
  }
  return options
})

function match(p: Project, k: string): boolean {
  if (!k.trim()) return true
  const needle = k.trim().toLowerCase()
  return [p.name, p.terms, p.description, clientName(p.clientId)].some((v) => v && v.toLowerCase().includes(needle))
}

const shown = computed(() =>
  projects.value.filter((p) => (status.value === 'all' || p.status === status.value) && match(p, kw.value)),
)

const stats = computed(() => [
  { icon: 'briefcase', color: '#4f7cff', value: projects.value.filter((p) => p.status !== 'done').length, label: '在跑项目' },
  { icon: 'wallet', color: '#07c160', value: money(projects.value.reduce((s, p) => s + (Number(p.amount) || 0), 0)), label: '合同总额' },
  { icon: 'receipt', color: '#7c5cff', value: money(invoices.value.filter((iv) => iv.status !== 'void').reduce((s, iv) => s + (Number(iv.amount) || 0), 0)), label: '累计开票' },
  { icon: 'hourglass', color: '#f5a623', value: money(invoices.value.reduce((s, iv) => s + (Number(iv.due) || 0), 0)), label: '待收金额' },
])

function clientName(id: string | null): string {
  if (!id) return '未挂客户'
  return clients.value.find((c) => c.id === id)?.name ?? '客户已删除'
}

function msOfProject(projectId: string): Milestone[] {
  return milestones.value.filter((m) => m.projectId === projectId)
}

function msProgress(p: Project) {
  const list = msOfProject(p.id)
  if (!list.length) return { done: 0, total: 0, pct: 0 }
  const done = list.filter((m) => m.done).length
  return { done, total: list.length, pct: Math.round((done * 100) / list.length) }
}

function msOverdue(p: Project): boolean {
  const now = today()
  return msOfProject(p.id).some((m) => !m.done && dateOf(m.dueDate) !== null && dateOf(m.dueDate)! < now)
}

function span(p: Project): string {
  if (p.startDate && p.endDate) return `${formatMd(p.startDate)} ~ ${formatMd(p.endDate)}`
  if (p.endDate) return `预计 ${formatMd(p.endDate)} 交付`
  if (p.startDate) return `${formatMd(p.startDate)} 开工`
  return '未排期'
}

function invoicedOf(projectId: string): number {
  return invoices.value.filter((iv) => iv.projectId === projectId && iv.status !== 'void').reduce((s, iv) => s + (Number(iv.amount) || 0), 0)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [p, m, c, iv, pay] = await Promise.all([
      api.get<Project[]>('/api/projects'),
      api.get<Milestone[]>('/api/projects/milestones'),
      api.get<Client[]>('/api/clients'),
      api.get<Invoice[]>('/api/finance/invoices'),
      api.get<Payment[]>('/api/finance/payments'),
    ])
    projects.value = p
    milestones.value = m
    clients.value = c
    invoices.value = iv
    payments.value = pay
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载项目台账失败'
  } finally {
    loading.value = false
  }
}

function openAdd() {
  edit.value = { id: '', name: '', clientId: null, status: 'talking', amount: 0, signedDate: null, startDate: null, endDate: null, expireDate: null, contractFile: null, terms: null, description: null, createTime: null, modifyTime: null }
  isNew.value = true
  editing.value = true
}
function openEdit(p: Project) { edit.value = { ...p }; isNew.value = false; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.name.trim()) return
  edit.value.name = edit.value.name.trim()
  await api.post<Project>('/api/projects', edit.value)
  editing.value = false
  await load()
}

function openMs(p: Project) {
  msOf.value = p
  msTitle.value = ''
  msStart.value = p.startDate
  msDue.value = null
  renaming.value = null
  msVisible.value = true
}

async function addMs() {
  if (!msOf.value || !msTitle.value.trim()) return
  await api.post<Milestone>('/api/projects/milestones', {
    projectId: msOf.value.id,
    title: msTitle.value.trim(),
    startDate: msStart.value,
    dueDate: msDue.value,
    sort: msOfProject(msOf.value.id).length,
  })
  milestones.value = await api.get<Milestone[]>('/api/projects/milestones')
  msTitle.value = ''
  msDue.value = null
}

async function toggleMs(m: Milestone) {
  await api.post<Milestone>('/api/projects/milestones', { ...m, done: !m.done, doneTime: !m.done ? new Date().toISOString() : null })
  milestones.value = await api.get<Milestone[]>('/api/projects/milestones')
}

function startRename(m: Milestone) { renaming.value = m.id; renameTitle.value = m.title }

async function commitRename(m: Milestone) {
  renaming.value = null
  if (!renameTitle.value.trim() || renameTitle.value === m.title) return
  await api.post<Milestone>('/api/projects/milestones', { ...m, title: renameTitle.value.trim() })
  milestones.value = await api.get<Milestone[]>('/api/projects/milestones')
}

async function setMsDate(m: Milestone, value: string | null, isStart: boolean) {
  await api.post<Milestone>('/api/projects/milestones', { ...m, startDate: isStart ? value : m.startDate, dueDate: isStart ? m.dueDate : value })
  milestones.value = await api.get<Milestone[]>('/api/projects/milestones')
}

async function deleteMs(m: Milestone) {
  await api.del(`/api/projects/milestones/${m.id}`)
  milestones.value = milestones.value.filter((x) => x.id !== m.id)
}

async function openKill(p: Project) {
  kill.value = p
  impact.value = await api.get<DeleteImpact>(`/api/projects/delete-impact/${p.id}`)
  killDetach.value = true
  killing.value = true
}

async function doDelete() {
  if (!kill.value || killBusy.value) return
  killBusy.value = true
  try {
    await api.del(`/api/projects/${kill.value.id}?detach=${killDetach.value}`)
    killing.value = false
    kill.value = null
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  } finally {
    killBusy.value = false
  }
}

async function doFinish() {
  if (!kill.value || killBusy.value) return
  killBusy.value = true
  try {
    await api.post<Project>('/api/projects', { ...kill.value, status: 'done' })
    killing.value = false
    kill.value = null
    await load()
  } finally {
    killBusy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading"><div class="spinner" /></div>
  <div v-else-if="error" class="card"><div class="empty">{{ error }}</div></div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">项目</div>
        <div class="page-sub">项目制管理：状态推进、合同额与回款、里程碑勾选进度。</div>
      </div>
      <div class="page-actions">
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建项目</button>
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
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索项目 / 客户 / 条款" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <select v-model="status" class="input" style="width: 130px">
        <option v-for="o in STATUS_FILTER" :key="o.value" :value="o.value">{{ o.text }}</option>
      </select>
      <div style="display: flex; gap: 2px; background: var(--bg-hover); border-radius: var(--radius-md); padding: 2px">
        <button class="btn" :class="{ primary: viewMode === 'card' }" @click="viewMode = 'card'"><AppIcon name="grid" :size="13" /> 卡片</button>
        <button class="btn" :class="{ primary: viewMode === 'gantt' }" @click="viewMode = 'gantt'"><AppIcon name="calendar-range" :size="13" /> 甘特</button>
      </div>
    </div>

    <div v-if="viewMode === 'gantt'" class="page-empty">
      <p>甘特视图要有带日期的里程碑才画得出来。先在项目「里程碑」里把开始与截止日期填上。</p>
    </div>

    <div v-else-if="!shown.length" class="page-empty">
      <p>{{ kw.trim() || status !== 'all' ? '没有符合条件的项目。' : '还没有项目。先建客户，再在项目里把客户选上。' }}</p>
      <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建项目</button>
    </div>

    <div v-else class="card-grid">
      <div v-for="p in shown" :key="p.id" class="ent-card">
        <div class="ent-top">
          <b class="ent-name" @click="openEdit(p)">{{ p.name }}</b>
          <span class="pill" :class="'st-' + (p.status || 'talking')">{{ label(PROJECT_STATUS, p.status, '洽谈中') }}</span>
        </div>
        <div class="ent-meta">
          <span><AppIcon name="users" :size="12" /> {{ clientName(p.clientId) }}</span>
          <span><AppIcon name="wallet" :size="12" /> {{ money(Number(p.amount)) }}</span>
          <span><AppIcon name="calendar" :size="12" /> {{ span(p) }}</span>
        </div>
        <div class="progress" :title="`${msProgress(p).done}/${msProgress(p).total} 已完成`">
          <div class="progress-in" :class="{ full: p.status === 'done' }" :style="{ width: msProgress(p).pct + '%' }" />
          <span class="progress-t">{{ msProgress(p).total === 0 ? '还没排里程碑' : `里程碑 ${msProgress(p).done}/${msProgress(p).total}` }}</span>
        </div>
        <div v-if="p.terms" class="ent-note">{{ p.terms }}</div>
        <div class="ent-flags">
          <span v-if="msOverdue(p)" class="flag warn">里程碑逾期</span>
          <span v-if="p.expireDate && dateOf(p.expireDate)! < today() && p.status !== 'done'" class="flag danger">维护到期 {{ p.expireDate.slice(0, 10) }}</span>
          <span v-else-if="p.expireDate" class="flag">维护至 {{ p.expireDate.slice(0, 10) }}</span>
          <span class="flag soft">开票 {{ money(invoicedOf(p.id)) }}</span>
        </div>
        <div class="ent-acts">
          <button class="btn" style="height: 28px; font-size: 12px" @click="openMs(p)"><AppIcon name="clipboard-check" :size="13" /> 里程碑</button>
          <button class="btn" style="height: 28px; font-size: 12px" @click="openEdit(p)"><AppIcon name="edit" :size="13" /></button>
          <button class="btn" style="height: 28px; font-size: 12px; color: var(--danger-color)" @click="openKill(p)"><AppIcon name="trash" :size="13" /></button>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <Modal v-if="editing && edit" :title="isNew ? '新建项目' : '编辑项目'" icon="package" @close="editing = false">
      <div class="form-grid">
        <div class="field full"><label>项目名称 <span class="req">*</span></label><input v-model="edit.name" class="input" maxlength="200" /></div>
        <div class="field"><label>客户</label>
          <select v-model="edit.clientId" class="input"><option :value="null">选客户</option><option v-for="c in clientOptions" :key="c.value" :value="c.value">{{ c.text }}</option></select>
        </div>
        <div class="field"><label>状态</label>
          <select v-model="edit.status" class="input"><option v-for="o in Object.entries(PROJECT_STATUS)" :key="o[0]" :value="o[0]">{{ o[1] }}</option></select>
        </div>
        <div class="field"><label>合同额（元）</label><input v-model.number="edit.amount" class="input" type="number" /></div>
        <div class="field"><label>签约日期</label><input v-model="edit.signedDate" class="input" type="date" /></div>
        <div class="field"><label>开始日期</label><input v-model="edit.startDate" class="input" type="date" /></div>
        <div class="field"><label>预计交付</label><input v-model="edit.endDate" class="input" type="date" /></div>
        <div class="field"><label>维护到期</label><input v-model="edit.expireDate" class="input" type="date" /></div>
        <div class="field full"><label>关键条款</label><input v-model="edit.terms" class="input" maxlength="1000" /></div>
        <div class="field full"><label>范围与说明</label><textarea v-model="edit.description" class="input" rows="3" maxlength="1000" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
    </Modal>

    <!-- 里程碑弹窗 -->
    <Modal v-if="msVisible && msOf" :title="msOf.name + ' · 里程碑'" icon="clipboard-check" @close="msVisible = false">
      <div v-for="m in msOfProject(msOf.id)" :key="m.id" class="ms-item">
        <input class="ms-check" type="checkbox" :checked="m.done" @change="toggleMs(m)" />
        <div class="ms-t">
          <span v-if="renaming !== m.id" :class="{ done: m.done }" @dblclick="startRename(m)">{{ m.title }}</span>
          <input v-else v-model="renameTitle" class="input" style="height: 26px" @blur="commitRename(m)" @keyup.enter="commitRename(m)" />
        </div>
        <div class="ms-dates">
          <input :value="m.startDate ? m.startDate.slice(0, 10) : ''" class="input" style="height: 26px" type="date" @change="setMsDate(m, ($event.target as HTMLInputElement).value, true)" />
          <input :value="m.dueDate ? m.dueDate.slice(0, 10) : ''" class="input" style="height: 26px" type="date" @change="setMsDate(m, ($event.target as HTMLInputElement).value, false)" />
          <button class="icon-btn" type="button" @click="deleteMs(m)"><AppIcon name="trash" :size="13" /></button>
        </div>
      </div>
      <div v-if="!msOfProject(msOf.id).length" class="muted" style="font-size: 13px; padding: 12px 0">还没有里程碑，在下面加第一个。</div>

      <div class="form-grid" style="margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border-light)">
        <div class="field full"><label>节点名称 <span class="req">*</span></label><input v-model="msTitle" class="input" maxlength="200" placeholder="如 首页开发完成" /></div>
        <div class="field"><label>开始</label><input v-model="msStart" class="input" type="date" /></div>
        <div class="field"><label>截止</label><input v-model="msDue" class="input" type="date" /></div>
        <div class="field full" style="text-align: right"><button class="btn primary" @click="addMs"><AppIcon name="plus" :size="14" /> 加里程碑</button></div>
      </div>
    </Modal>

    <!-- 删除弹窗 -->
    <Modal v-if="killing && kill" :title="'删除 ' + kill.name" icon="trash" @close="killing = false">
      <div class="impact">
        <p v-if="impact && impact.groups.length" class="muted" style="margin: 0 0 10px; font-size: 13px">删除前先看有哪些记录挂在它身上：</p>
        <div v-if="impact && impact.groups.length" class="impact-groups">
          <div v-for="g in impact.groups" :key="g.label" class="impact-row">
            <span>{{ g.label }}</span>
            <span class="pill" :class="g.mode === 'cascade' ? 'st-void' : 'st-talking'">{{ g.mode === 'cascade' ? '跟着删' : '可解绑保留' }}</span>
            <span class="muted">{{ g.count }}</span>
          </div>
        </div>
        <div v-else class="impact-none">这个项目下面没有挂着任务、发票或里程碑，删了不留尾巴。</div>
      </div>
      <div class="field" style="margin-bottom: 12px">
        <label style="display: flex; align-items: center; gap: 8px; font-weight: 500">
          <input v-model="killDetach" type="checkbox" /> 解绑并保留任务 / 发票 / 支出（否则原样保留，显示「项目已删除」）
        </label>
      </div>
      <template #footer>
        <button class="btn" @click="killing = false">取消</button>
        <button class="btn" :disabled="killBusy" @click="doFinish"><AppIcon name="check" :size="14" /> 标为已完结（推荐）</button>
        <button class="btn" style="background: var(--danger-color); border-color: var(--danger-color); color: #fff" :disabled="killBusy" @click="doDelete">
          <AppIcon name="trash" :size="14" /> 删除
        </button>
      </template>
    </Modal>
  </template>
</template>
