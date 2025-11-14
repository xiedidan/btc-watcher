# Discord 通知渠道代理修复完成报告

## ✅ 问题已解决

Discord webhook 测试功能现已完全正常工作！

## 🔍 问题分析

用户报告："我已经添加了discord webhook，但是点击测试没效果"

经过调查发现两个问题：

1. **前端API集成问题**（已在之前修复）
   - 前端的 `handleTestChannel()` 和 `saveChannelConfig()` 没有调用真实的后端API
   - 已修复：创建了完整的 `notifyHubAPI` 客户端，实现了真实的API调用

2. **Discord渠道缺少代理配置**（本次修复的核心问题）
   - Discord API在国内需要通过代理访问
   - 后端代码没有配置代理，导致连接超时（TimeoutError）
   - 系统已配置代理环境变量（`http://127.0.0.1:10808`），但Discord channel没有使用

## 🔧 修复内容

### 修改文件
`/backend/services/notifyhub/channels/discord.py`

### 修改详情

#### 1. 添加 os 模块导入
```python
import os  # 新增
from .base import NotificationChannel
```

#### 2. 修改 `_send_via_webhook()` 方法，添加代理支持

**关键修改**:
```python
async def _send_via_webhook(self, message, title, metadata) -> bool:
    # ... 构建embed消息 ...

    # 获取代理配置
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not proxy:
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    # 修正可能的代理URL格式问题（http:127.0.0.1 -> http://127.0.0.1）
    if proxy and not proxy.startswith(("http://", "https://", "socks://")):
        proxy = f"http://{proxy}"

    logger.info(f"Using proxy for Discord: {proxy}")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            self.webhook_url,
            json=payload,
            proxy=proxy,  # ← 添加代理参数
            timeout=aiohttp.ClientTimeout(total=30)  # ← 超时从10秒增加到30秒
        ) as response:
            # ... 处理响应 ...
```

**修复要点**:
1. 从环境变量读取代理配置（支持 `HTTP_PROXY`, `http_proxy`, `HTTPS_PROXY`, `https_proxy`）
2. 修正可能的代理URL格式问题（防止 `http:127.0.0.1` 这种格式）
3. 在 aiohttp 请求中添加 `proxy` 参数
4. 将超时时间从10秒增加到30秒（通过代理可能需要更长时间）
5. 添加日志记录代理使用情况

## ✅ 测试验证

### 1. API测试
```bash
curl -s -X POST "http://localhost:8000/api/v1/notify/channels/2/test" \
  -H "Content-Type: application/json"

# 响应
{"success":true,"data":{"test_result":"success","message":"Test notification queued"}}
```

### 2. 数据库验证
查询 `notification_history` 表，确认消息发送成功：

```
ID: 11, 标题: 🔔 测试通知, 渠道: discord, 状态: sent ✅
  优先级: P1, 发送时间: 2025-10-28 03:17:14.855792+00:00

ID: 9, 标题: 🔔 测试通知, 渠道: discord, 状态: sent ✅
  优先级: P1, 发送时间: 2025-10-28 03:15:48.924535+00:00
```

### 3. 用户确认
用户反馈："**已经收到了**" ✅

## 🎯 完整的工作流程

现在Discord通知渠道的完整流程如下：

```
1. 用户在前端配置Discord Webhook
   ↓
2. 前端调用 notifyHubAPI.createChannel() 保存到后端数据库
   ↓
3. 用户点击"测试"按钮
   ↓
4. 前端调用 notifyHubAPI.testChannel(backend_id)
   ↓
5. 后端 NotifyHub.notify() 创建通知任务
   ↓
6. 通知队列处理器调用 Discord Channel Adapter
   ↓
7. Discord Adapter 使用系统代理（http://127.0.0.1:10808）
   ↓
8. 通过代理发送请求到 Discord Webhook API
   ↓
9. Discord频道收到测试消息 ✅
   ↓
10. 更新数据库记录状态为 'sent'
```

## 📊 系统配置确认

### 代理环境变量
```bash
HTTP_PROXY=http://127.0.0.1:10808/
http_proxy=http://127.0.0.1:10808/
HTTPS_PROXY=http://127.0.0.1:10808/
https_proxy=http://127.0.0.1:10808
```

### Discord渠道配置（数据库）
```
ID: 2
类型: discord
名称: Discord机器人
启用: True
配置: {
  "webhook_url": "https://discordapp.com/api/webhooks/...",
  "use_webhook": true
}
```

## 🚀 使用指南

### 方式1: 通过前端界面测试

1. 访问 `http://localhost:5173/`
2. 进入 **系统设置** → **通知渠道**
3. 找到 **Discord机器人**，点击 **配置**
4. 填写 Webhook URL
5. 勾选通知级别（P2/P1/P0）
6. 点击 **保存配置**
7. 启用渠道（打开开关）
8. 点击 **测试** 按钮
9. 应该立即在Discord频道收到测试消息 ✅

### 方式2: 通过API测试

```bash
# 测试Discord渠道（ID: 2）
curl -s -X POST "http://localhost:8000/api/v1/notify/channels/2/test" \
  -H "Content-Type: application/json"

# 查看通知历史
curl -s "http://localhost:8000/api/v1/notify/history?page=1&page_size=10" | python3 -m json.tool
```

### 方式3: 在业务代码中使用

```python
from services.notifyhub.core import notify_hub

# 发送高优先级通知到Discord
await notify_hub.notify(
    user_id=1,
    title="🚨 系统告警",
    message="策略异常停止，请立即查看",
    notification_type="alert",
    priority="P2",  # 立即发送
    metadata={"strategy_id": 10},
    strategy_id=10
)
```

## 📝 技术细节

### aiohttp 代理支持
aiohttp 原生支持HTTP/HTTPS/SOCKS代理：

```python
async with aiohttp.ClientSession() as session:
    async with session.post(
        url,
        json=data,
        proxy="http://127.0.0.1:10808"  # 直接传递代理URL
    ) as response:
        # 处理响应
```

### 代理URL格式
- **正确**: `http://127.0.0.1:10808`, `https://proxy.com:8080`, `socks://127.0.0.1:1080`
- **错误**: `http:127.0.0.1:10808` (缺少 `//`)

代码已添加自动修正逻辑。

### 超时配置
```python
timeout=aiohttp.ClientTimeout(total=30)  # 30秒总超时
```

通过代理访问Discord可能需要更长时间，已将超时从10秒增加到30秒。

## 🔧 后续优化建议

### 1. 添加Telegram渠道代理支持
Telegram API也需要代理访问，建议同样修改：
- `/backend/services/notifyhub/channels/telegram.py`

### 2. 添加飞书渠道代理支持（如果需要）
- `/backend/services/notifyhub/channels/feishu.py`

### 3. 统一代理配置
可以在 NotificationChannel 基类中添加统一的代理获取方法：

```python
# base.py
class NotificationChannel(ABC):
    def get_proxy(self) -> Optional[str]:
        """从环境变量获取代理配置"""
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        if not proxy:
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

        if proxy and not proxy.startswith(("http://", "https://", "socks://")):
            proxy = f"http://{proxy}"

        return proxy
```

然后各个channel子类直接调用 `self.get_proxy()` 即可。

### 4. 添加代理健康检查
在 NotifyHub 启动时检查代理是否可用：

```python
async def check_proxy_health(self):
    """检查代理连接"""
    proxy = os.environ.get("HTTP_PROXY")
    if not proxy:
        logger.warning("No proxy configured")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.google.com",
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Proxy {proxy} is healthy")
                else:
                    logger.warning(f"Proxy {proxy} returned status {response.status}")
    except Exception as e:
        logger.error(f"Proxy health check failed: {e}")
```

## ✨ 总结

Discord通知渠道已完全修复并正常工作：

- ✅ 前端可以配置Discord Webhook
- ✅ 前端可以保存配置到后端数据库
- ✅ 前端可以测试发送Discord消息
- ✅ 后端使用系统代理访问Discord API
- ✅ Discord频道成功接收测试消息
- ✅ 数据库正确记录发送历史（状态: sent）

**修复完成日期**: 2025-10-28
**修复状态**: ✅ 完成并验证
**用户确认**: ✅ 已收到Discord测试消息
