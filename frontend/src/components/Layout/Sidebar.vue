<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <div class="logo-icon">
          <el-icon :size="24"><Magic /></el-icon>
        </div>
        <div class="logo-text">
          <span class="logo-title">StyleAI</span>
          <span class="logo-subtitle">智能风格迁移</span>
        </div>
      </div>
    </div>

    <nav class="nav-menu">
      <div class="nav-section">
        <span class="nav-section-title">核心功能</span>
        <router-link
          v-for="route in mainRoutes"
          :key="route.path"
          :to="route.path"
          :class="['nav-item', { active: $route.path === route.path }]"
        >
          <div class="nav-icon">
            <el-icon :size="20">
              <component :is="route.meta.icon" />
            </el-icon>
          </div>
          <span class="nav-label">{{ route.meta.title }}</span>
          <div v-if="$route.path === route.path" class="nav-indicator" />
        </router-link>
      </div>

      <div class="nav-section">
        <span class="nav-section-title">管理</span>
        <router-link
          v-for="route in manageRoutes"
          :key="route.path"
          :to="route.path"
          :class="['nav-item', { active: $route.path === route.path }]"
        >
          <div class="nav-icon">
            <el-icon :size="20">
              <component :is="route.meta.icon" />
            </el-icon>
          </div>
          <span class="nav-label">{{ route.meta.title }}</span>
          <div v-if="$route.path === route.path" class="nav-indicator" />
        </router-link>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="footer-card">
        <div class="footer-icon">
          <el-icon :size="16"><InfoFilled /></el-icon>
        </div>
        <div class="footer-info">
          <span class="version">v0.1.0 Beta</span>
          <span class="status">
            <span class="status-dot" />
            系统正常运行
          </span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Magic, InfoFilled } from '@element-plus/icons-vue'
import router from '@/router'

const $route = useRoute()

const allRoutes = computed(() =>
  router.getRoutes().filter(r => r.meta?.title)
)

const mainRoutes = computed(() =>
  allRoutes.value.filter(r => !r.meta?.isManagement)
)

const manageRoutes = computed(() =>
  allRoutes.value.filter(r => r.meta?.isManagement)
)
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  width: 260px;
  height: 100vh;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  display: flex;
  flex-direction: column;
  z-index: 100;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 44px;
  height: 44px;
  background: var(--primary-gradient);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: var(--shadow-glow);
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-size: 20px;
  font-weight: 700;
  color: white;
  letter-spacing: -0.5px;
}

.logo-subtitle {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 2px;
}

.nav-menu {
  flex: 1;
  padding: 20px 16px;
  overflow-y: auto;
}

.nav-section {
  margin-bottom: 24px;
}

.nav-section-title {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.4);
  padding: 0 12px;
  margin-bottom: 8px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 4px;
  color: rgba(255, 255, 255, 0.6);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  overflow: hidden;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  transform: translateX(4px);
}

.nav-item.active {
  background: rgba(102, 126, 234, 0.15);
  color: white;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--transition-fast);
}

.nav-item:hover .nav-icon {
  transform: scale(1.1);
}

.nav-label {
  font-size: 14px;
  font-weight: 500;
}

.nav-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--primary-gradient);
  border-radius: 0 3px 3px 0;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.footer-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.footer-icon {
  width: 32px;
  height: 32px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--success-color);
}

.footer-info {
  display: flex;
  flex-direction: column;
}

.version {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}

.status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 2px;
}

.status-dot {
  width: 6px;
  height: 6px;
  background: var(--success-color);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
