export interface Position {
  id: number
  created_at: string
  symbol: string
  direction: 'LONG' | 'SHORT'
  confidence: number
  entry_price: number
  stop_price: number
  target_price: number
  ko_level: number | null
  regime: string | null
  atr_pct: number | null
  reason: string | null
  status: 'analysis' | 'open' | 'closed'
  shares: number
  cert_buyin: number | null
  cert_type: string | null
  invested_eur: number
  realized_pnl_eur: number | null
}

export interface Portfolio {
  cash: number
  positions: Position[]
  closed_trades: Position[]
  total_invested: number
  portfolio_value: number
  slots_used: number
  slots_max: number
}

export interface ComboSignal {
  name: string
  direction: 'long' | 'short'
  strength: number
  detail: string
}

export interface ScanResult {
  symbol: string
  price: number
  price_eur: number
  rsi: number
  rsi_slope: number
  macd_signal: string
  regime: string
  atr_pct: number
  change_pct: number
  signals: ComboSignal[]
}

export interface Candle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  sma50?: number
  sma200?: number
  bb_upper?: number
  bb_lower?: number
  bb_middle?: number
  rsi?: number
}

export interface OHLCVData {
  symbol: string
  currency: string
  last_updated: string | null
  candles: Candle[]
  position: {
    ko: number | null
    stop: number | null
    entry: number | null
    target: number | null
    direction: string
  } | null
}

export interface HedgeSetup {
  symbol: string
  current_price: number
  rsi: number
  rsi_zone: string
  position: Position | null
  is_runner: boolean
  combo_signals: ComboSignal[]
  short_signals: ComboSignal[]
  recommended_short_ko: number
  ko_distance_pct: number
  hedge_recommended: boolean
  hedge_confidence: number
}

export interface TrackRecordData {
  trades: Position[]
  pnl_timeline: { date: string; symbol: string; pnl: number; cumulative: number }[]
  cumulative_pnl: number
  total_trades: number
  winners: number
  losers: number
  win_rate: number
  avg_win: number
  avg_loss: number
  discipline: {
    total_analyses: number
    traded_under_gate: number
    gate_compliance: number
  }
}

export interface AnalysisFull {
  id: number
  symbol: string
  timestamp: string
  step1: {
    collect_data: Record<string, unknown>
    chart_analysis: { trend: string; pattern: string; key_observation: string }
    nsi: number
    nsi_classification: string
    news: { date: string; headline: string; impact: string; source: string }[]
    macro: Record<string, string>
    correlation_ok: boolean
    sector_concentration_pct: number
  }
  step2: {
    bull_target: number
    bear_target: number
    bull_confidence: number
    bear_confidence: number
    scorecard: { long_total: number; short_total: number }
    strongest_bull_arg: string
    strongest_bear_arg: string
    debate_synthesis: string
    recommended_direction: string
  }
  step3: {
    signal: string
    confidence: number
    ko_level: number
    ko_method: string
    entry: number
    stop: number
    target: number
    risk_audit: { vetoes: string[]; warnings: string[]; approved: boolean }
    position_size_eur: number
    scout_eur: number
    confirmation_eur: number
  }
}

export type Tab = 'dashboard' | 'scanner' | 'analysis' | 'track-record' | 'hedge'
