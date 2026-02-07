<script setup>
import { ref, onMounted, computed } from 'vue'
import { getStatus, getTreeStats, getLogs } from '../api'

const status = ref({})
const evolution = ref({})
const recentLogs = ref([])
const loading = ref(true)

const stageInfo = computed(() => {
  const stages = {
    sprouting: { name: '🌱 萌芽期', color: '#67c23a', range: '0-30' },
    growing: { name: '🌿 成长期', color: '#e6a23c', range: '30-100' },
    maturing: { name: '🌳 成熟期', color: '#409eff', range: '100-300' },
    specializing: { name: '🏆 专精期', color: '#f56c6c', range: '300+' },
  }
  return stages[evolution.value.stage] || stages.sprouting
})

const stageProgress = computed(() => {
  const total = evolution.value.total_level || 0
  const thresholds = [0, 30, 100, 300]
  const stage = evolution.value.stage
  const idx = ['sprouting', 'growing', 'maturing', 'specializing'].indexOf(stage)
  if (idx === 3) return 100
  const min = thresholds[idx] || 0
  const max = thresholds[idx + 1] || 300
  return Math.min(100, ((total - min) / (max - min)) * 100)
})

const fetchData = async () => {
  loading.value = true
  try {
    const [statusRes, logsRes] = await Promise.all([
      getStatus(),
      getLogs(20, 0),
    ])
    status.value = statusRes.data.system || {}
    evolution.value = statusRes.data.evolution || {}
    recentLogs.value = logsRes.data.lines || []
  } catch (e) {
    console.error('获取数据失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="dashboard" v-loading="loading">
    <!-- 状态卡片行 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" :style="{ background: status.running ? '#e8f5e9' : '#fbe9e7' }">
            <el-icon :size="24" :color="status.running ? '#4caf50' : '#f44336'">
              <component :is="status.running ? 'CircleCheck' : 'CircleClose'" />
            </el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ status.running ? '运行中' : '已停止' }}</div>
            <div class="stat-label">系统状态</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #e3f2fd">
            <el-icon :size="24" color="#1976d2"><Odometer /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ evolution.total_level || 0 }}</div>
            <div class="stat-label">总等级</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #fff3e0">
            <el-icon :size="24" color="#ef6c00"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ status.evolution_count || 0 }}</div>
            <div class="stat-label">进化次数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #f3e5f5">
            <el-icon :size="24" color="#7b1fa2"><Timer /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">第 {{ status.current_generation || 0 }} 代</div>
            <div class="stat-label">当前代际</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 进化阶段 + 双树概览 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <div class="panel">
          <div class="panel-title">📊 进化阶段</div>
          <div class="stage-display">
            <div class="stage-name" :style="{ color: stageInfo.color }">
              {{ stageInfo.name }}
            </div>
            <div class="stage-range">等级范围: {{ stageInfo.range }}</div>
            <el-progress
              :percentage="stageProgress"
              :color="stageInfo.color"
              :stroke-width="12"
              style="margin-top: 12px"
            />
          </div>

          <el-divider />

          <div class="priority-display">
            <div class="priority-title">当前优先级</div>
            <div class="priority-bars">
              <div class="priority-item">
                <span class="priority-label">通用技能</span>
                <el-progress
                  :percentage="(evolution.priority?.general || 0.8) * 100"
                  color="#409eff"
                  :stroke-width="10"
                />
              </div>
              <div class="priority-item">
                <span class="priority-label">专业技能</span>
                <el-progress
                  :percentage="(evolution.priority?.domain || 0.2) * 100"
                  color="#e6a23c"
                  :stroke-width="10"
                />
              </div>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="panel">
          <div class="panel-title">🌳 技能树概览</div>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="tree-summary">
                <div class="tree-icon">📚</div>
                <div class="tree-name">通用技能</div>
                <div class="tree-level">Lv.{{ evolution.general?.level_sum || 0 }}</div>
                <div class="tree-unlock">
                  {{ evolution.general?.unlocked || 0 }} / {{ evolution.general?.total || 0 }} 已解锁
                </div>
                <el-progress
                  :percentage="evolution.general?.total ? (evolution.general.unlocked / evolution.general.total * 100) : 0"
                  color="#409eff"
                  :stroke-width="8"
                  style="margin-top: 8px"
                />
              </div>
            </el-col>
            <el-col :span="12">
              <div class="tree-summary">
                <div class="tree-icon">⚖️</div>
                <div class="tree-name">专业技能</div>
                <div class="tree-level">Lv.{{ evolution.domain?.level_sum || 0 }}</div>
                <div class="tree-unlock">
                  {{ evolution.domain?.unlocked || 0 }} / {{ evolution.domain?.total || 0 }} 已解锁
                </div>
                <el-progress
                  :percentage="evolution.domain?.total ? (evolution.domain.unlocked / evolution.domain.total * 100) : 0"
                  color="#e6a23c"
                  :stroke-width="8"
                  style="margin-top: 8px"
                />
              </div>
            </el-col>
          </el-row>
        </div>
      </el-col>
    </el-row>

    <!-- 最近日志 -->
    <div class="panel" style="margin-top: 16px">
      <div class="panel-title">
        📜 最近进化记录
        <el-button size="small" text @click="fetchData">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
      <el-table :data="recentLogs" size="small" max-height="300" stripe>
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column prop="level" label="级别" width="80">
          <template #default="{ row }">
            <el-tag
              :type="row.level === 'ERROR' ? 'danger' : row.level === 'WARNING' ? 'warning' : 'info'"
              size="small"
            >{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="160" />
        <el-table-column prop="message" label="内容" show-overflow-tooltip />
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.stat-row .stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stage-display {
  text-align: center;
  padding: 8px 0;
}
.stage-name {
  font-size: 24px;
  font-weight: 700;
}
.stage-range {
  color: #999;
  font-size: 13px;
  margin-top: 4px;
}
.priority-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}
.priority-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.priority-label {
  width: 70px;
  font-size: 13px;
  color: #666;
  flex-shrink: 0;
}
.priority-item .el-progress {
  flex: 1;
}
.tree-summary {
  text-align: center;
  padding: 16px 8px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
}
.tree-icon {
  font-size: 32px;
}
.tree-name {
  font-weight: 600;
  margin: 4px 0;
}
.tree-level {
  font-size: 22px;
  font-weight: 700;
  color: #333;
}
.tree-unlock {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
</style>
