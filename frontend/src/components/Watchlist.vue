<template>
  <div class="watchlist">
    <div class="watchlist-header">
      <h3>📋 Watchlist</h3>
      <button @click="showAddDialog = true" class="btn-add" title="Add to watchlist">
        <span>➕</span>
      </button>
    </div>

    <!-- Add Stock Dialog -->
    <div v-if="showAddDialog" class="dialog-overlay" @click="showAddDialog = false">
      <div class="dialog" @click.stop>
        <h4>Add to Watchlist</h4>
        <StockSearch @select="addToWatchlist" />
        <button @click="showAddDialog = false" class="btn-close">Cancel</button>
      </div>
    </div>

    <!-- Watchlist Items -->
    <div v-if="watchlistStocks.length === 0" class="empty-state">
      <p>📭 No stocks in watchlist</p>
      <small>Click + to add stocks</small>
    </div>

    <div v-else class="watchlist-items">
      <div
        v-for="stock in watchlistStocks"
        :key="stock.symbol"
        :class="['watchlist-item', { active: stock.symbol === currentSymbol }]"
        @click="selectStock(stock.symbol)"
      >
        <div class="item-header">
          <div class="item-symbol">
            <span class="symbol-text">{{ stock.symbol.replace('.NS', '').replace('.BO', '') }}</span>
            <span class="exchange-mini">{{ stock.exchange }}</span>
          </div>
          <button @click.stop="removeFromWatchlist(stock.symbol)" class="btn-remove">✕</button>
        </div>
        
        <div class="item-name">{{ stock.name }}</div>
        
        <div v-if="stock.price" class="item-price">
          <span class="price">₹{{ stock.price.toFixed(2) }}</span>
          <span :class="['change', stock.change >= 0 ? 'positive' : 'negative']">
            {{ stock.change >= 0 ? '+' : '' }}{{ stock.changePercent?.toFixed(2) }}%
          </span>
        </div>
        
        <div v-else class="item-price">
          <span class="price-loading">Loading...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import StockSearch from './StockSearch.vue'

const props = defineProps({
  currentSymbol: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select'])

const showAddDialog = ref(false)
const watchlistStocks = ref([])

// Load watchlist from localStorage
const loadWatchlist = () => {
  const saved = localStorage.getItem('watchlist')
  if (saved) {
    try {
      watchlistStocks.value = JSON.parse(saved)
    } catch (e) {
      console.error('Failed to load watchlist:', e)
      watchlistStocks.value = []
    }
  } else {
    // Default watchlist
    watchlistStocks.value = [
      { symbol: 'TCS.NS', name: 'Tata Consultancy Services', exchange: 'NSE' },
      { symbol: 'RELIANCE.NS', name: 'Reliance Industries', exchange: 'NSE' },
      { symbol: 'HDFCBANK.NS', name: 'HDFC Bank', exchange: 'NSE' },
    ]
    saveWatchlist()
  }
}

// Save watchlist to localStorage
const saveWatchlist = () => {
  localStorage.setItem('watchlist', JSON.stringify(watchlistStocks.value))
}

// Add stock to watchlist
const addToWatchlist = (symbol) => {
  // Check if already exists
  const exists = watchlistStocks.value.some(s => s.symbol === symbol)
  if (exists) {
    alert('Stock already in watchlist')
    return
  }

  // Extract info
  const exchange = symbol.includes('.NS') ? 'NSE' : symbol.includes('.BO') ? 'BSE' : 'Unknown'
  const cleanSymbol = symbol.replace('.NS', '').replace('.BO', '')
  
  watchlistStocks.value.push({
    symbol: symbol,
    name: cleanSymbol,
    exchange: exchange,
    price: null,
    change: 0,
    changePercent: 0
  })
  
  saveWatchlist()
  showAddDialog.value = false
}

// Remove stock from watchlist
const removeFromWatchlist = (symbol) => {
  if (confirm('Remove from watchlist?')) {
    watchlistStocks.value = watchlistStocks.value.filter(s => s.symbol !== symbol)
    saveWatchlist()
  }
}

// Select stock
const selectStock = (symbol) => {
  emit('select', symbol)
}

// Update prices (can be called from parent with live data)
const updatePrices = (priceData) => {
  const stock = watchlistStocks.value.find(s => s.symbol === priceData.symbol)
  if (stock) {
    stock.price = priceData.price
    stock.change = priceData.change
    stock.changePercent = priceData.changePercent
    // Save updated prices to localStorage
    saveWatchlist()
  }
}

onMounted(() => {
  loadWatchlist()
})

defineExpose({
  updatePrices
})
</script>

<style scoped>
.watchlist {
  background: #18181b;
  border-radius: 8px;
  border: 1px solid #2b2b2e;
  overflow: hidden;
}

.watchlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2b2b2e;
  background: #1a1a1d;
}

.watchlist-header h3 {
  margin: 0;
  font-size: 16px;
  color: #efeff1;
  font-weight: 600;
}

.btn-add {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #2962FF;
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-add:hover {
  background: #1e4fd9;
  transform: scale(1.1);
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(4px);
}

.dialog {
  background: #18181b;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 500px;
  border: 1px solid #2b2b2e;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.dialog h4 {
  margin: 0 0 16px 0;
  color: #efeff1;
  font-size: 18px;
}

.btn-close {
  margin-top: 16px;
  width: 100%;
  padding: 10px;
  background: #2b2b2e;
  border: none;
  border-radius: 6px;
  color: #efeff1;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.btn-close:hover {
  background: #3a3a3e;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #999;
}

.empty-state p {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.empty-state small {
  font-size: 13px;
  color: #666;
}

.watchlist-items {
  max-height: 400px;
  overflow-y: auto;
}

.watchlist-items::-webkit-scrollbar {
  width: 6px;
}

.watchlist-items::-webkit-scrollbar-track {
  background: #18181b;
}

.watchlist-items::-webkit-scrollbar-thumb {
  background: #2b2b2e;
  border-radius: 3px;
}

.watchlist-item {
  padding: 12px 16px;
  border-bottom: 1px solid #2b2b2e;
  cursor: pointer;
  transition: background 0.2s;
}

.watchlist-item:hover {
  background: #1a1a1d;
}

.watchlist-item.active {
  background: #2962FF;
  background: linear-gradient(90deg, rgba(41, 98, 255, 0.2), rgba(41, 98, 255, 0.05));
  border-left: 3px solid #2962FF;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.item-symbol {
  display: flex;
  align-items: center;
  gap: 8px;
}

.symbol-text {
  font-size: 15px;
  font-weight: 700;
  color: #efeff1;
  font-family: 'SF Mono', 'Monaco', monospace;
}

.exchange-mini {
  font-size: 10px;
  padding: 2px 6px;
  background: #2b2b2e;
  color: #999;
  border-radius: 3px;
  font-weight: 600;
}

.btn-remove {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: #666;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-remove:hover {
  background: #ef5350;
  color: white;
}

.item-name {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-price {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.price {
  font-size: 14px;
  font-weight: 600;
  color: #efeff1;
  font-family: 'SF Mono', 'Monaco', monospace;
}

.change {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
}

.change.positive {
  background: rgba(38, 166, 154, 0.2);
  color: #26a69a;
}

.change.negative {
  background: rgba(239, 83, 80, 0.2);
  color: #ef5350;
}

.price-loading {
  font-size: 12px;
  color: #666;
}
</style>

