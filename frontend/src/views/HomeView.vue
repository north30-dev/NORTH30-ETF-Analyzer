<template>
  <div class="home-view">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <h2>欢迎使用 ETF 分析工具</h2>
          </template>
          <p>ETF 分析工具提供以下功能：</p>
          <el-row :gutter="20" class="feature-cards">
            <el-col :span="6">
              <el-card shadow="hover" @click="$router.push('/etf')">
                <h3>ETF 查询</h3>
                <p>搜索和浏览 ETF 列表，查看实时行情</p>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" @click="$router.push('/analysis')">
                <h3>数据分析</h3>
                <p>净值走势、风险指标、绩效分析</p>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" @click="$router.push('/charts')">
                <h3>图表中心</h3>
                <p>K线图、走势图、行业分布图</p>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" @click="$router.push('/report')">
                <h3>报告生成</h3>
                <p>生成 PDF 分析报告</p>
              </el-card>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.home-view { max-width: 1200px; margin: 0 auto; }
.feature-cards { margin-top: 20px; }
.feature-cards .el-card { cursor: pointer; text-align: center; min-height: 120px; }
.feature-cards h3 { color: #409eff; margin-bottom: 8px; }
.feature-cards p { color: #909399; font-size: 14px; }
</style>
