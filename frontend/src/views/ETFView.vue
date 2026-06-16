<template>
  <div class="etf-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>ETF 查询</h2>
          <el-input
            v-model="keyword"
            placeholder="输入关键词搜索ETF"
            style="width: 300px"
            clearable
            @keyup.enter="searchETF"
          >
            <template #append>
              <el-button @click="searchETF" :loading="loading">搜索</el-button>
            </template>
          </el-input>
        </div>
      </template>

      <el-table :data="etfList" v-loading="loading" stripe>
        <el-table-column prop="代码" label="代码" width="100" />
        <el-table-column prop="名称" label="名称" width="200" />
        <el-table-column prop="最新价" label="最新价" width="100" />
        <el-table-column prop="涨跌幅" label="涨跌幅" width="100">
          <template #default="{ row }">
            <span :style="{ color: row['涨跌幅'] > 0 ? '#f56c6c' : row['涨跌幅'] < 0 ? '#67c23a' : '' }">
              {{ row['涨跌幅'] }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="成交额" label="成交额" width="120" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="viewQuote(row['代码'])">行情</el-button>
            <el-button size="small" @click="viewHistory(row['代码'])">历史</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 实时行情弹窗 -->
    <el-dialog v-model="quoteDialogVisible" :title="`${currentSymbol} 实时行情`" width="500px">
      <div v-if="quoteData" class="quote-info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称">{{ quoteData.name }}</el-descriptions-item>
          <el-descriptions-item label="最新价">{{ quoteData.price }}</el-descriptions-item>
          <el-descriptions-item label="涨跌幅">
            <span :style="{ color: quoteData.change_pct > 0 ? '#f56c6c' : '#67c23a' }">
              {{ quoteData.change_pct }}%
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="涨跌额">{{ quoteData.change_amt }}</el-descriptions-item>
          <el-descriptions-item label="开盘价">{{ quoteData.open }}</el-descriptions-item>
          <el-descriptions-item label="最高价">{{ quoteData.high }}</el-descriptions-item>
          <el-descriptions-item label="最低价">{{ quoteData.low }}</el-descriptions-item>
          <el-descriptions-item label="昨收价">{{ quoteData.prev_close }}</el-descriptions-item>
          <el-descriptions-item label="成交量">{{ quoteData.volume }}</el-descriptions-item>
          <el-descriptions-item label="成交额">{{ quoteData.amount }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { etfApi } from '../api'
import { ElMessage } from 'element-plus'

const keyword = ref('')
const etfList = ref([])
const loading = ref(false)
const quoteDialogVisible = ref(false)
const currentSymbol = ref('')
const quoteData = ref(null)

async function searchETF() {
  loading.value = true
  try {
    const res = await etfApi.getList(keyword.value || undefined)
    etfList.value = res.data || []
    if (etfList.value.length === 0) {
      ElMessage.info('未找到匹配的ETF')
    }
  } catch (e) {
    ElMessage.error('查询失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function viewQuote(symbol) {
  currentSymbol.value = symbol
  try {
    const res = await etfApi.getQuote(symbol)
    quoteData.value = res.data
    quoteDialogVisible.value = true
  } catch (e) {
    ElMessage.error('获取行情失败: ' + e.message)
  }
}

function viewHistory(symbol) {
  ElMessage.info('历史数据功能请前往数据分析页面')
}
</script>

<style scoped>
.etf-view { max-width: 1200px; margin: 0 auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-header h2 { margin: 0; }
</style>
