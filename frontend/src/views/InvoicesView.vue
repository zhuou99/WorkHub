<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Client, Invoice, Payment, Project } from '@/types'
import { formatDate, formatMd, INVOICE_STATUS, label, money } from '@/utils'

const loading = ref(true)
const error = ref('')
const invoices = ref<Invoice[]>([])
const payments = ref<Payment[]>([])
const clients = ref<Client[]>([])
const projects = ref<Project[]>([])

const kw = ref('')
const status = ref('all')
const clientId = ref('')
const tag = ref('')

const editing = ref(false)
const isNew = ref(false)
const edit = ref<Invoice | null>(null)

const paying = ref(false)
const payOf = ref<Invoice | null>(null)
const pay = ref<Payment | null>(null)
const payDate = ref('')

const STATUS_FILTER = [{ value: 'all', text: '全部状态' }, ...Object.entries(INVOICE_STATUS).map(([value, text]) => ({ value, text }))]
const TYPE_OPTIONS = [{ value: 'general', text: '普票' }, { value: 'special', text: '专票' }, { value: 'agent', text: '个人代开' }]
const METHOD_OPTIONS = [{ value: 'bank', text: '银行转账' }, { value: 'wechat', text: '微信' }, { value: 'alipay', text: '支付宝' }, { value: 'cash', text: '现金' }, { value: 'other', text: '其他' }]

function match(iv: Invoice, k: string): boolean {
  if (!k.trim()) return true
  const needle = k.trim().toLowerCase()
  return [iv.no, iv.note, iv.clientName, iv.projectName].some((v) => v && v.toLowerCase().includes(needle))
}

const shown = computed(() =>
  invoices.value.filter((iv) => {
    if (status.value !== 'all' && iv.status !== status.value) return false
    if (clientId.value && iv.clientId !== clientId.value) return false
    if (tag.value === 'overdue' && !iv.isOverdue) return false
    if (tag.value === 'due' && !(Number(iv.due) > 0)) return false
    return match(iv, kw.value)
  }),
)

const stats = computed(() => {
  const now = new Date()
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
  const billed = invoices.value.filter((iv) => iv.status !== 'void' && new Date(iv.issueDate ?? 0) >= monthStart).reduce((s, iv) => s + Number(iv.amount), 0)
  const came = payments.value.filter((p) => new Date(p.payDate ?? 0) >= monthStart).reduce((s, p) => s + Number(p.amount), 0)
  const due = invoices.value.reduce((s, iv) => s + Number(iv.due), 0)
  const overdue = invoices.value.filter((iv) => iv.isOverdue).length
  return [
    { icon: 'receipt', color: '#4f7cff', value: money(billed), label: '本月开票' },
    { icon: 'wallet', color: '#07c160', value: money(came), label: '本月回款' },
    { icon: 'hourglass', color: '#f5a623', value: money(due), label: '待收合计' },
    { icon: 'alert-circle', color: '#f5544c', value: overdue, label: '逾期未收' },
  ]
})

const clientFilter = computed(() => clients.value.map((c) => ({ value: c.id, text: c.name })))
const clientOptions = computed(() => {
  const options = clients.value.filter((c) => !c.archived).map((c) => ({ value: c.id, text: c.name }))
  if (edit.value?.clientId && !clients.value.some((c) => c.id === edit.value!.clientId && !c.archived)) {
    const c = clients.value.find((x) => x.id === edit.value!.clientId)
    if (c) options.push({ value: c.id, text: c.name + '（已归档）' })
  }
  return options
})
const projectOptions = computed(() => projects.value.map((p) => ({ value: p.id, text: p.name })))

function paysOf(invoiceId: string): Payment[] {
  return payments.value.filter((p) => p.invoiceId === invoiceId).sort((a, b) => String(b.payDate).localeCompare(String(a.payDate)))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [iv, pay, c, p] = await Promise.all([
      api.get<Invoice[]>('/api/finance/invoices'),
      api.get<Payment[]>('/api/finance/payments'),
      api.get<Client[]>('/api/clients'),
      api.get<Project[]>('/api/projects'),
    ])
    invoices.value = iv
    payments.value = pay
    clients.value = c
    projects.value = p
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载发票台账失败'
  } finally {
    loading.value = false
  }
}

function openAdd() {
  edit.value = { id: '', no: null, clientId: '', projectId: null, type: 'general', amount: 0, taxRate: 6, issueDate: new Date().toISOString().slice(0, 10), expectDate: null, status: 'opened', file: null, note: null, paid: 0, due: 0, isOverdue: false, tax: 0, clientName: '', projectName: '' }
  isNew.value = true
  editing.value = true
}
function openEdit(iv: Invoice) { edit.value = { ...iv }; isNew.value = false; editing.value = true }

function onProjectChanged(projectId: string) {
  if (!edit.value) return
  edit.value.projectId = projectId || null
  const p = projects.value.find((x) => x.id === projectId)
  if (p && !edit.value.clientId) edit.value.clientId = p.clientId ?? ''
}

async function save() {
  if (!edit.value || !edit.value.clientId) return
  edit.value.no = edit.value.no?.trim() ?? null
  edit.value.note = edit.value.note?.trim() ?? null
  await api.post<Invoice>('/api/finance/invoices', edit.value)
  editing.value = false
  await load()
}

async function remove(iv: Invoice) {
  await api.del(`/api/finance/invoices/${iv.id}`)
  await load()
}

function openPay(iv: Invoice) {
  payOf.value = iv
  pay.value = { id: '', invoiceId: iv.id, amount: Number(iv.due), payDate: new Date().toISOString().slice(0, 10), method: 'bank', note: null }
  payDate.value = new Date().toISOString().slice(0, 10)
  paying.value = true
}

async function addPayment() {
  if (!payOf.value || !pay.value || Number(pay.value.amount) <= 0) return
  pay.value.payDate = payDate.value
  await api.post<Payment>('/api/finance/payments', pay.value)
  paying.value = false
  await load()
}

async function deletePayment(p: Payment) {
  await api.del(`/api/finance/payments/${p.id}`)
  payments.value = payments.value.filter((x) => x.id !== p.id)
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
        <div class="page-greet">发票台账</div>
        <div class="page-sub">开票、回款、逾期一条线看完；金额以「价税合计」为准，已收由回款登记汇总。</div>
      </div>
      <div class="page-actions">
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 开票登记</button>
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
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索票号 / 客户 / 项目 / 备注" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <select v-model="status" class="input" style="width: 110px"><option v-for="o in STATUS_FILTER" :key="o.value" :value="o.value">{{ o.text }}</option></select>
      <select v-model="clientId" class="input" style="width: 120px"><option value="">全部客户</option><option v-for="c in clientFilter" :key="c.value" :value="c.value">{{ c.text }}</option></select>
      <button class="btn" :class="{ primary: tag === 'overdue' }" @click="tag = tag === 'overdue' ? '' : 'overdue'"><AppIcon name="alert-circle" :size="13" /> 只看逾期</button>
      <button class="btn" :class="{ primary: tag === 'due' }" @click="tag = tag === 'due' ? '' : 'due'"><AppIcon name="wallet" :size="13" /> 只看未收满</button>
    </div>

    <div v-if="!shown.length" class="page-empty">
      <p>{{ kw.trim() || status !== 'all' || clientId || tag ? '没有符合条件的发票。' : '还没有开票记录。' }}</p>
      <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 开票登记</button>
    </div>

    <table v-else class="table">
      <thead>
        <tr>
          <th>客户 / 项目</th><th>票号</th><th>类型</th><th class="right">金额</th>
          <th>开票日</th><th>回款期限</th><th class="right">已收</th><th class="right">待收</th><th>状态</th><th class="right">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="iv in shown" :key="iv.id">
          <td><div class="who"><b>{{ iv.clientName }}</b><span>{{ iv.projectName }}</span></div></td>
          <td>{{ iv.no || '未填' }}</td>
          <td>{{ iv.type === 'special' ? '专票' : iv.type === 'agent' ? '个人代开' : '普票' }}</td>
          <td class="num"><b>{{ money(Number(iv.amount)) }}</b><div class="tax">{{ money(Number(iv.tax)) }} 税</div></td>
          <td>{{ formatDate(iv.issueDate) || '—' }}</td>
          <td><span :class="{ late: iv.isOverdue }">{{ formatDate(iv.expectDate) || '—' }}</span></td>
          <td class="num">{{ money(Number(iv.paid)) }}</td>
          <td class="num"><b :class="Number(iv.due) > 0 ? 'due' : 'ok'">{{ money(Number(iv.due)) }}</b></td>
          <td>
            <span class="pill" :class="'st-' + (iv.status || 'opened')">{{ label(INVOICE_STATUS, iv.status, '已开票') }}</span>
            <span v-if="iv.isOverdue" class="flag danger" style="margin-left: 4px">逾期</span>
          </td>
          <td class="right"><div class="row-actions">
            <button class="btn" style="height: 26px; font-size: 12px" @click="openPay(iv)"><AppIcon name="wallet" :size="13" /> 回款</button>
            <button class="btn" style="height: 26px; font-size: 12px" @click="openEdit(iv)"><AppIcon name="edit" :size="13" /></button>
            <button class="btn" style="height: 26px; font-size: 12px; color: var(--danger-color)" @click="remove(iv)"><AppIcon name="trash" :size="13" /></button>
          </div></td>
        </tr>
      </tbody>
    </table>

    <!-- 编辑弹窗 -->
    <Modal v-if="editing && edit" :title="isNew ? '开票登记' : '编辑发票'" icon="receipt" @close="editing = false">
      <div class="form-grid">
        <div class="field"><label>客户 <span class="req">*</span></label>
          <select v-model="edit.clientId" class="input"><option value="">选客户</option><option v-for="c in clientOptions" :key="c.value" :value="c.value">{{ c.text }}</option></select>
        </div>
        <div class="field"><label>项目</label>
          <select :value="edit.projectId" class="input" @change="onProjectChanged(($event.target as HTMLSelectElement).value)"><option value="">不挂项目</option><option v-for="p in projectOptions" :key="p.value" :value="p.value">{{ p.text }}</option></select>
        </div>
        <div class="field"><label>发票号</label><input v-model="edit.no" class="input" maxlength="50" placeholder="可后补" /></div>
        <div class="field"><label>类型</label><select v-model="edit.type" class="input"><option v-for="o in TYPE_OPTIONS" :key="o.value" :value="o.value">{{ o.text }}</option></select></div>
        <div class="field"><label>价税合计（元）</label><input v-model.number="edit.amount" class="input" type="number" min="0" /></div>
        <div class="field"><label>税率（%）</label><input v-model.number="edit.taxRate" class="input" type="number" min="0" /></div>
        <div class="field"><label>开票日</label><input v-model="edit.issueDate" class="input" type="date" /></div>
        <div class="field"><label>回款期限</label><input v-model="edit.expectDate" class="input" type="date" /></div>
        <div class="field"><label>状态</label><select v-model="edit.status" class="input"><option v-for="o in Object.entries(INVOICE_STATUS)" :key="o[0]" :value="o[0]">{{ o[1] }}</option></select></div>
        <div class="field"><label>备注</label><input v-model="edit.note" class="input" maxlength="300" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
    </Modal>

    <!-- 回款弹窗 -->
    <Modal v-if="paying && payOf && pay" :title="'记一笔回款 · ' + payOf.clientName" icon="wallet" @close="paying = false">
      <div class="form-grid">
        <div class="field"><label>到账金额</label><input v-model.number="pay.amount" class="input" type="number" min="0" /></div>
        <div class="field"><label>方式</label><select v-model="pay.method" class="input"><option v-for="o in METHOD_OPTIONS" :key="o.value" :value="o.value">{{ o.text }}</option></select></div>
        <div class="field"><label>到账日</label><input v-model="payDate" class="input" type="date" /></div>
        <div class="field"><label>备注</label><input v-model="pay.note" class="input" maxlength="300" /></div>
      </div>
      <div v-if="paysOf(payOf.id).length" class="sec">已记回款</div>
      <div v-for="p in paysOf(payOf.id)" :key="p.id" class="rel">
        <span class="rel-t">{{ formatMd(p.payDate) }} · {{ label({ bank: '银行转账', wechat: '微信', alipay: '支付宝', cash: '现金', other: '其他' }, p.method, '银行转账') }}</span>
        <span class="rel-a">{{ money(Number(p.amount)) }}</span>
        <button class="icon-btn" type="button" @click="deletePayment(p)"><AppIcon name="trash" :size="13" /></button>
      </div>
      <template #footer>
        <button class="btn" @click="paying = false">取消</button>
        <button class="btn primary" @click="addPayment"><AppIcon name="check" :size="14" /> 记到账</button>
      </template>
    </Modal>
  </template>
</template>
