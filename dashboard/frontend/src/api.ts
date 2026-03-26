import type { Portfolio, ScanResult, OHLCVData, HedgeSetup, TrackRecordData, Position } from './types'

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  portfolio: () => get<Portfolio>('/portfolio'),
  predictions: (status?: string) =>
    get<Position[]>(`/predictions${status ? `?status=${status}` : ''}`),
  prediction: (id: number) => get<Position & { full_analysis?: unknown }>(`/predictions/${id}`),
  scan: () => get<ScanResult[]>('/scan'),
  ohlcv: (symbol: string, period = '6mo') =>
    get<OHLCVData>(`/ohlcv/${symbol}?period=${period}`),
  hedgeSetup: (symbol: string) => get<HedgeSetup>(`/hedge-setup/${symbol}`),
  trackRecord: () => get<TrackRecordData>('/track-record'),
  watchlist: () => get<Record<string, unknown>[]>('/watchlist'),
  backtest: () => get<Record<string, unknown>>('/backtest'),
  chartUrl: (symbol: string) => `${BASE}/chart/${symbol}`,
}
