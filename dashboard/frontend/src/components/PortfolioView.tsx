import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { Portfolio, Position } from '../types'

function PositionCard({ pos }: { pos: Position }) {
  const pnl = pos.realized_pnl_eur || 0
  const pnlColor = pnl > 0 ? '#22c55e' : pnl < 0 ? '#ef4444' : '#64748b'
  const dirColor = pos.direction === 'LONG' ? '#22c55e' : '#ef4444'

  return (
    <div style={{
      background: '#111827',
      border: '1px solid #1e293b',
      borderRadius: 8,
      padding: 16,
      borderLeft: `3px solid ${dirColor}`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <div>
          <span style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>{pos.symbol}</span>
          <span style={{
            marginLeft: 8, fontSize: 9, padding: '2px 6px', borderRadius: 3,
            background: pos.direction === 'LONG' ? '#052e16' : '#450a0a',
            color: dirColor, letterSpacing: 1,
          }}>{pos.direction}</span>
        </div>
        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 3,
          background: '#1e293b', color: '#f59e0b',
        }}>{pos.confidence}%</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 11 }}>
        <div>
          <div style={{ color: '#475569', fontSize: 9, letterSpacing: 1 }}>ENTRY</div>
          <div style={{ color: '#94a3b8' }}>${pos.entry_price}</div>
        </div>
        <div>
          <div style={{ color: '#475569', fontSize: 9, letterSpacing: 1 }}>INVESTED</div>
          <div style={{ color: '#94a3b8' }}>{pos.invested_eur?.toFixed(0)} EUR</div>
        </div>
        <div>
          <div style={{ color: '#475569', fontSize: 9, letterSpacing: 1 }}>P&L</div>
          <div style={{ color: pnlColor, fontWeight: 700 }}>
            {pnl > 0 ? '+' : ''}{pnl.toFixed(2)} EUR
          </div>
        </div>
      </div>

      {pos.ko_level && (
        <div style={{ marginTop: 8, fontSize: 10, color: '#475569' }}>
          KO: ${pos.ko_level} | Stop: ${pos.stop_price} | Target: ${pos.target_price}
        </div>
      )}

      {pos.reason && (
        <div style={{
          marginTop: 8, fontSize: 10, color: '#475569',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {pos.reason}
        </div>
      )}
    </div>
  )
}

export function PortfolioView() {
  const { data, isLoading, error } = useQuery<Portfolio>({
    queryKey: ['portfolio'],
    queryFn: api.portfolio,
  })

  if (isLoading) return <div style={{ color: '#64748b' }}>Loading...</div>
  if (error || !data) return <div style={{ color: '#ef4444' }}>Error loading portfolio</div>

  const cashPct = (data.cash / data.portfolio_value) * 100
  const investedPct = 100 - cashPct

  return (
    <div>
      {/* Section Description */}
      <div style={{ fontSize: 10, color: '#475569', marginBottom: 16 }}>
        Live portfolio from predictions.db. Partial closes are tracked in the P&L.
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'PORTFOLIO', value: `${data.portfolio_value.toFixed(0)} EUR`, color: '#f1f5f9' },
          { label: 'CASH', value: `${data.cash.toFixed(0)} EUR`, color: '#22c55e' },
          { label: 'INVESTED', value: `${data.total_invested.toFixed(0)} EUR`, color: '#f59e0b' },
          { label: 'SLOTS', value: `${data.slots_used}/${data.slots_max}`, color: data.slots_used >= data.slots_max ? '#ef4444' : '#22c55e' },
        ].map(item => (
          <div key={item.label} style={{
            background: '#111827', border: '1px solid #1e293b', borderRadius: 6, padding: '10px 14px',
          }}>
            <div style={{ fontSize: 9, color: '#64748b', letterSpacing: 2, marginBottom: 4 }}>{item.label}</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* Cash/Invested Bar */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', background: '#1e293b' }}>
          <div style={{ width: `${investedPct}%`, background: '#f59e0b', transition: 'width 0.3s' }} />
          <div style={{ width: `${cashPct}%`, background: '#22c55e', transition: 'width 0.3s' }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#475569', marginTop: 4 }}>
          <span>Invested {investedPct.toFixed(0)}%</span>
          <span>Cash {cashPct.toFixed(0)}%</span>
        </div>
      </div>

      {/* Open Positions */}
      <h2 style={{ fontSize: 13, color: '#f59e0b', letterSpacing: 2, marginBottom: 12 }}>OPEN POSITIONS</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 12, marginBottom: 24 }}>
        {data.positions.map(pos => (
          <PositionCard key={pos.id} pos={pos} />
        ))}
        {data.positions.length === 0 && (
          <div style={{ color: '#475569', fontSize: 12 }}>No open positions</div>
        )}
      </div>

      {/* Closed Trades */}
      <h2 style={{ fontSize: 13, color: '#64748b', letterSpacing: 2, marginBottom: 12 }}>CLOSED TRADES</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #1e293b' }}>
            {['#', 'Symbol', 'Direction', 'Conf.', 'P&L', 'Date'].map(h => (
              <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: '#475569', fontSize: 9, letterSpacing: 1 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.closed_trades.map(t => {
            const pnl = t.realized_pnl_eur || 0
            return (
              <tr key={t.id} style={{ borderBottom: '1px solid #111827' }}>
                <td style={{ padding: '6px 10px', color: '#64748b' }}>#{t.id}</td>
                <td style={{ padding: '6px 10px', color: '#e2e8f0', fontWeight: 600 }}>{t.symbol}</td>
                <td style={{ padding: '6px 10px', color: t.direction === 'LONG' ? '#22c55e' : '#ef4444' }}>{t.direction}</td>
                <td style={{ padding: '6px 10px', color: '#f59e0b' }}>{t.confidence}%</td>
                <td style={{ padding: '6px 10px', color: pnl > 0 ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                  {pnl > 0 ? '+' : ''}{pnl.toFixed(2)} EUR
                </td>
                <td style={{ padding: '6px 10px', color: '#475569' }}>{t.closed_at?.split(' ')[0]}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
