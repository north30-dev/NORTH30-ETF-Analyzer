import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code !== 0) {
      return Promise.reject(new Error(data.message || '请求失败'))
    }
    return data
  },
  (error) => {
    return Promise.reject(error)
  }
)

// ETF 相关 API
export const etfApi = {
  getList: (keyword, skip = 0, limit = 20) =>
    api.get('/etf/list', { params: { keyword, skip, limit } }),
  getQuote: (symbol) =>
    api.get(`/etf/${symbol}/quote`),
  getHistory: (symbol, startDate, endDate) =>
    api.get(`/etf/${symbol}/history`, { params: { start_date: startDate, end_date: endDate } }),
  getHoldings: (symbol) =>
    api.get(`/etf/${symbol}/holdings`),
}

// 分析相关 API
export const analysisApi = {
  navTrend: (symbol, startDate, endDate) =>
    api.post('/analysis/nav-trend', { symbol, start_date: startDate, end_date: endDate }),
  riskMetrics: (symbol, startDate, endDate, benchmarkSymbol) =>
    api.post('/analysis/risk-metrics', { symbol, start_date: startDate, end_date: endDate, benchmark_symbol: benchmarkSymbol }),
  performance: (symbol, benchmarkSymbol, startDate, endDate) =>
    api.post('/analysis/performance', { symbol, benchmark_symbol: benchmarkSymbol, start_date: startDate, end_date: endDate }),
  holdings: (symbol) =>
    api.post('/analysis/holdings', { symbol }),
  industryDistribution: (symbol) =>
    api.post('/analysis/industry-distribution', { symbol }),
}

// 图表相关 API
export const chartApi = {
  generate: (symbol, chartType, startDate, endDate) =>
    api.post('/chart/generate', { symbol, chart_type: chartType, start_date: startDate, end_date: endDate }),
}

// 报告相关 API
export const reportApi = {
  generate: (symbol, startDate, endDate, benchmarkSymbol, modules) =>
    api.post('/report/generate', { symbol, start_date: startDate, end_date: endDate, benchmark_symbol: benchmarkSymbol, modules }),
  getTaskStatus: (taskId) =>
    api.get(`/report/task/${taskId}`),
}

export default api
