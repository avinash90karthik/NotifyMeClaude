import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { HedgeSetup } from '../types'

export function HedgeView({ symbol }: { symbol: string }) {
  const { data, isLoading, error } = useQuery<HedgeSetup>({
    queryKey: ['hedge', symbol],
    queryFn: () => api.hedgeSetup(symbol),
    staleTime: 60_000,
  })

  if (isLoading) return <div style={{ color: '#64748b' }}>Loading hedge setup...</div>
  if (error || !data) return <div style={{ color: '#ef4444' }}>Error: {String(error)}</div>

  const zoneColors: Record<string, string> = {
    overbought: '#ef4444',
    elevated: '#f59e0b',
    mid: '#64748b',
    neutral: '#64748b',
    oversold: '#22c55e',
  }

  return (
    <div>
      {/* Section Description */}
      <div style={{ fontSize: 10, color: '#475569', marginBottom: 12 }}>
        Analyzes if a hedge (short) makes sense for your open runners.
      </div>

      <h2 style={{ fontSize: 16, color: '#f1f5f9', marginBottom: 16 }}>
        Hedge Setup: {symbol}
        {data.hedge_recommended && (
          <span style={{
            marginLeft: 12, fontSize: 11, padding: '3px 10px', borderRadius: 4,
            background: '#f59e0b20', color: '#f59e0b', border: '1px solid #f59e0b40',
          }}>
            HEDGE RECOMMENDED ({data.hedge_confidence}%)
          </span>
        )}
      </h2>

      {/* Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
        <div style={{ background: '#111827', border: '1px solid #1e293b', borderRadius: 6, padding: '10px 14px' }}>
          <div style={{ fontSize: 9, color: '#64748b', letterSpacing: 2 }}>PRICE</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#f1f5f9' }}>${data.current_price.toFixed(2)}</div>
        </div>
        <div style={{ background: '#111827', border: '1px solid #1e293b', borderRadius: 6, padding: '10px 14px' }}>
          <div style={{ fontSize: 9, color: '#64748b', letterSpacing: 2 }}>RSI ZONE</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: zoneColors[data.rsi_zone] || '#64748b' }}>
            {data.rsi.toFixed(1)} ({data.rsi_zone.toUpperCase()})
          </div>
        </div>
        <div style={{ background: '#111827', border: '1px solid #1e293b', borderRadius: 6, padding: '10px 14px' }}>
          <div style={{ fontSize: 9, color: '#64748b', letterSpacing: 2 }}>POSITION</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: data.is_runner ? '#22c55e' : '#64748b' }}>
            {data.is_runner ? 'RUNNER' : data.position ? 'OPEN' : 'NONE'}
          </div>
        </div>
        <div style={{ background: '#111827', border: '1px solid #1e293b', borderRadius: 6, padding: '10px 14px' }}>
          <div style={{ fontSize: 9, color: '#64748b', letterSpacing: 2 }}>SHORT KO RECOMMENDATION</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#ef4444' }}>
            ${data.recommended_short_ko.toFixed(2)}
          </div>
          <div style={{ fontSize: 9, color: '#475569' }}>+{data.ko_distance_pct}% distance</div>
        </div>
      </div>

      {/* Active Combo Signals */}
      <h3 style={{ fontSize: 13, color: '#f59e0b', letterSpacing: 2, marginBottom: 12 }}>ACTIVE SIGNALS</h3>
      {data.combo_signals.length === 0 ? (
        <div style={{ color: '#475569', fontSize: 12, marginBottom: 24 }}>No active combo signals</div>
      ) : (
        <div style={{ display: 'grid', gap: 8, marginBottom: 24 }}>
          {data.combo_signals.map((s, i) => (
            <div key={i} style={{
              background: '#111827',
              border: `1px solid ${s.direction === 'short' ? '#ef444440' : '#22c55e40'}`,
              borderRadius: 6,
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: s.direction === 'short' ? '#ef4444' : '#22c55e',
                }} />
                <div>
                  <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 12 }}>{s.name}</div>
                  <div style={{ color: '#475569', fontSize: 10 }}>{s.detail}</div>
                </div>
              </div>
              <div style={{
                fontSize: 14, fontWeight: 700,
                color: s.strength >= 75 ? '#22c55e' : s.strength >= 60 ? '#f59e0b' : '#64748b',
              }}>
                {s.strength}%
              </div>
            </div>
          ))}
        </div>
      )}

      {/* SHORT Signals Highlight */}
      {data.short_signals.length > 0 && (
        <>
          <h3 style={{ fontSize: 13, color: '#ef4444', letterSpacing: 2, marginBottom: 12 }}>SHORT SIGNALS</h3>
          <div style={{
            background: '#450a0a20',
            border: '1px solid #ef444430',
            borderRadius: 8,
            padding: 16,
            marginBottom: 24,
          }}>
            {data.short_signals.map((s, i) => (
              <div key={i} style={{ marginBottom: 8 }}>
                <span style={{ color: '#ef4444', fontWeight: 700 }}>{s.name}</span>
                <span style={{ color: '#475569', marginLeft: 8 }}>{s.detail}</span>
                <span style={{ color: '#f59e0b', marginLeft: 8, fontWeight: 700 }}>Strength: {s.strength}%</span>
              </div>
            ))}
            <div style={{ marginTop: 12, padding: '8px 12px', background: '#1e293b', borderRadius: 4, fontSize: 11 }}>
              <span style={{ color: '#f59e0b' }}>Recommended SHORT KO:</span>
              <span style={{ color: '#ef4444', fontWeight: 700, marginLeft: 8 }}>${data.recommended_short_ko.toFixed(2)}</span>
              <span style={{ color: '#475569', marginLeft: 8 }}>({data.ko_distance_pct}% above price)</span>
            </div>
          </div>
        </>
      )}

      {/* Current Position Info */}
      {data.position && (
        <>
          <h3 style={{ fontSize: 13, color: '#64748b', letterSpacing: 2, marginBottom: 12 }}>CURRENT POSITION</h3>
          <div style={{
            background: '#111827', border: '1px solid #1e293b', borderRadius: 8, padding: 16,
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, fontSize: 11 }}>
              {[
                { l: 'SYMBOL', v: data.position.symbol },
                { l: 'DIRECTION', v: data.position.direction, c: data.position.direction === 'LONG' ? '#22c55e' : '#ef4444' },
                { l: 'ENTRY', v: `$${data.position.entry_price}` },
                { l: 'STOP', v: `$${data.position.stop_price}` },
                { l: 'CONFIDENCE', v: `${data.position.confidence}%`, c: '#f59e0b' },
                { l: 'P&L', v: `${(data.position.realized_pnl_eur || 0) > 0 ? '+' : ''}${(data.position.realized_pnl_eur || 0).toFixed(2)} EUR`, c: (data.position.realized_pnl_eur || 0) >= 0 ? '#22c55e' : '#ef4444' },
              ].map(item => (
                <div key={item.l}>
                  <div style={{ color: '#475569', fontSize: 9, letterSpacing: 1 }}>{item.l}</div>
                  <div style={{ color: item.c || '#94a3b8', fontWeight: 600 }}>{item.v}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
