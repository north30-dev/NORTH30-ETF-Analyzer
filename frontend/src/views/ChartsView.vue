<template>
  <div class="charts-view">
    <el-card>
      <template #header><h2>图表中心</h2></template>
      <el-form :model="form" label-width="100px" inline>
        <el-form-item label="ETF代码">
          <el-input v-model="form.symbol" placeholder="如 510300" />
        </el-form-item>
        <el-form-item label="起始日期">
          <el-input v-model="form.startDate" placeholder="YYYYMMDD（可选）" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-input v-model="form.endDate" placeholder="YYYYMMDD（可选）" />
        </el-form-item>
        <el-form-item label="图表类型">
          <el-select v-model="form.chartType">
            <el-option label="K线图" value="kline" />
            <el-option label="净值走势图" value="nav_trend" />
            <el-option label="行业分布饼图" value="industry_pie" />
            <el-option label="成分股柱状图" value="holdings_bar" />
            <el-option label="回撤曲线图" value="drawdown" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="generateChart" :loading="loading">生成图表</el-button>
        </el-form-item>
      </el-form>

      <div v-if="chartOption" class="chart-display">
        <el-divider />
        <h3>{{ chartTitle }}</h3>
        <v-chart :option="chartOption" autoresize style="height: 520px; width: 100%;" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { analysisApi, etfApi } from '../api'
import { ElMessage } from 'element-plus'

const form = reactive({ symbol: '', chartType: 'kline', startDate: '', endDate: '' })
const loading = ref(false)
const chartOption = ref(null)
const chartTitle = ref('')

const chartTitleMap = {
  kline: 'K线图',
  nav_trend: '净值走势图',
  industry_pie: '行业分布饼图',
  holdings_bar: '成分股柱状图',
  drawdown: '回撤曲线图',
}

async function generateChart() {
  if (!form.symbol) { ElMessage.warning('请输入ETF代码'); return }
  loading.value = true
  chartOption.value = null
  try {
    const symbol = form.symbol
    const sd = form.startDate || undefined
    const ed = form.endDate || undefined
    chartTitle.value = chartTitleMap[form.chartType] || ''

    switch (form.chartType) {
      case 'kline':
        await buildKline(symbol, sd, ed)
        break
      case 'nav_trend':
        await buildNavTrend(symbol, sd, ed)
        break
      case 'industry_pie':
        await buildIndustryPie(symbol)
        break
      case 'holdings_bar':
        await buildHoldingsBar(symbol)
        break
      case 'drawdown':
        await buildDrawdown(symbol, sd, ed)
        break
    }
    ElMessage.success('图表生成成功')
  } catch (e) {
    ElMessage.error('图表生成失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

/* ---------- K线图 ---------- */
async function buildKline(symbol, sd, ed) {
  const res = await etfApi.getHistory(symbol, sd, ed)
  const rows = res.data?.history || res.data || []
  if (!rows.length) throw new Error('无历史数据')

  const dates = rows.map(r => r.date || r.trade_date)
  const ohlc = rows.map(r => [r.open, r.close, r.low, r.high])
  const volumes = rows.map(r => r.volume || 0)

  chartOption.value = {
    title: { text: `${symbol} K线图`, left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['K线', '成交量'], top: 30 },
    grid: [
      { left: '10%', right: '8%', top: 60, height: '50%' },
      { left: '10%', right: '8%', top: '72%', height: '16%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, boundaryGap: true, axisLabel: { show: false } },
      { type: 'category', data: dates, gridIndex: 1, boundaryGap: true },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitArea: { show: true } },
      { scale: true, gridIndex: 1, splitNumber: 2 },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], top: '92%' },
    ],
    series: [
      { name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0 },
      { name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1, itemStyle: { color: '#5470c6' } },
    ],
  }
}

/* ---------- 净值走势图 ---------- */
async function buildNavTrend(symbol, sd, ed) {
  const res = await analysisApi.navTrend(symbol, sd, ed)
  const rows = res.data?.nav_trend || res.data?.data || res.data || []
  if (!rows.length) throw new Error('无净值数据')

  const dates = rows.map(r => r.date || r.trade_date)
  const values = rows.map(r => r.nav || r.net_value || r.close)

  chartOption.value = {
    title: { text: `${symbol} 净值走势`, left: 'center' },
    tooltip: { trigger: 'axis' },
    grid: { left: '10%', right: '8%', top: 60, bottom: 80 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', scale: true, splitArea: { show: true } },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100 },
    ],
    series: [{ name: '净值', type: 'line', data: values, smooth: true, lineStyle: { width: 2 }, areaStyle: { opacity: 0.15 } }],
  }
}

/* ---------- 行业分布饼图 ---------- */
async function buildIndustryPie(symbol) {
  const res = await analysisApi.industryDistribution(symbol)
  const rows = res.data?.industries || res.data?.data || res.data || []
  if (!rows.length) throw new Error('无行业分布数据')

  const pieData = rows.map(r => ({
    name: r.industry || r.name || r.sector,
    value: r.weight || r.ratio || r.value,
  }))

  chartOption.value = {
    title: { text: `${symbol} 行业分布`, left: 'center' },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', left: 'left', top: 60 },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['55%', '55%'],
      data: pieData,
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
      label: { formatter: '{b}\n{d}%' },
    }],
  }
}

/* ---------- 成分股柱状图 ---------- */
async function buildHoldingsBar(symbol) {
  const res = await analysisApi.holdings(symbol)
  const rows = res.data?.holdings || res.data?.data || res.data || []
  if (!rows.length) throw new Error('无成分股数据')

  const names = rows.map(r => r.name || r.stock_name || r.code)
  const weights = rows.map(r => r.weight || r.ratio || r.holding_ratio || 0)

  chartOption.value = {
    title: { text: `${symbol} 成分股持仓`, left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '15%', right: '8%', top: 60, bottom: 80 },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 45 } },
    yAxis: { type: 'value', name: '权重(%)', splitArea: { show: true } },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100 },
    ],
    series: [{
      type: 'bar',
      data: weights,
      itemStyle: {
        color(params) {
          const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4']
          return colors[params.dataIndex % colors.length]
        },
      },
    }],
  }
}

/* ---------- 回撤曲线图 ---------- */
async function buildDrawdown(symbol, sd, ed) {
  const res = await analysisApi.navTrend(symbol, sd, ed)
  const rows = res.data?.nav_trend || res.data?.data || res.data || []
  if (!rows.length) throw new Error('无净值数据，无法计算回撤')

  const values = rows.map(r => r.nav || r.net_value || r.close)
  let peak = values[0]
  const drawdowns = values.map(v => {
    if (v > peak) peak = v
    return ((v - peak) / peak * 100)
  })
  const dates = rows.map(r => r.date || r.trade_date)

  chartOption.value = {
    title: { text: `${symbol} 回撤曲线`, left: 'center' },
    tooltip: { trigger: 'axis', formatter: params => `${params[0].axisValue}<br/>回撤: ${params[0].value.toFixed(2)}%` },
    grid: { left: '10%', right: '8%', top: 60, bottom: 80 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', name: '回撤(%)', splitArea: { show: true } },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100 },
    ],
    series: [{
      name: '回撤',
      type: 'line',
      data: drawdowns,
      smooth: true,
      lineStyle: { width: 2, color: '#ee6666' },
      areaStyle: { color: 'rgba(238,102,102,0.2)' },
      itemStyle: { color: '#ee6666' },
    }],
  }
}
</script>

<style scoped>
.charts-view { max-width: 1200px; margin: 0 auto; }
.chart-display { text-align: center; }
.chart-display h3 { margin-bottom: 15px; }
</style>
