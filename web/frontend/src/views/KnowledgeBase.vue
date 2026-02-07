<script setup>
import { ref, onMounted, computed } from 'vue'
import { getKnowledge, getKnowledgeDetail } from '../api'
import { marked } from 'marked'
import { ElMessage } from 'element-plus'

const knowledgeList = ref([])
const loading = ref(true)
const searchQuery = ref('')
const selectedItem = ref(null)
const detailContent = ref('')
const detailLoading = ref(false)

const fetchKnowledge = async () => {
  loading.value = true
  try {
    const params = {}
    if (searchQuery.value) params.q = searchQuery.value
    const res = await getKnowledge(params)
    knowledgeList.value = res.data.items || []
  } catch (e) {
    console.error('获取知识库失败:', e)
  } finally {
    loading.value = false
  }
}

const viewDetail = async (item) => {
  selectedItem.value = item
  detailLoading.value = true
  try {
    const res = await getKnowledgeDetail(item.id)
    detailContent.value = res.data.content || '无内容'
  } catch {
    detailContent.value = '获取详情失败'
  } finally {
    detailLoading.value = false
  }
}

const renderedContent = computed(() => {
  if (!detailContent.value) return ''
  return marked(detailContent.value)
})

const handleSearch = () => {
  fetchKnowledge()
}

onMounted(fetchKnowledge)
</script>

<template>
  <div class="knowledge-page">
    <el-row :gutter="16">
      <!-- 列表 -->
      <el-col :span="selectedItem ? 10 : 24">
        <div class="panel">
          <div class="panel-title">📚 知识库</div>

          <div class="search-bar">
            <el-input
              v-model="searchQuery"
              placeholder="搜索知识..."
              clearable
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            >
              <template #append>
                <el-button @click="handleSearch">
                  <el-icon><Search /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>

          <el-table
            :data="knowledgeList"
            size="small"
            stripe
            v-loading="loading"
            @row-click="viewDetail"
            style="cursor: pointer; margin-top: 12px"
          >
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="domain" label="领域" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.domain || '-' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="类别" width="120" />
            <el-table-column prop="quality_score" label="质量" width="80">
              <template #default="{ row }">
                <el-rate
                  :model-value="(row.quality_score || 0) * 5"
                  disabled
                  :max="5"
                  size="small"
                  style="display:inline-flex"
                />
              </template>
            </el-table-column>
          </el-table>

          <div v-if="knowledgeList.length === 0 && !loading" class="empty-state">
            暂无知识条目
          </div>
        </div>
      </el-col>

      <!-- 详情预览 -->
      <el-col v-if="selectedItem" :span="14">
        <div class="panel detail-panel" v-loading="detailLoading">
          <div class="panel-title">
            {{ selectedItem.title }}
            <el-button text size="small" @click="selectedItem = null">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>

          <div class="detail-meta">
            <el-tag size="small">{{ selectedItem.domain }}</el-tag>
            <el-tag size="small" type="info">{{ selectedItem.category }}</el-tag>
            <span v-if="selectedItem.created_at" class="meta-time">
              {{ selectedItem.created_at }}
            </span>
          </div>

          <div v-if="selectedItem.keywords?.length" class="keywords">
            <el-tag v-for="kw in selectedItem.keywords" :key="kw" size="small"
              type="info" style="margin: 2px">{{ kw }}</el-tag>
          </div>

          <el-divider />

          <div class="markdown-body" v-html="renderedContent"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.search-bar {
  margin-top: 8px;
}
.detail-panel {
  max-height: calc(100vh - 120px);
  overflow-y: auto;
}
.detail-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.meta-time {
  font-size: 12px;
  color: #999;
}
.keywords {
  margin-top: 8px;
}
.markdown-body {
  line-height: 1.8;
  font-size: 14px;
}
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 16px 0 8px;
  font-weight: 600;
}
.markdown-body :deep(pre) {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
}
.markdown-body :deep(code) {
  background: #f0f0f0;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 13px;
}
.empty-state {
  text-align: center;
  color: #999;
  padding: 40px;
}
</style>
