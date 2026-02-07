<script setup>
import { ref, onMounted, computed } from 'vue'
import { getGeneralTree, getDomainTree, unlockSkill, addSkill } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const generalTree = ref({ skills: {} })
const domainTree = ref({ skills: {} })
const loading = ref(true)
const activeTab = ref('general')
const selectedSkill = ref(null)
const showAddDialog = ref(false)

const newSkill = ref({
  id: '', name: '', category: 'knowledge_acquisition',
  tier: 'basic', max_level: 20, prerequisites: '',
  description: '', unlocked: false,
})

const tierColors = {
  basic: '#67c23a',
  intermediate: '#409eff',
  advanced: '#e6a23c',
  master: '#f56c6c',
  expert: '#9c27b0',
}

const tierNames = {
  basic: '基础', intermediate: '中级',
  advanced: '高级', master: '大师', expert: '专家',
}

const categoryNames = {
  knowledge_acquisition: '📚 知识获取',
  world_interaction: '🌐 外界交互',
  self_evolution: '🧬 自我进化',
}

const generalSkillsByCategory = computed(() => {
  const groups = {}
  for (const [id, skill] of Object.entries(generalTree.value.skills || {})) {
    const cat = skill.category || 'other'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push({ ...skill, id })
  }
  return groups
})

const domainSkillsByTier = computed(() => {
  const groups = {}
  for (const [id, skill] of Object.entries(domainTree.value.skills || {})) {
    const tier = skill.tier || 'basic'
    if (!groups[tier]) groups[tier] = []
    groups[tier].push({ ...skill, id })
  }
  // 按层级排序
  const order = ['basic', 'intermediate', 'advanced', 'master', 'expert']
  const sorted = {}
  for (const t of order) {
    if (groups[t]) sorted[t] = groups[t]
  }
  return sorted
})

const fetchData = async () => {
  loading.value = true
  try {
    const [gRes, dRes] = await Promise.all([getGeneralTree(), getDomainTree()])
    generalTree.value = normalizeTree(gRes.data)
    domainTree.value = normalizeTree(dRes.data)
  } catch (e) {
    ElMessage.error('获取技能树失败')
  } finally {
    loading.value = false
  }
}

const selectSkill = (skill) => {
  selectedSkill.value = skill
}

const handleUnlock = async (treeType, skillId) => {
  try {
    await ElMessageBox.confirm(`确认解锁技能 "${skillId}"？`, '手动解锁')
    await unlockSkill(treeType, skillId)
    ElMessage.success('已解锁')
    fetchData()
  } catch { /* cancelled */ }
}

const handleAddSkill = async () => {
  const data = {
    ...newSkill.value,
    prerequisites: newSkill.value.prerequisites
      ? newSkill.value.prerequisites.split(',').map(s => s.trim()).filter(Boolean)
      : [],
  }
  try {
    const res = await addSkill(activeTab.value, data)
    if (res.data.success) {
      ElMessage.success('技能已添加')
      showAddDialog.value = false
      newSkill.value = { id: '', name: '', category: 'knowledge_acquisition', tier: 'basic', max_level: 20, prerequisites: '', description: '', unlocked: false }
      fetchData()
    } else {
      ElMessage.error(res.data.error)
    }
  } catch (e) {
    ElMessage.error('添加失败')
  }
}

const getMaxLevel = (skill) => {
  return skill.max_level || { basic: 20, intermediate: 30, advanced: 50, master: 70, expert: 100 }[skill.tier] || 20
}

const normalizeTree = (tree) => {
  // 将 prerequisites 字符串转为数组
  if (tree.skills) {
    for (const skill of Object.values(tree.skills)) {
      if (typeof skill.prerequisites === 'string') {
        skill.prerequisites = skill.prerequisites.split(/[\s,]+/).filter(Boolean)
      }
    }
  }
  return tree
}

const getLevelPercent = (skill) => {
  const max = getMaxLevel(skill)
  return max > 0 ? (skill.level / max) * 100 : 0
}

onMounted(fetchData)
</script>

<template>
  <div class="skill-tree-page" v-loading="loading">
    <div class="tree-header">
      <el-radio-group v-model="activeTab" size="large">
        <el-radio-button value="general">📚 通用技能树</el-radio-button>
        <el-radio-button value="domain">⚖️ 专业技能树</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon> 添加技能
      </el-button>
    </div>

    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 技能列表 -->
      <el-col :span="selectedSkill ? 16 : 24">
        <!-- 通用技能树 -->
        <template v-if="activeTab === 'general'">
          <div v-for="(skills, cat) in generalSkillsByCategory" :key="cat" class="panel" style="margin-bottom: 16px">
            <div class="panel-title">{{ categoryNames[cat] || cat }}</div>
            <div class="skill-grid">
              <div
                v-for="skill in skills" :key="skill.id"
                class="skill-node"
                :class="{ locked: !skill.unlocked, active: selectedSkill?.id === skill.id }"
                @click="selectSkill(skill)"
              >
                <div class="skill-node-header">
                  <span class="skill-name">{{ skill.name }}</span>
                  <el-tag :color="tierColors[skill.tier]" size="small" effect="dark" style="border:none; color:#fff">
                    {{ tierNames[skill.tier] }}
                  </el-tag>
                </div>
                <div class="skill-level">
                  Lv.{{ skill.level }} / {{ getMaxLevel(skill) }}
                </div>
                <el-progress
                  :percentage="getLevelPercent(skill)"
                  :color="tierColors[skill.tier]"
                  :stroke-width="6"
                  :show-text="false"
                />
                <div v-if="!skill.unlocked" class="lock-overlay">
                  <el-icon :size="20"><Lock /></el-icon>
                </div>
                <div v-if="skill.ai_generated" class="ai-badge">✨</div>
              </div>
            </div>
          </div>
        </template>

        <!-- 专业技能树 -->
        <template v-else>
          <div v-for="(skills, tier) in domainSkillsByTier" :key="tier" class="panel" style="margin-bottom: 16px">
            <div class="panel-title">
              <el-tag :color="tierColors[tier]" effect="dark" style="border:none; color:#fff">
                {{ tierNames[tier] }}
              </el-tag>
              层技能
            </div>
            <div class="skill-grid">
              <div
                v-for="skill in skills" :key="skill.id"
                class="skill-node"
                :class="{ locked: !skill.unlocked, active: selectedSkill?.id === skill.id }"
                @click="selectSkill(skill)"
              >
                <div class="skill-node-header">
                  <span class="skill-name">{{ skill.name }}</span>
                </div>
                <div class="skill-level">
                  Lv.{{ skill.level }} / {{ getMaxLevel(skill) }}
                </div>
                <el-progress
                  :percentage="getLevelPercent(skill)"
                  :color="tierColors[tier]"
                  :stroke-width="6"
                  :show-text="false"
                />
                <div v-if="!skill.unlocked" class="lock-overlay">
                  <el-icon :size="20"><Lock /></el-icon>
                </div>
              </div>
            </div>
          </div>
        </template>
      </el-col>

      <!-- 详情面板 -->
      <el-col v-if="selectedSkill" :span="8">
        <div class="panel detail-panel">
          <div class="panel-title">
            技能详情
            <el-button text size="small" @click="selectedSkill = null">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>

          <div class="detail-name">{{ selectedSkill.name }}</div>
          <div class="detail-id">{{ selectedSkill.id }}</div>

          <el-descriptions :column="1" border size="small" style="margin-top: 12px">
            <el-descriptions-item label="层级">
              <el-tag :color="tierColors[selectedSkill.tier]" size="small" effect="dark" style="border:none; color:#fff">
                {{ tierNames[selectedSkill.tier] }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="等级">
              {{ selectedSkill.level }} / {{ getMaxLevel(selectedSkill) }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="selectedSkill.unlocked ? 'success' : 'info'" size="small">
                {{ selectedSkill.unlocked ? '已解锁' : '未解锁' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="selectedSkill.category" label="类别">
              {{ categoryNames[selectedSkill.category] || selectedSkill.category }}
            </el-descriptions-item>
            <el-descriptions-item v-if="selectedSkill.prerequisites?.length" label="前置技能">
              <el-tag v-for="p in selectedSkill.prerequisites" :key="p" size="small" style="margin: 2px">
                {{ p }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="selectedSkill.description" label="描述">
              {{ selectedSkill.description }}
            </el-descriptions-item>
            <el-descriptions-item v-if="selectedSkill.unlock_condition" label="解锁条件">
              <code>{{ selectedSkill.unlock_condition }}</code>
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="!selectedSkill.unlocked" style="margin-top: 16px">
            <el-button type="warning" @click="handleUnlock(activeTab, selectedSkill.id)" style="width: 100%">
              <el-icon><Unlock /></el-icon> 手动解锁
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 添加技能对话框 -->
    <el-dialog v-model="showAddDialog" title="添加自定义技能" width="500">
      <el-form :model="newSkill" label-width="80px">
        <el-form-item label="技能ID" required>
          <el-input v-model="newSkill.id" placeholder="如 data_analysis" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="newSkill.name" placeholder="技能名称" />
        </el-form-item>
        <el-form-item label="类别">
          <el-select v-model="newSkill.category" style="width: 100%">
            <el-option label="知识获取" value="knowledge_acquisition" />
            <el-option label="外界交互" value="world_interaction" />
            <el-option label="自我进化" value="self_evolution" />
          </el-select>
        </el-form-item>
        <el-form-item label="层级">
          <el-select v-model="newSkill.tier" style="width: 100%">
            <el-option label="基础" value="basic" />
            <el-option label="中级" value="intermediate" />
            <el-option label="高级" value="advanced" />
          </el-select>
        </el-form-item>
        <el-form-item label="前置技能">
          <el-input v-model="newSkill.prerequisites" placeholder="逗号分隔，如 web_search,file_ops" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newSkill.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddSkill">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.skill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.skill-node {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  background: #fff;
}
.skill-node:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}
.skill-node.active {
  border-color: #409eff;
  background: #f0f7ff;
}
.skill-node.locked {
  opacity: 0.6;
}
.skill-node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.skill-name {
  font-weight: 600;
  font-size: 14px;
}
.skill-level {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}
.lock-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  color: #ccc;
}
.ai-badge {
  position: absolute;
  top: -4px;
  left: -4px;
  font-size: 16px;
}
.detail-panel {
  position: sticky;
  top: 20px;
}
.detail-name {
  font-size: 20px;
  font-weight: 700;
}
.detail-id {
  font-size: 12px;
  color: #999;
  font-family: monospace;
}
</style>
