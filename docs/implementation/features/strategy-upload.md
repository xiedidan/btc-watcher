# 策略代码文件管理功能实施总结

> 完成时间: 2025-10-16
> 状态: ✅ 前端完成，等待后端API

---

## 📊 已实现的功能

### 1. 策略文件上传组件
- ✅ 使用 Element Plus `el-upload` 组件
- ✅ 支持拖拽和点击上传
- ✅ 限制文件类型为 `.py` Python文件
- ✅ 限制文件大小为 10MB
- ✅ 显示上传进度和状态

### 2. 文件验证
- ✅ `beforeUpload` 函数：上传前验证文件类型和大小
- ✅ 错误提示：不符合要求的文件会被拒绝

### 3. 自动扫描策略类
- ✅ 上传成功后，后端自动扫描Python文件中的策略类
- ✅ 前端接收策略类列表并展示

### 4. 策略类选择
- ✅ 将原来的输入框改为下拉选择框
- ✅ 动态显示从上传文件中扫描出的策略类
- ✅ 每个选项显示策略类名称和描述
- ✅ 如果只有一个策略类，自动选中

### 5. 状态显示
- ✅ 显示已上传文件名称
- ✅ 显示扫描到的策略类数量
- ✅ 成功提示：绿色✓图标和文件信息

### 6. 状态管理
- ✅ 打开对话框时重置所有上传相关状态
- ✅ 保存文件ID到表单数据

---

## 🔧 技术实现细节

### 修改的文件
`frontend/src/views/Strategies.vue`

### 新增的状态变量
```javascript
// 文件上传相关状态
const uploadedFiles = ref([])              // 已上传文件列表
const availableStrategyClasses = ref([])   // 可用策略类列表
const strategyFileInfo = ref(null)         // 当前策略文件信息
const uploadRef = ref(null)                // 上传组件引用

// 上传配置
const uploadAction = computed(() => {
  return `${import.meta.env.VITE_API_URL}/api/v1/strategies/upload`
})

const uploadHeaders = computed(() => {
  return {
    'Authorization': `Bearer ${userStore.token}`
  }
})
```

### 新增的处理函数
```javascript
// 上传前验证
const beforeUpload = (file) => {
  // 验证文件类型和大小
}

// 上传成功处理
const handleUploadSuccess = (response, file, fileList) => {
  // 更新策略类列表
  // 自动选中唯一策略类
}

// 上传失败处理
const handleUploadError = (error, file) => {
  // 显示错误提示
}
```

### 表单数据更新
```javascript
const createForm = reactive({
  name: '',
  strategy_class: '',
  strategy_file: null,  // 新增：保存文件ID
  exchange: 'binance',
  // ...其他字段
})
```

---

## 🔗 后端API要求

### API端点
`POST /api/v1/strategies/upload`

### 请求格式
- **Content-Type**: `multipart/form-data`
- **Headers**:
  - `Authorization: Bearer <token>`
- **Body**:
  - `file`: Python策略文件 (.py)

### 响应格式
```json
{
  "success": true,
  "file_id": "uuid-or-unique-id",
  "file_path": "/path/to/uploaded/file.py",
  "strategy_classes": [
    {
      "name": "MACrossStrategy",
      "description": "双均线交叉策略"
    },
    {
      "name": "RSIStrategy",
      "description": "RSI超买超卖策略"
    }
  ]
}
```

### 错误响应
```json
{
  "success": false,
  "message": "文件解析失败：语法错误"
}
```

---

## 📋 后端实现建议

### 1. 文件上传处理
```python
from fastapi import UploadFile, HTTPException
import uuid
import ast

@router.post("/strategies/upload")
async def upload_strategy_file(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    # 1. 验证文件类型
    if not file.filename.endswith('.py'):
        raise HTTPException(status_code=400, detail="只支持Python文件")

    # 2. 生成唯一文件ID
    file_id = str(uuid.uuid4())

    # 3. 保存文件到指定目录
    file_path = f"/app/user_data/strategies/{file_id}_{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # 4. 扫描策略类
    strategy_classes = scan_strategy_classes(content.decode('utf-8'))

    # 5. 返回结果
    return {
        "success": True,
        "file_id": file_id,
        "file_path": file_path,
        "strategy_classes": strategy_classes
    }
```

### 2. 策略类扫描
```python
import ast
import inspect

def scan_strategy_classes(code: str):
    """扫描Python代码中的策略类"""
    try:
        tree = ast.parse(code)
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 检查是否继承自IStrategy或BaseStrategy
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        if base.id in ['IStrategy', 'BaseStrategy']:
                            # 提取类名和文档字符串
                            class_info = {
                                "name": node.name,
                                "description": ast.get_docstring(node) or "无描述"
                            }
                            classes.append(class_info)
                            break

        return classes
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Python语法错误: {str(e)}")
```

### 3. 数据库存储
```python
# 策略文件表
class StrategyFile(Base):
    __tablename__ = "strategy_files"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    strategy_classes = Column(JSON)  # 存储扫描到的策略类列表
```

---

## ✅ 前端验证清单

- [x] 上传按钮可点击
- [x] 文件选择对话框只显示.py文件
- [x] 上传进度显示正常
- [x] 上传成功后显示文件信息
- [x] 策略类选择框被启用
- [x] 策略类选项显示名称和描述
- [x] 只有一个策略类时自动选中
- [x] 打开对话框时状态重置
- [x] 表单验证包含策略类必填

---

## 🚀 后续任务

- [ ] 后端实现策略文件上传API
- [ ] 后端实现策略类扫描功能
- [ ] 集成测试：前后端联调
- [ ] 添加策略文件管理页面（列表、删除、重命名）
- [ ] 添加策略文件版本控制
- [ ] 添加策略代码语法高亮预览

---

## 📝 使用说明

### 用户操作流程
1. 点击"创建策略"按钮
2. 在"策略代码"部分点击"上传策略文件"
3. 选择本地的.py Python文件
4. 等待上传完成，系统自动扫描策略类
5. 在"策略类"下拉框中选择要使用的策略类
6. 填写其他配置项
7. 点击"创建"完成策略创建

### 注意事项
- 文件必须是有效的Python代码
- 策略类必须继承自 `IStrategy` 或 `BaseStrategy`
- 文件大小不超过10MB
- 建议在文件中为策略类添加文档字符串（docstring）作为描述

---

## 📸 界面截图说明

### 上传前
```
┌─策略代码──────────────────────┐
│                              │
│ 策略文件: [上传策略文件 (.py)]  │
│ 支持上传Python策略文件，       │
│ 系统将自动扫描策略类           │
│                              │
│ 策略类: [请先上传策略文件▼]    │
│ (禁用状态)                    │
└──────────────────────────────┘
```

### 上传后
```
┌─策略代码──────────────────────┐
│                              │
│ 策略文件: ma_cross.py  [x]   │
│ ✓ 已加载: ma_cross.py        │
│   (2 个策略类)                │
│                              │
│ 策略类: [MACrossStrategy▼]   │
│ ├─ MACrossStrategy           │
│ │  双均线交叉策略              │
│ └─ MACrossProStrategy        │
│    双均线交叉专业版            │
└──────────────────────────────┘
```

---

完成！✨
