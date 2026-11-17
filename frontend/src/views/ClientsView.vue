<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Client, CommLog, DeleteImpact, Invoice, Payment, Project } from '@/types'
import { COMM_TYPE, formatDateTime, formatMd, INVOICE_STATUS, label, money, PROJECT_STATUS, SOURCE } from '@/utils'

const loading = ref(true)
const error = ref('')
const clients = ref<Client[]>([])
const logs = ref<CommLog[]>([])
const projects = ref<Project[]>([])
const invoices = ref<Invoice[]>([])
const payments = ref<Payment[]>([])

const kw = ref('')
const state = ref('all')

const editing = ref(false)
const isNew = ref(false)
const edit = ref<Client | null>(null)

const viewing = ref(false)
const view = ref<Client | null>(null)
const log = ref<CommLog | null>(null)
const logLimit = ref(20)

const killing = ref(false)
const kill = ref<Client | null>(null)
const killBusy = ref(false)
const killDetach = ref(true)
const impact = ref<DeleteImpact | null>(null)

const STATE_OPTIONS = [
  { value: 'all', text: '全部客户' },
  { value: 'active', text: '合作中' },
  { value: 'archived', text: '已归档' },
]

const SOURCE_OPTIONS = [
  { value: '', text: '未知' },
  { value: 'friend', text: '朋友介绍' },
  { value: 'referral', text: '老客户转介' },
  { value: 'platform', text: '平台接单' },
  { value: 'other', text: '其他' },
]

const COMM_TYPE_OPTIONS = [
  { value: 'wechat', text: '微信' },
  { value: 'phone', text: '电话' },
  { value: 'meet', text: '见面' },
  { value: 'mail', text: '邮件' },
  { value: 'other', text: '其他' },
]

function match(c: Client, k: string): boolean {
  if (!k.trim()) return true
  const needle = k.trim().toLowerCase()
  return [c.name, c.contact, c.phone, c.email, c.wechat, c.tags, c.note]
    .some((v) => v && v.toLowerCase().includes(needle))
}

const shown = computed(() =>
  clients.value.filter((c) => {
    if (state.value === 'archived') { if (!c.archived) return false }
    else if (state.value === 'active') { if (c.archived) return false }
    return match(c, kw.value)
  }),
)

const stats = computed(() => {
  const now = new Date()
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
  return [
    { icon: 'users', color: '#4f7cff', value: clients.value.filter((c) => !c.archived).length, label: '合作中客户' },
    { icon: 'briefcase', color: '#07c160', value: projects.value.filter((p) => p.status !== 'done').length, label: '在跑项目' },
    { icon: 'message-circle', color: '#7c5cff', value: logs.value.filter((l) => new Date(l.happenTime ?? 0) >= monthStart).length, label: '本月沟通' },
    { icon: 'wallet', color: '#f5a623', value: money(invoices.value.reduce((s, iv) => s + (Number(iv.due) || 0), 0)), label: '待收金额' },
  ]
})

function logsOf(id: string): CommLog[] {
  return logs.value.filter((l) => l.clientId === id).sort((a, b) => String(b.happenTime).localeCompare(String(a.happenTime)))
}
function logsShown(id: string): CommLog[] { return logsOf(id).slice(0, logLimit.value) }
function projOf(id: string): Project[] { return projects.value.filter((p) => p.clientId === id) }
function invoicesOf(id: string): Invoice[] { return invoices.value.filter((iv) => iv.clientId === id) }
function lastLog(id: string): CommLog | undefined { return logsOf(id)[0] }
function tagList(c: Client): string[] {
  return c.tags ? [...new Set(c.tags.split(',').map((t) => t.trim()).filter(Boolean))] : []
}
const show = (s: string | null) => s || '—'

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [c, l, p, iv, pay] = await Promise.all([
      api.get<Client[]>('/api/clients'),
      api.get<CommLog[]>('/api/clients/logs'),
      api.get<Project[]>('/api/projects'),
      api.get<Invoice[]>('/api/finance/invoices'),
      api.get<Payment[]>('/api/finance/payments'),
    ])
    clients.value = c
    logs.value = l
    projects.value = p
    invoices.value = iv
    payments.value = pay
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载客户台账失败'
  } finally {
    loading.value = false
  }
}

function openAdd() {
  edit.value = { id: '', name: '', contact: null, phone: null, email: null, wechat: null, source: null, tags: null, note: null, archived: false, createTime: null }
  isNew.value = true
  editing.value = true
}
function openEdit(c: Client) { edit.value = { ...c }; isNew.value = false; editing.value = true }

async function save() {
  if (!edit.value || !edit.value.name.trim()) return
  edit.value.name = edit.value.name.trim()
  await api.post<Client>('/api/clients', edit.value)
  editing.value = false
  await load()
}

function openView(c: Client) {
  view.value = c
  log.value = { id: '', clientId: c.id, type: 'wechat', content: '', happenTime: new Date().toISOString(), next: null }
  logLimit.value = 20
  viewing.value = true
}

async function saveLog() {
  if (!log.value || !log.value.content.trim()) return
  log.value.content = log.value.content.trim()
  await api.post<CommLog>('/api/clients/logs', log.value)
  logs.value = await api.get<CommLog[]>('/api/clients/logs')
  log.value = { id: '', clientId: view.value!.id, type: 'wechat', content: '', happenTime: new Date().toISOString(), next: null }
}

async function deleteLog(l: CommLog) {
  await api.del(`/api/clients/logs/${l.id}`)
  logs.value = logs.value.filter((x) => x.id !== l.id)
}

async function openKill(c: Client) {
  kill.value = c
  impact.value = await api.get<DeleteImpact>(`/api/clients/delete-impact/${c.id}`)
  killDetach.value = true
  killing.value = true
}

async function doDelete() {
  if (!kill.value || killBusy.value) return
  killBusy.value = true
  try {
    await api.del(`/api/clients/${kill.value.id}?detach=${killDetach.value}`)
    killing.value = false
    kill.value = null
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  } finally {
    killBusy.value = false
  }
}

async function doArchive() {
  if (!kill.value || killBusy.value) return
  killBusy.value = true
  try {
    await api.post<Client>('/api/clients', { ...kill.value, archived: true })
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
        <div class="page-greet">客户</div>
        <div class="page-sub">一人公司的客户台账：联系人、沟通留痕，项目与发票都挂在客户上，一处看全。</div>
      </div>
      <div class="page-actions">
        <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新增客户</button>
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
        <input v-model="kw" class="input" style="padding-left: 32px" placeholder="搜索名称 / 联系人 / 电话 / 微信 / 标签" />
        <AppIcon name="search" :size="15" style="position: absolute; left: 10px; top: 10px; color: var(--text-muted)" />
      </div>
      <select v-model="state" class="input" style="width: 120px">
        <option v-for="o in STATE_OPTIONS" :key="o.value" :value="o.value">{{ o.text }}</option>
      </select>
    </div>

    <div v-if="!shown.length" class="page-empty">
      <p>{{ kw.trim() || state !== 'all' ? '没有符合条件的客户。' : '还没有客户。有了第一个客户，项目、发票、沟通记录才串得起来。' }}</p>
      <button class="btn primary" @click="openAdd"><AppIcon name="plus" :size="14" /> 新增客户</button>
    </div>

    <div v-else class="card-grid">
      <div v-for="c in shown" :key="c.id" class="ent-card">
        <div class="ent-top">
          <b class="ent-name" @click="openView(c)">{{ c.name }}</b>
          <span v-if="c.archived" class="pill st-hold">已归档</span>
          <span class="pill st-talking">{{ label(SOURCE, c.source, '未知') }}</span>
        </div>
        <div v-if="c.contact || c.phone" class="ent-line"><AppIcon name="user" :size="12" /> {{ c.contact }}{{ c.phone ? ' · ' + c.phone : '' }}</div>
        <div v-if="c.wechat || c.email" class="ent-line"><AppIcon name="mail" :size="12" /> {{ c.wechat || c.email }}</div>
        <div class="ent-line muted">
          <template v-if="lastLog(c.id)">{{ formatMd(lastLog(c.id)!.happenTime) }} {{ lastLog(c.id)!.content }}</template>
          <template v-else>还没有沟通记录</template>
        </div>
        <div v-if="tagList(c).length" class="ent-tags">
          <span v-for="t in tagList(c)" :key="t" class="tag">{{ t }}</span>
        </div>
        <div class="ent-acts">
          <button class="btn" style="height: 28px; font-size: 12px" @click="openView(c)"><AppIcon name="folder" :size="13" /> 档案 · {{ projOf(c.id).length }}</button>
          <button class="btn" style="height: 28px; font-size: 12px" @click="openView(c)"><AppIcon name="message-circle" :size="13" /> 记一笔</button>
          <button class="btn" style="height: 28px; font-size: 12px" @click="openEdit(c)"><AppIcon name="edit" :size="13" /></button>
          <button class="btn" style="height: 28px; font-size: 12px; color: var(--danger-color)" @click="openKill(c)"><AppIcon name="trash" :size="13" /></button>
        </div>
      </div>
    </div>

    <!-- 档案弹窗 -->
    <Modal v-if="viewing && view" :title="view.name + ' · 档案'" icon="folder" wide @close="viewing = false">
      <div class="kv">
        <div><i>联系人</i>{{ show(view.contact) }}</div>
        <div><i>电话</i>{{ show(view.phone) }}</div>
        <div><i>微信</i>{{ show(view.wechat) }}</div>
        <div><i>邮箱</i>{{ show(view.email) }}</div>
        <div><i>来源</i>{{ label(SOURCE, view.source, '未知') }}</div>
        <div><i>累计开票</i>{{ money(invoicesOf(view.id).reduce((s, iv) => s + (Number(iv.amount) || 0), 0)) }} <span class="muted">待收 {{ money(invoicesOf(view.id).reduce((s, iv) => s + (Number(iv.due) || 0), 0)) }}</span></div>
      </div>
      <div v-if="view.note" class="ent-note" style="margin-top: 14px">{{ view.note }}</div>

      <div class="rel-grid">
        <div>
          <div class="sec">项目 {{ projOf(view.id).length }}</div>
          <div v-if="!projOf(view.id).length" class="muted" style="font-size: 13px">还没有项目。</div>
          <div v-for="p in projOf(view.id)" :key="p.id" class="rel">
            <span class="pill" :class="'st-' + (p.status || 'talking')">{{ label(PROJECT_STATUS, p.status, '洽谈中') }}</span>
            <span class="rel-t">{{ p.name }}</span>
            <span class="rel-a">{{ money(Number(p.amount)) }}</span>
          </div>
        </div>
        <div>
          <div class="sec">发票 {{ invoicesOf(view.id).length }}</div>
          <div v-if="!invoicesOf(view.id).length" class="muted" style="font-size: 13px">还没有开票记录。</div>
          <div v-for="iv in invoicesOf(view.id)" :key="iv.id" class="rel">
            <span class="pill" :class="'st-' + (iv.status || 'opened')">{{ label(INVOICE_STATUS, iv.status, '已开票') }}</span>
            <span class="rel-t">{{ iv.no || '未填票号' }} · {{ iv.issueDate ? iv.issueDate.slice(0, 10) : '未开票' }}</span>
            <span class="rel-a">{{ (Number(iv.due) || 0) > 0 ? '待收 ' + money(Number(iv.due)) : '已收满' }}</span>
          </div>
        </div>
      </div>

      <div class="sec">沟通记录</div>
      <div v-if="log" class="form-grid" style="margin-bottom: 14px">
        <div class="field">
          <select v-model="log.type" class="input">
            <option v-for="o in COMM_TYPE_OPTIONS" :key="o.value" :value="o.value">{{ o.text }}</option>
          </select>
        </div>
        <div class="field">
          <input v-model="log.happenTime" class="input" type="datetime-local" />
        </div>
        <div class="field full">
          <textarea v-model="log.content" class="input" rows="2" maxlength="1000" placeholder="沟通内容" />
        </div>
        <div class="field full">
          <input v-model="log.next" class="input" maxlength="500" placeholder="下一步要做的事（可选）" />
        </div>
        <div class="field full" style="text-align: right">
          <button class="btn primary" @click="saveLog"><AppIcon name="check" :size="14" /> 记一笔</button>
        </div>
      </div>
      <ul class="timeline-log">
        <li v-for="l in logsShown(view.id)" :key="l.id">
          <div class="tl-ico"><AppIcon :name="l.type === 'phone' ? 'phone' : l.type === 'meet' ? 'users' : l.type === 'mail' ? 'mail' : 'message-circle'" :size="13" /></div>
          <div class="tl-body">
            <div class="tl-head">
              <span>{{ formatDateTime(l.happenTime) }}</span>
              <span class="pill st-talking">{{ label(COMM_TYPE, l.type, '微信') }}</span>
              <button class="icon-btn" type="button" style="margin-left: auto" @click="deleteLog(l)"><AppIcon name="trash" :size="13" /></button>
            </div>
            <div class="tl-content">{{ l.content }}</div>
            <div v-if="l.next" class="tl-next">下一步：{{ l.next }}</div>
          </div>
        </li>
      </ul>
      <div v-if="logsOf(view.id).length > logLimit" style="text-align: center; margin-top: 10px">
        <button class="btn" @click="logLimit += 20">更多记录</button>
      </div>
    </Modal>

    <!-- 编辑弹窗 -->
    <Modal v-if="editing && edit" :title="isNew ? '新增客户' : '编辑客户'" icon="users" @close="editing = false">
      <div class="form-grid">
        <div class="field full">
          <label>客户名称 <span class="req">*</span></label>
          <input v-model="edit.name" class="input" maxlength="100" />
        </div>
        <div class="field"><label>联系人</label><input v-model="edit.contact" class="input" maxlength="60" /></div>
        <div class="field"><label>电话</label><input v-model="edit.phone" class="input" maxlength="30" /></div>
        <div class="field"><label>微信</label><input v-model="edit.wechat" class="input" maxlength="50" /></div>
        <div class="field"><label>邮箱</label><input v-model="edit.email" class="input" maxlength="80" /></div>
        <div class="field"><label>来源</label>
          <select v-model="edit.source" class="input">
            <option v-for="o in SOURCE_OPTIONS" :key="o.value" :value="o.value">{{ o.text }}</option>
          </select>
        </div>
        <div class="field"><label>标签</label><input v-model="edit.tags" class="input" maxlength="200" placeholder="逗号分隔" /></div>
        <div class="field full"><label>备注</label><textarea v-model="edit.note" class="input" rows="3" maxlength="1000" /></div>
      </div>
      <template #footer>
        <button class="btn" @click="editing = false">取消</button>
        <button class="btn primary" @click="save"><AppIcon name="check" :size="14" /> 保存</button>
      </template>
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
        <div v-else class="impact-none">这个客户下面没有挂着项目、发票或沟通记录，删了不留尾巴。</div>
      </div>
      <div class="field" style="margin-bottom: 12px">
        <label style="display: flex; align-items: center; gap: 8px; font-weight: 500">
          <input v-model="killDetach" type="checkbox" /> 解绑并保留项目 / 发票（否则原样保留，显示「客户已删除」）
        </label>
      </div>
      <template #footer>
        <button class="btn" @click="killing = false">取消</button>
        <button class="btn" :disabled="killBusy" @click="doArchive"><AppIcon name="folder" :size="14" /> 归档（推荐）</button>
        <button class="btn" style="background: var(--danger-color); border-color: var(--danger-color); color: #fff" :disabled="killBusy" @click="doDelete">
          <AppIcon name="trash" :size="14" /> 删除
        </button>
      </template>
    </Modal>
  </template>
</template>
