export type TradingSymbol = string

export type IndicatorPreset = {
  id: string
  label: string
  indicators: Array<'sma' | 'ema' | 'rsi' | 'macd'>
}

export const DEFAULT_SYMBOLS: TradingSymbol[] = [
  'TCS.NS',
  'RELIANCE.NS',
  'HDFCBANK.NS',
  'INFY.NS',
  'ICICIBANK.NS',
]

export const INDICATOR_PRESETS: IndicatorPreset[] = [
  { id: 'momentum', label: 'Momentum (EMA + RSI)', indicators: ['ema', 'rsi'] },
  { id: 'trend', label: 'Trend (SMA + MACD)', indicators: ['sma', 'macd'] },
  { id: 'volatility', label: 'Volatility (EMA + RSI + MACD)', indicators: ['ema', 'rsi', 'macd'] },
]
