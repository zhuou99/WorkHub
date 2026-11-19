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

/* 状态胶囊 → el-tag type 映射（sent 另加 tag-purple 类） */
type TagType = 'info' | 'primary' | 'success' | 'warning' | 'danger'

const IV_TAG_TYPE: Record<string, TagType> = { opened: 'primary', sent: 'primary', paid: 'success', void: 'danger' }

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
  if (p && !edit.value.clientId) edit.value.clientId = p.clientId ?? 'primary'
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
  <div v-if="loading" v-loading="true" style="min-height: 240px" />
  <el-alert v-else-if="error" type="error" :title="error" :closable="false" show-icon />

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">发票台账</div>
        <div class="page-sub">开票、回款、逾期一条线看完；金额以「价税合计」为准，已收由回款登记汇总。</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 开票登记</el-button>
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
        <el-input v-model="kw" placeholder="搜索票号 / 客户 / 项目 / 备注">
          <template #prefix><AppIcon name="search" :size="15" /></template>
        </el-input>
      </div>
      <el-select v-model="status" style="width: 110px"><el-option v-for="o in STATUS_FILTER" :key="o.value" :value="o.value" :label="o.text" /></el-select>
      <el-select :empty-values="[]" v-model="clientId" style="width: 120px"><el-option value="" label="全部客户" /><el-option v-for="c in clientFilter" :key="c.value" :value="c.value" :label="c.text" /></el-select>
      <el-button :type="tag === 'overdue' ? 'primary' : ''" @click="tag = tag === 'overdue' ? '' : 'overdue'"><AppIcon name="alert-circle" :size="13" /> 只看逾期</el-button>
      <el-button :type="tag === 'due' ? 'primary' : ''" @click="tag = tag === 'due' ? '' : 'due'"><AppIcon name="wallet" :size="13" /> 只看未收满</el-button>
    </div>

    <el-empty
      v-if="!shown.length"
      :description="kw.trim() || status !== 'all' || clientId || tag ? '没有符合条件的发票。' : '还没有开票记录。'"
    >
      <el-button type="primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 开票登记</el-button>
    </el-empty>

    <el-table v-else :data="shown">
      <el-table-column label="客户 / 项目" min-width="160">
        <template #default="{ row }"><div class="who"><b>{{ row.clientName }}</b><span>{{ row.projectName }}</span></div></template>
      </el-table-column>
      <el-table-column label="票号" min-width="100">
        <template #default="{ row }">{{ row.no || '未填' }}</template>
      </el-table-column>
      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ row.type === 'special' ? '专票' : row.type === 'agent' ? '个人代开' : '普票' }}</template>
      </el-table-column>
      <el-table-column label="金额" align="right" min-width="110">
        <template #default="{ row }"><b>{{ money(Number(row.amount)) }}</b><div class="tax">{{ money(Number(row.tax)) }} 税</div></template>
      </el-table-column>
      <el-table-column label="开票日" min-width="100">
        <template #default="{ row }">{{ formatDate(row.issueDate) || '—' }}</template>
      </el-table-column>
      <el-table-column label="回款期限" min-width="100">
        <template #default="{ row }"><span :class="{ late: row.isOverdue }">{{ formatDate(row.expectDate) || '—' }}</span></template>
      </el-table-column>
      <el-table-column label="已收" align="right" min-width="90">
        <template #default="{ row }">{{ money(Number(row.paid)) }}</template>
      </el-table-column>
      <el-table-column label="待收" align="right" min-width="90">
        <template #default="{ row }"><b :class="Number(row.due) > 0 ? 'due' : 'ok'">{{ money(Number(row.due)) }}</b></template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="IV_TAG_TYPE[row.status || 'opened'] ?? 'primary'" :class="{ 'tag-purple': (row.status || 'opened') === 'sent' }">{{ label(INVOICE_STATUS, row.status, '已开票') }}</el-tag>
          <span v-if="row.isOverdue" class="flag danger" style="margin-left: 4px">逾期</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" align="right" width="190">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button size="small" @click="openPay(row as Invoice)"><AppIcon name="wallet" :size="13" /> 回款</el-button>
            <el-button size="small" @click="openEdit(row as Invoice)"><AppIcon name="edit" :size="13" /></el-button>
            <el-button size="small" type="danger" plain @click="remove(row as Invoice)"><AppIcon name="trash" :size="13" /></el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑弹窗 -->
    <Modal v-if="editing && edit" :title="isNew ? '开票登记' : '编辑发票'" icon="receipt" @close="editing = false">
      <div class="form-grid">
        <div class="field"><label>客户 <span class="req">*</span></label>
          <el-select :empty-values="[]" v-model="edit.clientId"><el-option value="" label="选客户" /><el-option v-for="c in clientOptions" :key="c.value" :value="c.value" :label="c.text" /></el-select>
        </div>
        <div class="field"><label>项目</label>
          <el-select :empty-values="[]" :model-value="edit.projectId" @change="onProjectChanged"><el-option value="" label="不挂项目" /><el-option v-for="p in projectOptions" :key="p.value" :value="p.value" :label="p.text" /></el-select>
        </div>
        <div class="field"><label>发票号</label><el-input v-model="edit.no" maxlength="50" placeholder="可后补" /></div>
        <div class="field"><label>类型</label><el-select v-model="edit.type"><el-option v-for="o in TYPE_OPTIONS" :key="o.value" :value="o.value" :label="o.text" /></el-select></div>
        <div class="field"><label>价税合计（元）</label><el-input-number v-model="edit.amount" :controls="false" :min="0" style="width: 100%" /></div>
        <div class="field"><label>税率（%）</label><el-input-number v-model="edit.taxRate" :controls="false" :min="0" style="width: 100%" /></div>
        <div class="field"><label>开票日</label><el-date-picker v-model="edit.issueDate" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field"><label>回款期限</label><el-date-picker v-model="edit.expectDate" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field"><label>状态</label><el-select v-model="edit.status"><el-option v-for="o in Object.entries(INVOICE_STATUS)" :key="o[0]" :value="o[0]" :label="o[1]" /></el-select></div>
        <div class="field"><label>备注</label><el-input v-model="edit.note" maxlength="300" /></div>
      </div>
      <template #footer>
        <el-button @click="editing = false">取消</el-button>
        <el-button type="primary" @click="save"><AppIcon name="check" :size="14" /> 保存</el-button>
      </template>
    </Modal>

    <!-- 回款弹窗 -->
    <Modal v-if="paying && payOf && pay" :title="'记一笔回款 · ' + payOf.clientName" icon="wallet" @close="paying = false">
      <div class="form-grid">
        <div class="field"><label>到账金额</label><el-input-number v-model="pay.amount" :controls="false" :min="0" style="width: 100%" /></div>
        <div class="field"><label>方式</label><el-select v-model="pay.method"><el-option v-for="o in METHOD_OPTIONS" :key="o.value" :value="o.value" :label="o.text" /></el-select></div>
        <div class="field"><label>到账日</label><el-date-picker v-model="payDate" type="date" value-format="YYYY-MM-DD" /></div>
        <div class="field"><label>备注</label><el-input v-model="pay.note" maxlength="300" /></div>
      </div>
      <div v-if="paysOf(payOf.id).length" class="sec">已记回款</div>
      <div v-for="p in paysOf(payOf.id)" :key="p.id" class="rel">
        <span class="rel-t">{{ formatMd(p.payDate) }} · {{ label({ bank: '银行转账', wechat: '微信', alipay: '支付宝', cash: '现金', other: '其他' }, p.method, '银行转账') }}</span>
        <span class="rel-a">{{ money(Number(p.amount)) }}</span>
        <el-button text class="icon-btn" @click="deletePayment(p)"><AppIcon name="trash" :size="13" /></el-button>
      </div>
      <template #footer>
        <el-button @click="paying = false">取消</el-button>
        <el-button type="primary" @click="addPayment"><AppIcon name="check" :size="14" /> 记到账</el-button>
      </template>
    </Modal>
  </template>
</template>
