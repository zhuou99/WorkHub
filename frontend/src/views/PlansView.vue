<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Client, Invoice, Payment, PaymentPlan, Project } from '@/types'
import { dateOf, formatDate, formatMd, label, money } from '@/utils'

const loading = ref(true)
const error = ref('')
const plans = ref<PaymentPlan[]>([])
const projects = ref<Project[]>([])
const clients = ref<Client[]>([])
const invoices = ref<Invoice[]>([])
const payments = ref<Payment[]>([])

const kw = ref('')
const projectId = ref('')
const status = ref('all')

const editing = ref(false)
const isNew = ref(false)
const edit = ref<PaymentPlan | null>(null)

const PLAN_STATUS = { pending: '待收', paid: '已到账', skipped: '已免除' }
const STATUS_FILTER = [{ value: 'all', text: '全部状态' }, ...Object.entries(PLAN_STATUS).map(([value, text]) => ({ value, text }))]

/* 状态胶囊 → el-tag type 映射 */
type TagType = 'info' | 'primary' | 'success' | 'warning' | 'danger'

const PLAN_TAG_TYPE: Record<string, TagType> = { pending: 'info', paid: 'success', skipped: 'info' }

function clientName(id: string | null): string {
  if (!id) return ''
  return clients.value.find((c) => c.id === id)?.name ?? ''
}
function projName(id: string | null): string {
  if (!id) return '未挂项目'
  return projects.value.find((p) => p.id === id)?.name ?? '项目已删除'
}
function clientOf(p: PaymentPlan): string {
  const fromProject = projects.value.find((x) => x.id === p.projectId)?.clientId
  if (fromProject) return fromProject
  return invoices.value.find((x) => x.id === p.invoiceId)?.clientId ?? ''
}
function invoiceLabel(id: string | null): string {
  if (!id) return ''
  const iv = invoices.value.find((x) => x.id === id)
  return iv ? `${formatMd(iv.issueDate)} ${money(Number(iv.amount))}` : '发票已删除'
}

function match(p: PaymentPlan, k: string): boolean {
  if (!k.trim()) return true
  const needle = k.trim().toLowerCase()
  return [p.title, p.note, projName(p.projectId), clientName(clientOf(p))].some((v) => v && v.toLowerCase().includes(needle))
}

const shown = computed(() =>
  plans.value.filter((p) => {
    if (status.value !== 'all' && p.status !== status.value) return false
    if (projectId.value && p.projectId !== projectId.value) return false
    return match(p, kw.value)
  }),
)

const stats = computed(() => {
  const now = new Date()
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
  const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 1)
  const planDue = plans.value.filter((p) => p.status === 'pending').reduce((s, p) => s + Number(p.amount), 0)
  const overdue = plans.value.filter((p) => p.isOverdue).length
  const monthDue = plans.value.filter((p) => p.status === 'pending' && dateOf(p.dueDate) !== null && dateOf(p.dueDate)! >= monthStart && dateOf(p.dueDate)! < monthEnd).length
  const monthPaid = plans.value.filter((p) => p.status === 'paid' && dateOf(p.paidDate) !== null && dateOf(p.paidDate)! >= monthStart).reduce((s, p) => s + Number(p.amount), 0)
  return [
    { icon: 'hourglass', color: '#f5a623', value: money(planDue), label: '计划待收' },
    { icon: 'alert-circle', color: '#f5544c', value: overdue, label: '逾期期次' },
    { icon: 'calendar-check', color: '#4f7cff', value: monthDue, label: '本月应收' },
    { icon: 'wallet', color: '#07c160', value: money(monthPaid), label: '本月到账' },
  ]
})

const projectFilter = computed(() => projects.value.map((p) => ({ value: p.id, text: p.name })))
const projectOptions = computed(() => {
  const options = projects.value.filter((p) => p.status !== 'done').map((p) => ({ value: p.id, text: p.name }))
  if (edit.value?.projectId && !projects.value.some((p) => p.id === edit.value!.projectId && p.status !== 'done')) {
    const p = projects.value.find((x) => x.id === edit.value!.projectId)
    if (p) options.push({ value: p.id, text: p.name + '（已完结）' })
  }
  return options
})
const invoiceOptions = computed(() => {
  let list = invoices.value.filter((iv) => iv.status !== 'void' && Number(iv.due) > 0)
  if (edit.value?.projectId) list = list.filter((iv) => iv.projectId === edit.value!.projectId || !iv.projectId)
  return list.map((iv) => ({ value: iv.id, text: `${formatMd(iv.issueDate)} ${iv.clientName} ${money(Number(iv.amount))}${iv.no ? ' · ' + iv.no : ''}` }))
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [pl, p, c, iv, pay] = await Promise.all([
      api.get<PaymentPlan[]>('/api/finance/plans'),
      api.get<Project[]>('/api/projects'),
      api.get<Client[]>('/api/clients'),
      api.get<Invoice[]>('/api/finance/invoices'),
      api.get<Payment[]>('/api/finance/payments'),
    ])
    plans.value = pl
    projects.value = p
    clients.value = c
    invoices.value = iv
    payments.value = pay
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载回款计划失败'
  } finally {
    loading.value = false
  }
}

function plansOf(pid: string): PaymentPlan[] { return plans.value.filter((p) => p.projectId === pid) }

function openAdd() {
  const next = plansOf(projectId.value).length + 1
  const title = next === 1 ? '首款' : next === 2 ? '验收款' : '尾款'
  edit.value = { id: '', projectId: projectId.value || null, invoiceId: null, title, seq: next, dueDate: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10), amount: 0, status: 'pending', paidDate: null, note: null, isOverdue: false, percentOf: null, projectName: '' }
  isNew.value = true
  editing.value = true
}
function openEdit(p: PaymentPlan) { edit.value = { ...p }; isNew.value = false; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.title.trim() || Number(edit.value.amount) <= 0) return
  edit.value.title = edit.value.title.trim()
  edit.value.seq = edit.value.seq <= 0 ? 1 : edit.value.seq
  await api.post<PaymentPlan>('/api/finance/plans', edit.value)
  editing.value = false
  await load()
}

async function mark(p: PaymentPlan, newStatus: string) {
  await api.post(`/api/finance/plans/${p.id}/status`, { status: newStatus })
  await load()
}

async function remove(p: PaymentPlan) {
  await api.del(`/api/finance/plans/${p.id}`)
  plans.value = plans.value.filter((x) => x.id !== p.id)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" v-loading="true" style="min-height: 240px" />
  <el-alert v-else-if="error" type="error" :title="error" :closable="false" show-icon />

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">回款计划</div>
        <div class="page-sub">把合同额拆成期次，哪天该收哪一笔、哪期拖了，一眼看清。</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建期次</el-button>
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
        <el-input v-model="kw" placeholder="搜索期次 / 项目 / 客户">
          <template #prefix><AppIcon name="search" :size="15" /></template>
        </el-input>
      </div>
      <el-select :empty-values="[]" v-model="projectId" style="width: 140px"><el-option value="" label="全部项目" /><el-option v-for="p in projectFilter" :key="p.value" :value="p.value" :label="p.text" /></el-select>
      <el-select v-model="status" style="width: 110px"><el-option v-for="o in STATUS_FILTER" :key="o.value" :value="o.value" :label="o.text" /></el-select>
    </div>

    <el-empty
      v-if="!shown.length"
      :description="kw.trim() || status !== 'all' || projectId ? '没有符合条件的期次。' : '还没拆回款计划。选个项目，把合同额拆成「首款 → 验收款 → 尾款」。'"
    >
      <el-button type="primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新建期次</el-button>
    </el-empty>

    <el-table v-else :data="shown">
      <el-table-column label="项目 / 期次" min-width="200">
        <template #default="{ row }">
          <div class="who">
            <b>{{ projName(row.projectId) }} · 第 {{ row.seq }} 期 {{ row.title }}</b>
            <span v-if="row.invoiceId">{{ invoiceLabel(row.invoiceId) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="应收日" min-width="100">
        <template #default="{ row }"><span :class="{ late: row.isOverdue }">{{ formatDate(row.dueDate) || '—' }}</span></template>
      </el-table-column>
      <el-table-column label="金额" align="right" min-width="110">
        <template #default="{ row }"><b>{{ money(Number(row.amount)) }}</b></template>
      </el-table-column>
      <el-table-column label="占比" align="right" width="80">
        <template #default="{ row }">{{ row.percentOf !== null ? row.percentOf + '%' : '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }"><el-tag size="small" :type="PLAN_TAG_TYPE[row.status || 'pending'] ?? 'info'">{{ label(PLAN_STATUS, row.status, '待收') }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" align="right" width="210">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button v-if="row.status !== 'paid'" size="small" type="success" plain @click="mark(row as PaymentPlan, 'paid')"><AppIcon name="check" :size="13" /> 到账</el-button>
            <el-button v-if="row.status === 'paid'" size="small" @click="mark(row as PaymentPlan, 'pending')"><AppIcon name="refresh" :size="13" /> 退回</el-button>
            <el-button size="small" @click="openEdit(row as PaymentPlan)"><AppIcon name="edit" :size="13" /></el-button>
            <el-button size="small" type="danger" plain @click="remove(row as PaymentPlan)"><AppIcon name="trash" :size="13" /></el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑弹窗 -->
    <Modal v-if="editing && edit" :title="isNew ? '新建期次' : '编辑期次'" icon="wallet" @close="editing = false">
      <div class="form-grid">
        <div class="field"><label>项目</label>
          <el-select :empty-values="[]" v-model="edit.projectId"><el-option :value="(null as any)" label="不挂项目" /><el-option v-for="p in projectOptions" :key="p.value" :value="p.value" :label="p.text" /></el-select>
        </div>
        <div class="field"><label>第几期</label><el-input-number v-model="edit.seq" :controls="false" :min="1" :max="99" style="width: 100%" /></div>
        <div class="field"><label>期次名称</label><el-input v-model="edit.title" maxlength="100" placeholder="首款 / 验收款 / 尾款" /></div>
        <div class="field"><label>应收金额（元）</label><el-input-number v-model="edit.amount" :controls="false" :min="0" style="width: 100%" /></div>
        <div class="field"><label>应收日</label><el-date-picker v-model="edit.dueDate" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field"><label>状态</label><el-select v-model="edit.status"><el-option v-for="o in Object.entries(PLAN_STATUS)" :key="o[0]" :value="o[0]" :label="o[1]" /></el-select></div>
        <div class="field full"><label>挂发票（可选）</label>
          <el-select :empty-values="[]" v-model="edit.invoiceId"><el-option :value="(null as any)" label="不挂发票" /><el-option v-for="iv in invoiceOptions" :key="iv.value" :value="iv.value" :label="iv.text" /></el-select>
        </div>
        <div class="field full"><label>备注</label><el-input v-model="edit.note" maxlength="500" /></div>
      </div>
      <template #footer>
        <el-button @click="editing = false">取消</el-button>
        <el-button type="primary" @click="save"><AppIcon name="check" :size="14" /> 保存</el-button>
      </template>
    </Modal>
  </template>
</template>
