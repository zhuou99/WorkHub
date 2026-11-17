<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { api } from '@/api'
import type { AccountInfo, AuditLog, BackupInfo, ErrorLog, SecretInfo, SchedulerOptionsIn } from '@/types'

const tab = ref('account')
const busy = ref(false)
const notice = ref('')

const account = ref<AccountInfo | null>(null)
const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')

const users = ref<{ id: string; userName: string; displayName: string | null; role: string | null; enabled: boolean }[]>([])

const secrets = ref<SecretInfo[]>([])
const secretValues = ref<Record<string, string>>({})

const bkKeep = ref(10)
const bkExtra = ref('')
const backups = ref<BackupInfo[]>([])

const sched = ref<SchedulerOptionsIn>({ enabled: false, rssMinutes: 30, repoMinutes: 60, backupEnabled: false, backupHour: 3 })

const audits = ref<AuditLog[]>([])
const errs = ref<ErrorLog[]>([])

const TABS = [
  { key: 'account', name: '账号安全', icon: 'shield' },
  { key: 'secrets', name: '服务密钥', icon: 'lock' },
  { key: 'backup', name: '备份恢复', icon: 'database' },
  { key: 'scheduler', name: '定时任务', icon: 'calendar-clock' },
  { key: 'logs', name: '日志审计', icon: 'file-text' },
]

function say(msg: string) { notice.value = msg }

async function loadAccount() {
  try {
    account.value = await api.get<AccountInfo>('/api/settings/account')
    users.value = await api.get<{ id: string; userName: string; displayName: string | null; role: string | null; enabled: boolean }[]>('/api/users')
  } catch { /* 非 Owner 看不到用户列表 */ }
}

async function changePassword() {
  if (!oldPwd.value || !newPwd.value) { say('旧口令与新口令均不能为空。'); return }
  if (newPwd.value.length < 6) { say('新口令至少 6 位。'); return }
  if (newPwd.value !== confirmPwd.value) { say('两次输入的新口令不一致。'); return }
  busy.value = true
  try {
    await api.post('/api/settings/password', { oldPassword: oldPwd.value, newPassword: newPwd.value })
    oldPwd.value = newPwd.value = confirmPwd.value = ''
    say('口令已更新。')
  } catch (e) { say(e instanceof Error ? e.message : '修改失败') }
  finally { busy.value = false }
}

async function loadSecrets() {
  try {
    secrets.value = await api.get<SecretInfo[]>('/api/secrets')
  } catch { secrets.value = [] }
}

async function saveSecret(key: string) {
  const value = secretValues.value[key] ?? ''
  if (!value.trim()) { say('内容不能为空。'); return }
  await api.post('/api/secrets', { key, value })
  secretValues.value[key] = ''
  await loadSecrets()
  say('已加密保存。')
}

async function removeSecret(key: string) {
  await api.del(`/api/secrets/${key}`)
  await loadSecrets()
}

async function loadBackup() {
  try {
    const opts = await api.get<{ keep: number; extraFolder: string }>('/api/backup/options')
    bkKeep.value = opts.keep
    bkExtra.value = opts.extraFolder || ''
    backups.value = await api.get<BackupInfo[]>('/api/backup/list')
  } catch { /* 读取失败不阻塞 */ }
}

async function saveBackupOptions() {
  busy.value = true
  try {
    await api.post('/api/backup/options', { keep: bkKeep.value, extraFolder: bkExtra.value })
    say('备份设置已保存。')
  } catch (e) { say(e instanceof Error ? e.message : '保存失败') }
  finally { busy.value = false }
}

async function runBackup() {
  busy.value = true
  try { await api.post('/api/backup/run'); await loadBackup(); say('备份完成。') }
  catch (e) { say(e instanceof Error ? e.message : '备份失败') }
  finally { busy.value = false }
}

async function deleteBackup(name: string) {
  await api.del(`/api/backup/${name}`)
  await loadBackup()
}

async function loadScheduler() {
  try {
    const opts = await api.get<{ enabled: boolean; rssMinutes: number; repoMinutes: number; backupEnabled: boolean; backupHour: number }>('/api/scheduler/options')
    sched.value = opts
  } catch { /* 读取失败不阻塞 */ }
}

async function saveScheduler() {
  busy.value = true
  try {
    await api.post('/api/scheduler/options', sched.value)
    say('定时任务设置已保存。')
  } catch (e) { say(e instanceof Error ? e.message : '保存失败') }
  finally { busy.value = false }
}

async function loadLogs() {
  try {
    audits.value = await api.get<AuditLog[]>('/api/audit?take=50')
    errs.value = await api.get<ErrorLog[]>('/api/errors?take=50')
  } catch { /* 读取失败不阻塞 */ }
}

onMounted(() => {
  loadAccount(); loadSecrets(); loadBackup(); loadScheduler()
})
</script>

<template>
  <div class="page-head">
    <div>
      <div class="page-greet">偏好设置</div>
      <div class="page-sub">账号安全、服务密钥、备份恢复、定时任务与日志审计。</div>
    </div>
  </div>

  <div class="page-toolbar" style="margin-bottom: 18px">
    <button v-for="t in TABS" :key="t.key" class="btn" :class="{ primary: tab === t.key }" @click="tab = t.key; if (t.key === 'logs') loadLogs()">
      <AppIcon :name="t.icon" :size="14" /> {{ t.name }}
    </button>
  </div>

  <div v-if="notice" class="auth-note" style="margin-bottom: 14px">{{ notice }}</div>

  <!-- 账号安全 -->
  <div v-if="tab === 'account'" class="card" style="max-width: 640px">
    <div class="card-title"><AppIcon name="shield" :size="16" /> 当前账号</div>
    <div v-if="account" class="kv" style="grid-template-columns: 1fr 1fr">
      <div><i>账号</i>{{ account.userName }}</div>
      <div><i>显示名</i>{{ account.displayName || '—' }}</div>
      <div><i>口令设置时间</i>{{ account.setTime ? account.setTime.slice(0, 10) : '—' }}</div>
      <div><i>是否出厂口令</i><span :style="account.defaultPassword ? 'color: var(--warning-color)' : 'color: var(--success-color)'">{{ account.defaultPassword ? '是，建议尽快改' : '已修改' }}</span></div>
    </div>

    <div class="sec">修改口令</div>
    <div class="form-grid">
      <div class="field full"><label>旧口令</label><input v-model="oldPwd" class="input" type="password" /></div>
      <div class="field"><label>新口令（至少 6 位）</label><input v-model="newPwd" class="input" type="password" /></div>
      <div class="field"><label>确认新口令</label><input v-model="confirmPwd" class="input" type="password" /></div>
      <div class="field full" style="text-align: right"><button class="btn primary" :disabled="busy" @click="changePassword"><AppIcon name="check" :size="14" /> 修改口令</button></div>
    </div>

    <template v-if="users.length">
      <div class="sec">账号列表（Owner）</div>
      <table class="table">
        <thead><tr><th>账号</th><th>显示名</th><th>角色</th><th>状态</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.userName }}</td>
            <td>{{ u.displayName || '—' }}</td>
            <td>{{ u.role }}</td>
            <td><span class="pill" :class="u.enabled ? 'st-done' : 'st-void'">{{ u.enabled ? '启用' : '禁用' }}</span></td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>

  <!-- 服务密钥 -->
  <div v-else-if="tab === 'secrets'" class="card" style="max-width: 680px">
    <div class="card-title"><AppIcon name="lock" :size="16" /> 外部服务密钥</div>
    <div v-for="s in secrets" :key="s.key" class="rel" style="padding: 12px 0">
      <div style="flex: 1; min-width: 0">
        <div style="font-weight: 600">{{ s.name }}</div>
        <div class="muted" style="font-size: 12px">{{ s.usage }}</div>
        <div v-if="s.configured" class="muted" style="font-size: 12px; margin-top: 3px">
          {{ s.readable ? '已加密保存 · ' + s.masked : '密文解不开，需重录（换机器/换账户）' }}
        </div>
      </div>
      <input v-model="secretValues[s.key]" class="input" style="width: 220px" :placeholder="s.placeholder" :type="s.configured ? 'text' : 'text'" />
      <button class="btn" style="height: 28px; font-size: 12px" @click="saveSecret(s.key)">保存</button>
      <button v-if="s.configured" class="btn" style="height: 28px; font-size: 12px; color: var(--danger-color)" @click="removeSecret(s.key)">清除</button>
    </div>
    <div class="muted" style="font-size: 12px; margin-top: 8px">密钥用本机密钥加密后存 SysConfig，明文永不通过接口回显。</div>
  </div>

  <!-- 备份恢复 -->
  <div v-else-if="tab === 'backup'" class="card" style="max-width: 720px">
    <div class="card-title"><AppIcon name="database" :size="16" /> 一键备份</div>
    <div class="form-grid">
      <div class="field"><label>保留份数（1-100）</label><input v-model.number="bkKeep" class="input" type="number" min="1" max="100" /></div>
      <div class="field"><label>第二备份目录（可选，绝对路径）</label><input v-model="bkExtra" class="input" /></div>
      <div class="field full" style="display: flex; gap: 8px">
        <button class="btn primary" :disabled="busy" @click="runBackup"><AppIcon name="database" :size="14" /> 立即备份</button>
        <button class="btn" :disabled="busy" @click="saveBackupOptions">保存设置</button>
      </div>
    </div>

    <div class="sec">备份列表</div>
    <div v-if="!backups.length" class="empty">还没有备份包。</div>
    <table v-else class="table">
      <thead><tr><th>名称</th><th>时间</th><th>大小</th><th class="right">操作</th></tr></thead>
      <tbody>
        <tr v-for="b in backups" :key="b.name">
          <td>{{ b.name }}</td>
          <td>{{ b.created }}</td>
          <td>{{ b.size }}</td>
          <td class="right"><button class="btn" style="height: 26px; font-size: 12px; color: var(--danger-color)" @click="deleteBackup(b.name)"><AppIcon name="trash" :size="13" /></button></td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 定时任务 -->
  <div v-else-if="tab === 'scheduler'" class="card" style="max-width: 640px">
    <div class="card-title"><AppIcon name="calendar-clock" :size="16" /> 定时任务</div>
    <div class="form-grid">
      <div class="field full"><label style="display: flex; align-items: center; gap: 8px; font-weight: 500"><input v-model="sched.enabled" type="checkbox" /> 启用定时任务</label></div>
      <div class="field"><label>RSS 同步间隔（分钟，0=关）</label><input v-model.number="sched.rssMinutes" class="input" type="number" min="0" /></div>
      <div class="field"><label>仓库同步间隔（分钟，0=关）</label><input v-model.number="sched.repoMinutes" class="input" type="number" min="0" /></div>
      <div class="field"><label>自动备份开关</label><input v-model="sched.backupEnabled" type="checkbox" /></div>
      <div class="field"><label>备份时间点（0-23 点）</label><input v-model.number="sched.backupHour" class="input" type="number" min="0" max="23" /></div>
      <div class="field full" style="text-align: right"><button class="btn primary" :disabled="busy" @click="saveScheduler">保存</button></div>
    </div>
  </div>

  <!-- 日志审计 -->
  <div v-else-if="tab === 'logs'">
    <div class="card" style="margin-bottom: 16px">
      <div class="card-title"><AppIcon name="file-text" :size="16" /> 审计日志（最近 {{ audits.length }} 条）</div>
      <div v-if="!audits.length" class="empty">还没有审计记录。</div>
      <table v-else class="table">
        <thead><tr><th>时间</th><th>类型</th><th>动作</th><th>账号</th><th>结果</th><th>摘要</th></tr></thead>
        <tbody>
          <tr v-for="(a, i) in audits" :key="i">
            <td>{{ (a.time ?? '').slice(0, 16) }}</td>
            <td>{{ a.kind }}</td>
            <td>{{ a.action }}</td>
            <td>{{ a.userName || '—' }}</td>
            <td><span class="pill" :class="a.success ? 'st-done' : 'st-void'">{{ a.success ? '成功' : '失败' }}</span></td>
            <td class="muted">{{ a.detail || '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <div class="card-title"><AppIcon name="alert-circle" :size="16" /> 运行错误（最近 {{ errs.length }} 条）</div>
      <div v-if="!errs.length" class="empty">没有运行错误。</div>
      <table v-else class="table">
        <thead><tr><th>时间</th><th>级别</th><th>消息</th><th>路径</th></tr></thead>
        <tbody>
          <tr v-for="(e, i) in errs" :key="i">
            <td>{{ (e.time ?? '').slice(0, 16) }}</td>
            <td><span class="pill" :class="e.level === 'Error' ? 'st-void' : 'st-hold'">{{ e.level }}</span></td>
            <td>{{ e.message }}</td>
            <td class="muted">{{ e.path || '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
