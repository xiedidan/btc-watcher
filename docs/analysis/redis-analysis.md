# BTC Watcher 简化部署方案

## Redis 使用分析与简化建议

### 当前Redis用途评估

| 功能模块 | Redis作用 | 重要性 | 替代方案 | 建议 |
|----------|-----------|--------|----------|------|
| 价格数据缓存 | 减少API调用，提高性能 | ⭐⭐⭐ | 内存缓存 | **保留** |
| 会话管理 | 存储JWT token | ⭐ | 无状态JWT | 可简化 |
| 消息队列 | 异步通知处理 | ⭐⭐ | 文件队列 | 可简化 |
| WebSocket管理 | 连接状态管理 | ⭐ | 内存管理 | 可简化 |

## 简化方案对比

### 方案一：完全移除Redis
**优势：** 部署最简单，减少一个服务
**劣势：** 性能下降明显，API调用频繁可能被限流
**适用：** 监控货币对少于5个的轻量使用

### 方案二：最小化Redis（推荐）
**优势：** 保留核心性能，简化配置
**劣势：** 仍需Redis服务
**适用：** 个人交易者标准使用场景

### 方案三：保持原设计
**优势：** 最佳性能和扩展性
**劣势：** 部署稍复杂
**适用：** 重度使用或多用户场景

## 个人交易者推荐：方案二（最小化Redis）

基于以下考虑：
1. **价格数据缓存**是必需的（避免API限流）
2. **部署复杂度**适中（Redis alpine镜像很轻量）
3. **维护负担**较小（Redis很稳定）
4. **未来扩展性**保留

## 具体简化实施

### 1. Redis配置简化
```yaml
# docker-compose.yml 中的简化Redis配置
redis:
  image: redis:7-alpine
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
  volumes:
    - redis_data:/data
  restart: unless-stopped
```

### 2. 应用代码调整

#### 会话管理简化（使用无状态JWT）
```python
# 移除Redis会话存储，使用纯JWT
# backend/app/core/security.py
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

#### 消息队列简化（使用文件队列）
```python
# notification/queue_manager.py
import json
import os
from datetime import datetime

class SimpleFileQueue:
    def __init__(self, queue_dir="/app/queue"):
        self.queue_dir = queue_dir
        os.makedirs(queue_dir, exist_ok=True)

    def enqueue(self, message: dict):
        filename = f"{datetime.now().isoformat()}_{uuid.uuid4().hex[:8]}.json"
        with open(f"{self.queue_dir}/{filename}", 'w') as f:
            json.dump(message, f)

    def dequeue(self):
        files = sorted(os.listdir(self.queue_dir))
        if files:
            filepath = f"{self.queue_dir}/{files[0]}"
            with open(filepath) as f:
                message = json.load(f)
            os.remove(filepath)
            return message
        return None
```

### 3. 仅保留核心缓存功能
```python
# backend/app/services/cache.py
import redis
from typing import Optional

class MinimalRedisCache:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    def get_price(self, symbol: str) -> Optional[dict]:
        """获取缓存的价格数据"""
        data = self.redis.get(f"price:{symbol}")
        return json.loads(data) if data else None

    def set_price(self, symbol: str, price_data: dict, ttl: int = 30):
        """缓存价格数据，30秒过期"""
        self.redis.setex(
            f"price:{symbol}",
            ttl,
            json.dumps(price_data)
        )
```

## 完全无Redis方案（最简化）

如果你坚持不使用Redis，可以采用以下架构：

### 替代方案实现

#### 1. 内存缓存替代Redis
```python
# backend/app/services/memory_cache.py
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

class MemoryCache:
    def __init__(self):
        self._cache: Dict[str, dict] = {}

    async def get_price(self, symbol: str) -> Optional[dict]:
        data = self._cache.get(f"price:{symbol}")
        if data and data['expires'] > datetime.now():
            return data['value']
        return None

    async def set_price(self, symbol: str, price_data: dict, ttl: int = 30):
        self._cache[f"price:{symbol}"] = {
            'value': price_data,
            'expires': datetime.now() + timedelta(seconds=ttl)
        }

    async def cleanup_expired(self):
        """定期清理过期数据"""
        now = datetime.now()
        expired_keys = [
            key for key, data in self._cache.items()
            if data['expires'] <= now
        ]
        for key in expired_keys:
            del self._cache[key]
```

#### 2. 文件通知队列
```python
# notification/file_queue.py
import json
import os
import glob
from datetime import datetime

class FileNotificationQueue:
    def __init__(self, queue_dir="/app/notifications"):
        self.queue_dir = queue_dir
        os.makedirs(queue_dir, exist_ok=True)

    def add_notification(self, notification: dict):
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        filepath = os.path.join(self.queue_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(notification, f)

    def get_pending_notifications(self):
        files = glob.glob(os.path.join(self.queue_dir, "*.json"))
        notifications = []
        for filepath in sorted(files):
            try:
                with open(filepath) as f:
                    notification = json.load(f)
                notifications.append((filepath, notification))
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
        return notifications

    def mark_sent(self, filepath: str):
        os.remove(filepath)
```

### 3. 简化的docker-compose.yml
```yaml
version: '3.8'

services:
  nginx:
    build: ./nginx
    ports:
      - "80:80"
    depends_on:
      - web
      - api

  web:
    build: ./frontend
    environment:
      - VITE_API_BASE_URL=http://api:8000/api/v1

  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - USE_REDIS=false  # 关闭Redis依赖
    volumes:
      - ./data/cache:/app/cache
      - ./data/queue:/app/queue
    depends_on:
      - db

  freqtrade:
    build: ./freqtrade
    volumes:
      - ./freqtrade/user_data:/freqtrade/user_data
      - ./data/signals:/app/signals

  notification:
    build: ./notification
    environment:
      - USE_REDIS=false
    volumes:
      - ./data/queue:/app/queue

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 最终建议

**对于个人交易者，我推荐采用"最小化Redis"方案：**

### 理由：
1. **轻量级**: Redis alpine镜像只有几MB
2. **稳定性**: Redis极其稳定，几乎无需维护
3. **性能**: 避免频繁API调用被限流
4. **扩展性**: 未来可轻松扩展功能

### 如果坚持不用Redis：
- 适合监控币种少（<5个）的场景
- 需要接受API限流风险
- 通知可能有1-2秒延迟

你倾向于哪种方案？我可以为你提供对应的详细配置文件。