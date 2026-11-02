def patch_js():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    js_target = '    async function loadGoldDashboard(force=false) {'
    
    js_replace = '''    // --------------------------------------------------------------------------
    // TRADINGVIEW LIGHTWEIGHT CANDLESTICK CHART & STRATEGY OVERLAYS
    // --------------------------------------------------------------------------
    let goldChartInstance = null;
    let goldCandleSeries = null;
    let currentGoldChartTf = 'M15';
    let chartPriceLines = [];

    function initGoldChart() {
      const container = document.getElementById('goldTradingChart');
      if (!container || goldChartInstance) return;

      if (typeof LightweightCharts === 'undefined') {
        console.warn('LightweightCharts loading...');
        setTimeout(initGoldChart, 400);
        return;
      }

      try {
        goldChartInstance = LightweightCharts.createChart(container, {
          width: container.clientWidth || 800,
          height: container.clientHeight || 420,
          layout: {
            background: { color: '#020617' },
            textColor: '#94a3b8',
            fontSize: 11,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
          },
          grid: {
            vertLines: { color: 'rgba(30, 41, 59, 0.4)' },
            horzLines: { color: 'rgba(30, 41, 59, 0.4)' }
          },
          crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: { color: 'rgba(148, 163, 184, 0.5)', width: 1, style: 2 },
            horzLine: { color: 'rgba(148, 163, 184, 0.5)', width: 1, style: 2 }
          },
          rightPriceScale: {
            borderColor: 'rgba(30, 41, 59, 0.8)',
            scaleMargins: { top: 0.15, bottom: 0.15 }
          },
          timeScale: {
            borderColor: 'rgba(30, 41, 59, 0.8)',
            timeVisible: true,
            secondsVisible: false
          }
        });

        goldCandleSeries = goldChartInstance.addCandlestickSeries({
          upColor: '#10b981',
          downColor: '#ef4444',
          borderVisible: false,
          wickUpColor: '#10b981',
          wickDownColor: '#ef4444'
        });

        window.addEventListener('resize', () => {
          if (goldChartInstance && container) {
            goldChartInstance.applyOptions({ width: container.clientWidth, height: container.clientHeight });
          }
        });

        refreshGoldChart(true);
      } catch (e) {
        console.error('Failed to init chart:', e);
      }
    }

    async function switchGoldChartTf(tf) {
      currentGoldChartTf = tf;
      ['btnTfM5', 'btnTfM15', 'btnTfH1', 'btnTfH4'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
          btn.className = 'px-2.5 py-1 rounded text-slate-400 hover:text-white transition';
        }
      });
      const activeBtn = document.getElementById('btnTf' + tf);
      if (activeBtn) {
        activeBtn.className = 'px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40';
      }
      refreshGoldChart(true);
    }

    async function refreshGoldChart(fitTime = false) {
      if (!goldCandleSeries) {
        initGoldChart();
        return;
      }
      try {
        const res = await fetch(`/api/gold/candles?tf=${currentGoldChartTf}&count=140`);
        if (!res.ok) return;
        const candles = await res.json();
        if (candles && candles.length > 0) {
          goldCandleSeries.setData(candles);
          if (fitTime && goldChartInstance) {
            goldChartInstance.timeScale().fitContent();
          }
          const latest = candles[candles.length - 1];
          const quoteEl = document.getElementById('chartLiveQuote');
          if (quoteEl) {
            quoteEl.innerHTML = `XAUUSD: <span class="${latest.close >= latest.open ? 'text-emeraldaccent' : 'text-rose-400'} font-bold">${latest.close.toFixed(2)}</span>`;
          }
        }
        await updateChartStrategyOverlays();
      } catch (err) {
        console.error('Error refreshing Gold chart:', err);
      }
    }

    async function updateChartStrategyOverlays() {
      if (!goldCandleSeries) return;

      chartPriceLines.forEach(line => {
        try { goldCandleSeries.removePriceLine(line); } catch (e) {}
      });
      chartPriceLines = [];

      try {
        const stRes = await fetch('/api/gold/auto_trade/status');
        let activePos = null;
        if (stRes.ok) {
          const stData = await stRes.json();
          const openPositions = stData.open_gold_positions || [];
          if (openPositions.length > 0) {
            activePos = openPositions[0];
          }
        }

        const beBadge = document.getElementById('chartBeBadge');

        if (activePos) {
          const entryLine = goldCandleSeries.createPriceLine({
            price: activePos.entry,
            color: '#60a5fa',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: `ENTRY (${activePos.direction} #${activePos.ticket})`
          });
          chartPriceLines.push(entryLine);

          if (activePos.sl > 0) {
            const isBe = (activePos.direction === 'BUY' && activePos.sl >= activePos.entry) ||
                         (activePos.direction === 'SELL' && activePos.sl <= activePos.entry);
            const slLine = goldCandleSeries.createPriceLine({
              price: activePos.sl,
              color: isBe ? '#f59e0b' : '#ef4444',
              lineWidth: 2,
              lineStyle: LightweightCharts.LineStyle.Solid,
              axisLabelVisible: true,
              title: isBe ? '🛡️ BREAK-EVEN (RISK FREE)' : 'SL (PROTECTIVE)'
            });
            chartPriceLines.push(slLine);

            if (beBadge) {
              if (isBe) beBadge.classList.remove('hidden');
              else beBadge.classList.add('hidden');
            }
          }

          if (activePos.tp > 0) {
            const tpLine = goldCandleSeries.createPriceLine({
              price: activePos.tp,
              color: '#10b981',
              lineWidth: 2,
              lineStyle: LightweightCharts.LineStyle.Solid,
              axisLabelVisible: true,
              title: 'TP (TARGET)'
            });
            chartPriceLines.push(tpLine);
          }
        } else {
          if (beBadge) beBadge.classList.add('hidden');
          const setupsRes = await fetch('/api/gold/setups');
          if (setupsRes.ok) {
            const setups = await setupsRes.json();
            if (setups && setups.length > 0) {
              const best = setups[0];
              if (best.entry > 0) {
                chartPriceLines.push(goldCandleSeries.createPriceLine({
                  price: best.entry,
                  color: '#60a5fa',
                  lineWidth: 1,
                  lineStyle: LightweightCharts.LineStyle.Dashed,
                  axisLabelVisible: true,
                  title: `SETUP ENTRY (${best.direction})`
                }));
              }
              if (best.sl > 0) {
                chartPriceLines.push(goldCandleSeries.createPriceLine({
                  price: best.sl,
                  color: '#ef4444',
                  lineWidth: 1,
                  lineStyle: LightweightCharts.LineStyle.Solid,
                  axisLabelVisible: true,
                  title: 'SETUP SL'
                }));
              }
              if (best.tp1 > 0) {
                chartPriceLines.push(goldCandleSeries.createPriceLine({
                  price: best.tp1,
                  color: '#10b981',
                  lineWidth: 1,
                  lineStyle: LightweightCharts.LineStyle.Solid,
                  axisLabelVisible: true,
                  title: 'TP1 (1.8R)'
                }));
              }
              if (best.tp2 > 0) {
                chartPriceLines.push(goldCandleSeries.createPriceLine({
                  price: best.tp2,
                  color: '#22d3ee',
                  lineWidth: 1,
                  lineStyle: LightweightCharts.LineStyle.Solid,
                  axisLabelVisible: true,
                  title: 'TP2 (4.0R)'
                }));
              }
            }
          }
        }
      } catch (e) {
        console.error('Error updating chart overlays:', e);
      }
    }

    async function loadGoldDashboard(force=false) {
      if (!goldChartInstance) {
        initGoldChart();
      } else {
        refreshGoldChart(false);
      }'''

    if js_target not in content:
        print("ERROR: js_target not found!")
        return False

    content = content.replace(js_target, js_replace, 1)

    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: Patched JavaScript for TradingView Lightweight Chart!")
    return True

if __name__ == '__main__':
    patch_js()
