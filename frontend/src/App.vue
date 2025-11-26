<template>
  <div class="app-container">
    <el-container class="layout-container">
      <!-- 左侧侧边栏 -->
      <el-aside width="220px" class="sidebar">
        <div class="logo">
          <h2>Haokan Monitor</h2>
        </div>
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
          @select="handleSelect"
        >
          <el-menu-item index="overview">
            <el-icon><DataLine /></el-icon>
            <span>数据总览</span>
          </el-menu-item>
          <el-menu-item index="accounts">
            <el-icon><User /></el-icon>
            <span>账号列表</span>
          </el-menu-item>
          <el-menu-item index="config">
            <el-icon><Setting /></el-icon>
            <span>配置管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 右侧内容区 -->
      <el-container>
        <el-header class="header">
          <div class="header-title">
            {{ pageTitle }}
          </div>
          <div class="header-actions">
             <el-button type="primary" circle @click="refreshData" :loading="loading" icon="Refresh" title="刷新数据"></el-button>
          </div>
        </el-header>

        <el-main class="main-content">
          
          <!-- 1. 数据总览页 -->
          <div v-if="activeMenu === 'overview'" class="view-overview">
             <!-- 顶部核心指标 -->
             <div class="stats-grid">
               <el-card shadow="hover" class="stat-card primary-card">
                 <div class="stat-icon"><el-icon><VideoPlay /></el-icon></div>
                 <div class="stat-info">
                   <div class="label">所有视频总播放量</div>
                   <div class="value">{{ formatNumber(globalStats.total_play_count) }}</div>
                 </div>
               </el-card>

               <el-card shadow="hover" class="stat-card success-card">
                 <div class="stat-icon"><el-icon><Top /></el-icon></div>
                 <div class="stat-info">
                   <div class="label">1小时总增长</div>
                   <div class="value">+{{ formatNumber(globalStats.hour_growth) }}</div>
                 </div>
               </el-card>

               <el-card shadow="hover" class="stat-card warning-card">
                 <div class="stat-icon"><el-icon><TrendCharts /></el-icon></div>
                 <div class="stat-info">
                   <div class="label">24小时总增长</div>
                   <div class="value">+{{ formatNumber(globalStats.day_growth) }}</div>
                 </div>
               </el-card>
             </div>

             <!-- 详细指标行 -->
             <h3 class="section-title">历史对比</h3>
             <el-row :gutter="20">
                <el-col :span="6">
                   <el-card shadow="always" class="detail-stat">
                      <div class="detail-label">昨日增长</div>
                      <div class="detail-value text-blue">
                        <el-icon><CaretTop /></el-icon> {{ formatNumber(globalStats.yesterday_growth) }}
                      </div>
                   </el-card>
                </el-col>
                <el-col :span="6">
                   <el-card shadow="always" class="detail-stat">
                      <div class="detail-label">昨天总播放量(快照)</div>
                      <div class="detail-value">
                        {{ formatNumber(globalStats.yesterday_total) }}
                      </div>
                   </el-card>
                </el-col>
                <el-col :span="6">
                   <el-card shadow="always" class="detail-stat">
                      <div class="detail-label">上周总播放量(快照)</div>
                      <div class="detail-value">
                        {{ formatNumber(globalStats.last_week_total) }}
                      </div>
                   </el-card>
                </el-col>
                <el-col :span="6">
                   <el-card shadow="always" class="detail-stat">
                      <div class="detail-label">上月总播放量(快照)</div>
                      <div class="detail-value">
                        {{ formatNumber(globalStats.last_month_total) }}
                      </div>
                   </el-card>
                </el-col>
             </el-row>

          </div>

          <!-- 2. 账号列表页 -->
          <div v-if="activeMenu === 'accounts'" class="view-accounts">
             <el-table :data="accountsStats" style="width: 100%" stripe border @row-click="goToDetail" class="clickable-table">
                <el-table-column prop="name" label="账号昵称" min-width="200">
                   <template #default="scope">
                      <span class="account-name">{{ scope.row.name }}</span>
                      <br>
                      <small class="text-gray">{{ scope.row.app_id }}</small>
                   </template>
                </el-table-column>
                <el-table-column prop="video_count" label="视频总数" width="120" align="center" />
                
                <el-table-column label="1小时增长" width="150" align="right">
                  <template #default="scope">
                    <span :class="getHourlyTrendClass(scope.row.hour_growth)">
                       <el-icon v-if="scope.row.hour_growth > 0"><CaretTop /></el-icon>
                       {{ formatNumber(scope.row.hour_growth) }}
                    </span>
                  </template>
                </el-table-column>

                <el-table-column label="24小时增长" width="150" align="right">
                  <template #default="scope">
                    <span :class="getDailyTrendClass(scope.row.day_growth)">
                       <el-icon v-if="scope.row.day_growth > 0"><CaretTop /></el-icon>
                       {{ formatNumber(scope.row.day_growth) }}
                    </span>
                  </template>
                </el-table-column>

                <el-table-column label="昨日增长" width="150" align="right">
                  <template #default="scope">
                    <span :class="getTrendClass(scope.row.yesterday_growth)">
                       <el-icon v-if="scope.row.yesterday_growth > 0"><CaretTop /></el-icon>
                       {{ formatNumber(scope.row.yesterday_growth) }}
                    </span>
                  </template>
                </el-table-column>

                <el-table-column width="80" align="center">
                  <template #default>
                    <el-icon><ArrowRight /></el-icon>
                  </template>
                </el-table-column>
             </el-table>
          </div>

          <!-- 3. 账号详情页 (Sub-view) -->
          <div v-if="activeMenu === 'account_detail'" class="view-detail">
             <el-page-header @back="goBack" :content="currentAccount.name" class="mb-20" />
             
             <!-- 详情页顶部指标 -->
             <div class="detail-top-stats mb-20">
               <el-row :gutter="20">
                 <el-col :span="6">
                   <el-statistic title="1小时增长" :value="currentAccountStats.hour_growth">
                     <template #prefix>
                        <el-icon style="color: #E6A23C"><Top /></el-icon>
                     </template>
                   </el-statistic>
                 </el-col>
                 <el-col :span="6">
                   <el-statistic title="24小时增长" :value="currentAccountStats.day_growth">
                      <template #prefix>
                        <el-icon style="color: #F56C6C"><TrendCharts /></el-icon>
                     </template>
                   </el-statistic>
                 </el-col>
                  <el-col :span="6">
                   <el-statistic title="昨日增长" :value="currentAccountStats.yesterday_growth">
                      <template #prefix>
                        <el-icon style="color: #409EFF"><CaretTop /></el-icon>
                     </template>
                   </el-statistic>
                 </el-col>
               </el-row>
             </div>

             <!-- 趋势图占位 -->
             <el-card class="mb-20">
               <template #header><span>账号增长趋势</span></template>
               <div ref="accountChartRef" style="width: 100%; height: 300px;"></div>
             </el-card>

             <!-- 视频列表 -->
             <el-table :data="currentAccountVideos" style="width: 100%" stripe border>
                <el-table-column prop="title" label="视频标题" min-width="250" show-overflow-tooltip />
                
                <el-table-column label="当前播放量" width="150" align="right">
                  <template #default="scope">
                     <strong :class="getPlayCountClass(scope.row.play_count)">{{ formatNumber(scope.row.play_count) }}</strong>
                  </template>
                </el-table-column>

                <el-table-column label="1小时增长" width="140" align="right">
                  <template #default="scope">
                    <span :class="getHourlyTrendClass(scope.row.hour_growth)">
                       <el-icon v-if="scope.row.hour_growth > 0"><Top /></el-icon>
                       {{ formatNumber(scope.row.hour_growth) }}
                    </span>
                  </template>
                </el-table-column>

                <el-table-column label="24小时增长" width="140" align="right">
                  <template #default="scope">
                    <span :class="getDailyTrendClass(scope.row.day_growth)">
                       <el-icon v-if="scope.row.day_growth > 0"><TrendCharts /></el-icon>
                       {{ formatNumber(scope.row.day_growth) }}
                    </span>
                  </template>
                </el-table-column>

                 <el-table-column label="昨日增长" width="140" align="right">
                  <template #default="scope">
                    <span :class="getTrendClass(scope.row.yesterday_growth)">
                       <el-icon v-if="scope.row.yesterday_growth > 0"><CaretTop /></el-icon>
                       {{ formatNumber(scope.row.yesterday_growth) }}
                    </span>
                  </template>
                </el-table-column>
                
                <el-table-column label="趋势" width="80" align="center">
                   <template #default="scope">
                      <el-button type="primary" link @click="showVideoTrend(scope.row)">
                         <el-icon><Histogram /></el-icon>
                      </el-button>
                   </template>
                </el-table-column>
             </el-table>
          </div>

          <!-- 4. 配置页 -->
          <div v-if="activeMenu === 'config'" class="view-config">
             <el-card header="监控账号配置 (App ID)">
                <el-input
                  v-model="accountsText"
                  :rows="10"
                  type="textarea"
                  placeholder="请输入 App ID，每行一个"
                />
                <div class="mt-20">
                   <el-button type="primary" @click="saveConfig" :loading="configLoading">保存配置</el-button>
                   <el-button type="warning" @click="triggerCrawl" :loading="triggerLoading">立即触发爬取</el-button>
                </div>
             </el-card>
          </div>

        </el-main>
      </el-container>
    </el-container>

    <!-- 视频趋势图弹窗 -->
    <el-dialog v-model="showChart" :title="currentVideoTitle" width="800px" destroy-on-close>
      <div ref="chartRef" style="width: 100%; height: 400px;"></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { 
  DataLine, User, Setting, VideoPlay, Top, TrendCharts, 
  CaretTop, ArrowRight, Refresh, Histogram 
} from '@element-plus/icons-vue'

// State
const activeMenu = ref('overview')
const loading = ref(false)
const accountsText = ref('')
const configLoading = ref(false)
const triggerLoading = ref(false)

// Data
const globalStats = ref({
    total_play_count: 0,
    hour_growth: 0,
    day_growth: 0,
    yesterday_growth: 0,
    yesterday_total: 0,
    last_week_total: 0,
    last_month_total: 0
})
const accountsStats = ref([])
const currentAccount = ref({})
const currentAccountStats = ref({})
const currentAccountVideos = ref([])

// Chart
const showChart = ref(false)
const chartRef = ref(null)
const accountChartRef = ref(null)
const currentVideoTitle = ref('')
let chartInstance = null
let accountChartInstance = null

const API_BASE = '/api'

const pageTitle = computed(() => {
  const titles = {
    'overview': '数据总览 Dashboard',
    'accounts': '监控账号列表',
    'config': '系统配置',
    'account_detail': '账号详细数据'
  }
  return titles[activeMenu.value] || 'Haokan Monitor'
})

// Logic
const formatNumber = (num) => {
  if (num === undefined || num === null) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(3) + '万'
  }
  return num.toLocaleString()
}

// 1小时增长颜色逻辑
const getHourlyTrendClass = (val) => {
  // 1小时增长: 1W红色, 3K橙色, 1K绿色
  if (val > 10000) return 'trend-red'
  if (val > 3000) return 'trend-orange'
  if (val > 1000) return 'trend-green'
  return val > 0 ? 'trend-green' : (val < 0 ? 'trend-down' : 'trend-neutral')
}

// 24小时增长颜色逻辑
const getDailyTrendClass = (val) => {
  if (val > 100000) return 'trend-red'
  if (val > 30000) return 'trend-orange'
  if (val > 10000) return 'trend-green'
  return val > 0 ? 'trend-green' : (val < 0 ? 'trend-down' : 'trend-neutral')
}

// 播放量颜色逻辑
const getPlayCountClass = (val) => {
  // 单个视频播放量: 1W红色, 3K橙色, 1K绿色
  if (val > 10000) return 'trend-red'
  if (val > 3000) return 'trend-orange'
  if (val > 1000) return 'trend-green'
  return ''
}

const getTrendClass = (val) => {
   // 默认回退
   return val > 0 ? 'trend-green' : (val < 0 ? 'trend-down' : 'trend-neutral')
}

const handleSelect = (index) => {
  activeMenu.value = index
  if (index === 'overview') fetchDashboard()
  if (index === 'accounts') fetchDashboard() // Accounts data is in dashboard api too
  if (index === 'config') fetchConfig()
}

const goBack = () => {
  activeMenu.value = 'accounts'
}

const refreshData = () => {
  if (activeMenu.value === 'account_detail') {
    fetchAccountDetail(currentAccount.value.id)
  } else if (activeMenu.value === 'config') {
    fetchConfig()
  } else {
    fetchDashboard()
  }
}

// API
const fetchDashboard = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${API_BASE}/stats/dashboard`)
    if (res.data) {
      globalStats.value = res.data.global || {}
      accountsStats.value = res.data.accounts || []
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const fetchConfig = async () => {
  try {
    const res = await axios.get(`${API_BASE}/config`)
    if (res.data && res.data.accounts) {
      accountsText.value = res.data.accounts.map(a => a.id).join('\n')
    }
  } catch (error) {
    ElMessage.error('配置获取失败')
  }
}

const saveConfig = async () => {
  configLoading.value = true
  try {
    const ids = accountsText.value.split('\n').map(s => s.trim()).filter(s => s)
    // Construct config object list
    const newConfig = ids.map(id => ({ id: id })) 
    // Note: We lose names here if we just use IDs, but backend handles re-fetching/defaults
    await axios.post(`${API_BASE}/config`, newConfig)
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    configLoading.value = false
  }
}

const triggerCrawl = async () => {
  triggerLoading.value = true
  try {
    await axios.get(`${API_BASE}/crawlers/trigger`)
    ElMessage.success('任务已触发')
  } catch (e) {
    ElMessage.error('触发失败')
  } finally {
    triggerLoading.value = false
  }
}

const goToDetail = (row) => {
  currentAccount.value = row
  activeMenu.value = 'account_detail'
  fetchAccountDetail(row.app_id)
}

const fetchAccountDetail = async (appId) => {
  loading.value = true
  try {
    const res = await axios.get(`${API_BASE}/stats/account/${appId}`)
    if (res.data) {
      currentAccount.value = res.data.info
      currentAccountStats.value = res.data.stats
      currentAccountVideos.value = res.data.videos
      
      // Mock Chart Data for Account (Since backend doesn't provide account-level history yet)
      // We can simulate or just leave it empty/placeholder for now
      // To make it real, backend needs `get_account_history`
      initAccountChart([]) 
    }
  } catch (e) {
    ElMessage.error('详情获取失败')
  } finally {
    loading.value = false
  }
}

const showVideoTrend = async (video) => {
  currentVideoTitle.value = video.title
  showChart.value = true
  try {
    const res = await axios.get(`${API_BASE}/stats/video/${encodeURIComponent(video.vid || video.title)}`)
    nextTick(() => {
       initChart(res.data, chartRef.value, chartInstance)
    })
  } catch (e) {
    ElMessage.error('历史数据获取失败')
  }
}

// Chart Utils
const initChart = (data, dom, instance) => {
  if (instance) instance.dispose()
  const myChart = echarts.init(dom)
  
  const option = {
    tooltip: { trigger: 'axis' },
    xAxis: { 
      type: 'category', 
      data: data.map(i => i.crawl_time.substring(5, 16))
    },
    yAxis: { type: 'value', scale: true },
    series: [{
      data: data.map(i => i.play_count),
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.2 },
      itemStyle: { color: '#409EFF' }
    }],
    grid: { left: 50, right: 20, top: 30, bottom: 30 }
  }
  myChart.setOption(option)
  return myChart
}

const initAccountChart = (data) => {
  // Placeholder for account chart
  if (accountChartInstance) accountChartInstance.dispose()
  if (!accountChartRef.value) return
  
  accountChartInstance = echarts.init(accountChartRef.value)
  accountChartInstance.setOption({
    title: { text: '暂无历史聚合数据', left: 'center', top: 'center', textStyle: { color: '#ccc'} },
    xAxis: { show: false },
    yAxis: { show: false }
  })
}

onMounted(() => {
  fetchDashboard()
})
</script>

<style>
html, body { margin: 0; height: 100%; }
#app { height: 100%; }
.app-container { height: 100%; display: flex; }
.layout-container { height: 100%; width: 100%; }

.sidebar {
  background-color: #304156;
  color: white;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #2b3a4d;
}
.logo h2 { margin: 0; font-size: 18px; color: white; }
.el-menu-vertical { border-right: none; flex: 1; }

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}
.header-title { font-size: 20px; font-weight: 500; }

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

/* Overview Styles */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}
.stat-card {
  border: none;
  display: flex;
  align-items: center;
}
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 20px;
}
.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  font-size: 30px;
  color: white;
}
.primary-card .stat-icon { background-color: #409EFF; box-shadow: 0 4px 10px rgba(64, 158, 255, 0.3); }
.success-card .stat-icon { background-color: #67C23A; box-shadow: 0 4px 10px rgba(103, 194, 58, 0.3); }
.warning-card .stat-icon { background-color: #E6A23C; box-shadow: 0 4px 10px rgba(230, 162, 60, 0.3); }

.stat-info .label { font-size: 14px; color: #909399; margin-bottom: 5px; }
.stat-info .value { font-size: 24px; font-weight: bold; color: #303133; }

.section-title {
  margin: 0 0 20px 0;
  font-size: 18px;
  color: #303133;
  border-left: 4px solid #409EFF;
  padding-left: 10px;
}
.detail-stat { text-align: center; }
.detail-label { font-size: 14px; color: #909399; margin-bottom: 10px; }
.detail-value { font-size: 20px; font-weight: bold; }
.text-blue { color: #409EFF; }

/* Table Styles */
.clickable-table { cursor: pointer; }
.account-name { font-weight: bold; font-size: 15px; }
.text-gray { color: #909399; font-size: 12px; }

.trend-green { color: #67C23A; font-weight: bold; display: flex; align-items: center; justify-content: flex-end; gap: 4px;}
.trend-orange { color: #E6A23C; font-weight: bold; display: flex; align-items: center; justify-content: flex-end; gap: 4px;}
.trend-red { color: #F56C6C; font-weight: bold; display: flex; align-items: center; justify-content: flex-end; gap: 4px;}

.trend-up { color: #F56C6C; font-weight: bold; display: flex; align-items: center; justify-content: flex-end; gap: 4px;}
.trend-down { color: #909399; font-weight: bold; display: flex; align-items: center; justify-content: flex-end; gap: 4px;} 
.trend-neutral { color: #909399; }

.mb-20 { margin-bottom: 20px; }
.mt-20 { margin-top: 20px; }
</style>
