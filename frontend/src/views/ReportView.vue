<template>
  <div class="report-view">
    <el-card>
      <template #header><h2>报告生成</h2></template>
      <el-form :model="form" label-width="100px">
        <el-form-item label="ETF代码">
          <el-input v-model="form.symbol" placeholder="如 510300" />
        </el-form-item>
        <el-form-item label="起始日期">
          <el-input v-model="form.startDate" placeholder="YYYYMMDD" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-input v-model="form.endDate" placeholder="YYYYMMDD" />
        </el-form-item>
        <el-form-item label="基准代码">
          <el-input v-model="form.benchmarkSymbol" placeholder="可选" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="generateReport" :loading="loading" :disabled="loading">生成报告</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <!-- 生成中：进度条 -->
      <div v-if="loading && taskStatus">
        <el-progress
          :percentage="taskStatus.progress || 0"
          :status="taskStatus.status === 'failed' ? 'exception' : undefined"
          :stroke-width="20"
          :text-inside="true"
          style="margin-bottom: 16px;"
        />
        <p style="text-align: center; color: #909399;">{{ taskStatus.message || '报告生成中，请稍候...' }}</p>
      </div>

      <!-- 生成成功：PDF 预览 + 下载 -->
      <div v-if="reportResult">
        <el-result icon="success" title="报告生成成功" :sub-title="reportResult.output_path || ''">
          <template #extra>
            <el-button type="primary" @click="downloadReport">下载报告</el-button>
            <el-button @click="showPreview = true" v-if="pdfUrl">在线预览</el-button>
          </template>
        </el-result>

        <!-- PDF 在线预览 -->
        <el-dialog v-model="showPreview" title="PDF 在线预览" width="85%" top="2vh" destroy-on-close>
          <iframe
            :src="pdfUrl"
            style="width: 100%; height: 75vh; border: none;"
          />
        </el-dialog>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { reportApi } from '../api'
import { ElMessage } from 'element-plus'

const form = reactive({ symbol: '', startDate: '', endDate: '', benchmarkSymbol: '' })
const loading = ref(false)
const reportResult = ref(null)
const taskStatus = ref(null)
const showPreview = ref(false)
const pdfUrl = ref('')

let pollTimer = null

onUnmounted(() => {
  stopPolling()
})

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function generateReport() {
  if (!form.symbol) { ElMessage.warning('请输入ETF代码'); return }
  loading.value = true
  reportResult.value = null
  taskStatus.value = null
  pdfUrl.value = ''
  stopPolling()

  try {
    const res = await reportApi.generate(
      form.symbol,
      form.startDate || undefined,
      form.endDate || undefined,
      form.benchmarkSymbol || undefined,
    )
    const data = res.data || res

    // 如果后端直接返回结果（同步模式）
    if (data.output_path && !data.task_id) {
      reportResult.value = data
      pdfUrl.value = data.pdf_url || data.url || ''
      loading.value = false
      ElMessage.success('报告生成成功')
      return
    }

    // 异步模式：拿到 task_id，开始轮询
    const taskId = data.task_id
    if (!taskId) {
      reportResult.value = data
      pdfUrl.value = data.pdf_url || data.url || ''
      loading.value = false
      ElMessage.success('报告生成成功')
      return
    }

    startPolling(taskId)
  } catch (e) {
    ElMessage.error('报告生成失败: ' + (e.message || '未知错误'))
    loading.value = false
  }
}

function startPolling(taskId) {
  pollTimer = setInterval(async () => {
    try {
      const res = await reportApi.getTaskStatus(taskId)
      const status = res.data || res
      taskStatus.value = status

      if (status.status === 'completed') {
        stopPolling()
        loading.value = false
        reportResult.value = status.result || status
        pdfUrl.value = status.result?.pdf_url || status.result?.url || status.pdf_url || status.url || ''
        ElMessage.success('报告生成成功')
      } else if (status.status === 'failed') {
        stopPolling()
        loading.value = false
        ElMessage.error('报告生成失败: ' + (status.message || '未知错误'))
      }
      // status === 'pending' | 'running' → 继续轮询
    } catch (e) {
      stopPolling()
      loading.value = false
      ElMessage.error('查询任务状态失败: ' + (e.message || '未知错误'))
    }
  }, 2000)
}

function downloadReport() {
  const url = pdfUrl.value || reportResult.value?.pdf_url || reportResult.value?.url
  if (!url) {
    ElMessage.warning('未找到报告下载地址')
    return
  }
  const link = document.createElement('a')
  link.href = url
  link.target = '_blank'
  link.download = ''
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
</script>

<style scoped>
.report-view { max-width: 800px; margin: 0 auto; }
</style>
