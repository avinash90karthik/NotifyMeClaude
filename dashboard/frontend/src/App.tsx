import { useState } from 'react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import type { Tab, Position } from './types'
import { api } from './api'
import { PortfolioView } from './components/PortfolioView'
import { PatternScanner } from './components/PatternScanner'
import { TrackRecord } from './components/TrackRecord'
import { PriceChart } from './components/PriceChart'
import { HedgeView } from './components/HedgeView'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchInterval: 60_000 } },
})

const TABS: { key: Tab; label: string }[] = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'scanner', label: 'Scanner' },
  { key: 'analysis', label: 'Chart' },
  { key: 'track-record', label: 'Track Record' },
  { key: 'hedge', label: 'Hedge' },
]

const SYMBOLS = ['ENR.DE', 'ASTS', 'MU']

function WelcomePanel() {
  return (
    <div style={{
      background: '#111827',
      border: '1px solid #f59e0b40',
      borderRadius: 12,
      padding: 40,
      maxWidth: 600,
      margin: '60px auto',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 24, color: '#f59e0b', fontWeight: 700, marginBottom: 8 }}>
        Welcome to Silver Hawk Trading Dashboard
      </div>
      <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 32 }}>
        Your portfolio is empty. To get started, run an analysis with Claude Code.
      </div>

      <div style={{ textAlign: 'left', fontSize: 13, color: '#c8d6e5', lineHeight: 2.2 }}>
        <div style={{ color: '#f59e0b', fontSize: 11, letterSpacing: 2, marginBottom: 8, fontWeight: 700 }}>
          GETTING STARTED
        </div>
        <div>
          <span style={{ color: '#f59e0b', fontWeight: 700 }}>1.</span>{' '}
          Run an analysis:{' '}
          <code style={{ background: '#1e293b', padding: '2px 8px', borderRadius: 4, fontSize: 11, color: '#22c55e' }}>
            /analyse-stock NVDA
          </code>
        </div>
        <div>
          <span style={{ color: '#f59e0b', fontWeight: 700 }}>2.</span>{' '}
          Record a trade:{' '}
          <code style={{ background: '#1e293b', padding: '2px 8px', borderRadius: 4, fontSize: 11, color: '#22c55e' }}>
            python prediction_db.py open ID --shares 50 --cert-price 2.50
          </code>
        </div>
        <div>
          <span style={{ color: '#f59e0b', fontWeight: 700 }}>3.</span>{' '}
          Your positions and analyses will appear here automatically.
        </div>
      </div>

      <div style={{
        marginTop: 32, fontSize: 10, color: '#475569',
        borderTop: '1px solid #1e293b', paddingTop: 16,
      }}>
        The Scanner and Chart tabs work right away -- try them while you set up your first trade.
      </div>
    </div>
  )
}

function DashboardContent() {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [symbol, setSymbol] = useState('ENR.DE')
  const [customSymbol, setCustomSymbol] = useState('')

  const { data: predictions, isLoading: predictionsLoading } = useQuery<Position[]>({
    queryKey: ['predictions'],
    queryFn: () => api.predictions(),
    staleTime: 60_000,
  })

  const isFirstTimeUser = !predictionsLoading && predictions && predictions.length === 0

  const showSymbolTabs = tab === 'analysis' || tab === 'hedge' || tab === 'scanner'

  return (
    <div style={{
      fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
      background: '#0a0e17',
      color: '#c8d6e5',
      minHeight: '100vh',
    }}>
      {/* Header */}
      <header style={{
        borderBottom: '1px solid #1a2332',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: '#f59e0b', fontSize: 11, letterSpacing: 3, fontWeight: 700 }}>
            SILVER HAWK
          </span>
          <span style={{ color: '#1e293b' }}>|</span>
          <span style={{ color: '#64748b', fontSize: 11, letterSpacing: 2 }}>
            TRADING DASHBOARD
          </span>
        </div>
        <div style={{ fontSize: 10, color: '#475569' }}>
          {new Date().toLocaleDateString('en-US')} {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
        </div>
      </header>

      {/* Main Tabs */}
      <nav style={{
        display: 'flex',
        gap: 0,
        borderBottom: '1px solid #1a2332',
        padding: '0 24px',
      }}>
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              background: 'none',
              border: 'none',
              borderBottom: tab === t.key ? '2px solid #f59e0b' : '2px solid transparent',
              color: tab === t.key ? '#f59e0b' : '#64748b',
              padding: '10px 20px',
              fontSize: 11,
              fontFamily: 'inherit',
              letterSpacing: 2,
              cursor: 'pointer',
              fontWeight: tab === t.key ? 700 : 400,
            }}
          >
            {t.label.toUpperCase()}
          </button>
        ))}
      </nav>

      {/* Symbol Tabs */}
      {showSymbolTabs && (
        <div style={{
          display: 'flex',
          gap: 6,
          padding: '8px 24px',
          borderBottom: '1px solid #111827',
          alignItems: 'center',
        }}>
          {SYMBOLS.map(s => (
            <button
              key={s}
              onClick={() => setSymbol(s)}
              style={{
                background: symbol === s ? '#1e293b' : 'transparent',
                border: `1px solid ${symbol === s ? '#f59e0b' : '#1e293b'}`,
                color: symbol === s ? '#f1f5f9' : '#64748b',
                borderRadius: 4,
                padding: '4px 12px',
                fontSize: 11,
                fontFamily: 'inherit',
                cursor: 'pointer',
                letterSpacing: 1,
              }}
            >
              {s}
            </button>
          ))}
          <form onSubmit={e => {
            e.preventDefault()
            if (customSymbol.trim()) {
              setSymbol(customSymbol.trim().toUpperCase())
              setCustomSymbol('')
            }
          }} style={{ display: 'flex', gap: 4 }}>
            <input
              value={customSymbol}
              onChange={e => setCustomSymbol(e.target.value)}
              placeholder="+ Symbol"
              style={{
                background: '#111827',
                border: '1px solid #1e293b',
                borderRadius: 4,
                color: '#c8d6e5',
                padding: '4px 8px',
                fontSize: 11,
                fontFamily: 'inherit',
                width: 80,
              }}
            />
          </form>
        </div>
      )}

      {/* Content */}
      <main style={{ padding: 24 }}>
        {tab === 'dashboard' && (isFirstTimeUser ? <WelcomePanel /> : <PortfolioView />)}
        {tab === 'scanner' && <PatternScanner symbol={symbol} />}
        {tab === 'analysis' && <PriceChart symbol={symbol} />}
        {tab === 'track-record' && (isFirstTimeUser ? <WelcomePanel /> : <TrackRecord />)}
        {tab === 'hedge' && <HedgeView symbol={symbol} />}
      </main>
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DashboardContent />
    </QueryClientProvider>
  )
}

export default App
