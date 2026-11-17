/** 导航结构：一级窄边栏 + 二级子页面列。分组与 C# 的 AppConfig.AddMenuGroup 一致。 */

export interface NavChild {
  name: string
  icon: string
  path: string
}

export interface NavModule {
  key: string
  name: string
  icon: string
  path: string
  children: NavChild[]
}

export const NAV: NavModule[] = [
  { key: 'home', name: '工作台', icon: 'dashboard', path: '/', children: [] },
  { key: 'toolbox', name: '工具箱', icon: 'puzzle', path: '/toolbox', children: [
    { name: '万能工具台', icon: 'puzzle', path: '/toolbox' },
  ] },
  { key: 'library', name: '资料库', icon: 'bookmark', path: '/search', children: [
    { name: '全文检索', icon: 'search', path: '/search' },
    { name: '我的收藏', icon: 'bookmark', path: '/bookmarks' },
    { name: 'RSS 订阅', icon: 'rss', path: '/rss' },
  ] },
  { key: 'studio', name: '创作', icon: 'file-text', path: '/notes', children: [
    { name: '笔记', icon: 'notepad', path: '/notes' },
    { name: '代码片段', icon: 'code', path: '/snippets' },
    { name: '文章', icon: 'file-text', path: '/articles' },
    { name: '发布记录', icon: 'send', path: '/publish' },
  ] },
  { key: 'crm', name: '客户', icon: 'users', path: '/clients', children: [
    { name: '客户', icon: 'users', path: '/clients' },
  ] },
  { key: 'projects', name: '项目', icon: 'package', path: '/projects', children: [
    { name: '项目列表', icon: 'package', path: '/projects' },
    { name: '任务看板', icon: 'kanban', path: '/tasks' },
    { name: '开源项目', icon: 'git-branch', path: '/repos' },
  ] },
  { key: 'finance', name: '财务', icon: 'receipt', path: '/invoices', children: [
    { name: '发票台账', icon: 'receipt', path: '/invoices' },
    { name: '收支统计', icon: 'bar-chart', path: '/stats' },
    { name: '回款计划', icon: 'calendar-clock', path: '/plans' },
  ] },
  { key: 'settings', name: '设置', icon: 'cog', path: '/settings', children: [
    { name: '偏好设置', icon: 'cog', path: '/settings' },
  ] },
]

/** 根据当前路由找到所属模块。 */
export function moduleOf(path: string): NavModule | null {
  if (path === '/' || path === '/login') return NAV[0]
  for (const m of NAV) {
    if (m.children.some((c) => c.path === path)) return m
  }
  return null
}
