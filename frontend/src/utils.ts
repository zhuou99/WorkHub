/** 前端共用的格式化与标签映射（与后端 app/common/labels.py 口径一致）。 */

export function dateOf(value: string | null | undefined): Date | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

export function today(): Date {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
}

export function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

export function formatMd(value: string | null | undefined): string {
  const d = dateOf(value)
  if (!d) return ''
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function formatDate(value: string | null | undefined): string {
  const d = dateOf(value)
  if (!d) return ''
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function formatDateTime(value: string | null | undefined): string {
  const d = dateOf(value)
  if (!d) return ''
  return formatDate(value!) + ' ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0')
}

export function money(v: number): string {
  return '¥' + (Number(v) || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function money0(v: number): string {
  return '¥' + Math.round(Number(v) || 0).toLocaleString('zh-CN')
}

/* ---------- 状态标签（与后端 Labels 一致） ---------- */

export const TASK_COLUMNS = ['todo', 'doing', 'done', 'hold'] as const

export const TASK_STATUS: Record<string, string> = {
  todo: '待办', doing: '进行中', done: '已完成', hold: '搁置',
}

export const PRIORITY: Record<string, string> = {
  high: '急', normal: '普通', low: '不急',
}

export const PROJECT_STATUS: Record<string, string> = {
  talking: '洽谈中', active: '进行中', accept: '验收中', maintain: '维护期', done: '已完结',
}

export const SOURCE: Record<string, string> = {
  friend: '朋友介绍', referral: '老客户转介', platform: '平台接单', other: '其他',
}

export const COMM_TYPE: Record<string, string> = {
  wechat: '微信', phone: '电话', meet: '见面', mail: '邮件', other: '其他',
}

export const INVOICE_STATUS: Record<string, string> = {
  opened: '已开票', sent: '已寄出', paid: '已回款', void: '作废',
}

export function label(map: Record<string, string>, key: string | null | undefined, fallback: string): string {
  if (!key) return fallback
  return map[key] ?? fallback
}
