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

/* 状态胶囊 → el-tag type 映射（maintain 另加 tag-purple 类） */
type TagType = 'info' | 'primary' | 'success' | 'warning' | 'danger'

const PROJ_TAG_TYPE: Record<string, TagType> = { talking: 'info', active: 'success', accept: 'primary', maintain: 'primary', done: 'success' }

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
  <div v-if="loading" v-loading="true" style="min-height: 240px" />
  <el-alert v-else-if="error" type="error" :title="error" :closable="false" show-icon />

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">项目</div>
        <div class="page-sub">项目制管理：状态推进、合同额与回款、里程碑勾选进度。</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建项目</el-button>
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
      <div class="search">
        <el-input v-model="kw" placeholder="搜索项目 / 客户 / 条款">
          <template #prefix><AppIcon name="search" :size="15" /></template>
        </el-input>
      </div>
      <el-select v-model="status" style="width: 130px">
        <el-option v-for="o in STATUS_FILTER" :key="o.value" :value="o.value" :label="o.text" />
      </el-select>
      <div style="display: flex; gap: 2px; background: var(--bg-hover); border-radius: var(--radius-md); padding: 2px">
        <el-button :type="viewMode === 'card' ? 'primary' : ''" @click="viewMode = 'card'"><AppIcon name="grid" :size="13" /> 卡片</el-button>
        <el-button :type="viewMode === 'gantt' ? 'primary' : ''" @click="viewMode = 'gantt'"><AppIcon name="calendar-range" :size="13" /> 甘特</el-button>
      </div>
    </div>

    <el-empty v-if="viewMode === 'gantt'" description="甘特视图要有带日期的里程碑才画得出来。先在项目「里程碑」里把开始与截止日期填上。" />

    <el-empty
      v-else-if="!shown.length"
      :description="kw.trim() || status !== 'all' ? '没有符合条件的项目。' : '还没有项目。先建客户，再在项目里把客户选上。'"
    >
      <el-button type="primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建项目</el-button>
    </el-empty>

    <div v-else class="card-grid">
      <div v-for="p in shown" :key="p.id" class="ent-card">
        <div class="ent-top">
          <b class="ent-name" @click="openEdit(p)">{{ p.name }}</b>
          <el-tag size="small" :type="PROJ_TAG_TYPE[p.status || 'talking'] ?? 'info'" :class="{ 'tag-purple': (p.status || 'talking') === 'maintain' }">{{ label(PROJECT_STATUS, p.status, '洽谈中') }}</el-tag>
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
          <el-button size="small" @click="openMs(p)"><AppIcon name="clipboard-check" :size="13" /> 里程碑</el-button>
          <el-button size="small" @click="openEdit(p)"><AppIcon name="edit" :size="13" /></el-button>
          <el-button size="small" type="danger" plain @click="openKill(p)"><AppIcon name="trash" :size="13" /></el-button>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <Modal v-if="editing && edit" :title="isNew ? '新建项目' : '编辑项目'" icon="package" @close="editing = false">
      <div class="form-grid">
        <div class="field full"><label>项目名称 <span class="req">*</span></label><el-input v-model="edit.name" maxlength="200" /></div>
        <div class="field"><label>客户</label>
          <el-select :empty-values="[]" v-model="edit.clientId"><el-option :value="(null as any)" label="选客户" /><el-option v-for="c in clientOptions" :key="c.value" :value="c.value" :label="c.text" /></el-select>
        </div>
        <div class="field"><label>状态</label>
          <el-select v-model="edit.status"><el-option v-for="o in Object.entries(PROJECT_STATUS)" :key="o[0]" :value="o[0]" :label="o[1]" /></el-select>
        </div>
        <div class="field"><label>合同额（元）</label><el-input-number v-model="edit.amount" :controls="false" style="width: 100%" /></div>
        <div class="field"><label>签约日期</label><el-date-picker v-model="edit.signedDate" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field"><label>开始日期</label><el-date-picker v-model="edit.startDate" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field"><label>预计交付</label><el-date-picker v-model="edit.endDate" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field"><label>维护到期</label><el-date-picker v-model="edit.expireDate" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field full"><label>关键条款</label><el-input v-model="edit.terms" maxlength="1000" /></div>
        <div class="field full"><label>范围与说明</label><el-input v-model="edit.description" type="textarea" :rows="3" maxlength="1000" /></div>
      </div>
      <template #footer>
        <el-button @click="editing = false">取消</el-button>
        <el-button type="primary" @click="save"><AppIcon name="check" :size="14" /> 保存</el-button>
      </template>
    </Modal>

    <!-- 里程碑弹窗 -->
    <Modal v-if="msVisible && msOf" :title="msOf.name + ' · 里程碑'" icon="clipboard-check" @close="msVisible = false">
      <div v-for="m in msOfProject(msOf.id)" :key="m.id" class="ms-item">
        <el-checkbox :model-value="m.done" @change="toggleMs(m)" />
        <div class="ms-t">
          <span v-if="renaming !== m.id" :class="{ done: m.done }" @dblclick="startRename(m)">{{ m.title }}</span>
          <el-input v-else v-model="renameTitle" size="small" @blur="commitRename(m)" @keyup.enter="commitRename(m)" />
        </div>
        <div class="ms-dates">
          <el-date-picker :model-value="m.startDate ? m.startDate.slice(0, 10) : ''" type="date" value-format="YYYY-MM-DD" size="small" style="width: 130px" @change="(v: string | null) => setMsDate(m, v, true)" />
          <el-date-picker :model-value="m.dueDate ? m.dueDate.slice(0, 10) : ''" type="date" value-format="YYYY-MM-DD" size="small" style="width: 130px" @change="(v: string | null) => setMsDate(m, v, false)" />
          <el-button text class="icon-btn" @click="deleteMs(m)"><AppIcon name="trash" :size="13" /></el-button>
        </div>
      </div>
      <div v-if="!msOfProject(msOf.id).length" class="muted" style="font-size: 13px; padding: 12px 0">还没有里程碑，在下面加第一个。</div>

      <div class="form-grid" style="margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border-light)">
        <div class="field full"><label>节点名称 <span class="req">*</span></label><el-input v-model="msTitle" maxlength="200" placeholder="如 首页开发完成" /></div>
        <div class="field"><label>开始</label><el-date-picker v-model="msStart" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field"><label>截止</label><el-date-picker v-model="msDue" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field full" style="text-align: right"><el-button type="primary" @click="addMs"><AppIcon name="plus" :size="14" /> 加里程碑</el-button></div>
      </div>
    </Modal>

    <!-- 删除弹窗 -->
    <Modal v-if="killing && kill" :title="'删除 ' + kill.name" icon="trash" @close="killing = false">
      <div class="impact">
        <p v-if="impact && impact.groups.length" class="muted" style="margin: 0 0 10px; font-size: 13px">删除前先看有哪些记录挂在它身上：</p>
        <div v-if="impact && impact.groups.length" class="impact-groups">
          <div v-for="g in impact.groups" :key="g.label" class="impact-row">
            <span>{{ g.label }}</span>
            <el-tag size="small" :type="g.mode === 'cascade' ? 'danger' : 'info'">{{ g.mode === 'cascade' ? '跟着删' : '可解绑保留' }}</el-tag>
            <span class="muted">{{ g.count }}</span>
          </div>
        </div>
        <div v-else class="impact-none">这个项目下面没有挂着任务、发票或里程碑，删了不留尾巴。</div>
      </div>
      <div class="field" style="margin-bottom: 12px">
        <el-checkbox v-model="killDetach">解绑并保留任务 / 发票 / 支出（否则原样保留，显示「项目已删除」）</el-checkbox>
      </div>
      <template #footer>
        <el-button @click="killing = false">取消</el-button>
        <el-button :disabled="killBusy" @click="doFinish"><AppIcon name="check" :size="14" /> 标为已完结（推荐）</el-button>
        <el-button type="danger" :disabled="killBusy" @click="doDelete">
          <AppIcon name="trash" :size="14" /> 删除
        </el-button>
      </template>
    </Modal>
  </template>
</template>
