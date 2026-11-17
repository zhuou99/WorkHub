<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Expense, Invoice, Payment, PaymentPlan, Project } from '@/types'
import { formatDate, money } from '@/utils'

const loading = ref(true)
const error = ref('')
const invoices = ref<Invoice[]>([])
const payments = ref<Payment[]>([])
const expenses = ref<Expense[]>([])
const plans = ref<PaymentPlan[]>([])
const projects = ref<Project[]>([])

const year = ref(String(new Date().getFullYear()))
const expPage0 = ref(0)
const EXP_PAGE_SIZE = 20

const editing = ref(false)
const isNew = ref(true)
const edit = ref<Expense | null>(null)

const CATEGORY_HINTS = ['服务器', '域名', '软件订阅', '外包', '差旅', '办公', '税费', '其他']

const years = computed(() => {
  const set = new Set<number>([new Date().getFullYear()])
  for (const iv of invoices.value) { const y = new Date(iv.issueDate ?? '').getFullYear(); if (!Number.isNaN(y)) set.add(y) }
  for (const p of payments.value) { const y = new Date(p.payDate ?? '').getFullYear(); if (!Number.isNaN(y)) set.add(y) }
  for (const e of expenses.value) { const y = new Date(e.happenDate ?? '').getFullYear(); if (!Number.isNaN(y)) set.add(y) }
  return [...set].sort((a, b) => b - a)
})

const Y = computed(() => parseInt(year.value) || new Date().getFullYear())
const months = computed(() => Array.from({ length: 12 }, (_, i) => `${Y.value}-${String(i + 1).padStart(2, '0')}`))

const yearInvoices = computed(() => invoices.value.filter((iv) => iv.status !== 'void' && new Date(iv.issueDate ?? '').getFullYear() === Y.value))
const yearPayments = computed(() => payments.value.filter((p) => new Date(p.payDate ?? '').getFullYear() === Y.value))
const yearExpenses = computed(() => expenses.value.filter((e) => new Date(e.happenDate ?? '').getFullYear() === Y.value))

function monthKeyOf(v: string | null | undefined): string {
  return v ? v.slice(0, 7) : ''
}

const invoiceAmounts = computed(() => months.value.map((m) => yearInvoices.value.filter((iv) => monthKeyOf(iv.issueDate) === m).reduce((s, iv) => s + Number(iv.amount), 0)))
const paymentAmounts = computed(() => months.value.map((m) => yearPayments.value.filter((p) => monthKeyOf(p.payDate) === m).reduce((s, p) => s + Number(p.amount), 0)))
const expenseAmounts = computed(() => months.value.map((m) => yearExpenses.value.filter((e) => monthKeyOf(e.happenDate) === m).reduce((s, e) => s + Number(e.amount), 0)))
const planAmounts = computed(() => months.value.map((m) => plans.value.filter((p) => monthKeyOf(p.dueDate) === m).reduce((s, p) => s + Number(p.amount), 0)))

const overview = computed(() => {
  const inv = invoiceAmounts.value.reduce((s, v) => s + v, 0)
  const pay = paymentAmounts.value.reduce((s, v) => s + v, 0)
  const exp = expenseAmounts.value.reduce((s, v) => s + v, 0)
  return [
    { icon: 'receipt', color: '#4f7cff', value: money(inv), label: `${Y.value} 开票` },
    { icon: 'wallet', color: '#07c160', value: money(pay), label: `${Y.value} 回款` },
    { icon: 'coins', color: '#f5a623', value: money(exp), label: `${Y.value} 支出` },
    { icon: 'activity', color: '#7c5cff', value: money(pay - exp), label: `${Y.value} 净落袋` },
  ]
})

const maxBar = computed(() => {
  const all = [...invoiceAmounts.value, ...paymentAmounts.value, ...expenseAmounts.value, ...planAmounts.value]
  return Math.max(1, ...all)
})

function barHeight(v: number): string {
  return Math.max(2, (v / maxBar.value) * 100) + '%'
}

const expPage = computed(() => yearExpenses.value.slice(expPage0.value * EXP_PAGE_SIZE, (expPage0.value + 1) * EXP_PAGE_SIZE))
const expPageCount = computed(() => Math.max(1, Math.ceil(yearExpenses.value.length / EXP_PAGE_SIZE)))

function projName(id: string | null): string {
  if (!id) return ''
  return projects.value.find((p) => p.id === id)?.name ?? ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [iv, pay, exp, pl, p] = await Promise.all([
      api.get<Invoice[]>('/api/finance/invoices'),
      api.get<Payment[]>('/api/finance/payments'),
      api.get<Expense[]>('/api/finance/expenses'),
      api.get<PaymentPlan[]>('/api/finance/plans'),
      api.get<Project[]>('/api/projects'),
    ])
    invoices.value = iv
    payments.value = pay
    expenses.value = exp
    plans.value = pl
    projects.value = p
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载收支数据失败'
  } finally {
    loading.value = false
  }
}

function onYearChanged(v: string) { year.value = v; expPage0.value = 0 }

function openAdd() {
  edit.value = { id: '', category: '服务器', amount: 0, happenDate: new Date().toISOString().slice(0, 10), projectId: null, note: null, createTime: null }
  isNew.value = true
  editing.value = true
}
function openEdit(e: Expense) { edit.value = { ...e }; isNew.value = false; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.category.trim() || Number(edit.value.amount) <= 0) return
  edit.value.category = edit.value.category.trim()
  await api.post<Expense>('/api/finance/expenses', edit.value)
  editing.value = false
  await load()
}

async function remove(e: Expense) {
  await api.del(`/api/finance/expenses/${e.id}`)
  expenses.value = expenses.value.filter((x) => x.id !== e.id)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading"><div class="spinner" /></div>
  <div v-else-if="error" class="card"><div class="empty">{{ error }}</div></div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">收支统计</div>
        <div class="page-sub">年度开票、回款、支出按月汇总，净落袋一眼看清。</div>
      </div>
      <div class="page-actions">
        <select :value="year" class="input" style="width: 120px" @change="onYearChanged(($event.target as HTMLSelectElement).value)">
          <option v-for="y in years" :key="y" :value="String(y)">{{ y }} 年</option>
        </select>
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 记支出</button>
      </div>
    </div>

    <div class="stat-grid" style="grid-template-columns: repeat(4, minmax(0, 1fr))">
      <div v-for="s in overview" :key="s.label" class="stat-card">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
          <div class="stat-icon" :style="{ background: s.color + '22', color: s.color }"><AppIcon :name="s.icon" :size="15" /></div>
        </div>
      </div>
    </div>

    <div class="card" style="margin-bottom: 16px">
      <div class="card-title"><AppIcon name="activity" :size="16" /> 月度收支</div>
      <div class="bars">
        <div v-for="(m, i) in months" :key="m" class="bar-group">
          <div class="bar plan" :style="{ height: barHeight(planAmounts[i]) }" :title="`${m} 计划 ${money(planAmounts[i])}`" />
          <div class="bar invoice" :style="{ height: barHeight(invoiceAmounts[i]) }" :title="`${m} 开票 ${money(invoiceAmounts[i])}`" />
          <div class="bar payment" :style="{ height: barHeight(paymentAmounts[i]) }" :title="`${m} 回款 ${money(paymentAmounts[i])}`" />
          <div class="bar expense" :style="{ height: barHeight(expenseAmounts[i]) }" :title="`${m} 支出 ${money(expenseAmounts[i])}`" />
        </div>
      </div>
      <div style="display: flex; gap: 6px">
        <span v-for="m in months" :key="m" style="flex: 1; text-align: center; font-size: 10.5px; color: var(--text-muted)">{{ m.slice(5) }}月</span>
      </div>
      <div class="bar-legend">
        <span><i style="background: #7c5cff; opacity: .55" /> 计划</span>
        <span><i style="background: #4f7cff" /> 开票</span>
        <span><i style="background: #07c160" /> 回款</span>
        <span><i style="background: #f5a623" /> 支出</span>
      </div>
    </div>

    <div class="card">
      <div class="card-title"><AppIcon name="coins" :size="16" /> 支出流水（{{ yearExpenses.length }} 笔）</div>
      <div v-if="!yearExpenses.length" class="empty">这个年度还没有支出记录。</div>
      <table v-else class="table">
        <thead><tr><th>日期</th><th>类别</th><th>项目</th><th class="right">金额</th><th>备注</th><th class="right">操作</th></tr></thead>
        <tbody>
          <tr v-for="e in expPage" :key="e.id">
            <td>{{ formatDate(e.happenDate) }}</td>
            <td><span class="pill st-talking">{{ e.category }}</span></td>
            <td>{{ projName(e.projectId) || '—' }}</td>
            <td class="num">{{ money(Number(e.amount)) }}</td>
            <td class="muted">{{ e.note || '' }}</td>
            <td class="right"><div class="row-actions">
              <button class="btn" style="height: 26px; font-size: 12px" @click="openEdit(e)"><AppIcon name="edit" :size="13" /></button>
              <button class="btn" style="height: 26px; font-size: 12px; color: var(--danger-color)" @click="remove(e)"><AppIcon name="trash" :size="13" /></button>
            </div></td>
          </tr>
        </tbody>
      </table>
      <div v-if="expPageCount > 1" class="pager">
        <button class="btn" :disabled="expPage0 <= 0" @click="expPage0--"><AppIcon name="chevron-left" :size="13" /></button>
        <span>{{ expPage0 + 1 }} / {{ expPageCount }}</span>
        <button class="btn" :disabled="expPage0 >= expPageCount - 1" @click="expPage0++"><AppIcon name="chevron-right" :size="13" /></button>
      </div>
    </div>

    <Modal v-if="editing && edit" :title="isNew ? '记一笔支出' : '编辑支出'" icon="coins" @close="editing = false">
      <div class="form-grid">
        <div class="field full"><label>类别 <span class="req">*</span></label>
          <input v-model="edit.category" class="input" maxlength="40" list="cat-hints" />
          <datalist id="cat-hints"><option v-for="c in CATEGORY_HINTS" :key="c" :value="c" /></datalist>
        </div>
        <div class="field"><label>金额（元）</label><input v-model.number="edit.amount" class="input" type="number" min="0" /></div>
        <div class="field"><label>发生日期</label><input v-model="edit.happenDate" class="input" type="date" /></div>
        <div class="field"><label>项目</label>
          <select v-model="edit.projectId" class="input"><option :value="null">不挂项目</option><option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option></select>
        </div>
        <div class="field"><label>备注</label><input v-model="edit.note" class="input" maxlength="500" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
    </Modal>
  </template>
</template>
