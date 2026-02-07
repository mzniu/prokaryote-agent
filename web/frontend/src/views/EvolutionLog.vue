<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getLogs } from '../api'

const logs = ref([])
const liveLogs = ref([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const wsConnected = ref(false)
let ws = null

const levelFilters = [
  { text: 'INFO', value: 'INFO' },
  { text: 'WARNING', value: 'WARNING' },
  { text: 'ERROR', value: 'ERROR' },
  { text: 'DEBUG', value: 'DEBUG' },
]

const filterLevel = (value, row) => row.level === value

const fetchLogs = async () => {
  loading.value = true
  try {
    const offset = (page.value - 1) * pageSize.value
    const res = await getLogs(pageSize.value, offset)
    logs.value = res.data.lines || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('获取日志失败:', e)
  } finally {
    loading.value = false
  }
}

const connectWebSocket = () => {
  try {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${wsProtocol}//${window.location.host}/api/logs/ws`)
    ws.onopen = () => { wsConnected.value = true }
    ws.onclose = () => {
      wsConnected.value = false
      // 自动重连
      setTimeout(connectWebSocket, 3000)
    }
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'log') {
        liveLogs.value.unshift({
          timestamp: new Date().toLocaleTimeString(),
          message: msg.data,
          level: 'INFO',
          module: '',
        })
        // 只保留最新 200 条
        if (liveLogs.value.length > 200) {
          liveLogs.value = liveLogs.value.slice(0, 200)
        }
      }
    }
  } catch (e) {
    console.error('WebSocket 连接失败:', e)
  }
}

onMounted(() => {
  fetchLogs()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) ws.close()
})
</script>

<template>
  <div class="log-page">
    <!-- 实时日志 -->
    <div class="panel" style="margin-bottom: 16px">
      <div class="panel-title">
        🔴 实时日志
        <el-tag :type="wsConnected ? 'success' : 'danger'" size="small" style="margin-left: 8px">
          {{ wsConnected ? '已连接' : '未连接' }}
        </el-tag>
      </div>
      <div class="live-log-container">
        <div v-if="liveLogs.length === 0" class="empty-log">等待新日志...</div>
        <div v-for="(log, i) in liveLogs" :key="i" class="live-log-line">
          <span class="log-time">{{ log.timestamp }}</span>
          <span class="log-msg">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <!-- 历史日志 -->
    <div class="panel">
      <div class="panel-title">
        📜 历史日志
        <el-button text size="small" @click="fetchLogs">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
      <el-table :data="logs" size="small" stripe v-loading="loading" max-height="500">
        <el-table-column prop="timestamp" label="时间" width="180" sortable />
        <el-table-column prop="level" label="级别" width="100"
          :filters="levelFilters" :filter-method="filterLevel">
          <template #default="{ row }">
            <el-tag
              :type="row.level === 'ERROR' ? 'danger' : row.level === 'WARNING' ? 'warning' : 'info'"
              size="small"
            >{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="180" />
        <el-table-column prop="message" label="内容" show-overflow-tooltip />
      </el-table>
      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        style="margin-top: 12px; justify-content: flex-end"
        @current-change="fetchLogs"
      />
    </div>
  </div>
</template>

<style scoped>
.live-log-container {
  background: #1e1e2e;
  border-radius: 6px;
  padding: 12px;
  max-height: 250px;
  overflow-y: auto;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px;
}
.live-log-line {
  padding: 2px 0;
  color: #cdd6f4;
  word-break: break-all;
}
.log-time {
  color: #6c7086;
  margin-right: 8px;
}
.log-msg {
  color: #a6e3a1;
}
.empty-log {
  color: #6c7086;
  text-align: center;
  padding: 20px;
}
</style>
