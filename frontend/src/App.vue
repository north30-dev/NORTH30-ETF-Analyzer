<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-title">
        <h1>ETF 分析工具</h1>
      </div>
      <el-menu mode="horizontal" :default-active="activeMenu" router>
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/etf">ETF查询</el-menu-item>
        <el-menu-item index="/analysis">数据分析</el-menu-item>
        <el-menu-item index="/charts">图表中心</el-menu-item>
        <el-menu-item index="/report">报告生成</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
.app-container { min-height: 100vh; }
.app-header { display: flex; align-items: center; background: #fff; border-bottom: 1px solid #e4e7ed; padding: 0 20px; }
.header-title h1 { font-size: 20px; color: #409eff; margin-right: 40px; white-space: nowrap; }
.app-main { padding: 20px; background: #f5f7fa; }
</style>
