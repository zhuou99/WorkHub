<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import Modal from '@/components/Modal.vue'
import { api } from '@/api'
import type { Project, Task } from '@/types'
import { dateOf, formatMd, isSameDay, label, PRIORITY, TASK_COLUMNS, TASK_STATUS, today } from '@/utils'

const loading = ref(true)
const error = ref('')
const tasks = ref<Task[]>([])
const projects = ref<Project[]>([])
const projectId = ref('')

/* 拖拽状态 */
const drag = ref<Task | null>(null)
const over = ref<string | null>(null)

/* 编辑弹窗 */
const editing = ref(false)
const isNew = ref(false)
const edit = ref<Task | null>(null)

const COLUMNS = TASK_COLUMNS

/* 优先级胶囊 → el-tag type 映射 */
type TagType = 'info' | 'primary' | 'success' | 'warning' | 'danger'

const PRIORITY_TAG: Record<string, TagType> = { high: 'danger', normal: 'primary', low: 'info' }

const stats = computed(() => {
  const now = today()
  const isLate = (t: Task) => t.status !== 'done' && dateOf(t.dueDate) !== null && dateOf(t.dueDate)! < now
  const isToday = (t: Task) => t.status !== 'done' && dateOf(t.dueDate) !== null && isSameDay(dateOf(t.dueDate)!, now)
  return [
    { icon: 'kanban', color: '#4f7cff', value: tasks.value.filter((t) => t.status === 'todo').length, label: '待办' },
    { icon: 'loader', color: '#07c160', value: tasks.value.filter((t) => t.status === 'doing').length, label: '进行中' },
    { icon: 'calendar-check', color: '#7c5cff', value: tasks.value.filter(isToday).length, label: '今日到期' },
    { icon: 'alert-circle', color: '#f5544c', value: tasks.value.filter(isLate).length, label: '已逾期' },
  ]
})

function inColumn(key: string): Task[] {
  return tasks.value
    .filter((t) => t.status === key && (!projectId.value || t.projectId === projectId.value))
    .sort((a, b) => {
      const ad = dateOf(a.dueDate)
      const bd = dateOf(b.dueDate)
      if (ad === null && bd !== null) return -1
      if (ad !== null && bd === null) return 1
      if (ad && bd && ad.getTime() !== bd.getTime()) return ad.getTime() - bd.getTime()
      return (a.priority === 'high' ? 0 : 1) - (b.priority === 'high' ? 0 : 1)
    })
}

function isLate(t: Task): boolean {
  const now = today()
  return t.status !== 'done' && dateOf(t.dueDate) !== null && dateOf(t.dueDate)! < now
}

function projName(id: string | null): string {
  if (!id) return ''
  return projects.value.find((p) => p.id === id)?.name ?? '项目已删除'
}

const projectFilter = computed(() => projects.value.map((p) => ({ value: p.id, text: p.name })))

const projectOptions = computed(() => {
  const options = projects.value.filter((p) => p.status !== 'done').map((p) => ({ value: p.id, text: p.name }))
  if (edit.value?.projectId && !projects.value.some((p) => p.id === edit.value!.projectId && p.status !== 'done')) {
    const p = projects.value.find((x) => x.id === edit.value!.projectId)
    if (p) options.push({ value: p.id, text: p.name + '（已完结）' })
  }
  return options
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [t, p] = await Promise.all([api.get<Task[]>('/api/tasks'), api.get<Project[]>('/api/projects')])
    tasks.value = t
    projects.value = p
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载任务看板失败'
  } finally {
    loading.value = false
  }
}

function openAdd(status = 'todo') {
  edit.value = { id: '', title: '', status, projectId: projectId.value || null, dueDate: null, priority: 'normal', note: null, doneTime: null, createTime: null, modifyTime: null }
  isNew.value = true
  editing.value = true
}

function openEdit(t: Task) {
  edit.value = { ...t }
  isNew.value = false
  editing.value = true
}

async function save() {
  if (!edit.value || !edit.value.title.trim()) return
  const payload = edit.value
  payload.title = payload.title.trim()
  if (payload.status === 'done' && !payload.doneTime) payload.doneTime = new Date().toISOString()
  await api.post<Task>('/api/tasks', payload)
  editing.value = false
  await load()
}

async function remove() {
  if (!edit.value?.id) return
  await api.del(`/api/tasks/${edit.value.id}`)
  editing.value = false
  await load()
}

async function move(t: Task, status: string) {
  if (t.status === status) return
  await api.post(`/api/tasks/${t.id}/move`, { status })
  await load()
}

function shift(t: Task, delta: number) {
  const at = COLUMNS.indexOf(t.status as (typeof COLUMNS)[number])
  const target = COLUMNS[at + delta]
  if (target) move(t, target)
}

function onDrop(status: string) {
  over.value = null
  const t = drag.value
  drag.value = null
  if (t) move(t, status)
}

onMounted(load)
</script>

<template>
  <div v-if="loading" v-loading="true" style="min-height: 240px" />
  <el-alert v-else-if="error" type="error" :title="error" :closable="false" show-icon />

  <template v-else>
    <div class="page-head">
      <div>
        <div class="page-greet">任务看板</div>
        <div class="page-sub">待办 / 进行中 / 已完成 / 搁置四列：拖一下就算换状态，截止日和优先级直接标在卡上。</div>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openAdd()"><AppIcon name="plus" :size="14" /> 新建任务</el-button>
      </div>
    </div>

    <!-- 统计卡 -->
    <div class="stat-grid" style="grid-template-columns: repeat(4, minmax(0, 1fr))">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-top">
          <div>
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
          <div class="stat-icon" :style="{ background: s.color + '22', color: s.color }">
            <AppIcon :name="s.icon" :size="15" />
          </div>
        </div>
      </div>
    </div>

    <!-- 工具栏：项目筛选 -->
    <div class="page-toolbar">
      <el-select :empty-values="[]" v-model="projectId" style="width: 180px">
        <el-option value="" label="全部项目" />
        <el-option v-for="p in projectFilter" :key="p.value" :value="p.value" :label="p.text" />
      </el-select>
      <span class="muted" style="font-size: 12px"><AppIcon name="info" :size="12" /> 卡片可拖动换列，窄屏用左右箭头</span>
    </div>

    <!-- 看板 -->
    <div class="board">
      <div
        v-for="col in COLUMNS"
        :key="col"
        class="kb-col"
        :class="{ 'is-done': col === 'done', over: over === col }"
        @dragover.prevent
        @dragenter="over = col"
        @dragleave="over = over === col ? null : over"
        @drop="onDrop(col)"
      >
        <div class="kb-head">
          <span class="kb-dot" :class="col" />
          <b>{{ TASK_STATUS[col] }}</b>
          <span class="kb-count">{{ inColumn(col).length }}</span>
          <el-button text class="icon-btn kb-add" :title="`在「${TASK_STATUS[col]}」新建`" @click="openAdd(col)">
            <AppIcon name="plus" :size="14" />
          </el-button>
        </div>
        <div class="kb-cards">
          <div v-if="!inColumn(col).length" class="kb-none">{{ over === col ? '松手放这里' : '空' }}</div>
          <div
            v-for="t in inColumn(col)"
            :key="t.id"
            class="tk-card"
            :class="{ dragging: drag === t }"
            draggable="true"
            @dragstart="drag = t"
            @dragend="drag = null; over = null"
          >
            <div class="tk-title" @click="openEdit(t)">{{ t.title }}</div>
            <div class="tk-sub">
              <el-tag size="small" :type="PRIORITY_TAG[t.priority || 'normal'] ?? 'primary'">{{ label(PRIORITY, t.priority, '普通') }}</el-tag>
              <span v-if="t.dueDate" class="tk-due" :class="{ late: isLate(t) }">{{ formatMd(t.dueDate) }}</span>
              <span class="tk-proj">{{ projName(t.projectId) }}</span>
            </div>
            <div class="tk-move">
              <el-button text class="icon-btn" :disabled="COLUMNS.indexOf(col) <= 0" title="移到上一列" @click="shift(t, -1)">
                <AppIcon name="chevron-left" :size="14" />
              </el-button>
              <el-button text class="icon-btn" :disabled="COLUMNS.indexOf(col) >= COLUMNS.length - 1" title="移到下一列" @click="shift(t, 1)">
                <AppIcon name="chevron-right" :size="14" />
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <Modal v-if="editing && edit" :title="isNew ? '新建任务' : '编辑任务'" icon="kanban" @close="editing = false">
      <div class="form-grid">
        <div class="field full">
          <label>标题 <span class="req">*</span></label>
          <el-input v-model="edit.title" maxlength="300" placeholder="要做的事，一句话说清" />
        </div>
        <div class="field">
          <label>列</label>
          <el-select v-model="edit.status">
            <el-option v-for="c in COLUMNS" :key="c" :value="c" :label="TASK_STATUS[c]" />
          </el-select>
        </div>
        <div class="field">
          <label>优先级</label>
          <el-select v-model="edit.priority">
            <el-option value="high" label="急" />
            <el-option value="normal" label="普通" />
            <el-option value="low" label="不急" />
          </el-select>
        </div>
        <div class="field">
          <label>截止</label>
          <el-date-picker v-model="edit.dueDate" type="date" value-format="YYYY-MM-DD" />
        </div>
        <div class="field">
          <label>项目</label>
          <el-select :empty-values="[]" v-model="edit.projectId">
            <el-option :value="(null as any)" label="不挂项目" />
            <el-option v-for="p in projectOptions" :key="p.value" :value="p.value" :label="p.text" />
          </el-select>
        </div>
        <div class="field full">
          <label>备注</label>
          <el-input v-model="edit.note" type="textarea" :rows="3" maxlength="1000" placeholder="链接、要点、验收口径" />
        </div>
      </div>
      <template #footer>
        <el-button @click="editing = false">取消</el-button>
        <el-button v-if="!isNew" type="danger" plain @click="remove()">删除</el-button>
        <el-button type="primary" @click="save()"><AppIcon name="check" :size="14" /> 保存</el-button>
      </template>
    </Modal>
  </template>
</template>
