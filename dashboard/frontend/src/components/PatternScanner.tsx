import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { ScanResult, ComboSignal } from '../types'

function SignalBadge({ signal }: { signal: ComboSignal }) {
  const isLong = signal.direction === 'long'
  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      background: isLong ? '#052e1680' : '#450a0a80',
      border: `1px solid ${isLong ? '#22c55e40' : '#ef444440'}`,
      borderRadius: 4,
      padding: '3px 8px',
      fontSize: 10,
      marginRight: 4,
      marginBottom: 4,
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: isLong ? '#22c55e' : '#ef4444',
        display: 'inline-block',
      }} />
      <span style={{ color: isLong ? '#22c55e' : '#ef4444', fontWeight: 600 }}>{signal.name}</span>
      <span style={{
        color: '#f59e0b', fontWeight: 700,
        background: '#1e293b', borderRadius: 3, padding: '0 4px',
      }}>{signal.strength}%</span>
    </div>
  )
}

function StrengthBar({ strength }: { strength: number }) {
  const color = strength >= 75 ? '#22c55e' : strength >= 60 ? '#f59e0b' : '#64748b'
  return (
    <div style={{ width: 60, height: 6, background: '#1e293b', borderRadius: 3, overflow: 'hidden' }}>
      <div style={{ width: `${strength}%`, height: '100%', background: color, borderRadius: 3 }} />
    </div>
  )
}

export function PatternScanner({ symbol }: { symbol: string }) {
  const { data, isLoading, error } = useQuery<ScanResult[]>({
    queryKey: ['scan', symbol],
    queryFn: () => api.scan(symbol),
    staleTime: 120_000,
  })

  if (isLoading) return (
    <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>
      Scanning... (may take 30-60s while fetching yfinance data)
    </div>
  )
  if (error) return <div style={{ color: '#ef4444' }}>Scan Error: {String(error)}</div>
  if (!data) return <div style={{ color: '#475569' }}>No signals found</div>

  // Sort by max signal strength
  const sorted = [...data].sort((a, b) => {
    const aMax = Math.max(...a.signals.map(s => s.strength), 0)
    const bMax = Math.max(...b.signals.map(s => s.strength), 0)
    return bMax - aMax
  })

  // Check if selected symbol exists in scan results
  const selectedInResults = sorted.find(s => s.symbol === symbol)

  // Highlight selected symbol — place it first
  const highlighted = sorted.find(s => s.symbol === symbol)
  const rest = sorted.filter(s => s.symbol !== symbol)
  const ordered = highlighted ? [highlighted, ...rest] : sorted

  // Count symbols with actual signals
  const symbolsWithSignals = data.filter(s => s.signals.length > 0).length

  return (
    <div>
      {/* Section Description */}
      <div style={{ fontSize: 10, color: '#475569', marginBottom: 12 }}>
        Scans your watchlist for technical combo signals. Higher strength = stronger setup. Click a symbol tab to highlight it.
      </div>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ fontSize: 13, color: '#f59e0b', letterSpacing: 2, margin: 0 }}>
          COMBO SIGNAL SCANNER
        </h2>
        <span style={{ fontSize: 10, color: '#475569' }}>
          {symbolsWithSignals} symbol{symbolsWithSignals !== 1 ? 's' : ''} with active signals
        </span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #1e293b' }}>
              {['SYMBOL', 'PRICE', 'CHG', 'RSI', 'REGIME', 'ATR%', 'STRENGTH', 'SIGNALS'].map(h => (
                <th key={h} style={{
                  padding: '8px 10px',
                  textAlign: h === 'SIGNALS' ? 'left' : 'right',
                  color: '#64748b', fontSize: 9, letterSpacing: 2,
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* If selected symbol is NOT in results, show a placeholder row */}
            {!selectedInResults && (
              <tr style={{
                borderBottom: '1px solid #111827',
                background: '#1a233280',
              }}>
                <td style={{ padding: '10px', textAlign: 'right' }}>
                  <span style={{ color: '#e2e8f0', fontWeight: 700 }}>{symbol}</span>
                </td>
                <td style={{ padding: '10px', textAlign: 'right', color: '#475569' }}>--</td>
                <td style={{ padding: '10px', textAlign: 'right', color: '#475569' }}>--</td>
                <td style={{ padding: '10px', textAlign: 'right', color: '#475569' }}>--</td>
                <td style={{ padding: '10px', textAlign: 'right', color: '#475569' }}>--</td>
                <td style={{ padding: '10px', textAlign: 'right', color: '#475569' }}>--</td>
                <td style={{ padding: '10px', textAlign: 'right', color: '#475569' }}>--</td>
                <td style={{ padding: '10px', textAlign: 'left', color: '#475569', fontSize: 10 }}>
                  No active signals
                </td>
              </tr>
            )}
            {ordered.map((item, idx) => {
              const maxStrength = Math.max(...item.signals.map(s => s.strength), 0)
              const isHighlighted = item.symbol === symbol
              const hasLong = item.signals.some(s => s.direction === 'long')
              const hasShort = item.signals.some(s => s.direction === 'short')

              return (
                <tr key={item.symbol} style={{
                  borderBottom: '1px solid #111827',
                  background: isHighlighted ? '#1a233280' : idx % 2 === 0 ? '#0d1117' : 'transparent',
                }}>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    <span style={{ color: '#e2e8f0', fontWeight: 700 }}>{item.symbol}</span>
                    {hasLong && <span style={{ color: '#22c55e', marginLeft: 4, fontSize: 9 }}>L</span>}
                    {hasShort && <span style={{ color: '#ef4444', marginLeft: 2, fontSize: 9 }}>S</span>}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right', color: '#94a3b8' }}>
                    ${item.price?.toFixed(2)}
                  </td>
                  <td style={{
                    padding: '10px', textAlign: 'right', fontWeight: 600,
                    color: item.change_pct > 0 ? '#22c55e' : item.change_pct < 0 ? '#ef4444' : '#64748b',
                  }}>
                    {item.change_pct > 0 ? '+' : ''}{item.change_pct?.toFixed(1)}%
                  </td>
                  <td style={{
                    padding: '10px', textAlign: 'right', fontWeight: 600,
                    color: item.rsi < 30 ? '#22c55e' : item.rsi > 70 ? '#ef4444' : '#f59e0b',
                  }}>
                    {item.rsi?.toFixed(1)}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    <span style={{
                      fontSize: 9, padding: '2px 6px', borderRadius: 3,
                      background: '#1e293b',
                      color: item.regime === 'TRENDING' ? '#f59e0b' : item.regime === 'CHOPPY' ? '#ef4444' : '#64748b',
                    }}>{item.regime}</span>
                  </td>
                  <td style={{
                    padding: '10px', textAlign: 'right',
                    color: item.atr_pct > 7 ? '#ef4444' : item.atr_pct > 5 ? '#f59e0b' : '#94a3b8',
                  }}>
                    {item.atr_pct?.toFixed(1)}%
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
                      <StrengthBar strength={maxStrength} />
                      <span style={{ color: '#f59e0b', fontWeight: 700, width: 30, textAlign: 'right' }}>
                        {maxStrength}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '10px', textAlign: 'left' }}>
                    {item.signals.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                        {item.signals.map((s, i) => (
                          <SignalBadge key={i} signal={s} />
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: '#475569', fontSize: 10 }}>No active signals</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {data.length === 0 && (
        <div style={{ color: '#475569', fontSize: 12, textAlign: 'center', padding: 24 }}>
          No strong setups found. Check back later or expand your watchlist.
        </div>
      )}
    </div>
  )
}
