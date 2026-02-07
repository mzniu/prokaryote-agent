<script setup>
import { ref, onMounted } from 'vue'
import {
  getGoals, createGoal, updateGoalStatus, deleteGoal,
  getConfig, updateConfig, triggerEvolution, startEvolution,
  stopEvolution, getEvolutionRunning,
} from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

// 目标
const goals = ref([])
const goalStats = ref({})
const showGoalDialog = ref(false)
const newGoal = ref({ title: '', description: '', priority: 'medium', acceptance_criteria: '' })

// 配置
const config = ref({
  specialization: { dual_tree_mode: false, auto_inject_goals: false, domain_name: '' },
  restart_trigger: { threshold: 10 },
})
const configLoading = ref(false)

// 进化控制
const evolutionRunning = ref(false)

const statusTypes = {
  pending: 'info', in_progress: 'warning',
  completed: 'success', failed: 'danger', skipped: '',
}
const statusNames = {
  pending: '待执行', in_progress: '进行中',
  completed: '已完成', failed: '失败', skipped: '跳过',
}
const priorityTypes = {
  critical: 'danger', high: 'warning', medium: '', low: 'success',
}

const fetchGoals = async () => {
  try {
    const res = await getGoals()
    goals.value = res.data.goals || []
    goalStats.value = res.data.stats || {}
  } catch (e) { console.error(e) }
}

const fetchConfig = async () => {
  configLoading.value = true
  try {
    const res = await getConfig()
    // 深度合并，保持默认结构
    const data = res.data || {}
    config.value = {
      ...config.value,
      ...data,
      specialization: { ...config.value.specialization, ...(data.specialization || {}) },
      restart_trigger: { ...config.value.restart_trigger, ...(data.restart_trigger || {}) },
    }
  } catch (e) { console.error(e) }
  finally { configLoading.value = false }
}

const checkEvolutionStatus = async () => {
  try {
    const res = await getEvolutionRunning()
    evolutionRunning.value = res.data.running
  } catch { /* ignore */ }
}

const handleCreateGoal = async () => {
  const criteria = newGoal.value.acceptance_criteria
    ? newGoal.value.acceptance_criteria.split('\n').filter(Boolean)
    : []
  try {
    await createGoal({ ...newGoal.value, acceptance_criteria: criteria })
    ElMessage.success('目标已创建')
    showGoalDialog.value = false
    newGoal.value = { title: '', description: '', priority: 'medium', acceptance_criteria: '' }
    fetchGoals()
  } catch { ElMessage.error('创建失败') }
}

const handleStatusChange = async (goalId, status) => {
  try {
    await updateGoalStatus(goalId, status)
    ElMessage.success('状态已更新')
    fetchGoals()
  } catch { ElMessage.error('更新失败') }
}

const handleDeleteGoal = async (goalId) => {
  try {
    await ElMessageBox.confirm('确认删除此目标？', '删除目标')
    await deleteGoal(goalId)
    ElMessage.success('已删除')
    fetchGoals()
  } catch { /* cancelled */ }
}

const handleTriggerEvolution = async () => {
  try {
    ElMessage.info('正在触发进化...')
    const res = await triggerEvolution()
    ElMessage.success(res.data.message || '已触发')
  } catch (e) {
    ElMessage.error('触发失败: ' + (e.response?.data?.error || e.message))
  }
}

const handleToggleEvolution = async () => {
  try {
    if (evolutionRunning.value) {
      await stopEvolution()
      ElMessage.success('已停止自动进化')
    } else {
      await startEvolution()
      ElMessage.success('自动进化已启动')
    }
    setTimeout(checkEvolutionStatus, 1000)
  } catch { ElMessage.error('操作失败') }
}

const saveConfig = async () => {
  try {
    const spec = config.value.specialization || {}
    await updateConfig({
      specialization: {
        dual_tree_mode: spec.dual_tree_mode,
        auto_inject_goals: spec.auto_inject_goals,
      },
      restart_trigger: config.value.restart_trigger,
    })
    ElMessage.success('配置已保存')
  } catch { ElMessage.error('保存失败') }
}

onMounted(() => {
  fetchGoals()
  fetchConfig()
  checkEvolutionStatus()
})
</script>

<template>
  <div class="config-page">
    <!-- 进化控制 -->
    <div class="panel" style="margin-bottom: 16px">
      <div class="panel-title">🎮 进化控制</div>
      <div class="control-row">
        <el-button type="primary" @click="handleTriggerEvolution">
          <el-icon><VideoPlay /></el-icon> 触发一次进化
        </el-button>
        <el-button
          :type="evolutionRunning ? 'danger' : 'success'"
          @click="handleToggleEvolution"
        >
          <el-icon><component :is="evolutionRunning ? 'VideoPause' : 'VideoPlay'" /></el-icon>
          {{ evolutionRunning ? '停止自动进化' : '启动自动进化' }}
        </el-button>
        <el-tag :type="evolutionRunning ? 'success' : 'info'" style="margin-left: 12px">
          {{ evolutionRunning ? '自动进化运行中' : '自动进化已停止' }}
        </el-tag>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 目标管理 -->
      <el-col :span="14">
        <div class="panel">
          <div class="panel-title">
            🎯 进化目标
            <el-button size="small" type="primary" @click="showGoalDialog = true">
              <el-icon><Plus /></el-icon> 新目标
            </el-button>
          </div>

          <div class="goal-stats">
            <el-tag>总计 {{ goalStats.total || 0 }}</el-tag>
            <el-tag type="success">已完成 {{ goalStats.completed || 0 }}</el-tag>
            <el-tag type="info">待执行 {{ goalStats.pending || 0 }}</el-tag>
            <el-tag type="warning">进行中 {{ goalStats.in_progress || 0 }}</el-tag>
          </div>

          <el-table :data="goals" size="small" stripe style="margin-top: 12px">
            <el-table-column prop="title" label="目标" min-width="200" />
            <el-table-column prop="priority" label="优先级" width="90">
              <template #default="{ row }">
                <el-tag :type="priorityTypes[row.priority]" size="small">{{ row.priority }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTypes[row.status]" size="small">
                  {{ statusNames[row.status] }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-dropdown trigger="click" @command="(cmd) => handleStatusChange(row.id, cmd)">
                  <el-button text size="small">
                    状态 <el-icon><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="pending">待执行</el-dropdown-item>
                      <el-dropdown-item command="in_progress">进行中</el-dropdown-item>
                      <el-dropdown-item command="completed">已完成</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-button text size="small" type="danger" @click="handleDeleteGoal(row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>

      <!-- 策略配置 -->
      <el-col :span="10">
        <div class="panel" v-loading="configLoading">
          <div class="panel-title">⚙️ 策略配置</div>

          <el-form label-position="top" size="small">
            <el-form-item label="双树进化模式">
              <el-switch v-model="config.specialization.dual_tree_mode" />
            </el-form-item>
            <el-form-item label="自动注入目标">
              <el-switch v-model="config.specialization.auto_inject_goals" />
            </el-form-item>
            <el-form-item label="代际重启阈值">
              <el-input-number
                v-model="config.restart_trigger.threshold"
                :min="1" :max="100"
              />
              <span style="margin-left: 8px; color: #999; font-size: 12px">次进化</span>
            </el-form-item>
            <el-form-item label="专业领域">
              <el-input :value="config.specialization?.domain_name" disabled />
            </el-form-item>

            <el-button type="primary" @click="saveConfig" style="width: 100%; margin-top: 8px">
              保存配置
            </el-button>
          </el-form>
        </div>
      </el-col>
    </el-row>

    <!-- 新建目标对话框 -->
    <el-dialog v-model="showGoalDialog" title="创建进化目标" width="500">
      <el-form :model="newGoal" label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="newGoal.title" placeholder="目标标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newGoal.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="newGoal.priority" style="width: 100%">
            <el-option label="关键" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        <el-form-item label="验收标准">
          <el-input v-model="newGoal.acceptance_criteria" type="textarea" :rows="3"
            placeholder="每行一条验收标准" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGoalDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGoal">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.control-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.goal-stats {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
</style>
