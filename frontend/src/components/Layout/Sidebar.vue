<template>
  <aside class="sidebar">
    <div class="logo">
      <el-icon :size="28"><Document /></el-icon>
      <span>风格迁移系统</span>
    </div>
    <nav class="nav-menu">
      <router-link
        v-for="route in routes"
        :key="route.path"
        :to="route.path"
        :class="['nav-item', { active: $route.path === route.path }]"
      >
        <el-icon :size="18">
          <component :is="route.meta.icon" />
        </el-icon>
        <span>{{ route.meta.title }}</span>
      </router-link>
    </nav>
    <div class="sidebar-footer">
      <span>v0.1.0</span>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Document } from '@element-plus/icons-vue'
import router from '@/router'

const $route = useRoute()

const routes = computed(() =>
  router.getRoutes().filter(r => r.meta?.title)
)
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  width: 220px;
  height: 100vh;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.logo {
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo span {
  font-size: 18px;
  font-weight: 600;
}

.nav-menu {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.nav-item.active {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.nav-item span {
  font-size: 14px;
}

.sidebar-footer {
  padding: 16px;
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
