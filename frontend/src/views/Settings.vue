<template>
  <div class="settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统设置</span>
          <el-button type="primary" @click="saveSettings">保存设置</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="settings-tabs">
        <!-- 通知渠道 -->
        <el-tab-pane label="通知渠道" name="channels">
          <div class="channels-section">
            <!-- 渠道列表 -->
            <el-table
              :data="notificationChannels"
              v-loading="channelsLoading"
              style="width: 100%; margin-bottom: 20px"
            >
              <el-table-column prop="priority" label="优先级" width="100" sortable>
                <template #default="{ row }">
                  <div style="display: flex; align-items: center; gap: 4px">
                    <span>{{ row.priority }}</span>
                    <el-button-group size="small">
                      <el-button
                        :icon="ArrowUp"
                        size="small"
                        @click="handleChannelMovePriority(row, 'up')"
                        :disabled="row.priority === 1"
                      />
                      <el-button
                        :icon="ArrowDown"
                        size="small"
                        @click="handleChannelMovePriority(row, 'down')"
                        :disabled="row.priority === notificationChannels.length"
                      />
                    </el-button-group>
                  </div>
                </template>
              </el-table-column>

              <el-table-column label="渠道类型" width="120">
                <template #default="{ row }">
                  <el-tag :type="getChannelTypeColor(row.type)" size="small">
                    {{ getChannelTypeName(row.type) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column prop="name" label="渠道名称" min-width="150" />

              <el-table-column label="配置状态" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.configured" type="success">已配置</el-tag>
                  <el-tag v-else type="warning">未配置</el-tag>
                </template>
              </el-table-column>

              <el-table-column label="通知级别" width="200">
                <template #default="{ row }">
                  <el-space wrap>
                    <el-tag v-if="row.levels.includes('P0')" type="danger" size="small">P0</el-tag>
                    <el-tag v-if="row.levels.includes('P1')" type="warning" size="small">P1</el-tag>
                    <el-tag v-if="row.levels.includes('P2')" type="info" size="small">P2</el-tag>
                  </el-space>
                </template>
              </el-table-column>

              <el-table-column label="最后测试" width="150">
                <template #default="{ row }">
                  <span v-if="row.last_test_time" style="font-size: 12px">
                    {{ formatRelativeTime(row.last_test_time) }}
                  </span>
                  <span v-else style="color: #909399">未测试</span>
                </template>
              </el-table-column>

              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-switch
                    v-model="row.enabled"
                    @change="handleToggleChannel(row)"
                  />
                </template>
              </el-table-column>

              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    size="small"
                    @click="handleConfigureChannel(row)"
                  >
                    配置
                  </el-button>
                  <el-button
                    type="success"
                    size="small"
                    @click="handleTestChannel(row)"
                    :loading="testingChannelId === row.id"
                  >
                    测试
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 通知频率限制配置 -->
            <el-card shadow="never" header="通知频率限制" style="margin-bottom: 20px">
              <el-form label-width="160px">
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-form-item label="P2 最小间隔(秒)">
                      <el-input-number
                        v-model="frequencyLimits.p2_min_interval"
                        :min="0"
                        :max="300"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="P1 最小间隔(秒)">
                      <el-input-number
                        v-model="frequencyLimits.p1_min_interval"
                        :min="0"
                        :max="600"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="P0 批处理间隔(秒)">
                      <el-input-number
                        v-model="frequencyLimits.p0_batch_interval"
                        :min="60"
                        :max="3600"
                        style="width: 100%"
                      />
                    </el-form-item>
                </el-col>
                </el-row>

                <el-form-item>
                  <el-button type="primary" @click="saveFrequencyLimits">
                    保存频率限制
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 通知时间规则 -->
            <el-card shadow="never" header="通知时间规则">
              <el-form label-width="160px">
                <el-form-item label="勿扰模式">
                  <el-switch v-model="timeRules.do_not_disturb_enabled" />
                  <div class="form-item-tip">
                    在指定时间段内仅发送P2级别的紧急通知
                  </div>
                </el-form-item>

                <el-form-item label="勿扰时段" v-if="timeRules.do_not_disturb_enabled">
                  <el-row :gutter="10">
                    <el-col :span="8">
                      <el-time-select
                        v-model="timeRules.do_not_disturb_start"
                        start="00:00"
                        step="00:30"
                        end="23:30"
                        placeholder="开始时间"
                      />
                    </el-col>
                    <el-col :span="8">
                      <el-time-select
                        v-model="timeRules.do_not_disturb_end"
                        start="00:00"
                        step="00:30"
                        end="23:30"
                        placeholder="结束时间"
                      />
                    </el-col>
                  </el-row>
                </el-form-item>

                <el-form-item label="周末降级">
                  <el-switch v-model="timeRules.weekend_downgrade" />
                  <div class="form-item-tip">
                    周末时将P1降级为P0，P0通知进行批量发送
                  </div>
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" @click="saveTimeRules">
                    保存时间规则
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 通知设置 -->
        <el-tab-pane label="通知设置" name="notifications">
          <el-form :model="settings" label-width="160px">
            <el-form-item label="启用浏览器通知">
              <el-switch
                v-model="settings.notifications.browser_enabled"
                @change="handleBrowserNotificationChange"
              />
              <div class="form-item-tip">
                允许系统发送浏览器桌面通知
              </div>
            </el-form-item>

            <el-form-item label="通知权限状态">
              <el-tag :type="notificationPermissionType">
                {{ notificationPermissionText }}
              </el-tag>
              <el-button
                v-if="notificationPermission !== 'granted'"
                type="primary"
                size="small"
                @click="requestNotificationPermission"
                style="margin-left: 10px"
              >
                请求权限
              </el-button>
            </el-form-item>

            <el-divider />

            <el-form-item label="信号通知">
              <el-switch v-model="settings.notifications.signal_enabled" />
              <div class="form-item-tip">
                接收新交易信号的通知
              </div>
            </el-form-item>

            <el-form-item label="策略通知">
              <el-switch v-model="settings.notifications.strategy_enabled" />
              <div class="form-item-tip">
                接收策略启动/停止的通知
              </div>
            </el-form-item>

            <el-form-item label="系统通知">
              <el-switch v-model="settings.notifications.system_enabled" />
              <div class="form-item-tip">
                接收系统健康和性能警告
              </div>
            </el-form-item>

            <el-form-item label="通知声音">
              <el-switch v-model="settings.notifications.sound_enabled" />
              <div class="form-item-tip">
                播放通知提示音
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- WebSocket设置 -->
        <el-tab-pane label="WebSocket设置" name="websocket">
          <el-form :model="settings" label-width="160px">
            <el-form-item label="WebSocket状态">
              <el-tag :type="wsStore.isConnected ? 'success' : 'danger'">
                {{ wsStore.isConnected ? '已连接' : '未连接' }}
              </el-tag>
              <el-button
                type="primary"
                size="small"
                @click="reconnectWebSocket"
                style="margin-left: 10px"
                :disabled="wsStore.isConnected"
              >
                重新连接
              </el-button>
            </el-form-item>

            <el-form-item label="重连次数">
              <el-input-number
                v-model="settings.websocket.max_reconnect_attempts"
                :min="1"
                :max="10"
              />
              <div class="form-item-tip">
                WebSocket断开后的最大重连尝试次数
              </div>
            </el-form-item>

            <el-form-item label="重连延迟(秒)">
              <el-input-number
                v-model="settings.websocket.reconnect_delay"
                :min="1"
                :max="30"
              />
              <div class="form-item-tip">
                WebSocket重连的延迟时间
              </div>
            </el-form-item>

            <el-form-item label="心跳间隔(秒)">
              <el-input-number
                v-model="settings.websocket.heartbeat_interval"
                :min="10"
                :max="60"
              />
              <div class="form-item-tip">
                发送心跳的间隔时间（应小于服务器超时时间）
              </div>
            </el-form-item>

            <el-divider />

            <el-form-item label="订阅的主题">
              <el-checkbox-group v-model="settings.websocket.subscribed_topics">
                <el-checkbox label="monitoring">系统监控</el-checkbox>
                <el-checkbox label="strategies">策略状态</el-checkbox>
                <el-checkbox label="signals">交易信号</el-checkbox>
                <el-checkbox label="capacity">容量信息</el-checkbox>
                <el-checkbox label="logs">系统日志</el-checkbox>
              </el-checkbox-group>
              <div class="form-item-tip">
                选择需要订阅的WebSocket数据主题
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 显示设置 -->
        <el-tab-pane label="显示设置" name="display">
          <el-form :model="settings" label-width="160px">
            <el-form-item label="刷新间隔(秒)">
              <el-input-number
                v-model="settings.display.refresh_interval"
                :min="5"
                :max="300"
              />
              <div class="form-item-tip">
                仪表盘数据的自动刷新间隔
              </div>
            </el-form-item>

            <el-form-item label="每页显示行数">
              <el-input-number
                v-model="settings.display.page_size"
                :min="10"
                :max="100"
                :step="10"
              />
              <div class="form-item-tip">
                表格每页显示的数据行数
              </div>
            </el-form-item>

            <el-form-item label="日期格式">
              <el-select v-model="settings.display.date_format">
                <el-option label="YYYY-MM-DD HH:mm:ss" value="YYYY-MM-DD HH:mm:ss" />
                <el-option label="YYYY/MM/DD HH:mm:ss" value="YYYY/MM/DD HH:mm:ss" />
                <el-option label="DD/MM/YYYY HH:mm:ss" value="DD/MM/YYYY HH:mm:ss" />
                <el-option label="MM/DD/YYYY HH:mm:ss" value="MM/DD/YYYY HH:mm:ss" />
              </el-select>
              <div class="form-item-tip">
                日期时间的显示格式
              </div>
            </el-form-item>

            <el-form-item label="数字格式">
              <el-select v-model="settings.display.number_format">
                <el-option label="1,234.56" value="en-US" />
                <el-option label="1.234,56" value="de-DE" />
                <el-option label="1 234,56" value="fr-FR" />
              </el-select>
              <div class="form-item-tip">
                数字和货币的显示格式
              </div>
            </el-form-item>

            <el-divider />

            <el-form-item label="显示图表">
              <el-switch v-model="settings.display.show_charts" />
              <div class="form-item-tip">
                在仪表盘显示数据图表
              </div>
            </el-form-item>

            <el-form-item label="显示趋势线">
              <el-switch v-model="settings.display.show_trends" />
              <div class="form-item-tip">
                在图表中显示趋势线
              </div>
            </el-form-item>

            <el-form-item label="动画效果">
              <el-switch v-model="settings.display.enable_animations" />
              <div class="form-item-tip">
                启用页面切换和加载动画
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 账户设置 -->
        <el-tab-pane label="账户设置" name="account">
          <el-form :model="accountForm" label-width="160px">
            <el-form-item label="用户名">
              <el-input v-model="userStore.user.username" disabled />
            </el-form-item>

            <el-form-item label="邮箱">
              <el-input v-model="userStore.user.email" disabled />
            </el-form-item>

            <el-divider content-position="left">修改密码</el-divider>

            <el-form-item label="当前密码">
              <el-input
                v-model="accountForm.current_password"
                type="password"
                show-password
                placeholder="请输入当前密码"
              />
            </el-form-item>

            <el-form-item label="新密码">
              <el-input
                v-model="accountForm.new_password"
                type="password"
                show-password
                placeholder="请输入新密码"
              />
            </el-form-item>

            <el-form-item label="确认新密码">
              <el-input
                v-model="accountForm.confirm_password"
                type="password"
                show-password
                placeholder="请再次输入新密码"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="changePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 高级设置 -->
        <el-tab-pane label="高级设置" name="advanced">
          <el-form :model="settings" label-width="160px">
            <el-form-item label="调试模式">
              <el-switch v-model="settings.advanced.debug_mode" />
              <div class="form-item-tip">
                启用控制台调试信息输出
              </div>
            </el-form-item>

            <el-form-item label="API请求超时(秒)">
              <el-input-number
                v-model="settings.advanced.api_timeout"
                :min="10"
                :max="120"
              />
              <div class="form-item-tip">
                API请求的超时时间
              </div>
            </el-form-item>

            <el-form-item label="缓存策略">
              <el-select v-model="settings.advanced.cache_strategy">
                <el-option label="无缓存" value="none" />
                <el-option label="内存缓存" value="memory" />
                <el-option label="本地存储" value="localStorage" />
              </el-select>
              <div class="form-item-tip">
                数据缓存策略
              </div>
            </el-form-item>

            <el-divider />

            <el-form-item label="清除缓存">
              <el-button type="warning" @click="clearCache">清除所有缓存</el-button>
              <div class="form-item-tip">
                清除浏览器中存储的所有缓存数据
              </div>
            </el-form-item>

            <el-form-item label="重置设置">
              <el-button type="danger" @click="resetSettings">恢复默认设置</el-button>
              <div class="form-item-tip">
                将所有设置恢复到默认值
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 关于 -->
        <el-tab-pane label="关于" name="about">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="版本">
              {{ appVersion }}
            </el-descriptions-item>
            <el-descriptions-item label="环境">
              {{ appEnvironment }}
            </el-descriptions-item>
            <el-descriptions-item label="API地址">
              {{ apiBaseURL }}
            </el-descriptions-item>
            <el-descriptions-item label="WebSocket地址">
              {{ wsBaseURL }}
            </el-descriptions-item>
            <el-descriptions-item label="构建时间">
              {{ buildTime }}
            </el-descriptions-item>
          </el-descriptions>

          <el-divider />

          <div class="about-section">
            <h3>技术栈</h3>
            <ul>
              <li>Vue 3 (Composition API)</li>
              <li>Pinia (状态管理)</li>
              <li>Element Plus (UI框架)</li>
              <li>ECharts (数据可视化)</li>
              <li>WebSocket (实时通信)</li>
            </ul>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 渠道配置对话框 -->
    <el-dialog
      v-model="showChannelConfigDialog"
      :title="`配置${currentChannel?.name || '通知渠道'}`"
      width="700px"
      destroy-on-close
    >
      <el-form
        v-if="currentChannel"
        ref="channelFormRef"
        :model="channelForm"
        label-width="140px"
      >
        <el-form-item label="渠道名称">
          <el-input v-model="channelForm.name" placeholder="自定义渠道名称" />
        </el-form-item>

        <el-form-item label="通知级别">
          <el-checkbox-group v-model="channelForm.levels">
            <el-checkbox label="P2">P2 - 紧急通知（立即发送）</el-checkbox>
            <el-checkbox label="P1">P1 - 重要通知（实时发送）</el-checkbox>
            <el-checkbox label="P0">P0 - 一般通知（批量发送）</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-divider content-position="left">API配置</el-divider>

        <!-- SMS配置 -->
        <template v-if="currentChannel.type === 'sms'">
          <el-form-item label="API密钥">
            <el-input
              v-model="channelForm.config.api_key"
              placeholder="请输入短信服务API密钥"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item label="API密钥ID">
            <el-input
              v-model="channelForm.config.api_secret"
              placeholder="请输入API密钥ID"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item label="签名">
            <el-input v-model="channelForm.config.sign_name" placeholder="短信签名" />
          </el-form-item>
          <el-form-item label="接收号码">
            <el-select
              v-model="channelForm.config.phone_numbers"
              multiple
              filterable
              allow-create
              placeholder="请输入手机号码"
              style="width: 100%"
            >
            </el-select>
          </el-form-item>
        </template>

        <!-- 飞书配置 -->
        <template v-if="currentChannel.type === 'feishu'">
          <el-form-item label="Webhook URL">
            <el-input
              v-model="channelForm.config.webhook_url"
              placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
            />
          </el-form-item>
          <el-form-item label="签名密钥">
            <el-input
              v-model="channelForm.config.secret"
              placeholder="用于签名验证（可选）"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item label="@提醒用户">
            <el-select
              v-model="channelForm.config.at_users"
              multiple
              filterable
              allow-create
              placeholder="输入用户ID或@all"
              style="width: 100%"
            >
              <el-option label="@所有人" value="all" />
            </el-select>
          </el-form-item>
        </template>

        <!-- 微信配置 -->
        <template v-if="currentChannel.type === 'wechat'">
          <el-form-item label="企业ID">
            <el-input v-model="channelForm.config.corp_id" placeholder="企业微信CorpID" />
          </el-form-item>
          <el-form-item label="应用AgentID">
            <el-input v-model="channelForm.config.agent_id" placeholder="应用的AgentID" />
          </el-form-item>
          <el-form-item label="应用Secret">
            <el-input
              v-model="channelForm.config.secret"
              placeholder="应用的Secret"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item label="接收用户">
            <el-input
              v-model="channelForm.config.to_user"
              placeholder="用户UserID列表，用|分隔，@all表示全部"
            />
          </el-form-item>
        </template>

        <!-- Email配置 -->
        <template v-if="currentChannel.type === 'email'">
          <el-form-item label="SMTP服务器">
            <el-input v-model="channelForm.config.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item label="SMTP端口">
            <el-input-number
              v-model="channelForm.config.smtp_port"
              :min="1"
              :max="65535"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="发件人邮箱">
            <el-input v-model="channelForm.config.from_email" placeholder="noreply@example.com" />
          </el-form-item>
          <el-form-item label="发件人密码">
            <el-input
              v-model="channelForm.config.password"
              placeholder="SMTP密码或授权码"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item label="收件人">
            <el-select
              v-model="channelForm.config.to_emails"
              multiple
              filterable
              allow-create
              placeholder="请输入邮箱地址"
              style="width: 100%"
            >
            </el-select>
          </el-form-item>
          <el-form-item label="使用TLS">
            <el-switch v-model="channelForm.config.use_tls" />
          </el-form-item>
        </template>

        <!-- Telegram配置 -->
        <template v-if="currentChannel.type === 'telegram'">
          <el-form-item label="Bot Token">
            <el-input
              v-model="channelForm.config.bot_token"
              placeholder="从BotFather获取的Token"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item label="Chat ID">
            <el-select
              v-model="channelForm.config.chat_ids"
              multiple
              filterable
              allow-create
              placeholder="接收消息的Chat ID"
              style="width: 100%"
            >
            </el-select>
          </el-form-item>
          <el-form-item label="消息格式">
            <el-select v-model="channelForm.config.parse_mode" style="width: 100%">
              <el-option label="纯文本" value="" />
              <el-option label="Markdown" value="Markdown" />
              <el-option label="HTML" value="HTML" />
            </el-select>
          </el-form-item>
        </template>

        <el-divider content-position="left">消息模板</el-divider>

        <el-form-item label="P2模板">
          <el-input
            v-model="channelForm.templates.p2"
            type="textarea"
            :rows="3"
            placeholder="🚨 [紧急] {strategy_name}: {signal_type} 信号&#10;价格: {price}&#10;强度: {strength}"
          />
        </el-form-item>

        <el-form-item label="P1模板">
          <el-input
            v-model="channelForm.templates.p1"
            type="textarea"
            :rows="3"
            placeholder="⚠️ [重要] {strategy_name}: {signal_type} 信号&#10;价格: {price}&#10;强度: {strength}"
          />
        </el-form-item>

        <el-form-item label="P0模板">
          <el-input
            v-model="channelForm.templates.p0"
            type="textarea"
            :rows="3"
            placeholder="ℹ️ {strategy_name}: {signal_type} 信号&#10;价格: {price}"
          />
        </el-form-item>

        <el-form-item>
          <div class="form-item-tip">
            可用变量: {strategy_name}, {signal_type}, {price}, {strength}, {pair}, {exchange}
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showChannelConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="saveChannelConfig">
          保存配置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { notificationAPI, settingsAPI } from '@/api'

const userStore = useUserStore()
const wsStore = useWebSocketStore()

const activeTab = ref('channels')
const channelsLoading = ref(false)
const testingChannelId = ref(null)
const showChannelConfigDialog = ref(false)
const channelFormRef = ref(null)
const currentChannel = ref(null)

// 通知渠道列表
const notificationChannels = ref([
  {
    id: 1,
    type: 'sms',
    name: '短信通知',
    priority: 1,
    enabled: false,
    configured: false,
    levels: ['P2'],
    last_test_time: null
  },
  {
    id: 2,
    type: 'feishu',
    name: '飞书机器人',
    priority: 2,
    enabled: false,
    configured: false,
    levels: ['P2', 'P1'],
    last_test_time: null
  },
  {
    id: 3,
    type: 'wechat',
    name: '企业微信',
    priority: 3,
    enabled: false,
    configured: false,
    levels: ['P2', 'P1', 'P0'],
    last_test_time: null
  },
  {
    id: 4,
    type: 'email',
    name: '邮件通知',
    priority: 4,
    enabled: false,
    configured: false,
    levels: ['P1', 'P0'],
    last_test_time: null
  },
  {
    id: 5,
    type: 'telegram',
    name: 'Telegram机器人',
    priority: 5,
    enabled: false,
    configured: false,
    levels: ['P2', 'P1'],
    last_test_time: null
  }
])

// 频率限制配置
const frequencyLimits = reactive({
  p2_min_interval: 0,
  p1_min_interval: 60,
  p0_batch_interval: 300
})

// 时间规则配置
const timeRules = reactive({
  do_not_disturb_enabled: false,
  do_not_disturb_start: '23:00',
  do_not_disturb_end: '08:00',
  weekend_downgrade: false
})

// 渠道配置表单
const channelForm = reactive({
  name: '',
  levels: [],
  config: {},
  templates: {
    p2: '',
    p1: '',
    p0: ''
  }
})

// 渠道类型名称映射
const getChannelTypeName = (type) => {
  const nameMap = {
    sms: '短信',
    feishu: '飞书',
    wechat: '企业微信',
    email: '邮件',
    telegram: 'Telegram'
  }
  return nameMap[type] || type
}

// 渠道类型颜色映射
const getChannelTypeColor = (type) => {
  const colorMap = {
    sms: 'danger',
    feishu: 'primary',
    wechat: 'success',
    email: 'warning',
    telegram: 'info'
  }
  return colorMap[type] || ''
}

// 格式化相对时间
const formatRelativeTime = (timestamp) => {
  const now = new Date()
  const time = new Date(timestamp)
  const diff = (now - time) / 1000 // 秒

  if (diff < 60) {
    return '刚刚'
  } else if (diff < 3600) {
    return `${Math.floor(diff / 60)}分钟前`
  } else if (diff < 86400) {
    return `${Math.floor(diff / 3600)}小时前`
  } else {
    return `${Math.floor(diff / 86400)}天前`
  }
}

// 调整渠道优先级
const handleChannelMovePriority = (channel, direction) => {
  const currentIndex = notificationChannels.value.findIndex(c => c.id === channel.id)
  if (
    (direction === 'up' && currentIndex === 0) ||
    (direction === 'down' && currentIndex === notificationChannels.value.length - 1)
  ) {
    return
  }

  const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1
  const targetChannel = notificationChannels.value[targetIndex]

  // 交换优先级
  const tempPriority = channel.priority
  channel.priority = targetChannel.priority
  targetChannel.priority = tempPriority

  // 重新排序
  notificationChannels.value.sort((a, b) => a.priority - b.priority)

  ElMessage.success('优先级已调整')

  // TODO: 调用API保存优先级
  // await notificationAPI.updateChannelPriority(channel.id, targetChannel.id)
}

// 切换渠道启用状态
const handleToggleChannel = (channel) => {
  if (!channel.configured && channel.enabled) {
    ElMessage.warning('请先配置该渠道')
    channel.enabled = false
    return
  }

  ElMessage.success(channel.enabled ? '渠道已启用' : '渠道已禁用')

  // 保存启用状态到localStorage
  try {
    const saved = localStorage.getItem(`notification_channel_${channel.id}`)
    if (saved) {
      const config = JSON.parse(saved)
      config.enabled = channel.enabled
      localStorage.setItem(`notification_channel_${channel.id}`, JSON.stringify(config))
    }
  } catch (error) {
    console.error('Failed to save channel enabled state:', error)
  }

  // TODO: 调用API保存状态
  // await notificationAPI.updateChannelStatus(channel.id, channel.enabled)
}

// 配置渠道
const handleConfigureChannel = (channel) => {
  currentChannel.value = channel

  // 重置表单
  channelForm.name = channel.name
  channelForm.levels = [...channel.levels]
  channelForm.config = {}
  channelForm.templates = {
    p2: '🚨 [紧急] {strategy_name}: {signal_type} 信号\n价格: {price}\n强度: {strength}',
    p1: '⚠️ [重要] {strategy_name}: {signal_type} 信号\n价格: {price}\n强度: {strength}',
    p0: 'ℹ️ {strategy_name}: {signal_type} 信号\n价格: {price}'
  }

  // 根据渠道类型初始化config
  switch (channel.type) {
    case 'sms':
      channelForm.config = {
        api_key: '',
        api_secret: '',
        sign_name: '',
        phone_numbers: []
      }
      break
    case 'feishu':
      channelForm.config = {
        webhook_url: '',
        secret: '',
        at_users: []
      }
      break
    case 'wechat':
      channelForm.config = {
        corp_id: '',
        agent_id: '',
        secret: '',
        to_user: ''
      }
      break
    case 'email':
      channelForm.config = {
        smtp_host: '',
        smtp_port: 587,
        from_email: '',
        password: '',
        to_emails: [],
        use_tls: true
      }
      break
    case 'telegram':
      channelForm.config = {
        bot_token: '',
        chat_ids: [],
        parse_mode: 'Markdown'
      }
      break
  }

  showChannelConfigDialog.value = true
}

// 测试渠道
const handleTestChannel = async (channel) => {
  if (!channel.configured) {
    ElMessage.warning('请先配置该渠道')
    return
  }

  if (!channel.enabled) {
    ElMessage.warning('请先启用该渠道')
    return
  }

  testingChannelId.value = channel.id
  try {
    // TODO: 调用API测试渠道
    // const res = await notificationAPI.test(channel.type)

    // 模拟测试
    await new Promise(resolve => setTimeout(resolve, 1500))

    channel.last_test_time = new Date().toISOString()
    ElMessage.success('测试消息已发送，请检查接收情况')
  } catch (error) {
    console.error('Failed to test channel:', error)
    ElMessage.error('测试失败')
  } finally {
    testingChannelId.value = null
  }
}

// 保存渠道配置
const saveChannelConfig = () => {
  if (!channelForm.levels || channelForm.levels.length === 0) {
    ElMessage.warning('请至少选择一个通知级别')
    return
  }

  // 基本验证
  let isValid = true
  const config = channelForm.config

  switch (currentChannel.value.type) {
    case 'sms':
      if (!config.api_key || !config.api_secret || config.phone_numbers.length === 0) {
        ElMessage.warning('请填写完整的短信配置')
        isValid = false
      }
      break
    case 'feishu':
      if (!config.webhook_url) {
        ElMessage.warning('请填写飞书Webhook URL')
        isValid = false
      }
      break
    case 'wechat':
      if (!config.corp_id || !config.agent_id || !config.secret) {
        ElMessage.warning('请填写完整的企业微信配置')
        isValid = false
      }
      break
    case 'email':
      if (!config.smtp_host || !config.from_email || !config.password || config.to_emails.length === 0) {
        ElMessage.warning('请填写完整的邮件配置')
        isValid = false
      }
      break
    case 'telegram':
      if (!config.bot_token || config.chat_ids.length === 0) {
        ElMessage.warning('请填写完整的Telegram配置')
        isValid = false
      }
      break
  }

  if (!isValid) return

  // 保存配置到localStorage
  const channelConfig = {
    id: currentChannel.value.id,
    type: currentChannel.value.type,
    name: channelForm.name,
    levels: channelForm.levels,
    config: channelForm.config,
    templates: channelForm.templates,
    enabled: currentChannel.value.enabled || false
  }

  try {
    localStorage.setItem(`notification_channel_${currentChannel.value.id}`, JSON.stringify(channelConfig))

    // 在notificationChannels数组中找到并更新渠道 - 使用响应式方式
    const index = notificationChannels.value.findIndex(c => c.id === currentChannel.value.id)
    if (index !== -1) {
      // 使用Object.assign确保响应式更新
      Object.assign(notificationChannels.value[index], {
        name: channelForm.name,
        levels: [...channelForm.levels],
        configured: true
      })
    }

    ElMessage.success('渠道配置已保存')
    showChannelConfigDialog.value = false

    // TODO: 调用API保存配置
    // await notificationAPI.updateChannel(currentChannel.value.id, channelConfig)
  } catch (error) {
    console.error('Failed to save channel config:', error)
    ElMessage.error('保存配置失败')
  }
}

// 保存频率限制
const saveFrequencyLimits = () => {
  try {
    localStorage.setItem('notification_frequency_limits', JSON.stringify(frequencyLimits))
    ElMessage.success('频率限制已保存')

    // TODO: 调用API保存配置
    // await notificationAPI.updateFrequencyLimits(frequencyLimits)
  } catch (error) {
    console.error('Failed to save frequency limits:', error)
    ElMessage.error('保存失败')
  }
}

// 保存时间规则
const saveTimeRules = () => {
  if (timeRules.do_not_disturb_enabled) {
    if (!timeRules.do_not_disturb_start || !timeRules.do_not_disturb_end) {
      ElMessage.warning('请设置完整的勿扰时段')
      return
    }
  }

  try {
    localStorage.setItem('notification_time_rules', JSON.stringify(timeRules))
    ElMessage.success('时间规则已保存')

    // TODO: 调用API保存配置
    // await notificationAPI.updateTimeRules(timeRules)
  } catch (error) {
    console.error('Failed to save time rules:', error)
    ElMessage.error('保存失败')
  }
}

// 加载渠道配置
const loadChannelConfigs = () => {
  notificationChannels.value.forEach(channel => {
    try {
      const saved = localStorage.getItem(`notification_channel_${channel.id}`)
      if (saved) {
        const config = JSON.parse(saved)
        // 使用Object.assign确保响应式更新
        Object.assign(channel, {
          name: config.name,
          levels: config.levels,
          configured: true,
          enabled: config.enabled || false
        })
      }
    } catch (error) {
      console.error(`Failed to load config for channel ${channel.id}:`, error)
    }
  })

  // 加载频率限制
  try {
    const savedLimits = localStorage.getItem('notification_frequency_limits')
    if (savedLimits) {
      Object.assign(frequencyLimits, JSON.parse(savedLimits))
    }
  } catch (error) {
    console.error('Failed to load frequency limits:', error)
  }

  // 加载时间规则
  try {
    const savedRules = localStorage.getItem('notification_time_rules')
    if (savedRules) {
      Object.assign(timeRules, JSON.parse(savedRules))
    }
  } catch (error) {
    console.error('Failed to load time rules:', error)
  }
}

// 默认设置
const defaultSettings = {
  notifications: {
    browser_enabled: true,
    signal_enabled: true,
    strategy_enabled: true,
    system_enabled: true,
    sound_enabled: false
  },
  websocket: {
    max_reconnect_attempts: 5,
    reconnect_delay: 3,
    heartbeat_interval: 25,
    subscribed_topics: ['monitoring', 'strategies', 'signals', 'capacity']
  },
  display: {
    refresh_interval: 30,
    page_size: 20,
    date_format: 'YYYY-MM-DD HH:mm:ss',
    number_format: 'en-US',
    show_charts: true,
    show_trends: true,
    enable_animations: true
  },
  advanced: {
    debug_mode: false,
    api_timeout: 30,
    cache_strategy: 'memory'
  }
}

// 设置对象
const settings = reactive(JSON.parse(JSON.stringify(defaultSettings)))

// 账户表单
const accountForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

// 通知权限
const notificationPermission = ref('default')

const notificationPermissionType = computed(() => {
  const typeMap = {
    granted: 'success',
    denied: 'danger',
    default: 'warning'
  }
  return typeMap[notificationPermission.value] || 'info'
})

const notificationPermissionText = computed(() => {
  const textMap = {
    granted: '已授权',
    denied: '已拒绝',
    default: '未设置'
  }
  return textMap[notificationPermission.value] || '未知'
})

// 应用信息
const appVersion = ref('1.0.0')
const appEnvironment = ref(import.meta.env.MODE || 'development')
const apiBaseURL = ref(import.meta.env.VITE_API_URL || 'http://localhost:8000')
const wsBaseURL = ref(import.meta.env.VITE_WS_URL || 'ws://localhost:8000')
const buildTime = ref(new Date().toLocaleString('zh-CN'))

// 加载设置
const loadSettings = async () => {
  try {
    // 先从localStorage加载（快速显示）
    const saved = localStorage.getItem('app_settings')
    if (saved) {
      const parsed = JSON.parse(saved)
      Object.assign(settings, parsed)
    }

    // 从后端API加载最新设置
    const response = await settingsAPI.get()
    Object.assign(settings, response)

    // 同步到localStorage
    localStorage.setItem('app_settings', JSON.stringify(settings))
  } catch (error) {
    console.error('Failed to load settings:', error)
    // 如果API失败，继续使用localStorage的设置
  }
}

// 保存设置
const saveSettings = async () => {
  try {
    // 保存到localStorage（本地缓存）
    localStorage.setItem('app_settings', JSON.stringify(settings))

    // 保存到后端API（持久化）
    await settingsAPI.update(settings)

    ElMessage.success('设置已保存')
  } catch (error) {
    console.error('Failed to save settings:', error)
    ElMessage.error('保存设置失败')
  }
}

// 重置设置
const resetSettings = async () => {
  ElMessageBox.confirm(
    '确定要恢复默认设置吗？此操作不可撤销。',
    '确认重置',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // 调用后端API重置设置
      const response = await settingsAPI.reset()

      // 更新本地设置
      Object.assign(settings, response.settings)

      // 更新localStorage
      localStorage.setItem('app_settings', JSON.stringify(settings))

      ElMessage.success('已恢复默认设置')
    } catch (error) {
      console.error('Failed to reset settings:', error)
      ElMessage.error('重置设置失败')
    }
  }).catch(() => {
    // 用户取消
  })
}

// 清除缓存
const clearCache = () => {
  ElMessageBox.confirm(
    '确定要清除所有缓存数据吗？',
    '确认清除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    localStorage.clear()
    sessionStorage.clear()
    ElMessage.success('缓存已清除，请刷新页面')
  }).catch(() => {
    // 用户取消
  })
}

// 请求通知权限
const requestNotificationPermission = async () => {
  if ('Notification' in window) {
    try {
      const permission = await Notification.requestPermission()
      notificationPermission.value = permission
      if (permission === 'granted') {
        ElMessage.success('通知权限已授予')
      } else if (permission === 'denied') {
        ElMessage.warning('通知权限被拒绝')
      }
    } catch (error) {
      console.error('Failed to request notification permission:', error)
      ElMessage.error('请求通知权限失败')
    }
  } else {
    ElMessage.warning('浏览器不支持通知功能')
  }
}

// 处理浏览器通知开关变化
const handleBrowserNotificationChange = (enabled) => {
  if (enabled && notificationPermission.value !== 'granted') {
    requestNotificationPermission()
  }
}

// 重连WebSocket
const reconnectWebSocket = () => {
  if (userStore.token) {
    wsStore.disconnect()
    setTimeout(() => {
      wsStore.connect(userStore.token)
      ElMessage.success('正在重新连接WebSocket...')
    }, 500)
  } else {
    ElMessage.error('未登录，无法连接WebSocket')
  }
}

// 修改密码
const changePassword = async () => {
  if (!accountForm.current_password || !accountForm.new_password) {
    ElMessage.warning('请填写完整的密码信息')
    return
  }

  if (accountForm.new_password !== accountForm.confirm_password) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }

  if (accountForm.new_password.length < 6) {
    ElMessage.error('新密码长度不能少于6位')
    return
  }

  try {
    // TODO: 调用修改密码API
    // await authAPI.changePassword(accountForm.current_password, accountForm.new_password)
    ElMessage.success('密码修改成功，请重新登录')

    // 清空表单
    accountForm.current_password = ''
    accountForm.new_password = ''
    accountForm.confirm_password = ''

    // TODO: 登出并跳转到登录页
    // await userStore.logout()
    // router.push('/login')
  } catch (error) {
    console.error('Failed to change password:', error)
    ElMessage.error('修改密码失败：' + (error.message || '未知错误'))
  }
}

// 组件挂载
onMounted(() => {
  loadSettings()
  loadChannelConfigs()

  // 检查通知权限
  if ('Notification' in window) {
    notificationPermission.value = Notification.permission
  }
})
</script>

<style scoped>
.settings {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.settings-tabs {
  margin-top: 20px;
}

.form-item-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.about-section {
  margin-top: 20px;
}

.about-section h3 {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 12px;
}

.about-section ul {
  list-style: none;
  padding: 0;
}

.about-section li {
  padding: 8px 0;
  color: #606266;
  border-bottom: 1px solid #EBEEF5;
}

.about-section li:last-child {
  border-bottom: none;
}

.about-section li:before {
  content: "•";
  color: #409EFF;
  font-weight: bold;
  display: inline-block;
  width: 1em;
  margin-left: -1em;
}
</style>
