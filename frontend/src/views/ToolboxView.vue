<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { api } from '@/api'
import type { ToolInfo } from '@/types'

const tools = ref<ToolInfo[]>([])
const kw = ref('')
const selectedId = ref('')
const input = ref('')
const option = ref('')
const output = ref('')
const data = ref<any>(null)
const busy = ref(false)
const err = ref('')

// 面板工具参数
const p = ref<Record<string, any>>({})

const UNIT_GROUPS = [
  { id: 'length', name: '长度', units: ['mm', 'cm', 'm', 'km', 'in', 'ft', 'yd', 'mi', 'nmi', 'ly'] },
  { id: 'area', name: '面积', units: ['mm2', 'm2', 'ha', 'km2', 'mu', 'acre'] },
  { id: 'volume', name: '体积', units: ['ml', 'l', 'm3', 'gal', 'floz'] },
  { id: 'mass', name: '重量', units: ['g', 'kg', 't', 'jin', 'liang', 'lb', 'oz'] },
  { id: 'data', name: '存储', units: ['B', 'KB', 'MB', 'GB', 'TB', 'KiB', 'MiB', 'GiB', 'TiB'] },
  { id: 'time', name: '时间', units: ['ms', 's', 'min', 'h', 'd', 'wk', 'yr'] },
  { id: 'speed', name: '速度', units: ['kmh', 'mps', 'mph', 'kn'] },
  { id: 'temp', name: '温度', units: ['c', 'f', 'k'] },
]

const filtered = computed(() =>
  !kw.value.trim() ? tools.value : tools.value.filter((t) => t.name.toLowerCase().includes(kw.value.trim().toLowerCase()) || t.description.toLowerCase().includes(kw.value.trim().toLowerCase())),
)

const grouped = computed(() => {
  const map = new Map<string, ToolInfo[]>()
  for (const t of filtered.value) {
    if (!map.has(t.category)) map.set(t.category, [])
    map.get(t.category)!.push(t)
  }
  return [...map.entries()]
})

const selected = computed(() => tools.value.find((t) => t.id === selectedId.value) ?? null)

function pick(id: string) {
  selectedId.value = id
  input.value = ''
  option.value = ''
  output.value = ''
  data.value = null
  err.value = ''
  p.value = {}
  // 默认 option
  const tool = tools.value.find((t) => t.id === id)
  if (tool?.options?.length) option.value = tool.options[0].value
  // 面板工具默认参数
  if (id === 'unit') { p.value = { groupId: 'data', fromId: 'GB', value: '1' } }
  else if (id === 'guid') { p.value = { count: '5', format: 'D' } }
  else if (id === 'password') { p.value = { length: '16', count: '5', lower: 'true', upper: 'true', digit: 'true' } }
  else if (id === 'color') { p.value = { hex: '#2f5bff' } }
  else if (id === 'translate') { p.value = { text: '', to: 'en' } }
}

async function run() {
  if (!selected.value) return
  busy.value = true
  err.value = ''
  output.value = ''
  data.value = null
  try {
    let body: { input: string; option: string; params?: Record<string, unknown> }
    if (selected.value.kind === 'io') {
      body = { input: input.value, option: option.value }
    } else {
      const params: Record<string, unknown> = {}
      for (const key of selected.value.params) {
        const v = p.value[key] ?? ''
        if (v === 'true') params[key] = true
        else if (v === 'false') params[key] = false
        else if (key === 'value' || key === 'count' || key === 'length' || key === 'seq') params[key] = Number(v) || 0
        else params[key] = v
      }
      body = { input: input.value, option: '', params }
    }
    const result = await api.post<{ output: string; data: Record<string, unknown> | null }>(`/api/tools/${selected.value.id}/run`, body)
    output.value = result.output
    data.value = result.data
    // 记历史
    await api.post(`/api/tools/${selected.value.id}/record`, { toolName: selected.value.name, input: input.value || JSON.stringify(p.value) })
  } catch (e) {
    err.value = e instanceof Error ? e.message : '执行失败'
  } finally {
    busy.value = false
  }
}

async function load() {
  tools.value = await api.get<ToolInfo[]>('/api/tools')
  if (tools.value.length) pick(tools.value[0].id)
}

onMounted(load)
</script>

<template>
  <div class="page-head">
    <div>
      <div class="page-greet">万能工具台</div>
      <div class="page-sub">编解码、格式转换、哈希、正则、单位与颜色换算，输入即算。</div>
    </div>
  </div>

  <div class="page-toolbar">
    <div class="search">
      <el-input v-model="kw" placeholder="搜索工具">
        <template #prefix><AppIcon name="search" :size="15" /></template>
      </el-input>
    </div>
  </div>

  <div class="cols" style="grid-template-columns: 200px 1fr; align-items: start">
    <!-- 工具列表 -->
    <div class="col tool-list">
      <div v-for="[cat, list] in grouped" :key="cat" class="card" style="padding: 12px; margin-bottom: 12px">
        <div class="muted" style="font-size: 11px; margin-bottom: 6px; padding-left: 4px">{{ cat }}</div>
        <button v-for="t in list" :key="t.id" class="app-sitem" :class="{ on: selectedId === t.id }" style="width: 100%" @click="pick(t.id)">
          <AppIcon :name="t.icon" :size="14" /><span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ t.name }}</span>
        </button>
      </div>
    </div>

    <!-- 工具面板 -->
    <div class="col">
      <div v-if="selected" class="card">
        <div class="card-title">
          <AppIcon :name="selected.icon" :size="16" /> {{ selected.name }}
          <span class="muted" style="font-size: 12px; font-weight: 400">{{ selected.description }}</span>
        </div>

        <!-- io 工具 -->
        <template v-if="selected.kind === 'io'">
          <el-input v-model="input" type="textarea" :rows="6" placeholder="输入内容…" />
          <div class="page-toolbar" style="margin: 10px 0">
            <el-select v-if="selected.options?.length" v-model="option" style="width: 180px">
              <el-option v-for="o in selected.options" :key="o.value" :value="o.value" :label="o.label" />
            </el-select>
            <el-button type="primary" :disabled="busy" @click="run"><AppIcon name="zap" :size="14" /> {{ busy ? '执行中…' : '执行' }}</el-button>
          </div>
          <div v-if="err" class="auth-error">{{ err }}</div>
          <pre v-else-if="output" class="code-preview" style="min-height: 60px">{{ output }}</pre>
        </template>

        <!-- unit 面板 -->
        <template v-else-if="selected.id === 'unit'">
          <div class="form-grid">
            <div class="field"><label>组</label>
              <el-select v-model="p.groupId" style="width: 100%"><el-option v-for="g in UNIT_GROUPS" :key="g.id" :value="g.id" :label="g.name" /></el-select>
            </div>
            <div class="field"><label>从</label>
              <el-select v-model="p.fromId" style="width: 100%"><el-option v-for="u in UNIT_GROUPS.find((g) => g.id === p.groupId)?.units ?? []" :key="u" :value="u" :label="u" /></el-select>
            </div>
            <div class="field"><label>值</label><el-input-number v-model="p.value" :controls="false" style="width: 100%" /></div>
            <div class="field" style="align-self: end"><el-button type="primary" :disabled="busy" @click="run">换算</el-button></div>
          </div>
          <el-table v-if="data?.units" :data="data.units" style="margin-top: 12px">
            <el-table-column label="单位">
              <template #default="{ row }">{{ row.label }}</template>
            </el-table-column>
            <el-table-column label="结果" align="right">
              <template #default="{ row }">{{ row.text }}</template>
            </el-table-column>
          </el-table>
        </template>

        <!-- regex 面板 -->
        <template v-else-if="selected.id === 'regex'">
          <div class="field" style="margin-bottom: 8px"><label>表达式</label><el-input v-model="p.pattern" /></div>
          <div class="field" style="margin-bottom: 12px"><label>测试文本</label><el-input v-model="p.subject" type="textarea" :rows="4" /></div>
          <el-button type="primary" :disabled="busy" @click="run">匹配</el-button>
          <div v-if="err" class="auth-error" style="margin-top: 8px">{{ err }}</div>
          <div v-else-if="data?.matches" style="margin-top: 10px">
            <div class="muted" style="font-size: 12px">{{ data.matches.length }} 个匹配</div>
            <div v-for="(m, i) in (data.matches)" :key="i" class="rel">
              <el-tag size="small" type="info">#{{ m.index }}</el-tag><span class="rel-t" style="font-family: monospace">{{ m.value }}</span>
              <span v-if="m.groups?.length" class="muted">{{ JSON.stringify(m.groups) }}</span>
            </div>
          </div>
        </template>

        <!-- diff / count / hmac / guid / password / color / translate 面板 -->
        <template v-else-if="selected.id === 'diff'">
          <div class="cols" style="grid-template-columns: 1fr 1fr; gap: 10px">
            <div class="field"><label>原文</label><el-input v-model="p.left" type="textarea" :rows="6" /></div>
            <div class="field"><label>新文</label><el-input v-model="p.right" type="textarea" :rows="6" /></div>
          </div>
          <el-button type="primary" :disabled="busy" @click="run">比对</el-button>
          <div v-if="data?.rows" style="margin-top: 10px">
            <div class="muted" style="font-size: 12px">增 {{ (data).add }} · 删 {{ (data).del }} · 同 {{ (data).same }}</div>
            <div v-for="(r, i) in (data.rows)" :key="i" style="font-family: monospace; font-size: 12.5px; padding: 2px 6px" :style="r.op === 'add' ? 'background: var(--success-soft)' : r.op === 'del' ? 'background: var(--danger-soft)' : ''">{{ r.op === 'add' ? '+' : r.op === 'del' ? '-' : ' ' }} {{ r.line }}</div>
          </div>
        </template>

        <template v-else-if="selected.id === 'count'">
          <el-input v-model="p.text" type="textarea" :rows="6" />
          <el-button type="primary" :disabled="busy" @click="run" style="margin-top: 8px">统计</el-button>
          <div v-if="data" class="kv" style="margin-top: 12px; grid-template-columns: repeat(4, 1fr)">
            <div v-for="(v, k) in data" :key="k"><i>{{ k }}</i>{{ v }}</div>
          </div>
        </template>

        <template v-else-if="selected.id === 'hmac'">
          <div class="field" style="margin-bottom: 8px"><label>密钥</label><el-input v-model="p.key" /></div>
          <div class="field" style="margin-bottom: 10px"><label>数据</label><el-input v-model="p.data" /></div>
          <el-button type="primary" :disabled="busy" @click="run">签名</el-button>
          <pre v-if="output" class="code-preview" style="margin-top: 10px">{{ output }}</pre>
        </template>

        <template v-else-if="selected.id === 'guid'">
          <div class="page-toolbar">
            <div class="field" style="margin-bottom: 0"><label style="font-size: 11px">数量</label><el-input-number v-model="p.count" :controls="false" style="width: 80px" /></div>
            <div class="field" style="margin-bottom: 0"><label style="font-size: 11px">格式</label>
              <el-select v-model="p.format" style="width: 120px"><el-option value="D" label="标准" /><el-option value="N" label="无连字符" /><el-option value="B" label="{花括号}" /><el-option value="P" label="(圆括号)" /><el-option value="ULID" label="ULID" /></el-select>
            </div>
            <el-button type="primary" :disabled="busy" @click="run">生成</el-button>
          </div>
          <pre v-if="data?.ids" class="code-preview" style="margin-top: 10px">{{ data.ids.join('\n') }}</pre>
        </template>

        <template v-else-if="selected.id === 'password'">
          <div class="page-toolbar">
            <div class="field" style="margin-bottom: 0"><label style="font-size: 11px">长度</label><el-input-number v-model="p.length" :controls="false" style="width: 80px" /></div>
            <div class="field" style="margin-bottom: 0"><label style="font-size: 11px">数量</label><el-input-number v-model="p.count" :controls="false" style="width: 80px" /></div>
            <el-button type="primary" :disabled="busy" @click="run">生成</el-button>
          </div>
          <pre v-if="data?.passwords" class="code-preview" style="margin-top: 10px">{{ data.passwords.join('\n') }}</pre>
        </template>

        <template v-else-if="selected.id === 'color'">
          <div class="field" style="margin-bottom: 10px"><label>颜色（#RRGGBB）</label><el-input v-model="p.hex" style="width: 160px" /></div>
          <el-button type="primary" :disabled="busy" @click="run">转换</el-button>
          <div v-if="data" class="kv" style="margin-top: 12px; grid-template-columns: repeat(3, 1fr)">
            <div><i>HEX</i>{{ data.hex }}</div>
            <div><i>RGB</i>{{ data.rgb }}</div>
            <div><i>HSL</i>{{ data.hsl }}</div>
          </div>
          <div v-if="data?.shades" class="ent-tags" style="margin-top: 10px">
            <el-tag v-for="s in (data.shades)" :key="s.hex" size="small" round effect="plain" type="info" :style="{ background: s.hex, color: '#fff' }">{{ s.label }}</el-tag>
          </div>
        </template>

        <!-- translate / qr 简化面板 -->
        <template v-else-if="selected.id === 'translate' || selected.id === 'qr'">
          <el-input v-model="input" type="textarea" :rows="4" placeholder="输入内容…" />
          <el-button type="primary" :disabled="busy" @click="run" style="margin-top: 8px">执行</el-button>
          <div v-if="err" class="auth-error" style="margin-top: 8px">{{ err }}</div>
          <pre v-else-if="output" class="code-preview" style="margin-top: 10px">{{ output }}</pre>
        </template>

        <!-- 其他 panel 工具兜底 -->
        <template v-else>
          <el-input v-model="input" type="textarea" :rows="4" />
          <el-button type="primary" :disabled="busy" @click="run" style="margin-top: 8px">执行</el-button>
          <div v-if="err" class="auth-error" style="margin-top: 8px">{{ err }}</div>
          <pre v-else-if="output" class="code-preview" style="margin-top: 10px">{{ output }}</pre>
        </template>
      </div>
    </div>
  </div>
</template>
