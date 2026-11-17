import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import DashboardView from '@/views/DashboardView.vue'
import ClientsView from '@/views/ClientsView.vue'
import ProjectsView from '@/views/ProjectsView.vue'
import TasksView from '@/views/TasksView.vue'
import InvoicesView from '@/views/InvoicesView.vue'
import PlansView from '@/views/PlansView.vue'
import StatsView from '@/views/StatsView.vue'
import NotesView from '@/views/NotesView.vue'
import ArticlesView from '@/views/ArticlesView.vue'
import SnippetsView from '@/views/SnippetsView.vue'
import BookmarksView from '@/views/BookmarksView.vue'
import PublishLogsView from '@/views/PublishLogsView.vue'
import SearchView from '@/views/SearchView.vue'
import RssView from '@/views/RssView.vue'
import ReposView from '@/views/ReposView.vue'
import SettingsView from '@/views/SettingsView.vue'
import ToolboxView from '@/views/ToolboxView.vue'

/** 尚未铺开的页面先给个占位，避免点到空白页。 */
const Placeholder = (title: string) => ({
  template: `<div class="card"><div class="card-title">${title}</div>
    <div class="empty">这一页还在铺开中，先回工作台看看。</div></div>`,
})
void Placeholder

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/', name: 'home', component: DashboardView },
    { path: '/clients', name: 'clients', component: ClientsView },
    { path: '/projects', name: 'projects', component: ProjectsView },
    { path: '/tasks', name: 'tasks', component: TasksView },
    { path: '/invoices', name: 'invoices', component: InvoicesView },
    { path: '/plans', name: 'plans', component: PlansView },
    { path: '/stats', name: 'stats', component: StatsView },
    { path: '/notes', name: 'notes', component: NotesView },
    { path: '/bookmarks', name: 'bookmarks', component: BookmarksView },
    { path: '/snippets', name: 'snippets', component: SnippetsView },
    { path: '/articles', name: 'articles', component: ArticlesView },
    { path: '/publish', name: 'publish', component: PublishLogsView },
    { path: '/search', name: 'search', component: SearchView },
    { path: '/rss', name: 'rss', component: RssView },
    { path: '/toolbox', name: 'toolbox', component: ToolboxView },
    { path: '/repos', name: 'repos', component: ReposView },
    { path: '/settings', name: 'settings', component: SettingsView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export default router
