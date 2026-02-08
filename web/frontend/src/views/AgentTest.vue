<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({ baseURL: '/api/agent' })

// ==================== 状态 ====================
const query = ref('')
const mode = ref('auto')
const selectedSkill = ref('')
const useKnowledgeFirst = ref(true)
const allowWeb = ref(false)
const showAdvanced = ref(false)

const loading = ref(false)
const result = reactive({
  interaction_id: '',
  output: '',
  skills_used: [],
  knowledge_refs: [],
  trace: [],
  intent: null,
  duration_ms: 0,
  success: false,
  visible: false,
})

const feedback = reactive({
  rating: 0,
  resolved: null,
  tags: [],
  comment: '',
  submitted: false,
})

const availableSkills = ref([])
const history = ref([])
const activeTab = ref('output')

const feedbackTags = [
  { label: '准确性', value: 'accuracy' },
  { label: '完整性', value: 'completeness' },
  { label: '格式质量', value: 'format' },
  { label: '鲁棒性', value: 'robustness' },
  { label: '实用性', value: 'usefulness' },
]

const ratingLabels = {
  1: '很差',
  2: '较差',
  3: '一般',
  4: '较好',
  5: '很好',
}

// ==================== 初始化 ====================
onMounted(async () => {
  try {
    const [skillsRes, historyRes] = await Promise.all([
      api.get('/skills'),
      api.get('/interactions?limit=10'),
    ])
    availableSkills.value = skillsRes.data || []
    history.value = historyRes.data || []
  } catch (e) {
    console.error('初始化加载失败', e)
  }
})

const skillOptions = computed(() =>
  availableSkills.value.map(s => ({
    label: `${s.name} (${s.domain} Lv.${s.level})`,
    value: s.skill_id,
  }))
)

// ==================== 求解 ====================
async function handleSolve() {
  if (!query.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }

  loading.value = true
  result.visible = false
  resetFeedback()

  try {
    const res = await api.post('/solve', {
      query: query.value,
      mode: mode.value,
      skill_id: mode.value === 'manual' ? selectedSkill.value : undefined,
      use_knowledge_first: useKnowledgeFirst.value,
      allow_web: allowWeb.value,
    })

    const data = res.data
    result.interaction_id = data.interaction_id
    result.output = data.output || ''
    result.skills_used = data.skills_used || []
    result.knowledge_refs = data.knowledge_refs || []
    result.trace = data.trace || []
    result.intent = data.intent
    result.duration_ms = data.duration_ms || 0
    result.success = data.success
    result.visible = true
    activeTab.value = 'output'

    // 刷新历史
    refreshHistory()
  } catch (e) {
    ElMessage.error('求解失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// ==================== 反馈 ====================
function resetFeedback() {
  feedback.rating = 0
  feedback.resolved = null
  feedback.tags = []
  feedback.comment = ''
  feedback.submitted = false
}

async function handleFeedback() {
  if (!feedback.rating) {
    ElMessage.warning('请选择评分')
    return
  }
  if (feedback.resolved === null) {
    ElMessage.warning('请选择是否解决问题')
    return
  }

  try {
    await api.post('/feedback', {
      interaction_id: result.interaction_id,
      rating: feedback.rating,
      resolved: feedback.resolved,
      tags: feedback.tags,
      comment: feedback.comment,
    })
    feedback.submitted = true
    ElMessage.success('感谢你的反馈！已纳入进化策略。')
  } catch (e) {
    ElMessage.error('反馈提交失败')
  }
}

// ==================== 历史 ====================
async function refreshHistory() {
  try {
    const res = await api.get('/interactions?limit=10')
    history.value = res.data || []
  } catch (e) { /* ignore */ }
}

function loadHistory(record) {
  query.value = record.query || ''
  result.interaction_id = record.interaction_id
  result.output = record.output || ''
  result.skills_used = record.skills_used || []
  result.knowledge_refs = record.knowledge_refs || []
  result.trace = record.trace || []
  result.intent = record.intent
  result.duration_ms = record.duration_ms || 0
  result.success = record.success
  result.visible = true
  activeTab.value = 'output'
  resetFeedback()
}

function formatTime(ts) {
  if (!ts) return ''
  return ts.replace('T', ' ').substring(0, 19)
}
</script>

<template>
  <div class="agent-test">
    <el-row :gutter="20">
      <!-- 左侧：输入 + 结果 -->
      <el-col :span="17">
        <!-- 输入区 -->
        <el-card shadow="never" class="input-card">
          <template #header>
            <div class="card-header">
              <span>🧪 测试 Agent 能力</span>
              <el-tag size="small" type="info">
                {{ availableSkills.length }} 个技能可用
              </el-tag>
            </div>
          </template>

          <el-input
            v-model="query"
            type="textarea"
            :rows="3"
            placeholder="输入你的问题，Agent 将使用已学技能为你解答..."
            :disabled="loading"
            @keydown.ctrl.enter="handleSolve"
          />

          <div class="input-controls">
            <div class="left-controls">
              <el-radio-group v-model="mode" size="small">
                <el-radio-button value="auto">自动选择技能</el-radio-button>
                <el-radio-button value="manual">手动指定</el-radio-button>
              </el-radio-group>

              <el-select
                v-if="mode === 'manual'"
                v-model="selectedSkill"
                placeholder="选择技能"
                size="small"
                style="width: 220px; margin-left: 12px;"
              >
                <el-option
                  v-for="s in skillOptions"
                  :key="s.value"
                  :label="s.label"
                  :value="s.value"
                />
              </el-select>

              <el-button
                link type="primary" size="small"
                @click="showAdvanced = !showAdvanced"
                style="margin-left: 12px;"
              >
                {{ showAdvanced ? '收起' : '高级设置' }}
              </el-button>
            </div>

            <el-button
              type="primary"
              @click="handleSolve"
              :loading="loading"
              :disabled="!query.trim()"
            >
              {{ loading ? '执行中...' : '开始求解' }}
            </el-button>
          </div>

          <div v-if="showAdvanced" class="advanced-settings">
            <el-checkbox v-model="useKnowledgeFirst">
              优先使用知识库
            </el-checkbox>
            <el-checkbox v-model="allowWeb">
              允许联网搜索
            </el-checkbox>
          </div>
        </el-card>

        <!-- 结果区 -->
        <el-card v-if="result.visible" shadow="never" class="result-card">
          <template #header>
            <div class="card-header">
              <span>
                {{ result.success ? '✅' : '❌' }}
                执行结果
              </span>
              <div class="result-meta">
                <el-tag size="small" v-for="s in result.skills_used" :key="s">
                  {{ s }}
                </el-tag>
                <el-tag size="small" type="info">
                  {{ result.duration_ms }}ms
                </el-tag>
              </div>
            </div>
          </template>

          <el-tabs v-model="activeTab">
            <!-- 输出 -->
            <el-tab-pane label="回答" name="output">
              <div class="output-content" v-html="renderOutput(result.output)"></div>
            </el-tab-pane>

            <!-- 知识引用 -->
            <el-tab-pane
              :label="`知识引用 (${result.knowledge_refs.length})`"
              name="refs"
            >
              <div v-if="result.knowledge_refs.length === 0" class="empty-tip">
                未使用知识库引用
              </div>
              <div
                v-for="(ref, i) in result.knowledge_refs" :key="i"
                class="ref-item"
              >
                <div class="ref-title">📄 {{ ref.title }}</div>
                <div class="ref-snippet">{{ ref.snippet }}</div>
                <el-tag size="small" type="info">{{ ref.source }}</el-tag>
              </div>
            </el-tab-pane>

            <!-- 执行轨迹 -->
            <el-tab-pane
              :label="`调用轨迹 (${result.trace.length})`"
              name="trace"
            >
              <el-timeline>
                <el-timeline-item
                  v-for="(t, i) in result.trace" :key="i"
                  :type="t.success ? 'success' : 'danger'"
                  :timestamp="`${t.duration_ms}ms`"
                  placement="top"
                >
                  <div class="trace-item">
                    <strong>{{ t.skill }}</strong>
                    <span class="trace-status">
                      {{ t.success ? '成功' : '失败' }}
                    </span>
                    <div class="trace-detail">
                      <div v-if="t.input">
                        <span class="trace-label">输入:</span>
                        {{ JSON.stringify(t.input).substring(0, 120) }}
                      </div>
                      <div v-if="t.output_summary">
                        <span class="trace-label">输出:</span>
                        {{ t.output_summary.substring(0, 200) }}
                      </div>
                      <div v-if="t.knowledge_queries">
                        知识库查询 {{ t.knowledge_queries }} 次,
                        存储 {{ t.knowledge_stores || 0 }} 条
                      </div>
                    </div>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </el-tab-pane>

            <!-- 意图解析 -->
            <el-tab-pane label="意图解析" name="intent" v-if="result.intent">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="领域">
                  {{ result.intent.domain }}
                </el-descriptions-item>
                <el-descriptions-item label="任务类型">
                  {{ result.intent.task_type }}
                </el-descriptions-item>
                <el-descriptions-item label="链式调用">
                  {{ result.intent.needs_chain ? '是' : '否' }}
                </el-descriptions-item>
                <el-descriptions-item label="提取参数">
                  {{ JSON.stringify(result.intent.extracted_params || {}) }}
                </el-descriptions-item>
              </el-descriptions>

              <div style="margin-top: 12px;">
                <strong>候选技能:</strong>
                <div
                  v-for="(c, i) in (result.intent.skill_candidates || [])"
                  :key="i"
                  class="candidate-item"
                >
                  <el-tag :type="c.relevance === 'high' ? 'success' : 'info'"
                          size="small">
                    {{ c.relevance }}
                  </el-tag>
                  <span>{{ c.skill_id }}</span>
                  <span class="candidate-reason">{{ c.reason }}</span>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>

        <!-- 反馈区 -->
        <el-card
          v-if="result.visible && !feedback.submitted"
          shadow="never"
          class="feedback-card"
        >
          <template #header>
            <span>📝 反馈评价</span>
          </template>

          <div class="feedback-form">
            <div class="feedback-row">
              <span class="feedback-label">满意度:</span>
              <el-rate
                v-model="feedback.rating"
                :texts="Object.values(ratingLabels)"
                show-text
              />
            </div>

            <div class="feedback-row">
              <span class="feedback-label">是否解决问题:</span>
              <el-radio-group v-model="feedback.resolved">
                <el-radio :value="true">是</el-radio>
                <el-radio :value="false">否</el-radio>
              </el-radio-group>
            </div>

            <div class="feedback-row">
              <span class="feedback-label">薄弱维度:</span>
              <el-checkbox-group v-model="feedback.tags">
                <el-checkbox
                  v-for="t in feedbackTags" :key="t.value"
                  :value="t.value" :label="t.label"
                />
              </el-checkbox-group>
            </div>

            <div class="feedback-row">
              <span class="feedback-label">建议:</span>
              <el-input
                v-model="feedback.comment"
                type="textarea"
                :rows="2"
                placeholder="具体改进建议（可选）"
              />
            </div>

            <div class="feedback-actions">
              <el-button type="primary" @click="handleFeedback">
                提交反馈
              </el-button>
              <span class="feedback-hint">
                反馈会影响 Agent 后续进化方向
              </span>
            </div>
          </div>
        </el-card>

        <!-- 反馈已提交 -->
        <el-alert
          v-if="feedback.submitted"
          title="反馈已提交，将纳入进化策略"
          type="success"
          show-icon
          :closable="false"
          style="margin-top: 16px;"
        />
      </el-col>

      <!-- 右侧：历史记录 -->
      <el-col :span="7">
        <el-card shadow="never" class="history-card">
          <template #header>
            <div class="card-header">
              <span>📋 历史记录</span>
              <el-button link size="small" @click="refreshHistory">刷新</el-button>
            </div>
          </template>

          <div v-if="history.length === 0" class="empty-tip">
            暂无历史记录
          </div>

          <div
            v-for="h in history" :key="h.interaction_id"
            class="history-item"
            @click="loadHistory(h)"
          >
            <div class="history-query">{{ h.query?.substring(0, 40) }}</div>
            <div class="history-meta">
              <el-tag size="small" :type="h.success ? 'success' : 'danger'">
                {{ h.success ? '成功' : '失败' }}
              </el-tag>
              <span class="history-time">{{ formatTime(h.timestamp) }}</span>
            </div>
            <div class="history-skills">
              <el-tag
                v-for="s in (h.skills_used || [])" :key="s"
                size="small" type="info"
              >
                {{ s }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
export default {
  methods: {
    renderOutput(text) {
      if (!text) return '<span class="empty-tip">无输出</span>'
      // 简单 markdown → HTML（加粗、换行）
      return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br/>')
    },
  },
}
</script>

<style scoped>
.agent-test {
  max-width: 1400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-card .el-textarea {
  margin-bottom: 12px;
}

.input-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left-controls {
  display: flex;
  align-items: center;
}

.advanced-settings {
  margin-top: 12px;
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  display: flex;
  gap: 20px;
}

.result-card {
  margin-top: 16px;
}

.result-meta {
  display: flex;
  gap: 6px;
  align-items: center;
}

.output-content {
  padding: 12px;
  background: #fafbfc;
  border-radius: 6px;
  line-height: 1.7;
  min-height: 60px;
  max-height: 500px;
  overflow-y: auto;
  word-break: break-word;
}

.ref-item {
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
}
.ref-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.ref-snippet {
  color: #666;
  font-size: 13px;
  margin-bottom: 4px;
}

.trace-item {
  font-size: 13px;
}
.trace-status {
  margin-left: 8px;
  font-size: 12px;
  color: #999;
}
.trace-detail {
  margin-top: 4px;
  color: #666;
  font-size: 12px;
}
.trace-label {
  font-weight: 600;
  color: #333;
}

.candidate-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.candidate-reason {
  color: #999;
  font-size: 12px;
}

/* 反馈 */
.feedback-card {
  margin-top: 16px;
}
.feedback-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.feedback-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.feedback-label {
  min-width: 80px;
  font-weight: 500;
  line-height: 32px;
}
.feedback-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.feedback-hint {
  color: #999;
  font-size: 12px;
}

/* 历史 */
.history-card {
  position: sticky;
  top: 20px;
}
.history-item {
  padding: 10px 8px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.15s;
}
.history-item:hover {
  background: #f0f5ff;
}
.history-query {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.history-time {
  font-size: 11px;
  color: #aaa;
}
.history-skills {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.empty-tip {
  color: #ccc;
  text-align: center;
  padding: 20px;
}
</style>
