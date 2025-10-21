# Charts.vue 简化指南

## 简化目标

移除所有技术指标功能，只保留核心的K线图、成交量图和信号标记功能。

## 已完成的文档更新

1. ✅ **REQUIREMENTS.md** - 已移除技术指标需求
   - 第39行：标记"技术指标: 暂不实现（第二期迭代）"
   - 移除了技术指标计算相关章节

2. ✅ **DETAILED_DESIGN.md** - 已简化图表设计
   - 第1678行：移除 `/api/v1/market/indicators` API
   - 第1838行：标记技术指标计算服务为第二期实现

## Charts.vue 需要的修改

### 1. 移除技术指标选择UI (第68-76行)

**原代码**:
```vue
<div class="toolbar-right">
  <!-- 技术指标选择 -->
  <el-checkbox-group v-model="activeIndicators" size="small">
    <el-checkbox-button label="MA">MA</el-checkbox-button>
    <el-checkbox-button label="MACD">MACD</el-checkbox-button>
    <el-checkbox-button label="RSI">RSI</el-checkbox-button>
    <el-checkbox-button label="BOLL">BOLL</el-checkbox-button>
    <el-checkbox-button label="VOL">VOL</el-checkbox-button>
  </el-checkbox-group>
</div>
```

**修改为**:
```vue
<!-- 移除整个 toolbar-right 部分 -->
```

### 2. 移除状态变量 (第203-204行)

**原代码**:
```javascript
const activeIndicators = ref(['MA', 'VOL'])
const indicatorData = ref({}) // 存储技术指标数据
```

**修改为**:
```javascript
// 删除这两行
```

### 3. 移除fetchIndicators函数 (第698-729行)

**原代码**:
```javascript
// 获取技术指标数据
const fetchIndicators = async () => {
  // ... 完整实现
}
```

**修改为**:
```javascript
// 删除整个函数
```

### 4. 简化candlestickOption (第257-660行)

这是最复杂的部分。需要：

**移除的部分**:
- 第291-306行：`hasSubplot` 相关逻辑
- 第334-347行：第三个xAxis配置（用于MACD/RSI）
- 第383-391行：第三个yAxis配置
- 第459-619行：所有技术指标的series添加逻辑（MA、BOLL、MACD、RSI）

**保留的部分**:
- K线主图
- 成交量副图
- 信号标记点
- dataZoom配置

**简化后的grid配置**:
```javascript
const grids = [
  {
    left: '10%',
    right: '8%',
    height: '65%'  // 主图占比增加
  },
  {
    left: '10%',
    right: '8%',
    top: '75%',
    height: '10%'  // 成交量图
  }
]
```

**简化后的dataZoom**:
```javascript
const dataZoomConfig = [
  {
    id: 'dataZoomX',
    type: 'inside',
    xAxisIndex: [0, 1],  // 只有两个axis
    start: 70,
    end: 100,
    zoomOnMouseWheel: true,
    moveOnMouseMove: true
  },
  {
    id: 'dataZoomSlider',
    show: true,
    xAxisIndex: [0, 1],
    type: 'slider',
    top: '90%',  // 固定位置
    start: 70,
    end: 100
  }
]
```

**简化后的series**:
```javascript
const series = [
  // K线
  {
    name: 'K线',
    type: 'candlestick',
    data: candlestickData.value.values,
    itemStyle: {
      color: colors.up,
      color0: colors.down
    },
    markPoint: {
      data: generateSignalMarkers()
    }
  },
  // 成交量
  {
    name: '成交量',
    type: 'bar',
    xAxisIndex: 1,
    yAxisIndex: 1,
    data: candlestickData.value.volumes,
    itemStyle: {
      color: colors.volume
    }
  }
]
```

### 5. 移除onMounted中的fetchIndicators调用 (第902-904行)

**原代码**:
```javascript
onMounted(async () => {
  fetchAllPairsPrices()
  await fetchKlineData()
  await fetchIndicators()  // ← 删除这行
  fetchStrategies()
  fetchSignals()
```

**修改为**:
```javascript
onMounted(async () => {
  fetchAllPairsPrices()
  await fetchKlineData()
  fetchStrategies()
  fetchSignals()
```

### 6. 移除定时器中的fetchIndicators调用 (第908-913行)

**原代码**:
```javascript
refreshTimer = setInterval(async () => {
  fetchAllPairsPrices()
  await fetchKlineData()
  await fetchIndicators()  // ← 删除这行
  fetchSignals()
}, 10000)
```

**修改为**:
```javascript
refreshTimer = setInterval(async () => {
  fetchAllPairsPrices()
  await fetchKlineData()
  fetchSignals()
}, 10000)
```

### 7. 移除generateVolumeData函数 (如果只在技术指标中使用)

简化后直接使用 `candlestickData.value.volumes`

## 预期效果

简化后的Charts页面将：
- ✅ 显示K线主图
- ✅ 显示成交量副图
- ✅ 显示策略信号标记点
- ✅ 支持时间周期切换
- ✅ 支持货币对选择
- ❌ 不显示技术指标线（MA、MACD、RSI、BOLL）
- ❌ 没有技术指标选择器

## 测试验证

修改完成后：
1. 刷新页面 http://localhost:3000/charts
2. 检查是否有JavaScript错误
3. 验证K线图正常显示
4. 验证成交量图正常显示
5. 验证信号标记点正常显示
6. 验证时间周期切换正常工作

## 相关文件

- `/home/xd/project/btc-watcher/frontend/src/views/Charts.vue` - 主文件
- `/home/xd/project/btc-watcher/frontend/src/views/Charts.vue.backup` - 修改前备份
