import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { TrackRecordData } from '../types'

function StatCard({ label, value, color = '#f1f5f9', sub }: { label: string; value: string; color?: string; sub?: string }) {
  return (
    <div style={{
      background: '#111827', border: '1px solid #1e293b', borderRadius: 6, padding: '10px 14px',
    }}>
      <div style={{ fontSize: 9, color: '#64748b', letterSpacing: 2, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
      {sub && <div style={{ fontSize: 9, color: '#475569', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function PnLBar({ pnl, maxAbs }: { pnl: number; maxAbs: number }) {
  const pct = Math.abs(pnl) / maxAbs * 100
  const isPos = pnl >= 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, height: 16 }}>
      <div style={{ width: 80, display: 'flex', justifyContent: isPos ? 'flex-start' : 'flex-end' }}>
        <div style={{
          width: `${Math.min(pct, 100)}%`,
          minWidth: 2,
          height: 10,
          background: isPos ? '#22c55e' : '#ef4444',
          borderRadius: 2,
        }} />
      </div>
      <span style={{ fontSize: 10, color: isPos ? '#22c55e' : '#ef4444', fontWeight: 600, width: 60 }}>
        {pnl > 0 ? '+' : ''}{pnl.toFixed(2)} EUR
      </span>
    </div>
  )
}

export function TrackRecord() {
  const { data, isLoading, error } = useQuery<TrackRecordData>({
    queryKey: ['track-record'],
    queryFn: api.trackRecord,
  })

  if (isLoading) return <div style={{ color: '#64748b' }}>Loading...</div>
  if (error || !data) return <div style={{ color: '#ef4444' }}>Error loading track record</div>

  const maxPnl = Math.max(...data.trades.map(t => Math.abs(t.realized_pnl_eur || 0)), 1)

  return (
    <div>
      {/* Section Description */}
      <div style={{ fontSize: 10, color: '#475569', marginBottom: 16 }}>
        All trades from close_events. Includes partial sells of open positions.
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 }}>
        <StatCard
          label="CUMULATIVE P&L"
          value={`${data.cumulative_pnl > 0 ? '+' : ''}${data.cumulative_pnl.toFixed(2)} EUR`}
          color={data.cumulative_pnl >= 0 ? '#22c55e' : '#ef4444'}
        />
        <StatCard label="TRADES" value={String(data.total_trades)} />
        <StatCard
          label="WIN RATE"
          value={`${data.win_rate.toFixed(0)}%`}
          color={data.win_rate >= 50 ? '#22c55e' : '#ef4444'}
          sub={`${data.winners}W / ${data.losers}L`}
        />
        <StatCard
          label="AVG WIN"
          value={`+${data.avg_win.toFixed(0)} EUR`}
          color="#22c55e"
        />
        <StatCard
          label="AVG LOSS"
          value={`-${data.avg_loss.toFixed(0)} EUR`}
          color="#ef4444"
        />
        <StatCard
          label="DISCIPLINE"
          value={`${data.discipline.gate_compliance.toFixed(0)}%`}
          color={data.discipline.gate_compliance >= 90 ? '#22c55e' : '#f59e0b'}
          sub={`Gate: ${data.discipline.traded_under_gate} violations`}
        />
      </div>

      {/* P&L Timeline */}
      <h3 style={{ fontSize: 13, color: '#f59e0b', letterSpacing: 2, marginBottom: 12 }}>P&L TIMELINE</h3>
      <div style={{
        background: '#111827', border: '1px solid #1e293b', borderRadius: 8,
        padding: 16, marginBottom: 24,
      }}>
        {data.pnl_timeline.length === 0 ? (
          <div style={{ color: '#475569', fontSize: 12 }}>No closed trades yet</div>
        ) : (
          <div>
            {data.pnl_timeline.map((t, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '6px 0', borderBottom: '1px solid #111827',
              }}>
                <span style={{ fontSize: 10, color: '#475569', width: 80 }}>{t.date.split(' ')[0]}</span>
                <span style={{ fontSize: 11, color: '#94a3b8', width: 60, fontWeight: 600 }}>{t.symbol}</span>
                <PnLBar pnl={t.pnl} maxAbs={maxPnl} />
                <span style={{
                  fontSize: 10, color: t.cumulative >= 0 ? '#22c55e' : '#ef4444',
                  marginLeft: 'auto', fontWeight: 600,
                }}>
                  Cum: {t.cumulative > 0 ? '+' : ''}{t.cumulative.toFixed(0)} EUR
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Win/Loss Distribution */}
      <h3 style={{ fontSize: 13, color: '#64748b', letterSpacing: 2, marginBottom: 12 }}>WIN / LOSS DISTRIBUTION</h3>
      <div style={{
        display: 'flex', gap: 4, height: 24, borderRadius: 4, overflow: 'hidden', marginBottom: 24,
      }}>
        {data.winners > 0 && (
          <div style={{
            flex: data.winners, background: '#22c55e', display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#052e16', fontWeight: 700,
          }}>
            {data.winners}W ({data.win_rate.toFixed(0)}%)
          </div>
        )}
        {data.losers > 0 && (
          <div style={{
            flex: data.losers, background: '#ef4444', display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#450a0a', fontWeight: 700,
          }}>
            {data.losers}L ({(100 - data.win_rate).toFixed(0)}%)
          </div>
        )}
      </div>

      {/* All Trades Table */}
      <h3 style={{ fontSize: 13, color: '#64748b', letterSpacing: 2, marginBottom: 12 }}>ALL TRADES</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #1e293b' }}>
            {['#', 'Symbol', 'Dir', 'Conf', 'Invested', 'P&L', 'Date'].map(h => (
              <th key={h} style={{ padding: '6px 10px', textAlign: 'right', color: '#475569', fontSize: 9, letterSpacing: 1 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.trades.map(t => {
            const pnl = t.realized_pnl_eur || 0
            return (
              <tr key={t.id} style={{ borderBottom: '1px solid #111827' }}>
                <td style={{ padding: '6px 10px', textAlign: 'right', color: '#64748b' }}>#{t.id}</td>
                <td style={{ padding: '6px 10px', textAlign: 'right', color: '#e2e8f0', fontWeight: 600 }}>{t.symbol}</td>
                <td style={{ padding: '6px 10px', textAlign: 'right', color: t.direction === 'LONG' ? '#22c55e' : '#ef4444' }}>{t.direction}</td>
                <td style={{ padding: '6px 10px', textAlign: 'right', color: '#f59e0b' }}>{t.confidence}%</td>
                <td style={{ padding: '6px 10px', textAlign: 'right', color: '#94a3b8' }}>{t.invested_eur?.toFixed(0)} EUR</td>
                <td style={{ padding: '6px 10px', textAlign: 'right', color: pnl > 0 ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
                  {pnl > 0 ? '+' : ''}{pnl.toFixed(2)} EUR
                </td>
                <td style={{ padding: '6px 10px', textAlign: 'right', color: '#475569' }}>{t.closed_at?.split(' ')[0]}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
