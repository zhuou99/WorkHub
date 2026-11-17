/** 后端返回的数据形状（camelCase 线格式）。 */

export interface UserInfo {
  id: string
  userName: string
  name: string
  role: string | null
  appId: string
  token: string
  enabled: boolean
  lastLoginTime: string | null
}

export interface AuthGuardState {
  locked: boolean
  remainingSeconds: number
  failures: number
  remainingTries: number
  defaultPassword: boolean
}

export interface Note {
  id: string
  title: string
  content: string | null
  tags: string | null
  pinned: boolean
  createTime: string | null
  modifyTime: string | null
}

export interface Bookmark {
  id: string
  title: string
  url: string
  site: string | null
  summary: string | null
  content: string | null
  tags: string | null
  status: string | null
  favorite: boolean
  snapshot: string | null
  createTime: string | null
}

export interface Article {
  id: string
  title: string
  summary: string | null
  cover: string | null
  tags: string | null
  projectId: string | null
  content: string | null
  status: string | null
  publishTime: string | null
  createTime: string | null
  modifyTime: string | null
}

export interface Snippet {
  id: string
  title: string
  language: string | null
  code: string | null
  description: string | null
  tags: string | null
  createTime: string | null
}

export interface Client {
  id: string
  name: string
  contact: string | null
  phone: string | null
  email: string | null
  wechat: string | null
  source: string | null
  tags: string | null
  note: string | null
  archived: boolean
  createTime: string | null
}

export interface CommLog {
  id: string
  clientId: string
  type: string | null
  content: string
  happenTime: string | null
  next: string | null
}

export interface Project {
  id: string
  name: string
  clientId: string | null
  status: string | null
  amount: number
  signedDate: string | null
  startDate: string | null
  endDate: string | null
  expireDate: string | null
  contractFile: string | null
  terms: string | null
  description: string | null
  createTime: string | null
  modifyTime: string | null
}

export interface Milestone {
  id: string
  projectId: string
  title: string
  startDate: string | null
  dueDate: string | null
  done: boolean
  doneTime: string | null
  sort: number
}

export interface Task {
  id: string
  title: string
  status: string | null
  projectId: string | null
  dueDate: string | null
  priority: string | null
  note: string | null
  doneTime: string | null
  createTime: string | null
  modifyTime: string | null
}

export interface Invoice {
  id: string
  no: string | null
  clientId: string
  projectId: string | null
  type: string | null
  amount: number
  taxRate: number
  issueDate: string | null
  expectDate: string | null
  status: string | null
  file: string | null
  note: string | null
  /** 以下由服务端现算 */
  paid: number
  due: number
  isOverdue: boolean
  tax: number
  clientName: string
  projectName: string
}

export interface Payment {
  id: string
  invoiceId: string
  amount: number
  payDate: string | null
  method: string | null
  note: string | null
}

export interface Expense {
  id: string
  category: string
  amount: number
  happenDate: string | null
  projectId: string | null
  note: string | null
  createTime: string | null
}

export interface PaymentPlan {
  id: string
  projectId: string | null
  invoiceId: string | null
  title: string
  seq: number
  dueDate: string | null
  amount: number
  status: string | null
  paidDate: string | null
  note: string | null
  isOverdue: boolean
  percentOf: number | null
  projectName: string
}

export interface ToolPref {
  id: string
  toolId: string
  toolName: string | null
  input: string | null
  createTime: string | null
}

export interface Repo {
  id: string
  owner: string
  name: string
  description: string | null
  topics: string | null
  homepage: string | null
  note: string | null
  projectId: string | null
  stars: number
  forks: number
  openIssues: number
  language: string | null
  url: string | null
  syncTime: string | null
  pushedAt: string | null
  lastRelease: string | null
  lastReleaseAt: string | null
}

export interface ReleasePlan {
  id: string
  repoId: string
  tag: string
  planDate: string | null
  notes: string | null
  released: boolean
  releaseDate: string | null
}

export interface ToolOption {
  label: string
  value: string
}

export interface ToolInfo {
  id: string
  name: string
  category: string
  icon: string
  description: string
  kind: string
  options: ToolOption[]
  params: string[]
}

export interface LinkGroup {
  label: string
  count: number
  mode: string
}

export interface DeleteImpact {
  name: string
  groups: LinkGroup[]
  total: number
  hasRefs: boolean
}

export interface RssFeed {
  id: string
  title: string
  url: string
  siteUrl: string | null
  description: string | null
  etag: string | null
  lastFetchAt: string | null
  lastError: string | null
  paused: boolean
  note: string | null
}

export interface RssItem {
  id: string
  feedId: string
  title: string
  url: string | null
  guid: string | null
  author: string | null
  summary: string | null
  publishedAt: string | null
  read: boolean
  starred: boolean
}

export interface SecretInfo {
  key: string
  name: string
  usage: string
  placeholder: string
  required: boolean
  configured: boolean
  readable: boolean
  masked: string
}

export interface PublishLog {
  id: string
  articleId: string | null
  articleTitle: string | null
  channel: string
  result: string | null
  detail: string | null
  createTime: string | null
}

export interface AccountInfo {
  userName: string
  displayName: string | null
  setTime: string | null
  defaultPassword: boolean
}

export interface SearchPart {
  text: string
  mark: boolean
}

export interface SearchHit {
  id: string
  kind: string
  title: string
  url: string
  time: string
  titleParts: SearchPart[]
  parts: SearchPart[]
}

export interface SearchIndex {
  engine: string
  count: number
  source: number
  gap: number
  builtAt: string
}

export interface SearchResult {
  hits: SearchHit[]
  kinds: Record<string, number>
  engine: string
}

export interface BackupInfo {
  name: string
  created: string
  size: string
  folder: string
}

export interface SchedulerOptionsIn {
  enabled: boolean
  rssMinutes: number
  repoMinutes: number
  backupEnabled: boolean
  backupHour: number
}

export interface AuditLog {
  id: string
  time: string | null
  kind: string | null
  action: string | null
  userName: string | null
  ip: string | null
  success: boolean
  detail: string | null
}

export interface ErrorLog {
  id: string
  time: string | null
  level: string | null
  source: string | null
  message: string | null
  detail: string | null
  path: string | null
  userName: string | null
}
