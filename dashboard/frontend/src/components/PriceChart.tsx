import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createChart, type IChartApi, ColorType, LineStyle, CandlestickSeries, LineSeries, HistogramSeries } from 'lightweight-charts'
import { api } from '../api'
import type { OHLCVData } from '../types'

export function PriceChart({ symbol }: { symbol: string }) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartApi = useRef<IChartApi | null>(null)

  const { data, isLoading, error } = useQuery<OHLCVData>({
    queryKey: ['ohlcv', symbol],
    queryFn: () => api.ohlcv(symbol),
    staleTime: 900_000,
  })

  useEffect(() => {
    if (!chartRef.current || !data || data.candles.length === 0) return

    // Cleanup previous chart
    if (chartApi.current) {
      chartApi.current.remove()
      chartApi.current = null
    }

    const chart = createChart(chartRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0a0e17' },
        textColor: '#64748b',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: '#111827' },
        horzLines: { color: '#111827' },
      },
      crosshair: {
        vertLine: { color: '#f59e0b40', width: 1, style: LineStyle.Dashed },
        horzLine: { color: '#f59e0b40', width: 1, style: LineStyle.Dashed },
      },
      width: chartRef.current.clientWidth,
      height: 500,
      timeScale: { timeVisible: false, borderColor: '#1e293b' },
      rightPriceScale: { borderColor: '#1e293b' },
    })
    chartApi.current = chart

    // Candlestick series (v5 API)
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e80',
      wickDownColor: '#ef444480',
    })
    candleSeries.setData(data.candles.map(c => ({
      time: c.time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    })))

    // Volume
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    })
    volumeSeries.setData(data.candles.map(c => ({
      time: c.time,
      value: c.volume,
      color: c.close >= c.open ? '#22c55e20' : '#ef444420',
    })))

    // SMA50 line
    const sma50Data = data.candles.filter(c => c.sma50).map(c => ({ time: c.time, value: c.sma50! }))
    if (sma50Data.length > 0) {
      const sma50Series = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1, title: 'SMA50' })
      sma50Series.setData(sma50Data)
    }

    // SMA200 line
    const sma200Data = data.candles.filter(c => c.sma200).map(c => ({ time: c.time, value: c.sma200! }))
    if (sma200Data.length > 0) {
      const sma200Series = chart.addSeries(LineSeries, { color: '#8b5cf6', lineWidth: 1, title: 'SMA200' })
      sma200Series.setData(sma200Data)
    }

    // Bollinger Bands
    const bbUpperData = data.candles.filter(c => c.bb_upper).map(c => ({ time: c.time, value: c.bb_upper! }))
    const bbLowerData = data.candles.filter(c => c.bb_lower).map(c => ({ time: c.time, value: c.bb_lower! }))
    if (bbUpperData.length > 0) {
      const bbUpper = chart.addSeries(LineSeries, { color: '#3b82f680', lineWidth: 1, lineStyle: LineStyle.Dotted })
      bbUpper.setData(bbUpperData)
      const bbLower = chart.addSeries(LineSeries, { color: '#3b82f680', lineWidth: 1, lineStyle: LineStyle.Dotted })
      bbLower.setData(bbLowerData)
    }

    // Position levels (KO zone, stop, entry, target)
    if (data.position) {
      // KO Level — thick red line (most important for turbos!)
      if (data.position.ko) {
        const koPrice = data.position.ko
        const koBuffer = koPrice * 0.02
        candleSeries.createPriceLine({
          price: koPrice,
          color: '#ef4444',
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          axisLabelVisible: true,
          title: `KO ${koPrice}`,
        })
        candleSeries.createPriceLine({
          price: koPrice + koBuffer,
          color: '#ef444440',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: false,
          title: '',
        })
      }

      // Stop
      if (data.position.stop) {
        candleSeries.createPriceLine({
          price: data.position.stop,
          color: '#f97316',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `Stop ${data.position.stop}`,
        })
      }

      // Entry
      if (data.position.entry) {
        candleSeries.createPriceLine({
          price: data.position.entry,
          color: '#22c55e80',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `Entry ${data.position.entry}`,
        })
      }

      // Target
      if (data.position.target) {
        candleSeries.createPriceLine({
          price: data.position.target,
          color: '#22c55e',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `Target ${data.position.target}`,
        })
      }
    }

    // Resize handler
    const handleResize = () => {
      if (chartRef.current) chart.applyOptions({ width: chartRef.current.clientWidth })
    }
    window.addEventListener('resize', handleResize)

    chart.timeScale().fitContent()

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartApi.current = null
    }
  }, [data])

  const lastCandle = data?.candles[data.candles.length - 1]
  const curr = data?.currency === 'EUR' ? '\u20AC' : data?.currency === 'GBP' ? '\u00A3' : '$'

  return (
    <div>
      {/* Section Description + Last Updated */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#475569', marginBottom: 12 }}>
        <span>6-month candlestick chart with overlays. Position levels shown if you have an open trade.</span>
        {data?.last_updated && (
          <span>Last data: <span style={{ color: '#94a3b8' }}>{data.last_updated}</span> · {data.currency}</span>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ fontSize: 16, color: '#f1f5f9', margin: 0 }}>
          {symbol}
          {lastCandle && (
            <span style={{ color: '#94a3b8', fontWeight: 400, fontSize: 14, marginLeft: 12 }}>
              {curr}{lastCandle.close.toFixed(2)}
            </span>
          )}
        </h2>
        {lastCandle?.rsi && (
          <div style={{ display: 'flex', gap: 16, fontSize: 11 }}>
            <span>
              RSI <span style={{
                fontWeight: 700,
                color: lastCandle.rsi < 30 ? '#22c55e' : lastCandle.rsi > 70 ? '#ef4444' : '#f59e0b',
              }}>{lastCandle.rsi.toFixed(1)}</span>
            </span>
            {data?.position && (
              <span style={{ color: '#ef4444' }}>
                KO {curr}{data.position.ko}
              </span>
            )}
          </div>
        )}
      </div>

      {isLoading && <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>Loading chart...</div>}
      {error && <div style={{ color: '#ef4444' }}>Chart Error: {String(error)}</div>}

      <div ref={chartRef} style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid #1e293b' }} />

      <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 10, color: '#475569', flexWrap: 'wrap' }}>
        {data?.candles.some(c => c.sma50) && <span><span style={{ color: '#f59e0b' }}>&#9473;</span> SMA50</span>}
        {data?.candles.some(c => c.sma200) && <span><span style={{ color: '#8b5cf6' }}>&#9473;</span> SMA200</span>}
        {data?.candles.some(c => c.bb_upper) && <span><span style={{ color: '#3b82f6' }}>&#9476;&#9476;</span> Bollinger Bands</span>}
        {data?.position?.ko && <span><span style={{ color: '#ef4444' }}>&#9473;&#9473;</span> KO Zone</span>}
        {data?.position?.stop && <span><span style={{ color: '#f97316' }}>- -</span> Stop</span>}
        {data?.position?.entry && <span><span style={{ color: '#22c55e' }}>- -</span> Entry</span>}
        {data?.position?.target && <span><span style={{ color: '#22c55e' }}>- -</span> Target</span>}
      </div>
    </div>
  )
}
