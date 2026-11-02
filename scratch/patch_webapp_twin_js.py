import re

def patch_js_twin():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update renderGoldAutoStatus to render the live positions table & telemetry
    old_render_auto = '''    function renderGoldAutoStatus(st) {
      if (!st) return;
      const badge = document.getElementById('goldAutoTradeBadge');
      const dot = document.getElementById('goldAutoDot');
      const btnText = document.getElementById('goldAutoBtnText');
      const pulse = document.getElementById('goldAutoTradePulse');
      const msg = document.getElementById('goldAutoStatusMsg');
      const btn = document.getElementById('btnToggleGoldAuto');

      if (badge && dot && btnText && btn) {
        if (st.enabled) {
          badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-500/20 text-emeraldaccent border border-emerald-500/30';
          badge.innerText = 'AUTONOMOUS TRADING: ACTIVE';
          dot.className = 'w-2.5 h-2.5 rounded-full bg-emeraldaccent animate-pulse';
          btnText.innerText = 'PAUSE GOLD AUTO-TRADE';
          btn.className = 'px-4 py-2.5 rounded-xl text-xs font-black transition shadow-lg flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-500/20';
          if (pulse) pulse.className = 'w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-lg shadow-inner animate-pulse';
        } else {
          badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-slate-800 text-slate-400 border border-slate-700';
          badge.innerText = 'STANDBY / DISABLED';
          dot.className = 'w-2.5 h-2.5 rounded-full bg-slate-500';
          btnText.innerText = 'ENABLE GOLD AUTO-TRADE';
          btn.className = 'px-4 py-2.5 rounded-xl text-xs font-black transition shadow-lg flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700';
          if (pulse) pulse.className = 'w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-lg shadow-inner';
        }
      }

      if (msg && st.status_message) {
        msg.innerText = `${st.status_message} (Check: ${st.last_eval_time || 'Just now'})`;
      }

      if (st.config) {
        const confEl = document.getElementById('goldCfgConf');
        if (confEl) confEl.innerText = `≥ ${st.config.min_confidence}%`;
        const lotEl = document.getElementById('goldCfgLot');
        if (lotEl) lotEl.innerText = `${st.config.lot_size} Lot`;
        const tpEl = document.getElementById('goldCfgTp');
        if (tpEl) tpEl.innerText = st.config.tp_mode.replace(/_/g, ' ');

        const lotSel = document.getElementById('goldLotSelect');
        if (lotSel && document.activeElement !== lotSel) lotSel.value = String(st.config.lot_size);
        const confSel = document.getElementById('goldConfSelect');
        if (confSel && document.activeElement !== confSel) confSel.value = String(st.config.min_confidence);
        const tpSel = document.getElementById('goldTpSelect');
        if (tpSel && document.activeElement !== tpSel) tpSel.value = st.config.tp_mode;
      }

      const dailyEl = document.getElementById('goldDailyTrades');
      if (dailyEl) dailyEl.innerText = `${st.daily_trades_count || 0} / ${st.max_daily_trades || 3} max`;

      const openPosEl = document.getElementById('goldOpenPosStatus');
      if (openPosEl) {
        if (st.open_gold_positions && st.open_gold_positions.length > 0) {
          const p = st.open_gold_positions[0];
          openPosEl.className = 'font-bold text-emeraldaccent';
          openPosEl.innerText = `#${p.ticket} ${p.direction} (P&L: $${p.profit})`;
        } else {
          openPosEl.className = 'font-bold text-slate-400';
          openPosEl.innerText = 'None (0/1 max)';
        }
      }'''

    new_render_auto = '''    function renderGoldAutoStatus(st) {
      if (!st) return;
      const badge = document.getElementById('goldAutoTradeBadge');
      const dot = document.getElementById('goldAutoDot');
      const btnText = document.getElementById('goldAutoBtnText');
      const pulse = document.getElementById('goldAutoTradePulse');
      const msg = document.getElementById('goldAutoStatusMsg');
      const btn = document.getElementById('btnToggleGoldAuto');

      if (badge && dot && btnText && btn) {
        if (st.enabled) {
          badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-500/20 text-emeraldaccent border border-emerald-500/30';
          badge.innerText = 'AUTONOMOUS TRADING: ACTIVE';
          dot.className = 'w-2.5 h-2.5 rounded-full bg-emeraldaccent animate-pulse';
          btnText.innerText = 'PAUSE GOLD AUTO-TRADE';
          btn.className = 'px-4 py-2.5 rounded-xl text-xs font-black transition shadow-lg flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-500/20';
          if (pulse) pulse.className = 'w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-lg shadow-inner animate-pulse';
        } else {
          badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-slate-800 text-slate-400 border border-slate-700';
          badge.innerText = 'STANDBY / DISABLED';
          dot.className = 'w-2.5 h-2.5 rounded-full bg-slate-500';
          btnText.innerText = 'ENABLE GOLD AUTO-TRADE';
          btn.className = 'px-4 py-2.5 rounded-xl text-xs font-black transition shadow-lg flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700';
          if (pulse) pulse.className = 'w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-lg shadow-inner';
        }
      }

      if (msg && st.status_message) {
        msg.innerText = `${st.status_message} (Check: ${st.last_eval_time || 'Just now'})`;
      }

      if (st.config) {
        const confEl = document.getElementById('goldCfgConf');
        if (confEl) confEl.innerText = `≥ ${st.config.min_confidence}%`;
        const lotEl = document.getElementById('goldCfgLot');
        if (lotEl) lotEl.innerText = `${st.config.lot_size} Lot`;
        const tpEl = document.getElementById('goldCfgTp');
        if (tpEl) tpEl.innerText = 'TWIN (1 FIX + 1 TRL)';

        const lotSel = document.getElementById('goldLotSelect');
        if (lotSel && document.activeElement !== lotSel) lotSel.value = String(st.config.lot_size);
        const confSel = document.getElementById('goldConfSelect');
        if (confSel && document.activeElement !== confSel) confSel.value = String(st.config.min_confidence);
        const autoTfSel = document.getElementById('goldAutoTfSelect');
        if (autoTfSel && document.activeElement !== autoTfSel && st.config.timeframe_filter) {
          autoTfSel.value = st.config.timeframe_filter;
        }
      }

      const dailyEl = document.getElementById('goldDailyTrades');
      if (dailyEl) dailyEl.innerText = `${st.daily_trades_count || 0} / ${st.max_daily_trades || 6} max`;

      const openPositions = st.open_gold_positions || [];
      const trailingMap = {};
      (st.trailing_positions || []).forEach(tr => { trailingMap[tr.ticket] = tr; });

      const openPosEl = document.getElementById('goldOpenPosStatus');
      const legsCountEl = document.getElementById('goldOpenLegsCount');
      if (legsCountEl) legsCountEl.innerText = `${openPositions.length} Active Leg${openPositions.length === 1 ? '' : 's'}`;

      if (openPosEl) {
        if (openPositions.length > 0) {
          openPosEl.className = 'font-bold text-emeraldaccent';
          openPosEl.innerText = `${openPositions.length} active leg${openPositions.length === 1 ? '' : 's'} (${openPositions.map(p => `#${p.ticket} $${p.profit}`).join(', ')})`;
        } else {
          openPosEl.className = 'font-bold text-slate-400';
          openPosEl.innerText = 'None (0/2 active)';
        }
      }

      // Populate Gold Positions Table
      const tbody = document.getElementById('goldPositionsTbody');
      if (tbody) {
        if (openPositions.length === 0) {
          tbody.innerHTML = '<tr><td colspan="10" class="py-4 text-center text-slate-500">No open Gold positions currently. Use terminal above or setup cards to enter twin trades.</td></tr>';
        } else {
          tbody.innerHTML = openPositions.map(p => {
            const trInfo = trailingMap[p.ticket];
            const isTrailingLeg = !!trInfo || p.tp === 0;
            const isBuy = p.direction === 'BUY';
            const profitVal = parseFloat(p.profit) || 0.0;
            const pnlColor = profitVal >= 0 ? 'text-emeraldaccent font-bold' : 'text-rose-400 font-bold';

            let roleBadge = '';
            let telemetryHtml = '';

            if (isTrailingLeg) {
              roleBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">✨ Trade 2: Trailing Runner</span>';
              const beStatus = trInfo && trInfo.be_moved ? '<span class="text-emeraldaccent font-bold">🛡️ BE Armed</span>' : '<span class="text-slate-400">BE Pending (+1R)</span>';
              telemetryHtml = `<div class="text-[10px]">${beStatus} &bull; Trail: <span class="text-amber-300">$${trInfo ? trInfo.trail_dist : 3.50}/oz</span></div>`;
            } else {
              roleBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">🎯 Trade 1: Fixed Target</span>';
              telemetryHtml = `<div class="text-[10px] text-slate-400">Broker Limit Target: <span class="text-emeraldaccent font-bold">${p.tp}</span></div>`;
            }

            return `
              <tr class="hover:bg-slate-900/60 transition">
                <td class="py-2.5 px-3 font-bold text-slate-200">#${p.ticket}</td>
                <td class="py-2.5 px-3">${roleBadge}</td>
                <td class="py-2.5 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${isBuy ? 'bg-emerald-500/20 text-emeraldaccent' : 'bg-rose-500/20 text-rose-300'}">${p.direction}</span></td>
                <td class="py-2.5 px-3 text-slate-300">${p.lot} lot</td>
                <td class="py-2.5 px-3 text-slate-300">${p.entry}</td>
                <td class="py-2.5 px-3 text-white font-bold">${p.current}</td>
                <td class="py-2.5 px-3 text-rose-300">${p.sl || '--'}</td>
                <td class="py-2.5 px-3 text-emeraldaccent">${p.tp > 0 ? p.tp : 'Trailing'}</td>
                <td class="py-2.5 px-3 ${pnlColor}">$${profitVal.toFixed(2)}</td>
                <td class="py-2.5 px-3">${telemetryHtml}</td>
              </tr>
            `;
          }).join('');
        }
      }'''

    if old_render_auto in content:
        content = content.replace(old_render_auto, new_render_auto, 1)
        print("Updated renderGoldAutoStatus to render dynamic twin position table")

    # 2. Update updateGoldAutoSettings to send timeframe_filter
    old_update_settings = '''    async function updateGoldAutoSettings() {
      const lot = parseFloat(document.getElementById('goldLotSelect').value);
      const conf = parseInt(document.getElementById('goldConfSelect').value);
      const tpMode = document.getElementById('goldTpSelect').value;
      try {
        await fetch('/api/gold/auto_trade/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lot_size: lot,
            min_confidence: conf,
            tp_mode: tpMode
          })
        });
        loadGoldDashboard();
      } catch (err) {
        console.error('Failed to update Gold auto settings:', err);
      }
    }'''

    new_update_settings = '''    async function updateGoldAutoSettings() {
      const lot = parseFloat(document.getElementById('goldLotSelect') ? document.getElementById('goldLotSelect').value : 0.01);
      const conf = parseInt(document.getElementById('goldConfSelect') ? document.getElementById('goldConfSelect').value : 90);
      const tfFilter = document.getElementById('goldAutoTfSelect') ? document.getElementById('goldAutoTfSelect').value : 'M1_M5';
      try {
        await fetch('/api/gold/auto_trade/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lot_size: lot,
            min_confidence: conf,
            timeframe_filter: tfFilter,
            twin_trade_enabled: true
          })
        });
        loadGoldDashboard();
      } catch (err) {
        console.error('Failed to update Gold auto settings:', err);
      }
    }'''

    if old_update_settings in content:
        content = content.replace(old_update_settings, new_update_settings, 1)
        print("Updated updateGoldAutoSettings to send timeframe_filter")

    # 3. Add Manual Terminal Controllers and Twin Execution Methods
    manual_terminal_js = '''    // --------------------------------------------------------------------------
    // GOLD HIGH-FREQUENCY MANUAL TRADING TERMINAL & TWIN-ORDER CONTROLLER
    // --------------------------------------------------------------------------
    let currentManualTradeTf = 'M1';

    function setManualTradeTf(tf) {
      currentManualTradeTf = tf;
      ['btnTerminalM1', 'btnTerminalM5', 'btnTerminalM15'].forEach(id => {
        const b = document.getElementById(id);
        if (b) {
          b.className = 'py-2 px-2.5 rounded-xl bg-slate-950 text-slate-400 hover:text-white border border-bordercol text-center transition flex flex-col items-center';
        }
      });
      const activeBtn = document.getElementById('btnTerminal' + tf);
      if (activeBtn) {
        activeBtn.className = 'py-2 px-2.5 rounded-xl bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 text-center transition flex flex-col items-center';
      }

      const displayEl = document.getElementById('activeTerminalTfDisplay');
      if (displayEl) {
        displayEl.innerText = tf === 'M1' ? '⚡ M1 SCALP MODE' : (tf === 'M5' ? '⚡ 5M MOMENTUM MODE' : 'M15 INTRADAY MODE');
      }

      // Automatically sync chart timeframe
      switchGoldChartTf(tf);
      updateTerminalPreview();
    }

    function updateTerminalPreview() {
      const lotSel = document.getElementById('terminalLotSelect');
      const lot = parseFloat(lotSel ? lotSel.value : 0.01);
      const totalEl = document.getElementById('terminalTotalLot');
      if (totalEl) totalEl.innerText = `${(lot * 2).toFixed(2)} Lot (${(lot * 200).toFixed(0)} oz total)`;

      const p1El = document.getElementById('previewLeg1Tp');
      const p2El = document.getElementById('previewLeg2Tp');
      if (currentManualTradeTf === 'M1') {
        if (p1El) p1El.innerText = '+1.5R Fixed Target (Scalp TP1)';
        if (p2El) p2El.innerText = 'Trailing Stop ($3.00/oz Trail)';
      } else if (currentManualTradeTf === 'M5') {
        if (p1El) p1El.innerText = '+1.8R Fixed Target (Momentum TP1)';
        if (p2El) p2El.innerText = 'Trailing Stop ($4.50/oz Trail)';
      } else {
        if (p1El) p1El.innerText = '+2.5R Fixed Target (Intraday TP1)';
        if (p2El) p2El.innerText = 'Trailing Stop ($5.00/oz Trail)';
      }
    }

    async function executeManualGoldTrade(action) {
      const lotVal = parseFloat(document.getElementById('terminalLotSelect') ? document.getElementById('terminalLotSelect').value : 0.01);

      // Find matching setup for the chosen timeframe if available
      let matchedSetup = null;
      if (cachedGoldSetups && cachedGoldSetups.length > 0) {
        matchedSetup = cachedGoldSetups.find(s => s.timeframe === currentManualTradeTf && s.direction === action) ||
                       cachedGoldSetups.find(s => s.timeframe === currentManualTradeTf) ||
                       cachedGoldSetups[0];
      }

      let sl = matchedSetup ? matchedSetup.sl : 0.0;
      let tp1 = matchedSetup ? matchedSetup.tp1 : 0.0;

      const confirmMsg = `⚡ CONFIRM TWIN TRADE EXECUTION ON GOLD (XAUUSD)?\\n\\n` +
                         `• Direction: ${action}\\n` +
                         `• Timeframe: ${currentManualTradeTf}\\n` +
                         `• Volume: ${lotVal} lot per leg (Total: ${(lotVal * 2).toFixed(2)} lots)\\n` +
                         `• Trade 1: Hard Fixed Take Profit (TP1 ${tp1 || '~1.5R'})\\n` +
                         `• Trade 2: Dynamic Trailing Take Profit (Runner)\\n` +
                         `• Stop Loss: Shared Structural Risk (${sl || 'ATR-based'})`;

      if (!confirm(confirmMsg)) return;

      try {
        const res = await fetch('/api/gold/execute_twin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            direction: action,
            lot: lotVal,
            timeframe: currentManualTradeTf,
            sl: sl,
            tp_fixed: tp1,
            confidence: matchedSetup ? matchedSetup.confidence_score : 92,
            strategy: matchedSetup ? matchedSetup.strategy : `Manual ${currentManualTradeTf} Twin Scalp`
          })
        });

        const out = await res.json();
        alert(out.message || 'Orders submitted to broker!');
        loadGoldDashboard();
      } catch (err) {
        alert('Execution failed: ' + err);
      }
    }

    async function closeAllGoldPositions() {
      if (!confirm('Are you sure you want to close ALL active Gold positions immediately at market?')) return;
      try {
        const res = await fetch('/api/gold/close_all', { method: 'POST' });
        const out = await res.json();
        alert(`Closed ${out.closed_count || 0} Gold position(s).`);
        loadGoldDashboard();
      } catch (e) {
        alert('Close error: ' + e);
      }
    }
'''

    # Insert manual terminal JS right before executeGoldSetupNow
    setup_now_target = '    async function executeGoldSetupNow(direction, entry, sl, tp, confidence, strategy) {'
    new_setup_now = manual_terminal_js + '''    async function executeGoldSetupNow(direction, entry, sl, tp, confidence, strategy, timeframe='M1') {
      const lotVal = parseFloat(document.getElementById('goldLotSelect') ? document.getElementById('goldLotSelect').value : 0.01);
      const confirmMsg = `⚡ EXECUTE TWIN TRADES ON GOLD (${strategy})?\\n\\n` +
                         `• Direction: ${direction} (${lotVal} lot x 2)\\n` +
                         `• Entry Zone: ~${entry}\\n` +
                         `• Trade 1: Fixed Target TP1 @ ${tp}\\n` +
                         `• Trade 2: Dynamic Trailing Stop Runner\\n` +
                         `• Stop Loss: ${sl} (Confidence: ${confidence}%)`;

      if (!confirm(confirmMsg)) return;

      try {
        const res = await fetch('/api/gold/execute_twin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            direction: direction,
            lot: lotVal,
            sl: sl,
            tp_fixed: tp,
            confidence: confidence,
            strategy: strategy,
            timeframe: timeframe
          })
        });
        const out = await res.json();
        alert(out.message || 'Twin trade submitted!');
        loadGoldDashboard();
      } catch (err) {
        alert('Execution error: ' + err);
      }
    }'''

    if setup_now_target in content:
        content = content.replace(setup_now_target, new_setup_now, 1)
        print("Updated executeGoldSetupNow and inserted manual terminal JavaScript controller")

    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: Part 2 of web_app.py JavaScript patch applied!")
    return True

if __name__ == '__main__':
    patch_js_twin()
