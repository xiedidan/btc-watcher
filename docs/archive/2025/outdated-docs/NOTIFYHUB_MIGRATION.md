# NotifyHub 数据库迁移说明

## 概述

NotifyHub通知中心需要4张数据库表来存储配置和历史数据。这些表的模型已经在 `models/notification.py` 中定义。

## 数据库表

### 1. notification_channel_configs
通知渠道配置表，存储用户配置的通知渠道（Telegram、Discord、飞书等）

**字段说明：**
- `id`: 主键
- `user_id`: 用户ID（外键关联users表）
- `channel_type`: 渠道类型（telegram/discord/feishu/wechat/email/sms）
- `channel_name`: 渠道名称（用户自定义）
- `enabled`: 是否启用
- `priority`: 渠道优先级（��字越小优先级越高）
- `supported_priorities`: 支持的通知优先级（JSON数组，如 ["P2", "P1", "P0"]）
- `config`: 渠道特定配置（JSON，存储bot_token、webhook_url等）
- `templates`: 消息模板（JSON，可选）
- `rate_limit_enabled`: 是否启用频率限制
- `max_notifications_per_hour`: 每小时最大通知数
- `max_notifications_per_day`: 每天最大通知数
- `total_sent`: 总发送次数（统计）
- `total_failed`: 总失败次数（统计）
- `last_sent_at`: 最后发送时间
- `last_error`: 最后错误信息
- `last_error_at`: 最后错误时间
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. notification_frequency_limits
通知频率限制配置表，控制不同优先级通知的发送频率

**字段说明：**
- `id`: 主键
- `user_id`: 用户ID（外键关联users表）
- `p2_min_interval`: P2（最高优先级）最小发送间隔（秒），默认0（无限制）
- `p1_min_interval`: P1（中等优先级）最小发送间隔（秒），默认60
- `p0_batch_interval`: P0（最低优先级）批量发送间隔（秒），默认300
- `p0_batch_enabled`: 是否启用P0批量发送，默认True
- `p0_batch_max_size`: 每批最多合并通知数，默认10
- `enabled`: 是否启用频率控制，默认True
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 3. notification_time_rules
通知时间规则配置表，控制通知发送的时间规则（勿扰时段、工作时间等）

**字段说明：**
- `id`: 主键
- `user_id`: 用户ID（外键关联users表）
- `rule_name`: 规则名称
- `enabled`: 是否启用
- `quiet_hours_enabled`: 是否启用勿扰时段
- `quiet_start_time`: 勿扰开始时间（HH:MM格式）
- `quiet_end_time`: 勿扰结束时间（HH:MM格式）
- `quiet_priority_filter`: 勿扰时段只发送此优先级及以上的通知（如 "P2"）
- `weekend_mode_enabled`: 是否启用周末模式
- `weekend_downgrade_p1_to_p0`: 周末是否将P1降级为P0
- `weekend_batch_p0`: 周末是否批量发送P0
- `working_hours_enabled`: 是否启用工作时间限制
- `working_start_time`: 工作开始时间（HH:MM格式）
- `working_end_time`: 工作结束时间（HH:MM格式）
- `working_days`: 工作日（JSON数组，1=Monday, 7=Sunday）
- `holiday_mode_enabled`: 是否启用假期模式
- `holiday_dates`: 假期日期列表（JSON数组，格式 "YYYY-MM-DD"）
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 4. notification_history
通知历史记录表，记录所有发送的通知

**字段说明：**
- `id`: 主键
- `user_id`: 用户ID（外键关联users表）
- `title`: 通知标题
- `message`: 通知内容
- `notification_type`: 通知类型（signal/alert/info/system）
- `priority`: 优先级（P2/P1/P0）
- `channel_type`: 发送渠道类型
- `channel_config_id`: 渠道配置ID（外键，可选）
- `status`: 状态（pending/sent/failed/batched）
- `sent_at`: 发送时间
- `error_message`: 错误信息（如果失败）
- `signal_id`: 关联的信号ID（可选）
- `strategy_id`: 关联的策略ID（可选）
- `extra_data`: 额外元数据（JSON）
- `created_at`: 创建时间

## 迁移步骤

### 方式1：自动创建（推荐）

系统启动时会自动创建所有表（通过 `Base.metadata.create_all()`）

```bash
# 启动应用即可自动创建表
cd backend
python main.py
```

### 方式2：手动SQL创建

如果需要手动创建表，可以使用以下SQL（PostgreSQL）：

```sql
-- 1. 通知渠道配置表
CREATE TABLE notification_channel_configs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    channel_type VARCHAR(50) NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 1,
    supported_priorities JSON DEFAULT '["P2", "P1", "P0"]',
    config JSON,
    templates JSON,
    rate_limit_enabled BOOLEAN DEFAULT true,
    max_notifications_per_hour INTEGER DEFAULT 60,
    max_notifications_per_day INTEGER DEFAULT 500,
    total_sent INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    last_sent_at TIMESTAMP WITH TIME ZONE,
    last_error VARCHAR(500),
    last_error_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notification_channel_configs_user_id ON notification_channel_configs(user_id);

-- 2. 通知频率限制配置表
CREATE TABLE notification_frequency_limits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    p2_min_interval INTEGER DEFAULT 0,
    p1_min_interval INTEGER DEFAULT 60,
    p0_batch_interval INTEGER DEFAULT 300,
    p0_batch_enabled BOOLEAN DEFAULT true,
    p0_batch_max_size INTEGER DEFAULT 10,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notification_frequency_limits_user_id ON notification_frequency_limits(user_id);

-- 3. 通知时间规则配置表
CREATE TABLE notification_time_rules (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    quiet_hours_enabled BOOLEAN DEFAULT false,
    quiet_start_time VARCHAR(5) DEFAULT '22:00',
    quiet_end_time VARCHAR(5) DEFAULT '08:00',
    quiet_priority_filter VARCHAR(10) DEFAULT 'P2',
    weekend_mode_enabled BOOLEAN DEFAULT false,
    weekend_downgrade_p1_to_p0 BOOLEAN DEFAULT true,
    weekend_batch_p0 BOOLEAN DEFAULT true,
    working_hours_enabled BOOLEAN DEFAULT false,
    working_start_time VARCHAR(5) DEFAULT '09:00',
    working_end_time VARCHAR(5) DEFAULT '18:00',
    working_days JSON DEFAULT '[1, 2, 3, 4, 5]',
    holiday_mode_enabled BOOLEAN DEFAULT false,
    holiday_dates JSON DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_notification_time_rules_user_id ON notification_time_rules(user_id);

-- 4. 通知历史记录表
CREATE TABLE notification_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    message VARCHAR(2000) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    channel_type VARCHAR(50) NOT NULL,
    channel_config_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message VARCHAR(500),
    signal_id INTEGER,
    strategy_id INTEGER,
    extra_data JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notification_history_user_id ON notification_history(user_id);
CREATE INDEX idx_notification_history_created_at ON notification_history(created_at DESC);
```

## 初始化数据

可以为默认用户（user_id=1）创建初始配置：

```sql
-- 创建默认频率限制配置
INSERT INTO notification_frequency_limits (user_id, p2_min_interval, p1_min_interval, p0_batch_interval, p0_batch_enabled, p0_batch_max_size, enabled)
VALUES (1, 0, 60, 300, true, 10, true);

-- 可选：创建默认时间规则
INSERT INTO notification_time_rules (user_id, rule_name, enabled, quiet_hours_enabled, quiet_start_time, quiet_end_time, quiet_priority_filter)
VALUES (1, '默认规则', true, true, '22:00', '08:00', 'P2');
```

## 验证迁移

启动应用后，可以通过以下API验证表是否创建成功：

```bash
# 检查NotifyHub健康状态
curl http://localhost:8000/api/v1/notify/system/health

# 获取渠道配置列表
curl http://localhost:8000/api/v1/notify/channels

# 获取频率限制配置
curl http://localhost:8000/api/v1/notify/frequency-limits
```

## 注意事项

1. **表已存在**：如果表已经存在，SQLAlchemy的 `create_all()` 不会重复创建或修改表结构
2. **数据备份**：在生产环境迁移前，请先备份数据库
3. **用户ID**：确保users表已存在，因为notification表需要关联user_id
4. **索引优化**：notification_history表会快速增长，建议定期清理或分区

## 故障排除

### 问题1：表创建失败
**原因**：数据库连接失败或权限不足
**解决**：检查数据库连接配置，确保用户有CREATE TABLE权限

### 问题2：启动时报错 "table already exists"
**原因**：表已存在但结构不匹配
**解决**：删除旧表或使用Alembic进行版本化迁移

### 问题3：外键约束失败
**原因**：users表不存在
**解决**：先确保users表已创建

## 下一步

配置完成后，可以：

1. 通过API配置通知渠道：`POST /api/v1/notify/channels`
2. 配置频率限制：`PUT /api/v1/notify/frequency-limits`
3. 配置时间规则：`POST /api/v1/notify/time-rules`
4. 发送测试通知：`POST /api/v1/notify/send`

详细API文档请参考 `API_DESIGN.md` 第2.7节。
