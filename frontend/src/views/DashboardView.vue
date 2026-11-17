<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { api } from '@/api'
import type {
  Bookmark, Client, Invoice, Note, Payment, PaymentPlan, Project, ReleasePlan,
  Repo, Snippet, Task, ToolInfo, ToolPref, UserInfo,
} from '@/types'

const props = defineProps<{ user: UserInfo | null }>()

const loading = ref(true)
const error = ref('')
const quick = ref('')

const notes = ref<Note[]>([])
const marks = ref<Bookmark[]>([])
const snippets = ref<Snippet[]>([])
const projects = ref<Project[]>([])
const tasks = ref<Task[]>([])
const invoices = ref<Invoice[]>([])
const payments = ref<Payment[]>([])
const plans = ref<PaymentPlan[]>([])
const clients = ref<Client[]>([])
const repos = ref<Repo[]>([])
const releasePlans = ref<ReleasePlan[]>([])
const toolPrefs = ref<ToolPref[]>([])

/* ---------- 派生计算（口径与 C# 的 Home.razor.cs 一致） ---------- */

const today = () => new Date()

const isSameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()

const dateOf = (value: string | null | undefined): Date | null => {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

const isHot = (t: Task) => {
  if (t.status === 'done') return false
  const due = dateOf(t.dueDate)
  return due !== null && due.getTime() <= today().getTime()
}

const taskHeat = computed(() => tasks.value.filter(isHot).length)

const taskFoot = computed(() => {
  const now = today()
  const late = tasks.value.filter((t) => {
    const due = dateOf(t.dueDate)
    return t.status !== 'done' && due !== null && due.getTime() < now.getTime()
  }).length
  const dueToday = tasks.value.filter((t) => {
    const due = dateOf(t.dueDate)
    return t.status !== 'done' && due !== null && isSameDay(due, now)
  }).length
  return late > 0 ? `逾期 ${late} · 今日 ${dueToday}` : `今日到期 ${dueToday}`
})

const monthBilled = computed(() => {
  const now = today()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  return invoices.value
    .filter((iv) => iv.status !== 'void' && dateOf(iv.issueDate)! && dateOf(iv.issueDate)! >= start)
    .reduce((sum, iv) => sum + Number(iv.amount ?? 0), 0)
})

const totalDue = computed(() =>
  invoices.value.reduce((sum, iv) => sum + Number(iv.due ?? 0), 0),
)

const unread = computed(() => marks.value.filter((b) => b.status === 'unread').length)

const recentNotes = computed(() => notes.value.slice(0, 5))
const recentMarks = computed(() => marks.value.slice(0, 5))

/** 按最近使用时间聚合工具记录，取前 8 个还能对上目录的工具。 */
const favoriteTools = computed<ToolInfo[]>(() => {
  const last = new Map<string, string>()
  for (const pref of toolPrefs.value) {
    const current = last.get(pref.toolId)
    if (!current || (pref.createTime ?? '') > current) last.set(pref.toolId, pref.createTime ?? '')
  }
  return [...last.entries()]
    .sort((a, b) => (b[1] ?? '').localeCompare(a[1] ?? ''))
    .map(([id]) => ALL_TOOLS.find((t) => t.id === id))
    .filter((t): t is ToolInfo => Boolean(t))
    .slice(0, 8)
})

const ALL_TOOLS: ToolInfo[] = []

interface Alert { kind: 'danger' | 'warn'; tag: string; text: string; right: string }

const alerts = computed<Alert[]>(() => {
  const list: Alert[] = []
  const now = today()

  for (const t of tasks.value.filter(isHot).sort((a, b) =>
    String(a.dueDate).localeCompare(String(b.dueDate))).slice(0, 3)) {
    const due = dateOf(t.dueDate)!
    const late = due.getTime() < now.getTime()
    list.push({
      kind: late ? 'danger' : 'warn',
      tag: late ? '逾期' : '今日',
      text: t.title,
      right: projName(t.projectId),
    })
  }
  for (const iv of invoices.value.filter((x) => x.isOverdue).slice(0, 2)) {
    list.push({
      kind: 'danger', tag: '欠款',
      text: `${iv.clientName} 待收 ${money0(Number(iv.due))}`,
      right: iv.expectDate ? formatMd(iv.expectDate) : '',
    })
  }
  for (const p of plans.value.filter((x) => x.isOverdue).sort((a, b) =>
    String(a.dueDate).localeCompare(String(b.dueDate))).slice(0, 2)) {
    list.push({
      kind: 'danger', tag: '期次',
      text: `${p.projectName} 第 ${p.seq} 期 ${p.title} ${money0(Number(p.amount))}`,
      right: p.dueDate ? formatMd(p.dueDate) : '',
    })
  }
  for (const p of projects.value.filter((x) => {
    const e = dateOf(x.expireDate)
    return x.status !== 'done' && e !== null && e.getTime() <= now.getTime() + 30 * 86400000
  }).slice(0, 2)) {
    list.push({
      kind: 'warn', tag: '维护', text: p.name,
      right: p.expireDate ? `到期 ${formatMd(p.expireDate)}` : '',
    })
  }
  return list.slice(0, 6)
})

const projName = (id: string | null) =>
  projects.value.find((p) => p.id === id)?.name ?? '未挂项目'

const ROADMAP = [
  { title: 'M0 · 地基', desc: '登录、菜单壳、建表管线。' },
  { title: 'M1 · 高频自用', desc: '工具箱、剪藏、笔记与代码片段。' },
  { title: 'M2 · 创作发布', desc: '文章写作 + 博客园/公众号导出发布闭环。' },
  { title: 'M3 · 生意管理', desc: '客户、项目与里程碑、任务看板、发票回款与收支统计。' },
  { title: 'M4 · 增强', desc: '密钥加密、百度翻译、GitHub 开源跟踪、RSS 订阅、全文检索、本周小结、一键备份。' },
]

/* ---------- 格式化 ---------- */

const money0 = (v: number) =>
  '¥' + Math.round(v).toLocaleString('zh-CN')

const money2 = (v: number) =>
  '¥' + v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const formatMd = (value: string) => {
  const d = dateOf(value)
  if (!d) return ''
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const formatTime = (value: string | null) => {
  const d = dateOf(value)
  if (!d) return ''
  return isSameDay(d, today())
    ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    : formatMd(value!)
}

const greeting = computed(() => {
  const h = today().getHours()
  const word = h < 6 ? '夜深了' : h < 11 ? '早上好' : h < 14 ? '中午好' : h < 18 ? '下午好' : '晚上好'
  return `${word}，${props.user?.name ?? ''}`
})

const dateLine = computed(() => {
  const now = today()
  const week = ['日', '一', '二', '三', '四', '五', '六'][now.getDay()]
  return `${now.getMonth() + 1} 月 ${now.getDate()} 日 星期${week} · 数据都在本机，安心用。`
})

/* ---------- 载入 ---------- */

async function load() {
  loading.value = true
  error.value = ''
  try {
    // 这些查询互不依赖，一起发；任一失败由下面的 catch 整块降级
    const [n, b, s, p, t, iv, pay, pl, cl, rb, prefs, tools] = await Promise.all([
      api.get<Note[]>('/api/notes'),
      api.get<Bookmark[]>('/api/bookmarks'),
      api.get<Snippet[]>('/api/snippets'),
      api.get<Project[]>('/api/projects'),
      api.get<Task[]>('/api/tasks'),
      api.get<Invoice[]>('/api/finance/invoices'),
      api.get<Payment[]>('/api/finance/payments'),
      api.get<PaymentPlan[]>('/api/finance/plans'),
      api.get<Client[]>('/api/clients'),
      api.get<{ repos: Repo[]; plans: ReleasePlan[] }>('/api/repos/board'),
      api.get<ToolPref[]>('/api/tools/prefs'),
      api.get<ToolInfo[]>('/api/tools'),
    ])
    notes.value = n
    marks.value = b
    snippets.value = s
    projects.value = p
    tasks.value = t
    invoices.value = iv
    payments.value = pay
    plans.value = pl
    clients.value = cl
    repos.value = [...rb.repos].sort((x, y) => y.stars - x.stars)
    releasePlans.value = rb.plans
    toolPrefs.value = prefs
    ALL_TOOLS.length = 0
    ALL_TOOLS.push(...tools)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载工作台失败'
  } finally {
    loading.value = false
  }
}

/** 快记：回车进笔记收件箱。 */
async function quickAdd() {
  const text = quick.value.trim()
  if (!text) return
  await api.post('/api/notes', {
    title: text.length > 30 ? text.slice(0, 30) + '…' : text,
    content: text,
    tags: '收件箱',
  })
  quick.value = ''
  notes.value = await api.get<Note[]>('/api/notes')
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading"><div class="spinner" /></div>

  <div v-else-if="error" class="card">
    <div class="empty">加载工作台失败：{{ error }}</div>
    <button class="btn" style="margin-top: 12px" @click="load">重试</button>
  </div>

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">{{ greeting }}</div>
        <div class="page-sub">{{ dateLine }}</div>
      </div>
      <div class="page-actions">
        <div class="quick">
          <div class="quick-in">
            <AppIcon name="zap" :size="15" />
            <input
              v-model="quick"
              class="input"
              placeholder="快记：想到什么先丢这里，回车进笔记收件箱"
              @keyup.enter="quickAdd"
            />
          </div>
          <button class="btn primary" :disabled="!quick.trim()" @click="quickAdd">
            <AppIcon name="plus" :size="14" /> 记下
          </button>
        </div>
      </div>
    </div>

    <!-- 统计卡 -->
    <div class="stat-grid">
      <div class="stat-card" @click="$router.push('/notes')">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ notes.length }}</div>
            <div class="stat-label">笔记</div>
          </div>
          <div class="stat-icon"><AppIcon name="notepad" :size="15" /></div>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/bookmarks')">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ unread }}</div>
            <div class="stat-label">未读收藏</div>
          </div>
          <div class="stat-icon"><AppIcon name="bookmark" :size="15" /></div>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/snippets')">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ snippets.length }}</div>
            <div class="stat-label">代码片段</div>
          </div>
          <div class="stat-icon"><AppIcon name="code" :size="15" /></div>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/toolbox')">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ favoriteTools.length }}</div>
            <div class="stat-label">用过工具</div>
          </div>
          <div class="stat-icon"><AppIcon name="puzzle" :size="15" /></div>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/projects')">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ projects.filter((p) => p.status !== 'done').length }}</div>
            <div class="stat-label">在跑项目</div>
          </div>
          <div class="stat-icon"><AppIcon name="briefcase" :size="15" /></div>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/tasks')">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ taskHeat }}</div>
            <div class="stat-label">今日要办的任务</div>
            <div class="stat-foot">{{ taskFoot }}</div>
          </div>
          <div class="stat-icon"><AppIcon name="kanban" :size="15" /></div>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/invoices')">
        <div class="stat-top">
          <div>
            <div class="stat-value money">{{ money2(monthBilled) }}</div>
            <div class="stat-label">本月开票</div>
          </div>
          <div class="stat-icon"><AppIcon name="receipt" :size="15" /></div>
        </div>
      </div>

      <div class="stat-card" @click="$router.push('/invoices')">
        <div class="stat-top">
          <div>
            <div class="stat-value money warn">{{ money2(totalDue) }}</div>
            <div class="stat-label">待收金额</div>
          </div>
          <div class="stat-icon"><AppIcon name="wallet" :size="15" /></div>
        </div>
      </div>
    </div>

    <!-- 两列 -->
    <div class="cols">
      <div class="col">
        <div class="card">
          <div class="card-title">
            <AppIcon name="alert-circle" :size="16" /> 今天要盯的
            <button class="card-more" @click="$router.push('/tasks')">看板 <AppIcon name="chevron-right" :size="13" /></button>
          </div>
          <div v-if="!alerts.length" class="empty">没有逾期任务、逾期发票和到期维护，清净。</div>
          <div v-for="(a, i) in alerts" :key="i" class="row">
            <span class="pill" :class="a.kind">{{ a.tag }}</span>
            <span class="row-t">{{ a.text }}</span>
            <span class="row-d">{{ a.right }}</span>
          </div>
        </div>

        <div class="card">
          <div class="card-title">
            <AppIcon name="notepad" :size="16" /> 最近笔记
            <button class="card-more" @click="$router.push('/notes')">全部 <AppIcon name="chevron-right" :size="13" /></button>
          </div>
          <div v-if="!recentNotes.length" class="empty">还没有笔记，用上面的快记框记第一条。</div>
          <div v-for="n in recentNotes" :key="n.id" class="row" @click="$router.push('/notes')">
            <span v-if="n.pinned" class="pin">置顶</span>
            <span class="row-t">{{ n.title }}</span>
            <span class="row-d">{{ formatTime(n.createTime) }}</span>
          </div>
        </div>

        <div class="card">
          <div class="card-title">
            <AppIcon name="bookmark" :size="16" /> 最新收藏
            <button class="card-more" @click="$router.push('/bookmarks')">全部 <AppIcon name="chevron-right" :size="13" /></button>
          </div>
          <div v-if="!recentMarks.length" class="empty">还没有剪藏，去「我的收藏」贴一个链接试试。</div>
          <div v-for="b in recentMarks" :key="b.id" class="row" @click="$router.push('/bookmarks')">
            <span class="dot" :class="{ read: b.status !== 'unread' }" />
            <span class="row-t">{{ b.title }}</span>
            <span class="row-d">{{ b.site || formatTime(b.createTime) }}</span>
          </div>
        </div>
      </div>

      <div class="col">
        <div class="card">
          <div class="card-title">
            <AppIcon name="puzzle" :size="16" /> 常用工具
            <button class="card-more" @click="$router.push('/toolbox')">全部 <AppIcon name="chevron-right" :size="13" /></button>
          </div>
          <div v-if="!favoriteTools.length" class="empty">还没用过工具，去「万能工具台」开个头。</div>
          <div v-else class="tools">
            <div v-for="t in favoriteTools" :key="t.id" class="tool" @click="$router.push('/toolbox')">
              <AppIcon :name="t.icon" :size="15" /><span>{{ t.name }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">
            <AppIcon name="git-branch" :size="16" /> 开源动态
            <button class="card-more" @click="$router.push('/repos')">仓库 <AppIcon name="chevron-right" :size="13" /></button>
          </div>
          <div v-if="!repos.length" class="empty">还没镜像 GitHub 仓库，去「开源项目」填 owner/name。</div>
          <div v-for="r in repos.slice(0, 4)" :key="r.id" class="row" @click="$router.push('/repos')">
            <span class="pill">{{ r.stars.toLocaleString('zh-CN') }} ★</span>
            <span class="row-t">{{ r.owner }}/{{ r.name }}</span>
            <span class="row-d">{{ r.syncTime ? formatMd(r.syncTime) + ' 同步' : '未同步' }}</span>
          </div>
          <div v-if="releasePlans.filter((p) => !p.released).length" class="empty">
            还有 {{ releasePlans.filter((p) => !p.released).length }} 个版本没发。
          </div>
        </div>

        <div class="card">
          <div class="card-title"><AppIcon name="rocket" :size="16" /> 路线图</div>
          <ul class="timeline">
            <li v-for="m in ROADMAP" :key="m.title">
              <div class="timeline-t">{{ m.title }}</div>
              <div class="timeline-d">{{ m.desc }}</div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </template>
</template>
