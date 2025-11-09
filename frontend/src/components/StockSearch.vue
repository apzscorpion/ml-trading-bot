<template>
  <div class="stock-search">
    <div class="search-container">
      <div class="search-input-wrapper">
        <span class="search-icon">🔍</span>
        <input
          ref="searchInput"
          v-model="searchQuery"
          @input="handleSearch"
          @focus="showDropdown = true"
          @blur="handleBlur"
          @keydown.down.prevent="navigateDown"
          @keydown.up.prevent="navigateUp"
          @keydown.enter.prevent="selectHighlighted"
          @keydown.esc="showDropdown = false"
          type="text"
          placeholder="Search stocks (e.g., TCS, Reliance, HDFC...)"
          class="search-input"
        />
        <button v-if="searchQuery" @click="clearSearch" class="clear-btn">✕</button>
      </div>
      
      <div v-if="showDropdown && filteredStocks.length > 0" class="dropdown">
        <div class="dropdown-header">
          <span>{{ filteredStocks.length }} results</span>
        </div>
        <div class="dropdown-list">
          <div
            v-for="(stock, index) in filteredStocks.slice(0, 50)"
            :key="stock.symbol"
            :class="['stock-item', { highlighted: index === highlightedIndex }]"
            @mousedown.prevent="selectStock(stock)"
            @mouseenter="highlightedIndex = index"
          >
            <div class="stock-main">
              <span class="stock-symbol">{{ stock.symbol }}</span>
              <span class="stock-exchange">{{ stock.exchange }}</span>
            </div>
            <div class="stock-name">{{ stock.name }}</div>
          </div>
        </div>
      </div>

      <div v-if="showDropdown && searchQuery && filteredStocks.length === 0" class="dropdown no-results">
        <div class="no-results-content">
          <span>📭</span>
          <p>No stocks found</p>
          <small>Try searching by name or symbol</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const emit = defineEmits(['select'])

const searchInput = ref(null)
const searchQuery = ref('')
const showDropdown = ref(false)
const highlightedIndex = ref(0)
const stocks = ref([])

// Comprehensive Indian stock list
const indianStocks = [
  // NSE Top 50
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries Ltd', exchange: 'NSE' },
  { symbol: 'TCS.NS', name: 'Tata Consultancy Services Ltd', exchange: 'NSE' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank Ltd', exchange: 'NSE' },
  { symbol: 'INFY.NS', name: 'Infosys Ltd', exchange: 'NSE' },
  { symbol: 'ICICIBANK.NS', name: 'ICICI Bank Ltd', exchange: 'NSE' },
  { symbol: 'HINDUNILVR.NS', name: 'Hindustan Unilever Ltd', exchange: 'NSE' },
  { symbol: 'ITC.NS', name: 'ITC Ltd', exchange: 'NSE' },
  { symbol: 'SBIN.NS', name: 'State Bank of India', exchange: 'NSE' },
  { symbol: 'BHARTIARTL.NS', name: 'Bharti Airtel Ltd', exchange: 'NSE' },
  { symbol: 'KOTAKBANK.NS', name: 'Kotak Mahindra Bank Ltd', exchange: 'NSE' },
  { symbol: 'LT.NS', name: 'Larsen & Toubro Ltd', exchange: 'NSE' },
  { symbol: 'AXISBANK.NS', name: 'Axis Bank Ltd', exchange: 'NSE' },
  { symbol: 'ASIANPAINT.NS', name: 'Asian Paints Ltd', exchange: 'NSE' },
  { symbol: 'MARUTI.NS', name: 'Maruti Suzuki India Ltd', exchange: 'NSE' },
  { symbol: 'HCLTECH.NS', name: 'HCL Technologies Ltd', exchange: 'NSE' },
  { symbol: 'SUNPHARMA.NS', name: 'Sun Pharmaceutical Industries Ltd', exchange: 'NSE' },
  { symbol: 'TITAN.NS', name: 'Titan Company Ltd', exchange: 'NSE' },
  { symbol: 'BAJFINANCE.NS', name: 'Bajaj Finance Ltd', exchange: 'NSE' },
  { symbol: 'ULTRACEMCO.NS', name: 'UltraTech Cement Ltd', exchange: 'NSE' },
  { symbol: 'WIPRO.NS', name: 'Wipro Ltd', exchange: 'NSE' },
  { symbol: 'NESTLEIND.NS', name: 'Nestle India Ltd', exchange: 'NSE' },
  { symbol: 'ONGC.NS', name: 'Oil & Natural Gas Corporation Ltd', exchange: 'NSE' },
  { symbol: 'TATAMOTORS.NS', name: 'Tata Motors Ltd', exchange: 'NSE' },
  { symbol: 'TATASTEEL.NS', name: 'Tata Steel Ltd', exchange: 'NSE' },
  { symbol: 'NTPC.NS', name: 'NTPC Ltd', exchange: 'NSE' },
  { symbol: 'POWERGRID.NS', name: 'Power Grid Corporation of India Ltd', exchange: 'NSE' },
  { symbol: 'M&M.NS', name: 'Mahindra & Mahindra Ltd', exchange: 'NSE' },
  { symbol: 'TECHM.NS', name: 'Tech Mahindra Ltd', exchange: 'NSE' },
  { symbol: 'ADANIENT.NS', name: 'Adani Enterprises Ltd', exchange: 'NSE' },
  { symbol: 'ADANIPORTS.NS', name: 'Adani Ports and Special Economic Zone Ltd', exchange: 'NSE' },
  { symbol: 'BAJAJFINSV.NS', name: 'Bajaj Finserv Ltd', exchange: 'NSE' },
  { symbol: 'COALINDIA.NS', name: 'Coal India Ltd', exchange: 'NSE' },
  { symbol: 'DIVISLAB.NS', name: 'Divi\'s Laboratories Ltd', exchange: 'NSE' },
  { symbol: 'DRREDDY.NS', name: 'Dr. Reddy\'s Laboratories Ltd', exchange: 'NSE' },
  { symbol: 'EICHERMOT.NS', name: 'Eicher Motors Ltd', exchange: 'NSE' },
  { symbol: 'GRASIM.NS', name: 'Grasim Industries Ltd', exchange: 'NSE' },
  { symbol: 'HDFCLIFE.NS', name: 'HDFC Life Insurance Company Ltd', exchange: 'NSE' },
  { symbol: 'HEROMOTOCO.NS', name: 'Hero MotoCorp Ltd', exchange: 'NSE' },
  { symbol: 'HINDALCO.NS', name: 'Hindalco Industries Ltd', exchange: 'NSE' },
  { symbol: 'INDUSINDBK.NS', name: 'IndusInd Bank Ltd', exchange: 'NSE' },
  { symbol: 'JSWSTEEL.NS', name: 'JSW Steel Ltd', exchange: 'NSE' },
  { symbol: 'SBILIFE.NS', name: 'SBI Life Insurance Company Ltd', exchange: 'NSE' },
  { symbol: 'SHREECEM.NS', name: 'Shree Cement Ltd', exchange: 'NSE' },
  { symbol: 'TATACONSUM.NS', name: 'Tata Consumer Products Ltd', exchange: 'NSE' },
  { symbol: 'CIPLA.NS', name: 'Cipla Ltd', exchange: 'NSE' },
  { symbol: 'BRITANNIA.NS', name: 'Britannia Industries Ltd', exchange: 'NSE' },
  { symbol: 'APOLLOHOSP.NS', name: 'Apollo Hospitals Enterprise Ltd', exchange: 'NSE' },
  { symbol: 'BPCL.NS', name: 'Bharat Petroleum Corporation Ltd', exchange: 'NSE' },
  { symbol: 'BAJAJ-AUTO.NS', name: 'Bajaj Auto Ltd', exchange: 'NSE' },
  
  // BSE Popular Stocks
  { symbol: 'RELIANCE.BO', name: 'Reliance Industries Ltd', exchange: 'BSE' },
  { symbol: 'TCS.BO', name: 'Tata Consultancy Services Ltd', exchange: 'BSE' },
  { symbol: 'HDFCBANK.BO', name: 'HDFC Bank Ltd', exchange: 'BSE' },
  { symbol: 'INFY.BO', name: 'Infosys Ltd', exchange: 'BSE' },
  { symbol: 'ICICIBANK.BO', name: 'ICICI Bank Ltd', exchange: 'BSE' },
  
  // Banking Sector
  { symbol: 'BANKBARODA.NS', name: 'Bank of Baroda', exchange: 'NSE' },
  { symbol: 'PNB.NS', name: 'Punjab National Bank', exchange: 'NSE' },
  { symbol: 'FEDERALBNK.NS', name: 'Federal Bank Ltd', exchange: 'NSE' },
  { symbol: 'IDFCFIRSTB.NS', name: 'IDFC First Bank Ltd', exchange: 'NSE' },
  
  // IT Sector
  { symbol: 'MPHASIS.NS', name: 'Mphasis Ltd', exchange: 'NSE' },
  { symbol: 'COFORGE.NS', name: 'Coforge Ltd', exchange: 'NSE' },
  { symbol: 'PERSISTENT.NS', name: 'Persistent Systems Ltd', exchange: 'NSE' },
  { symbol: 'LTI.NS', name: 'Larsen & Toubro Infotech Ltd', exchange: 'NSE' },
  
  // Pharma Sector
  { symbol: 'BIOCON.NS', name: 'Biocon Ltd', exchange: 'NSE' },
  { symbol: 'LUPIN.NS', name: 'Lupin Ltd', exchange: 'NSE' },
  { symbol: 'TORNTPHARM.NS', name: 'Torrent Pharmaceuticals Ltd', exchange: 'NSE' },
  { symbol: 'AUROPHARMA.NS', name: 'Aurobindo Pharma Ltd', exchange: 'NSE' },
  
  // Auto Sector
  { symbol: 'TVSMOTOR.NS', name: 'TVS Motor Company Ltd', exchange: 'NSE' },
  { symbol: 'ASHOKLEY.NS', name: 'Ashok Leyland Ltd', exchange: 'NSE' },
  { symbol: 'MOTHERSON.NS', name: 'Samvardhana Motherson International Ltd', exchange: 'NSE' },
  
  // Telecom
  { symbol: 'IDEA.NS', name: 'Vodafone Idea Ltd', exchange: 'NSE' },
  
  // Retail
  { symbol: 'DMART.NS', name: 'Avenue Supermarts Ltd', exchange: 'NSE' },
  { symbol: 'TRENT.NS', name: 'Trent Ltd', exchange: 'NSE' },
  
  // Energy
  { symbol: 'ADANIGREEN.NS', name: 'Adani Green Energy Ltd', exchange: 'NSE' },
  { symbol: 'TATAPOWER.NS', name: 'Tata Power Company Ltd', exchange: 'NSE' },
  { symbol: 'IOC.NS', name: 'Indian Oil Corporation Ltd', exchange: 'NSE' },
  
  // Infrastructure
  { symbol: 'NHAI.NS', name: 'National Highways Authority of India', exchange: 'NSE' },
]

const filteredStocks = computed(() => {
  if (!searchQuery.value.trim()) return []
  
  const query = searchQuery.value.toLowerCase().trim()
  
  return stocks.value.filter(stock => {
    const symbolMatch = stock.symbol.toLowerCase().includes(query)
    const nameMatch = stock.name.toLowerCase().includes(query)
    const exchangeMatch = stock.exchange.toLowerCase().includes(query)
    
    return symbolMatch || nameMatch || exchangeMatch
  }).sort((a, b) => {
    // Prioritize symbol matches over name matches
    const aSymbolMatch = a.symbol.toLowerCase().startsWith(query)
    const bSymbolMatch = b.symbol.toLowerCase().startsWith(query)
    
    if (aSymbolMatch && !bSymbolMatch) return -1
    if (!aSymbolMatch && bSymbolMatch) return 1
    
    return a.symbol.localeCompare(b.symbol)
  })
})

const handleSearch = () => {
  showDropdown.value = true
  highlightedIndex.value = 0
}

const handleBlur = () => {
  setTimeout(() => {
    showDropdown.value = false
  }, 200)
}

const clearSearch = () => {
  searchQuery.value = ''
  showDropdown.value = false
  searchInput.value?.focus()
}

const selectStock = (stock) => {
  emit('select', stock.symbol)
  searchQuery.value = `${stock.symbol.replace('.NS', '').replace('.BO', '')} - ${stock.name}`
  showDropdown.value = false
}

const navigateDown = () => {
  if (highlightedIndex.value < filteredStocks.value.length - 1) {
    highlightedIndex.value++
  }
}

const navigateUp = () => {
  if (highlightedIndex.value > 0) {
    highlightedIndex.value--
  }
}

const selectHighlighted = () => {
  if (filteredStocks.value[highlightedIndex.value]) {
    selectStock(filteredStocks.value[highlightedIndex.value])
  }
}

onMounted(() => {
  stocks.value = indianStocks
})
</script>

<style scoped>
.stock-search {
  position: relative;
  width: 100%;
}

.search-container {
  position: relative;
  width: 100%;
}

.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: #1a1a1d;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  transition: border-color 0.2s;
}

.search-input-wrapper:focus-within {
  border-color: #2962FF;
}

.search-icon {
  padding: 0 12px;
  font-size: 16px;
  color: #999;
}

.search-input {
  flex: 1;
  padding: 10px 8px;
  background: transparent;
  border: none;
  color: #efeff1;
  font-size: 14px;
  outline: none;
}

.search-input::placeholder {
  color: #666;
}

.clear-btn {
  padding: 0 12px;
  background: transparent;
  border: none;
  color: #999;
  font-size: 16px;
  cursor: pointer;
  transition: color 0.2s;
}

.clear-btn:hover {
  color: #efeff1;
}

.dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: #1a1a1d;
  border: 1px solid #2b2b2e;
  border-radius: 6px;
  max-height: 400px;
  overflow: hidden;
  z-index: 1000;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.dropdown-header {
  padding: 8px 12px;
  border-bottom: 1px solid #2b2b2e;
  font-size: 12px;
  color: #999;
  background: #18181b;
}

.dropdown-list {
  max-height: 360px;
  overflow-y: auto;
}

.dropdown-list::-webkit-scrollbar {
  width: 8px;
}

.dropdown-list::-webkit-scrollbar-track {
  background: #18181b;
}

.dropdown-list::-webkit-scrollbar-thumb {
  background: #2b2b2e;
  border-radius: 4px;
}

.dropdown-list::-webkit-scrollbar-thumb:hover {
  background: #3a3a3e;
}

.stock-item {
  padding: 12px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #2b2b2e;
}

.stock-item:last-child {
  border-bottom: none;
}

.stock-item:hover,
.stock-item.highlighted {
  background: #2b2b2e;
}

.stock-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.stock-symbol {
  font-size: 14px;
  font-weight: 600;
  color: #efeff1;
}

.stock-exchange {
  font-size: 11px;
  padding: 2px 6px;
  background: #2962FF;
  color: white;
  border-radius: 3px;
  font-weight: 500;
}

.stock-name {
  font-size: 12px;
  color: #999;
}

.no-results {
  padding: 0;
}

.no-results-content {
  padding: 32px;
  text-align: center;
  color: #999;
}

.no-results-content span {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.no-results-content p {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #efeff1;
}

.no-results-content small {
  font-size: 12px;
  color: #666;
}
</style>

