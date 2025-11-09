<template>
  <div class="notification-center">
    <!-- Notification Button -->
    <button 
      class="notification-button" 
      @click="toggleNotifications"
      :class="{ 'has-notifications': unreadCount > 0 }"
    >
      <span class="notification-icon">🔔</span>
      <span v-if="unreadCount > 0" class="notification-badge">{{ unreadCount }}</span>
    </button>

    <!-- Notification Panel -->
    <div v-if="isOpen" class="notification-panel">
      <div class="notification-header">
        <h3>Notifications</h3>
        <div class="notification-actions">
          <button @click="markAllRead" class="btn-mark-read">Mark all read</button>
          <button @click="clearAll" class="btn-clear">Clear all</button>
          <button @click="toggleNotifications" class="btn-close">✕</button>
        </div>
      </div>

      <div class="notification-list">
        <div 
          v-for="notification in notifications" 
          :key="notification.id"
          class="notification-item"
          :class="{
            'notification-error': notification.type === 'error',
            'notification-warning': notification.type === 'warning',
            'notification-success': notification.type === 'success',
            'notification-info': notification.type === 'info',
            'unread': !notification.read
          }"
          @click="markAsRead(notification.id)"
        >
          <div class="notification-content">
            <div class="notification-title">
              <span class="notification-type-icon">
                <span v-if="notification.type === 'error'">❌</span>
                <span v-else-if="notification.type === 'warning'">⚠️</span>
                <span v-else-if="notification.type === 'success'">✅</span>
                <span v-else>ℹ️</span>
              </span>
              <span class="notification-time">{{ formatTime(notification.timestamp) }}</span>
            </div>
            <div class="notification-message">{{ notification.message }}</div>
            <div v-if="notification.details" class="notification-details">
              <details>
                <summary>Details</summary>
                <pre>{{ formatDetails(notification.details) }}</pre>
              </details>
            </div>
            <div v-if="notification.apiCall" class="notification-api">
              <small>{{ notification.apiCall }}</small>
            </div>
          </div>
          <button 
            @click.stop="removeNotification(notification.id)" 
            class="notification-remove"
          >
            ✕
          </button>
        </div>
        <div v-if="notifications.length === 0" class="notification-empty">
          No notifications
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const isOpen = ref(false)
const notifications = ref([])

const unreadCount = computed(() => {
  return notifications.value.filter(n => !n.read).length
})

const toggleNotifications = () => {
  isOpen.value = !isOpen.value
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const formatDetails = (details) => {
  if (typeof details === 'string') return details
  return JSON.stringify(details, null, 2)
}

const markAsRead = (id) => {
  const notification = notifications.value.find(n => n.id === id)
  if (notification) {
    notification.read = true
  }
}

const markAllRead = () => {
  notifications.value.forEach(n => n.read = true)
}

const removeNotification = (id) => {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    notifications.value.splice(index, 1)
  }
}

const clearAll = () => {
  notifications.value = []
}

// Public methods for adding notifications
const addNotification = (type, message, details = null, apiCall = null) => {
  const notification = {
    id: Date.now() + Math.random(),
    type,
    message,
    details,
    apiCall,
    timestamp: new Date(),
    read: false
  }
  notifications.value.unshift(notification)
  
  // Keep only last 100 notifications
  if (notifications.value.length > 100) {
    notifications.value = notifications.value.slice(0, 100)
  }
  
  return notification.id
}

const addError = (message, details = null, apiCall = null) => {
  return addNotification('error', message, details, apiCall)
}

const addWarning = (message, details = null, apiCall = null) => {
  return addNotification('warning', message, details, apiCall)
}

const addSuccess = (message, details = null, apiCall = null) => {
  return addNotification('success', message, details, apiCall)
}

const addInfo = (message, details = null, apiCall = null) => {
  return addNotification('info', message, details, apiCall)
}

// Expose methods for use in other components
defineExpose({
  addNotification,
  addError,
  addWarning,
  addSuccess,
  addInfo,
  notifications
})

// Make notification methods available globally
onMounted(() => {
  window.notificationCenter = {
    addError,
    addWarning,
    addSuccess,
    addInfo,
    addNotification
  }
})
</script>

<style scoped>
.notification-center {
  position: relative;
}

.notification-button {
  position: relative;
  background: #4a5568;
  border: none;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 18px;
  transition: background 0.2s;
}

.notification-button:hover {
  background: #5a6578;
}

.notification-button.has-notifications {
  background: #e53e3e;
  animation: pulse 2s infinite;
}

.notification-button.has-notifications:hover {
  background: #c53030;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.notification-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: #fff;
  color: #e53e3e;
  border-radius: 10px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: bold;
  min-width: 18px;
  text-align: center;
}

.notification-panel {
  position: absolute;
  top: 50px;
  right: 0;
  width: 400px;
  max-height: 600px;
  background: #1a202c;
  border: 1px solid #2d3748;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.notification-header {
  padding: 12px 16px;
  border-bottom: 1px solid #2d3748;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notification-header h3 {
  margin: 0;
  font-size: 16px;
  color: #e2e8f0;
}

.notification-actions {
  display: flex;
  gap: 8px;
}

.notification-actions button {
  background: transparent;
  border: 1px solid #4a5568;
  color: #a0aec0;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.notification-actions button:hover {
  background: #2d3748;
  color: #e2e8f0;
}

.notification-list {
  overflow-y: auto;
  max-height: 500px;
}

.notification-item {
  padding: 12px 16px;
  border-bottom: 1px solid #2d3748;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.notification-item:hover {
  background: #2d3748;
}

.notification-item.unread {
  background: #2d3748;
  border-left: 3px solid;
}

.notification-item.notification-error.unread {
  border-left-color: #e53e3e;
}

.notification-item.notification-warning.unread {
  border-left-color: #dd6b20;
}

.notification-item.notification-success.unread {
  border-left-color: #38a169;
}

.notification-item.notification-info.unread {
  border-left-color: #3182ce;
}

.notification-content {
  flex: 1;
}

.notification-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.notification-type-icon {
  font-size: 16px;
  margin-right: 8px;
}

.notification-time {
  font-size: 11px;
  color: #718096;
}

.notification-message {
  color: #e2e8f0;
  font-size: 14px;
  margin-bottom: 4px;
}

.notification-details {
  margin-top: 8px;
}

.notification-details details {
  cursor: pointer;
}

.notification-details summary {
  color: #a0aec0;
  font-size: 12px;
  margin-bottom: 4px;
}

.notification-details pre {
  background: #2d3748;
  padding: 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #cbd5e0;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
}

.notification-api {
  margin-top: 4px;
}

.notification-api small {
  color: #718096;
  font-size: 11px;
  font-family: monospace;
}

.notification-remove {
  background: transparent;
  border: none;
  color: #718096;
  cursor: pointer;
  padding: 4px;
  margin-left: 8px;
  opacity: 0.5;
}

.notification-remove:hover {
  opacity: 1;
  color: #e53e3e;
}

.notification-empty {
  padding: 40px;
  text-align: center;
  color: #718096;
}

/* Scrollbar styling */
.notification-list::-webkit-scrollbar {
  width: 6px;
}

.notification-list::-webkit-scrollbar-track {
  background: #1a202c;
}

.notification-list::-webkit-scrollbar-thumb {
  background: #4a5568;
  border-radius: 3px;
}

.notification-list::-webkit-scrollbar-thumb:hover {
  background: #5a6578;
}
</style>

