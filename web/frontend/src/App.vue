<script setup>
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const menuItems = [
  { path: '/dashboard', title: '仪表盘', icon: 'Odometer' },
  { path: '/skill-tree', title: '技能树', icon: 'Share' },
  { path: '/evolution-log', title: '进化日志', icon: 'Document' },
  { path: '/evolution-config', title: '进化配置', icon: 'Setting' },
  { path: '/knowledge', title: '知识库', icon: 'Reading' },
  { path: '/agent-test', title: 'Agent测试', icon: 'ChatDotRound' },
]

const handleSelect = (path) => {
  router.push(path)
}
</script>

<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="app-aside">
      <div class="logo-area">
        <span class="logo-icon">🧬</span>
        <span class="logo-text">原智控制台</span>
      </div>
      <el-menu
        :default-active="route.path"
        class="side-menu"
        background-color="#1d1e2c"
        text-color="#a0a4b8"
        active-text-color="#409eff"
        @select="handleSelect"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
      <div class="aside-footer">
        <span class="version">v0.3 · 双树进化版</span>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <el-header class="app-header">
        <div class="header-title">
          <h2>{{ route.meta?.title || '原智' }}</h2>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-container {
  height: 100vh;
}
.app-aside {
  background: #1d1e2c;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #2d2e3e;
}
.logo-area {
  padding: 20px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #2d2e3e;
}
.logo-icon {
  font-size: 28px;
}
.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #e0e2f0;
  letter-spacing: 1px;
}
.side-menu {
  flex: 1;
  border-right: none !important;
}
.aside-footer {
  padding: 12px 16px;
  border-top: 1px solid #2d2e3e;
  text-align: center;
}
.version {
  color: #555;
  font-size: 12px;
}
.app-header {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 56px;
}
.header-title h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}
.app-main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
