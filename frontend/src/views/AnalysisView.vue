<template>
  <div class="analysis-view">
    <el-card>
      <template #header><h2>数据分析</h2></template>
      <el-form :model="form" label-width="100px" inline>
        <el-form-item label="ETF代码">
          <el-input v-model="form.symbol" placeholder="如 510300" />
        </el-form-item>
        <el-form-item label="起始日期">
          <el-input v-model="form.startDate" placeholder="YYYYMMDD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-input v-model="form.endDate" placeholder="YYYYMMDD" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="analyzeNavTrend" :loading="loading">净值分析</el-button>
          <el-button @click="analyzeRisk" :loading="loading">风险指标</el-button>
          <el-button @click="analyzeIndustry" :loading="loading">行业分布</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <div v-if="navResult" class="result-section">
        <h3>净值走势分析</h3>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="累计收益率">{{ navResult.cumulative_return }}%</el-descriptions-item>
          <el-descriptions-item label="年化收益率">{{ navResult.annualized_return }}%</el-descriptions-item>
          <el-descriptions-item label="趋势判断">{{ navResult.trend }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div v-if="riskResult" class="result-section">
        <h3>风险指标</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="年化波动率">{{ riskResult.annualized_volatility }}</el-descriptions-item>
          <el-descriptions-item label="最大回撤">{{ riskResult.max_drawdown }}%</el-descriptions-item>
          <el-descriptions-item label="夏普比率">{{ riskResult.sharpe_ratio }}</el-descriptions-item>
          <el-descriptions-item label="信息比率">{{ riskResult.information_ratio || 'N/A' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div v-if="industryResult" class="result-section">
        <h3>行业分布</h3>
        <el-table :data="industryResult.industry_distribution" stripe>
          <el-table-column prop="行业" label="行业" />
          <el-table-column prop="占比" label="占比" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { analysisApi } from '../api'
import { ElMessage } from 'element-plus'

const form = reactive({ symbol: '', startDate: '', endDate: '' })
const loading = ref(false)
const navResult = ref(null)
const riskResult = ref(null)
const industryResult = ref(null)

async function analyzeNavTrend() {
  if (!form.symbol) { ElMessage.warning('请输入ETF代码'); return }
  loading.value = true
  try {
    const res = await analysisApi.navTrend(form.symbol, form.startDate || undefined, form.endDate || undefined)
    navResult.value = res.data
    ElMessage.success('净值分析完成')
  } catch (e) {
    ElMessage.error('分析失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function analyzeRisk() {
  if (!form.symbol) { ElMessage.warning('请输入ETF代码'); return }
  loading.value = true
  try {
    const res = await analysisApi.riskMetrics(form.symbol, form.startDate || undefined, form.endDate || undefined)
    riskResult.value = res.data
    ElMessage.success('风险指标计算完成')
  } catch (e) {
    ElMessage.error('分析失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function analyzeIndustry() {
  if (!form.symbol) { ElMessage.warning('请输入ETF代码'); return }
  loading.value = true
  try {
    const res = await analysisApi.industryDistribution(form.symbol)
    industryResult.value = res.data
    ElMessage.success('行业分布统计完成')
  } catch (e) {
    ElMessage.error('分析失败: ' + e.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.analysis-view { max-width: 1200px; margin: 0 auto; }
.result-section { margin-top: 20px; }
.result-section h3 { margin-bottom: 10px; color: #303133; }
</style>
