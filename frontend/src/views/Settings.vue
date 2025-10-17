<template>
  <div class="settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('settings.title') }}</span>
          <el-button type="primary" @click="saveSettings">{{ t('settings.save') }}</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="settings-tabs">
        <!-- 通知渠道 -->
        <el-tab-pane :label="t('settings.channels')" name="channels">
          <div class="channels-section">
            <!-- 渠道列表 -->
            <el-table
              :data="notificationChannels"
              v-loading="channelsLoading"
              style="width: 100%; margin-bottom: 20px"
            >
              <el-table-column prop="priority" :label="t('settings.priority')" width="100" sortable>
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

              <el-table-column :label="t('settings.channelType')" width="120">
                <template #default="{ row }">
                  <el-tag :type="getChannelTypeColor(row.type)" size="small">
                    {{ getChannelTypeName(row.type) }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column prop="name" :label="t('settings.channelName')" min-width="150" />

              <el-table-column :label="t('settings.configStatus')" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.configured" type="success">{{ t('settings.configured') }}</el-tag>
                  <el-tag v-else type="warning">{{ t('settings.notConfigured') }}</el-tag>
                </template>
              </el-table-column>

              <el-table-column :label="t('settings.notificationLevel')" width="200">
                <template #default="{ row }">
                  <el-space wrap>
                    <el-tag v-if="row.levels.includes('P0')" type="danger" size="small">P0</el-tag>
                    <el-tag v-if="row.levels.includes('P1')" type="warning" size="small">P1</el-tag>
                    <el-tag v-if="row.levels.includes('P2')" type="info" size="small">P2</el-tag>
                  </el-space>
                </template>
              </el-table-column>

              <el-table-column :label="t('settings.lastTest')" width="150">
                <template #default="{ row }">
                  <span v-if="row.last_test_time" style="font-size: 12px">
                    {{ formatRelativeTime(row.last_test_time) }}
                  </span>
                  <span v-else style="color: #909399">{{ t('settings.notTested') }}</span>
                </template>
              </el-table-column>

              <el-table-column :label="t('settings.status')" width="80">
                <template #default="{ row }">
                  <el-switch
                    v-model="row.enabled"
                    @change="handleToggleChannel(row)"
                  />
                </template>
              </el-table-column>

              <el-table-column :label="t('settings.actions')" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    size="small"
                    @click="handleConfigureChannel(row)"
                  >
                    {{ t('settings.configure') }}
                  </el-button>
                  <el-button
                    type="success"
                    size="small"
                    @click="handleTestChannel(row)"
                    :loading="testingChannelId === row.id"
                  >
                    {{ t('settings.test') }}
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <!-- 通知频率限制配置 -->
            <el-card shadow="never" :header="t('settings.frequencyLimit')" style="margin-bottom: 20px">
              <el-form label-width="160px">
                <el-row :gutter="20">
                  <el-col :span="8">
                    <el-form-item :label="t('settings.p2MinInterval')">
                      <el-input-number
                        v-model="frequencyLimits.p2_min_interval"
                        :min="0"
                        :max="300"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="t('settings.p1MinInterval')">
                      <el-input-number
                        v-model="frequencyLimits.p1_min_interval"
                        :min="0"
                        :max="600"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item :label="t('settings.p0BatchInterval')">
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
                    {{ t('settings.saveFrequencyLimit') }}
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 通知时间规则 -->
            <el-card shadow="never" :header="t('settings.timeRules')">
              <el-form label-width="160px">
                <el-form-item :label="t('settings.doNotDisturb')">
                  <el-switch v-model="timeRules.do_not_disturb_enabled" />
                  <div class="form-item-tip">
                    {{ t('settings.doNotDisturbTip') }}
                  </div>
                </el-form-item>

                <el-form-item :label="t('settings.doNotDisturbPeriod')" v-if="timeRules.do_not_disturb_enabled">
                  <el-row :gutter="10">
                    <el-col :span="8">
                      <el-time-select
                        v-model="timeRules.do_not_disturb_start"
                        start="00:00"
                        step="00:30"
                        end="23:30"
                        :placeholder="t('settings.startTime')"
                      />
                    </el-col>
                    <el-col :span="8">
                      <el-time-select
                        v-model="timeRules.do_not_disturb_end"
                        start="00:00"
                        step="00:30"
                        end="23:30"
                        :placeholder="t('settings.endTime')"
                      />
                    </el-col>
                  </el-row>
                </el-form-item>

                <el-form-item :label="t('settings.weekendDowngrade')">
                  <el-switch v-model="timeRules.weekend_downgrade" />
                  <div class="form-item-tip">
                    {{ t('settings.weekendDowngradeTip') }}
                  </div>
                </el-form-item>

                <el-form-item>
                  <el-button type="primary" @click="saveTimeRules">
                    {{ t('settings.saveTimeRules') }}
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 通知设置 -->
        <el-tab-pane :label="t('settings.notifications')" name="notifications">
          <el-form :model="settings" label-width="160px">
            <el-form-item :label="t('settings.browserNotification')">
              <el-switch
                v-model="settings.notifications.browser_enabled"
                @change="handleBrowserNotificationChange"
              />
              <div class="form-item-tip">
                {{ t('settings.browserNotificationTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.notificationPermission')">
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
                {{ t('settings.requestPermission') }}
              </el-button>
            </el-form-item>

            <el-divider />

            <el-form-item :label="t('settings.signalNotification')">
              <el-switch v-model="settings.notifications.signal_enabled" />
              <div class="form-item-tip">
                {{ t('settings.signalNotificationTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.strategyNotification')">
              <el-switch v-model="settings.notifications.strategy_enabled" />
              <div class="form-item-tip">
                {{ t('settings.strategyNotificationTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.systemNotification')">
              <el-switch v-model="settings.notifications.system_enabled" />
              <div class="form-item-tip">
                {{ t('settings.systemNotificationTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.notificationSound')">
              <el-switch v-model="settings.notifications.sound_enabled" />
              <div class="form-item-tip">
                {{ t('settings.notificationSoundTip') }}
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- WebSocket设置 -->
        <el-tab-pane :label="t('settings.websocket')" name="websocket">
          <el-form :model="settings" label-width="160px">
            <el-form-item :label="t('settings.wsStatus')">
              <el-tag :type="wsStore.isConnected ? 'success' : 'danger'">
                {{ wsStore.isConnected ? t('settings.connected') : t('settings.disconnected') }}
              </el-tag>
              <el-button
                type="primary"
                size="small"
                @click="reconnectWebSocket"
                style="margin-left: 10px"
                :disabled="wsStore.isConnected"
              >
                {{ t('settings.reconnect') }}
              </el-button>
            </el-form-item>

            <el-form-item :label="t('settings.maxReconnectAttempts')">
              <el-input-number
                v-model="settings.websocket.max_reconnect_attempts"
                :min="1"
                :max="10"
              />
              <div class="form-item-tip">
                {{ t('settings.maxReconnectAttemptsTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.reconnectDelay')">
              <el-input-number
                v-model="settings.websocket.reconnect_delay"
                :min="1"
                :max="30"
              />
              <div class="form-item-tip">
                {{ t('settings.reconnectDelayTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.heartbeatInterval')">
              <el-input-number
                v-model="settings.websocket.heartbeat_interval"
                :min="10"
                :max="60"
              />
              <div class="form-item-tip">
                {{ t('settings.heartbeatIntervalTip') }}
              </div>
            </el-form-item>

            <el-divider />

            <el-form-item :label="t('settings.subscribedTopics')">
              <el-checkbox-group v-model="settings.websocket.subscribed_topics">
                <el-checkbox label="monitoring">{{ t('settings.topicMonitoring') }}</el-checkbox>
                <el-checkbox label="strategies">{{ t('settings.topicStrategies') }}</el-checkbox>
                <el-checkbox label="signals">{{ t('settings.topicSignals') }}</el-checkbox>
                <el-checkbox label="capacity">{{ t('settings.topicCapacity') }}</el-checkbox>
                <el-checkbox label="logs">{{ t('settings.topicLogs') }}</el-checkbox>
              </el-checkbox-group>
              <div class="form-item-tip">
                {{ t('settings.subscribedTopicsTip') }}
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 显示设置 -->
        <el-tab-pane :label="t('settings.display')" name="display">
          <el-form :model="settings" label-width="160px">
            <el-form-item :label="t('settings.refreshInterval')">
              <el-input-number
                v-model="settings.display.refresh_interval"
                :min="5"
                :max="300"
              />
              <div class="form-item-tip">
                {{ t('settings.refreshIntervalTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.pageSize')">
              <el-input-number
                v-model="settings.display.page_size"
                :min="10"
                :max="100"
                :step="10"
              />
              <div class="form-item-tip">
                {{ t('settings.pageSizeTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.dateFormat')">
              <el-select v-model="settings.display.date_format">
                <el-option label="YYYY-MM-DD HH:mm:ss" value="YYYY-MM-DD HH:mm:ss" />
                <el-option label="YYYY/MM/DD HH:mm:ss" value="YYYY/MM/DD HH:mm:ss" />
                <el-option label="DD/MM/YYYY HH:mm:ss" value="DD/MM/YYYY HH:mm:ss" />
                <el-option label="MM/DD/YYYY HH:mm:ss" value="MM/DD/YYYY HH:mm:ss" />
              </el-select>
              <div class="form-item-tip">
                {{ t('settings.dateFormatTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.numberFormat')">
              <el-select v-model="settings.display.number_format">
                <el-option label="1,234.56" value="en-US" />
                <el-option label="1.234,56" value="de-DE" />
                <el-option label="1 234,56" value="fr-FR" />
              </el-select>
              <div class="form-item-tip">
                {{ t('settings.numberFormatTip') }}
              </div>
            </el-form-item>

            <el-divider />

            <el-form-item :label="t('settings.showCharts')">
              <el-switch v-model="settings.display.show_charts" />
              <div class="form-item-tip">
                {{ t('settings.showChartsTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.showTrends')">
              <el-switch v-model="settings.display.show_trends" />
              <div class="form-item-tip">
                {{ t('settings.showTrendsTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.enableAnimations')">
              <el-switch v-model="settings.display.enable_animations" />
              <div class="form-item-tip">
                {{ t('settings.enableAnimationsTip') }}
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 账户设置 -->
        <el-tab-pane :label="t('settings.account')" name="account">
          <el-form :model="accountForm" label-width="160px">
            <el-form-item :label="t('settings.username')">
              <el-input v-model="userStore.user.username" disabled />
            </el-form-item>

            <el-form-item :label="t('settings.email')">
              <el-input v-model="userStore.user.email" disabled />
            </el-form-item>

            <el-divider content-position="left">{{ t('settings.changePassword') }}</el-divider>

            <el-form-item :label="t('settings.currentPassword')">
              <el-input
                v-model="accountForm.current_password"
                type="password"
                show-password
                :placeholder="t('settings.enterCurrentPassword')"
              />
            </el-form-item>

            <el-form-item :label="t('settings.newPassword')">
              <el-input
                v-model="accountForm.new_password"
                type="password"
                show-password
                :placeholder="t('settings.enterNewPassword')"
              />
            </el-form-item>

            <el-form-item :label="t('settings.confirmPassword')">
              <el-input
                v-model="accountForm.confirm_password"
                type="password"
                show-password
                :placeholder="t('settings.enterConfirmPassword')"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="changePassword">{{ t('settings.changePassword') }}</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 高级设置 -->
        <el-tab-pane :label="t('settings.advanced')" name="advanced">
          <el-form :model="settings" label-width="160px">
            <el-form-item :label="t('settings.debugMode')">
              <el-switch v-model="settings.advanced.debug_mode" />
              <div class="form-item-tip">
                {{ t('settings.debugModeTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.apiTimeout')">
              <el-input-number
                v-model="settings.advanced.api_timeout"
                :min="10"
                :max="120"
              />
              <div class="form-item-tip">
                {{ t('settings.apiTimeoutTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.cacheStrategy')">
              <el-select v-model="settings.advanced.cache_strategy">
                <el-option :label="t('settings.cacheNone')" value="none" />
                <el-option :label="t('settings.cacheMemory')" value="memory" />
                <el-option :label="t('settings.cacheLocalStorage')" value="localStorage" />
              </el-select>
              <div class="form-item-tip">
                {{ t('settings.cacheStrategyTip') }}
              </div>
            </el-form-item>

            <el-divider />

            <el-form-item :label="t('settings.clearCache')">
              <el-button type="warning" @click="clearCache">{{ t('settings.clearAllCache') }}</el-button>
              <div class="form-item-tip">
                {{ t('settings.clearCacheTip') }}
              </div>
            </el-form-item>

            <el-form-item :label="t('settings.resetSettings')">
              <el-button type="danger" @click="resetSettings">{{ t('settings.restoreDefaults') }}</el-button>
              <div class="form-item-tip">
                {{ t('settings.resetSettingsTip') }}
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 关于 -->
        <el-tab-pane :label="t('settings.about')" name="about">
          <el-descriptions :column="1" border>
            <el-descriptions-item :label="t('settings.version')">
              {{ appVersion }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('settings.environment')">
              {{ appEnvironment }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('settings.apiAddress')">
              {{ apiBaseURL }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('settings.wsAddress')">
              {{ wsBaseURL }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('settings.buildTime')">
              {{ buildTime }}
            </el-descriptions-item>
          </el-descriptions>

          <el-divider />

          <div class="about-section">
            <h3>{{ t('settings.techStack') }}</h3>
            <ul>
              <li>Vue 3 (Composition API)</li>
              <li>Pinia ({{ t('settings.stateManagement') }})</li>
              <li>Element Plus ({{ t('settings.uiFramework') }})</li>
              <li>ECharts ({{ t('settings.dataVisualization') }})</li>
              <li>WebSocket ({{ t('settings.realtimeCommunication') }})</li>
            </ul>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 渠道配置对话框 -->
    <el-dialog
      v-model="showChannelConfigDialog"
      :title="`${t('settings.configureChannel')}${currentChannel?.name || t('settings.channels')}`"
      width="700px"
      destroy-on-close
    >
      <el-form
        v-if="currentChannel"
        ref="channelFormRef"
        :model="channelForm"
        label-width="140px"
      >
        <el-form-item :label="t('settings.channelName')">
          <el-input v-model="channelForm.name" :placeholder="t('settings.customChannelName')" />
        </el-form-item>

        <el-form-item :label="t('settings.notificationLevel')">
          <el-checkbox-group v-model="channelForm.levels">
            <el-checkbox label="P2">{{ t('settings.p2Emergency') }}</el-checkbox>
            <el-checkbox label="P1">{{ t('settings.p1Important') }}</el-checkbox>
            <el-checkbox label="P0">{{ t('settings.p0Normal') }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-divider content-position="left">{{ t('settings.apiConfig') }}</el-divider>

        <!-- SMS配置 -->
        <template v-if="currentChannel.type === 'sms'">
          <el-form-item :label="t('settings.apiKey')">
            <el-input
              v-model="channelForm.config.api_key"
              :placeholder="t('settings.enterApiKey')"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('settings.apiSecret')">
            <el-input
              v-model="channelForm.config.api_secret"
              :placeholder="t('settings.enterApiSecret')"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('settings.signature')">
            <el-input v-model="channelForm.config.sign_name" :placeholder="t('settings.signature')" />
          </el-form-item>
          <el-form-item :label="t('settings.phoneNumbers')">
            <el-select
              v-model="channelForm.config.phone_numbers"
              multiple
              filterable
              allow-create
              :placeholder="t('settings.enterPhoneNumbers')"
              style="width: 100%"
            >
            </el-select>
          </el-form-item>
        </template>

        <!-- 飞书配置 -->
        <template v-if="currentChannel.type === 'feishu'">
          <el-form-item :label="t('settings.webhookUrl')">
            <el-input
              v-model="channelForm.config.webhook_url"
              placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
            />
          </el-form-item>
          <el-form-item :label="t('settings.secretKey')">
            <el-input
              v-model="channelForm.config.secret"
              :placeholder="t('settings.secretKeyOptional')"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('settings.atUsers')">
            <el-select
              v-model="channelForm.config.at_users"
              multiple
              filterable
              allow-create
              :placeholder="t('settings.enterUserId')"
              style="width: 100%"
            >
              <el-option :label="t('settings.atAll')" value="all" />
            </el-select>
          </el-form-item>
        </template>

        <!-- 微信配置 -->
        <template v-if="currentChannel.type === 'wechat'">
          <el-form-item :label="t('settings.corpId')">
            <el-input v-model="channelForm.config.corp_id" :placeholder="t('settings.corpId')" />
          </el-form-item>
          <el-form-item :label="t('settings.agentId')">
            <el-input v-model="channelForm.config.agent_id" :placeholder="t('settings.agentId')" />
          </el-form-item>
          <el-form-item :label="t('settings.appSecret')">
            <el-input
              v-model="channelForm.config.secret"
              :placeholder="t('settings.appSecret')"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('settings.toUser')">
            <el-input
              v-model="channelForm.config.to_user"
              :placeholder="t('settings.toUserTip')"
            />
          </el-form-item>
        </template>

        <!-- Email配置 -->
        <template v-if="currentChannel.type === 'email'">
          <el-form-item :label="t('settings.smtpServer')">
            <el-input v-model="channelForm.config.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item :label="t('settings.smtpPort')">
            <el-input-number
              v-model="channelForm.config.smtp_port"
              :min="1"
              :max="65535"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item :label="t('settings.fromEmail')">
            <el-input v-model="channelForm.config.from_email" placeholder="noreply@example.com" />
          </el-form-item>
          <el-form-item :label="t('settings.emailPassword')">
            <el-input
              v-model="channelForm.config.password"
              :placeholder="t('settings.smtpPasswordTip')"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('settings.toEmails')">
            <el-select
              v-model="channelForm.config.to_emails"
              multiple
              filterable
              allow-create
              :placeholder="t('settings.enterEmail')"
              style="width: 100%"
            >
            </el-select>
          </el-form-item>
          <el-form-item :label="t('settings.useTls')">
            <el-switch v-model="channelForm.config.use_tls" />
          </el-form-item>
        </template>

        <!-- Telegram配置 -->
        <template v-if="currentChannel.type === 'telegram'">
          <el-form-item :label="t('settings.botToken')">
            <el-input
              v-model="channelForm.config.bot_token"
              :placeholder="t('settings.botTokenTip')"
              type="password"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('settings.chatId')">
            <el-select
              v-model="channelForm.config.chat_ids"
              multiple
              filterable
              allow-create
              :placeholder="t('settings.chatIdTip')"
              style="width: 100%"
            >
            </el-select>
          </el-form-item>
          <el-form-item :label="t('settings.messageFormat')">
            <el-select v-model="channelForm.config.parse_mode" style="width: 100%">
              <el-option :label="t('settings.plainText')" value="" />
              <el-option label="Markdown" value="Markdown" />
              <el-option label="HTML" value="HTML" />
            </el-select>
          </el-form-item>
        </template>

        <el-divider content-position="left">{{ t('settings.messageTemplates') }}</el-divider>

        <el-form-item :label="t('settings.p2Template')">
          <el-input
            v-model="channelForm.templates.p2"
            type="textarea"
            :rows="3"
            placeholder="🚨 [紧急] {strategy_name}: {signal_type} 信号&#10;价格: {price}&#10;强度: {strength}"
          />
        </el-form-item>

        <el-form-item :label="t('settings.p1Template')">
          <el-input
            v-model="channelForm.templates.p1"
            type="textarea"
            :rows="3"
            placeholder="⚠️ [重要] {strategy_name}: {signal_type} 信号&#10;价格: {price}&#10;强度: {strength}"
          />
        </el-form-item>

        <el-form-item :label="t('settings.p0Template')">
          <el-input
            v-model="channelForm.templates.p0"
            type="textarea"
            :rows="3"
            placeholder="ℹ️ {strategy_name}: {signal_type} 信号&#10;价格: {price}"
          />
        </el-form-item>

        <el-form-item>
          <div class="form-item-tip">
            {{ t('settings.availableVariables') }}: {strategy_name}, {signal_type}, {price}, {strength}, {pair}, {exchange}
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showChannelConfigDialog = false">{{ t('settings.cancel') }}</el-button>
        <el-button type="primary" @click="saveChannelConfig">
          {{ t('settings.saveConfig') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useWebSocketStore } from '@/stores/websocket'
import { notificationAPI, settingsAPI } from '@/api'

const { t } = useI18n()

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
    sms: t('settings.smsChannel'),
    feishu: t('settings.feishuChannel'),
    wechat: t('settings.wechatChannel'),
    email: t('settings.emailChannel'),
    telegram: t('settings.telegramChannel')
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
    return t('settings.justNow')
  } else if (diff < 3600) {
    return `${Math.floor(diff / 60)}${t('settings.minutesAgo')}`
  } else if (diff < 86400) {
    return `${Math.floor(diff / 3600)}${t('settings.hoursAgo')}`
  } else {
    return `${Math.floor(diff / 86400)}${t('settings.daysAgo')}`
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

  ElMessage.success(t('settings.priorityAdjusted'))

  // TODO: 调用API保存优先级
  // await notificationAPI.updateChannelPriority(channel.id, targetChannel.id)
}

// 切换渠道启用状态
const handleToggleChannel = (channel) => {
  if (!channel.configured && channel.enabled) {
    ElMessage.warning(t('settings.pleaseConfigureFirst'))
    channel.enabled = false
    return
  }

  ElMessage.success(channel.enabled ? t('settings.channelEnabled') : t('settings.channelDisabled'))

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
    ElMessage.warning(t('settings.pleaseConfigureFirst'))
    return
  }

  if (!channel.enabled) {
    ElMessage.warning(t('settings.pleaseEnableFirst'))
    return
  }

  testingChannelId.value = channel.id
  try {
    // TODO: 调用API测试渠道
    // const res = await notificationAPI.test(channel.type)

    // 模拟测试
    await new Promise(resolve => setTimeout(resolve, 1500))

    channel.last_test_time = new Date().toISOString()
    ElMessage.success(t('settings.testMessageSent'))
  } catch (error) {
    console.error('Failed to test channel:', error)
    ElMessage.error(t('settings.testFailed'))
  } finally {
    testingChannelId.value = null
  }
}

// 保存渠道配置
const saveChannelConfig = () => {
  if (!channelForm.levels || channelForm.levels.length === 0) {
    ElMessage.warning(t('settings.selectNotificationLevel'))
    return
  }

  // 基本验证
  let isValid = true
  const config = channelForm.config

  switch (currentChannel.value.type) {
    case 'sms':
      if (!config.api_key || !config.api_secret || config.phone_numbers.length === 0) {
        ElMessage.warning(t('settings.fillSmsConfig'))
        isValid = false
      }
      break
    case 'feishu':
      if (!config.webhook_url) {
        ElMessage.warning(t('settings.fillFeishuWebhook'))
        isValid = false
      }
      break
    case 'wechat':
      if (!config.corp_id || !config.agent_id || !config.secret) {
        ElMessage.warning(t('settings.fillWechatConfig'))
        isValid = false
      }
      break
    case 'email':
      if (!config.smtp_host || !config.from_email || !config.password || config.to_emails.length === 0) {
        ElMessage.warning(t('settings.fillEmailConfig'))
        isValid = false
      }
      break
    case 'telegram':
      if (!config.bot_token || config.chat_ids.length === 0) {
        ElMessage.warning(t('settings.fillTelegramConfig'))
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

    ElMessage.success(t('settings.channelConfigSaved'))
    showChannelConfigDialog.value = false

    // TODO: 调用API保存配置
    // await notificationAPI.updateChannel(currentChannel.value.id, channelConfig)
  } catch (error) {
    console.error('Failed to save channel config:', error)
    ElMessage.error(t('settings.saveConfigFailed'))
  }
}

// 保存频率限制
const saveFrequencyLimits = () => {
  try {
    localStorage.setItem('notification_frequency_limits', JSON.stringify(frequencyLimits))
    ElMessage.success(t('settings.frequencyLimitSaved'))

    // TODO: 调用API保存配置
    // await notificationAPI.updateFrequencyLimits(frequencyLimits)
  } catch (error) {
    console.error('Failed to save frequency limits:', error)
    ElMessage.error(t('settings.saveFailed'))
  }
}

// 保存时间规则
const saveTimeRules = () => {
  if (timeRules.do_not_disturb_enabled) {
    if (!timeRules.do_not_disturb_start || !timeRules.do_not_disturb_end) {
      ElMessage.warning(t('settings.setDoNotDisturbPeriod'))
      return
    }
  }

  try {
    localStorage.setItem('notification_time_rules', JSON.stringify(timeRules))
    ElMessage.success(t('settings.timeRulesSaved'))

    // TODO: 调用API保存配置
    // await notificationAPI.updateTimeRules(timeRules)
  } catch (error) {
    console.error('Failed to save time rules:', error)
    ElMessage.error(t('settings.saveFailed'))
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
    granted: t('settings.permissionGranted'),
    denied: t('settings.permissionDenied'),
    default: t('settings.permissionDefault')
  }
  return textMap[notificationPermission.value] || t('settings.permissionDefault')
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

    ElMessage.success(t('settings.settingsSaved'))
  } catch (error) {
    console.error('Failed to save settings:', error)
    ElMessage.error(t('settings.saveFailed'))
  }
}

// 重置设置
const resetSettings = async () => {
  ElMessageBox.confirm(
    t('settings.confirmReset'),
    t('settings.confirmResetTitle'),
    {
      confirmButtonText: t('settings.confirm'),
      cancelButtonText: t('settings.cancel'),
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

      ElMessage.success(t('settings.defaultSettingsRestored'))
    } catch (error) {
      console.error('Failed to reset settings:', error)
      ElMessage.error(t('settings.resetFailed'))
    }
  }).catch(() => {
    // 用户取消
  })
}

// 清除缓存
const clearCache = () => {
  ElMessageBox.confirm(
    t('settings.confirmClearCache'),
    t('settings.confirmClearTitle'),
    {
      confirmButtonText: t('settings.confirm'),
      cancelButtonText: t('settings.cancel'),
      type: 'warning'
    }
  ).then(() => {
    localStorage.clear()
    sessionStorage.clear()
    ElMessage.success(t('settings.cacheCleared'))
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
        ElMessage.success(t('settings.notificationPermissionGranted'))
      } else if (permission === 'denied') {
        ElMessage.warning(t('settings.notificationPermissionDenied'))
      }
    } catch (error) {
      console.error('Failed to request notification permission:', error)
      ElMessage.error(t('settings.requestPermissionFailed'))
    }
  } else {
    ElMessage.warning(t('settings.browserNotSupported'))
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
      ElMessage.success(t('settings.reconnectingWs'))
    }, 500)
  } else {
    ElMessage.error(t('settings.notLoggedIn'))
  }
}

// 修改密码
const changePassword = async () => {
  if (!accountForm.current_password || !accountForm.new_password) {
    ElMessage.warning(t('settings.fillPasswordInfo'))
    return
  }

  if (accountForm.new_password !== accountForm.confirm_password) {
    ElMessage.error(t('settings.passwordMismatch'))
    return
  }

  if (accountForm.new_password.length < 6) {
    ElMessage.error(t('settings.passwordTooShort'))
    return
  }

  try {
    // TODO: 调用修改密码API
    // await authAPI.changePassword(accountForm.current_password, accountForm.new_password)
    ElMessage.success(t('settings.passwordChanged'))

    // 清空表单
    accountForm.current_password = ''
    accountForm.new_password = ''
    accountForm.confirm_password = ''

    // TODO: 登出并跳转到登录页
    // await userStore.logout()
    // router.push('/login')
  } catch (error) {
    console.error('Failed to change password:', error)
    ElMessage.error(t('settings.changePasswordFailed') + ': ' + (error.message || ''))
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
