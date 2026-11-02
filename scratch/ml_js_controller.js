    // =================================================================
    // AI / MACHINE LEARNING TRADING INTELLIGENCE CONTROLLER
    // =================================================================
    let currentMLSubmenu = 'overview';
    let mlCachedRecs = [];
    let mlTrainPollTimer = null;

    function switchMLSubmenu(subTab) {
      currentMLSubmenu = subTab;
      document.querySelectorAll('.ml-sub-tab').forEach(btn => {
        btn.className = 'ml-sub-tab px-3 py-1.5 rounded-lg text-xs font-bold transition text-slate-400 hover:text-white hover:bg-slate-800 whitespace-nowrap';
      });
      const activeBtn = document.getElementById('mlSubTab_' + subTab);
      if (activeBtn) {
        activeBtn.className = 'ml-sub-tab px-3 py-1.5 rounded-lg text-xs font-bold transition bg-purple-600 text-white shadow whitespace-nowrap';
      }

      document.querySelectorAll('.ml-sub-panel').forEach(panel => {
        panel.classList.add('hidden');
      });
      const activePanel = document.getElementById('mlPanel_' + subTab);
      if (activePanel) {
        activePanel.classList.remove('hidden');
      }

      // Load specific submenu data
      if (subTab === 'overview') fetchMLOverview();
      else if (subTab === 'recommendations') fetchMLRecommendations();
      else if (subTab === 'strategy_lab') fetchMLStrategies();
      else if (subTab === 'mtf') fetchMLMTF();
      else if (subTab === 'regime') fetchMLRegime();
      else if (subTab === 'training') fetchMLTrainingStatus();
      else if (subTab === 'backtest') fetchMLBacktest();
      else if (subTab === 'performance') fetchMLPerformance();
      else if (subTab === 'journal') fetchMLJournal();
      else if (subTab === 'risk') fetchMLRisk();
      else if (subTab === 'settings') fetchMLSettings();
    }

    async function loadMLDashboard(force = false) {
      const syncIcon = document.getElementById('mlSyncIcon');
      if (syncIcon) syncIcon.classList.add('animate-spin');

      try {
        await fetchMLOverview();
        if (currentMLSubmenu !== 'overview') {
          switchMLSubmenu(currentMLSubmenu);
        }
      } catch (err) {
        console.error("Error loading ML dashboard:", err);
      } finally {
        if (syncIcon) {
          setTimeout(() => syncIcon.classList.remove('animate-spin'), 600);
        }
      }
    }

    async function fetchMLOverview() {
      try {
        const res = await fetch('/api/ml/overview');
        const data = await res.json();
        if (!data.success) return;

        const pEl = document.getElementById('mlGoldLivePrice');
        if (pEl) pEl.innerText = `$${data.live_price.toFixed(2)}`;

        const accEl = document.getElementById('mlHeaderAccuracy');
        if (accEl) accEl.innerText = `${(data.accuracy * 100).toFixed(1)}%`;

        const brierEl = document.getElementById('mlHeaderBrier');
        if (brierEl) brierEl.innerText = data.brier_score.toFixed(3);

        const aucEl = document.getElementById('mlHeaderAUC');
        if (aucEl) aucEl.innerText = data.roc_auc.toFixed(3);

        const regEl = document.getElementById('mlHeaderRegime');
        if (regEl) regEl.innerText = data.current_regime;

        const confEl = document.getElementById('mlHeaderConfluence');
        if (confEl) confEl.innerText = `${data.mtf_confluence}%`;

        const stratsEl = document.getElementById('mlHeaderStrats');
        if (stratsEl) stratsEl.innerText = `${data.active_strategies_count} / ${data.total_strategies_count} Active`;

        const driftBadge = document.getElementById('mlDriftBadge');
        if (driftBadge && data.model_drift) {
          driftBadge.innerText = `DRIFT: ${data.model_drift.status} (${(data.model_drift.accuracy_drift * 100).toFixed(1)}%)`;
          if (data.model_drift.status === 'DRIFT_DETECTED') {
            driftBadge.className = 'px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30';
          } else {
            driftBadge.className = 'px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
          }
        }

        const modelVer = document.getElementById('mlOverviewModelVer');
        if (modelVer) modelVer.innerText = data.model_version;

        // Render top features
        const featsContainer = document.getElementById('mlOverviewTopFeatures');
        if (featsContainer && data.feature_importances) {
          let html = '';
          const sorted = Object.entries(data.feature_importances).slice(0, 6);
          sorted.forEach(([name, wt]) => {
            const pct = Math.min(100, Math.round(wt * 100 * 3));
            html += `
              <div class="space-y-1">
                <div class="flex justify-between text-[11px]">
                  <span class="text-slate-300">${name}</span>
                  <span class="text-purple-300 font-bold">${(wt * 100).toFixed(1)}%</span>
                </div>
                <div class="w-full bg-slate-950 rounded-full h-1.5 border border-bordercol/40">
                  <div class="bg-gradient-to-r from-purple-500 to-indigo-500 h-1.5 rounded-full" style="width: ${pct}%"></div>
                </div>
              </div>
            `;
          });
          featsContainer.innerHTML = html;
        }
      } catch (e) {
        console.error("fetchMLOverview failed:", e);
      }
    }

    async function fetchMLRecommendations() {
      const container = document.getElementById('mlRecsContainer');
      if (!container) return;
      container.innerHTML = '<div class="col-span-2 text-center py-10 text-slate-500 font-mono">Generating 24-field ML trade setups...</div>';

      try {
        const res = await fetch('/api/ml/recommendations');
        const data = await res.json();
        if (!data.success || !data.recommendations || data.recommendations.length === 0) {
          container.innerHTML = '<div class="col-span-2 text-center py-12 text-slate-400 font-mono bg-slate-900/40 rounded-2xl border border-bordercol">No trade setups currently satisfy the minimum calibrated confidence threshold (60%) and positive expected value. Risk gate: capital preserved.</div>';
          return;
        }

        mlCachedRecs = data.recommendations;
        renderMLRecommendations(mlCachedRecs);
      } catch (err) {
        container.innerHTML = `<div class="col-span-2 text-center py-10 text-rose-400 font-mono">Failed to load trade recommendations: ${err.message}</div>`;
      }
    }

    function renderMLRecommendations(recs) {
      const container = document.getElementById('mlRecsContainer');
      if (!container) return;

      let html = '';
      recs.forEach((r, idx) => {
        const isBuy = r.direction === 'BUY';
        const dirBadge = isBuy
          ? '<span class="px-2.5 py-0.5 rounded-md bg-emerald-500/20 text-emerald-400 font-black border border-emerald-500/40">BUY</span>'
          : '<span class="px-2.5 py-0.5 rounded-md bg-rose-500/20 text-rose-400 font-black border border-rose-500/40">SELL</span>';

        html += `
          <div class="rounded-2xl border border-purple-500/30 bg-surface/95 p-5 shadow-2xl relative overflow-hidden space-y-4">
            <div class="flex items-center justify-between pb-3 border-b border-bordercol/60">
              <div class="flex items-center gap-3">
                ${dirBadge}
                <div>
                  <h3 class="text-sm font-bold text-white">${r.strategy_name}</h3>
                  <div class="text-[11px] font-mono text-purple-300">${r.strategy_code} • ${r.timeframe}</div>
                </div>
              </div>
              <div class="text-right font-mono">
                <div class="text-base font-black text-purple-300">${r.win_probability_pct}</div>
                <div class="text-[10px] text-slate-400">Calibrated Win Prob</div>
              </div>
            </div>

            <!-- Key Levels Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2.5 font-mono text-xs">
              <div class="p-2.5 rounded-xl bg-slate-950/70 border border-bordercol/40">
                <div class="text-[10px] text-slate-400">ENTRY ZONE</div>
                <div class="font-bold text-white mt-0.5">${r.entry_zone}</div>
              </div>
              <div class="p-2.5 rounded-xl bg-slate-950/70 border border-bordercol/40">
                <div class="text-[10px] text-rose-400">STOP LOSS (${r.sl_points} pts)</div>
                <div class="font-bold text-rose-400 mt-0.5">$${r.stop_loss.toFixed(2)}</div>
              </div>
              <div class="p-2.5 rounded-xl bg-slate-950/70 border border-bordercol/40">
                <div class="text-[10px] text-emerald-400">TP1 / TP2 (1:2.0)</div>
                <div class="font-bold text-emerald-400 mt-0.5">$${r.tp1.toFixed(2)} / $${r.tp2.toFixed(2)}</div>
              </div>
              <div class="p-2.5 rounded-xl bg-slate-950/70 border border-bordercol/40">
                <div class="text-[10px] text-indigo-400">EXPECTED VALUE</div>
                <div class="font-bold text-indigo-300 mt-0.5">${r.expected_value_r}</div>
              </div>
            </div>

            <!-- Invalidation Condition Box -->
            <div class="p-3 rounded-xl bg-rose-950/20 border border-rose-500/30 text-xs font-mono text-slate-300 space-y-1">
              <div class="flex items-center gap-1.5 text-rose-400 font-bold">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                Technical Invalidation Rule:
              </div>
              <div class="text-rose-200">${r.invalidation_condition}</div>
            </div>

            <!-- Catalyst & Liquidity Target -->
            <div class="text-xs font-mono space-y-1 text-slate-400">
              <div><strong class="text-slate-300">Target Liquidity:</strong> ${r.liquidity_target}</div>
              <div><strong class="text-slate-300">Market Regime:</strong> ${r.market_regime} (${r.mtf_confluence})</div>
              <div><strong class="text-slate-300">Smart Chaser:</strong> Option B Recovery Active (${r.chaser_config.pullback_threshold} tolerance)</div>
            </div>

            <!-- Execution Action Bar -->
            <div class="flex items-center justify-between pt-3 border-t border-bordercol/60">
              <div class="text-xs font-mono">
                <span class="text-slate-400">Recommended Size:</span>
                <strong class="text-white ml-1">${r.recommended_lot_size} Lots</strong>
                <span class="text-slate-500 text-[11px] ml-1">($${r.risk_amount_cash.toFixed(2)} risk)</span>
              </div>
              <button onclick="executeMLTrade(${idx})" class="px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs shadow-lg transition flex items-center gap-1.5">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                1-Click Execute
              </button>
            </div>
          </div>
        `;
      });
      container.innerHTML = html;
    }

    function filterMLRecs(dir) {
      document.querySelectorAll('.ml-rec-filter').forEach(btn => {
        if (btn.innerText === dir) {
          btn.className = 'ml-rec-filter px-2.5 py-1 rounded text-xs font-bold bg-purple-600 text-white';
        } else {
          btn.className = 'ml-rec-filter px-2.5 py-1 rounded text-xs font-bold text-slate-400 hover:text-white';
        }
      });

      if (dir === 'ALL') {
        renderMLRecommendations(mlCachedRecs);
      } else {
        const filtered = mlCachedRecs.filter(r => r.direction === dir);
        renderMLRecommendations(filtered);
      }
    }

    async function executeMLTrade(index) {
      if (!mlCachedRecs || !mlCachedRecs[index]) return;
      const rec = mlCachedRecs[index];
      if (!confirm(`Confirm 1-Click execution for ${rec.direction} ${rec.recommended_lot_size} lots on XAUUSD via Smart Profit Chaser Option B?`)) {
        return;
      }

      try {
        const res = await fetch('/api/ml/recommendations/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ recommendation: rec })
        });
        const data = await res.json();
        if (data.success) {
          alert(`Order Executed Successfully! Ticket: #${data.ticket || 'Active'}\nOption B Smart Profit Chaser is now managing this trade.`);
          fetchMLRecommendations();
        } else {
          alert(`Execution Blocked by Risk Gate: ${data.message || data.error}`);
        }
      } catch (err) {
        alert(`Order execution error: ${err.message}`);
      }
    }

    async function fetchMLStrategies() {
      const container = document.getElementById('mlStrategiesGrid');
      if (!container) return;

      try {
        const res = await fetch('/api/ml/strategies');
        const data = await res.json();
        if (!data.success || !data.strategies) return;

        let html = '';
        data.strategies.forEach(s => {
          const isBuy = s.direction === 'BUY';
          const isSell = s.direction === 'SELL';
          const statusBadge = isBuy
            ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">BUY TRIGGER</span>'
            : (isSell
              ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">SELL TRIGGER</span>'
              : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">NO SIGNAL</span>');

          html += `
            <div class="rounded-2xl border border-bordercol bg-surface/90 p-5 shadow-xl space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-sm font-bold text-white">${s.name}</h3>
                  <span class="text-[11px] font-mono text-purple-400">${s.code}</span>
                </div>
                ${statusBadge}
              </div>

              <div class="p-3 rounded-xl bg-slate-950 border border-bordercol text-xs font-mono text-slate-300">
                <span class="text-slate-500 block mb-1">Trigger Logic:</span>
                ${s.trigger}
              </div>

              <div class="space-y-2 font-mono text-xs">
                <div class="flex justify-between">
                  <span class="text-slate-400">Baseline Win Rate:</span>
                  <strong class="text-slate-300">${s.baseline_win_rate}%</strong>
                </div>
                <div class="flex justify-between">
                  <span class="text-slate-400">ML-Filtered Win Rate:</span>
                  <strong class="text-purple-300">${s.ml_filtered_win_rate}% (+${(s.ml_filtered_win_rate - s.baseline_win_rate).toFixed(1)}%)</strong>
                </div>
              </div>

              <div class="pt-2 border-t border-bordercol/60 flex items-center justify-between">
                <span class="text-xs font-mono text-slate-400">Strategy Status:</span>
                <button onclick="toggleMLStrategy('${s.code_letter}', ${!s.enabled})" class="px-3 py-1 rounded-lg text-xs font-bold transition ${s.enabled ? 'bg-purple-900/30 text-purple-300 border border-purple-500/30' : 'bg-slate-800 text-slate-500'}">
                  ${s.enabled ? 'ACTIVE ✓' : 'DISABLED ✗'}
                </button>
              </div>
            </div>
          `;
        });
        container.innerHTML = html;
      } catch (err) {
        console.error("fetchMLStrategies error:", err);
      }
    }

    async function toggleMLStrategy(code, enabled) {
      try {
        await fetch('/api/ml/strategies/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ strategy_code: code, enabled: enabled })
        });
        fetchMLStrategies();
      } catch (err) {
        console.error("toggleMLStrategy error:", err);
      }
    }

    async function fetchMLMTF() {
      const tbody = document.getElementById('mlMTFTbody');
      if (!tbody) return;

      try {
        const res = await fetch('/api/ml/mtf');
        const data = await res.json();
        if (!data.success || !data.data) return;

        const mtf = data.data;
        const overallBadge = document.getElementById('mlMTFOverallBadge');
        if (overallBadge) {
          overallBadge.innerText = `${mtf.confluence_percentage}% ${mtf.dominant_bias}`;
        }
        const recTf = document.getElementById('mlMTFRecTf');
        if (recTf) {
          recTf.innerText = mtf.recommended_timeframe;
        }

        let html = '';
        Object.entries(mtf.matrix).forEach(([tf, info]) => {
          const isBull = info.trend === 'BULLISH';
          const isBear = info.trend === 'BEARISH';
          const trendClass = isBull ? 'text-emerald-400 font-bold' : (isBear ? 'text-rose-400 font-bold' : 'text-slate-400');

          html += `
            <tr class="hover:bg-slate-800/40 transition">
              <td class="py-3 px-4 font-bold text-white">${tf}</td>
              <td class="py-3 px-4 ${trendClass}">${info.trend}</td>
              <td class="py-3 px-4 text-slate-300">${info.structure}</td>
              <td class="py-3 px-4 text-purple-300">${info.rsi}</td>
              <td class="py-3 px-4 text-slate-400">${info.liquidity_state}</td>
              <td class="py-3 px-4 font-bold ${trendClass}">${info.bias}</td>
              <td class="py-3 px-4 text-right text-emerald-400">${info.status}</td>
            </tr>
          `;
        });
        tbody.innerHTML = html;
      } catch (err) {
        console.error("fetchMLMTF error:", err);
      }
    }

    async function fetchMLRegime() {
      try {
        const res = await fetch('/api/ml/regime');
        const data = await res.json();
        if (!data.success || !data.regime) return;

        const r = data.regime;
        document.getElementById('mlRegimeADX').innerText = r.adx;
        document.getElementById('mlRegimeATRPct').innerText = `${r.atr_percentile}%`;
        document.getElementById('mlRegimeVolRatio').innerText = `${r.volume_ratio}x`;
        document.getElementById('mlRegimeHurst').innerText = r.hurst_exponent;

        const tbody = document.getElementById('mlRegimeSuitabilityTbody');
        if (tbody && data.all_regimes) {
          let html = '';
          const strats = ['A', 'B', 'C', 'D', 'E', 'F', 'G'];
          data.all_regimes.forEach(regName => {
            const isCurr = regName === r.regime_name;
            const rowClass = isCurr ? 'bg-purple-950/30 border-l-4 border-purple-500' : 'hover:bg-slate-800/40';

            html += `<tr class="${rowClass}">
              <td class="py-2.5 px-3 font-bold text-white">${regName} ${isCurr ? '<span class="text-purple-400 text-[10px] ml-1">(ACTIVE)</span>' : ''}</td>`;

            strats.forEach(s => {
              const suit = (r.strategy_suitability && r.strategy_suitability[s]) || 'FAIR';
              const badgeClass = suit === 'OPTIMAL' ? 'text-emerald-400 font-bold' : (suit === 'REJECT' ? 'text-rose-400 font-bold' : (suit === 'AVOID' ? 'text-amber-400' : 'text-slate-400'));
              html += `<td class="py-2.5 px-3 text-center ${badgeClass}">${suit}</td>`;
            });
            html += `</tr>`;
          });
          tbody.innerHTML = html;
        }
      } catch (err) {
        console.error("fetchMLRegime error:", err);
      }
    }

    async function triggerMLTraining() {
      const btn = document.getElementById('btnStartMLTrain');
      if (btn) btn.disabled = true;
      const logBox = document.getElementById('mlTrainTerminalLog');
      if (logBox) logBox.innerHTML = '<div>[START] Initiating non-blocking background model training job...</div>';

      try {
        await fetch('/api/ml/train', { method: 'POST' });
        if (mlTrainPollTimer) clearInterval(mlTrainPollTimer);
        mlTrainPollTimer = setInterval(pollMLTrainStatus, 1000);
      } catch (err) {
        alert("Training error: " + err.message);
        if (btn) btn.disabled = false;
      }
    }

    async function pollMLTrainStatus() {
      try {
        const res = await fetch('/api/ml/train/status');
        const st = await res.json();

        const bar = document.getElementById('mlTrainProgressBar');
        if (bar) bar.style.width = `${st.progress}%`;

        const pill = document.getElementById('mlTrainStatusPill');
        if (pill) {
          pill.innerText = st.is_training ? `TRAINING (${st.progress}%)` : (st.progress === 100 ? 'COMPLETED' : 'IDLE');
          pill.className = st.is_training ? 'px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-500/20 text-amber-300' : 'px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-500/20 text-emerald-300';
        }

        const logBox = document.getElementById('mlTrainTerminalLog');
        if (logBox) {
          logBox.innerHTML += `<div>[${new Date().toLocaleTimeString()}] ${st.message}</div>`;
          logBox.scrollTop = logBox.scrollHeight;
        }

        if (!st.is_training && st.progress === 100) {
          clearInterval(mlTrainPollTimer);
          const btn = document.getElementById('btnStartMLTrain');
          if (btn) btn.disabled = false;
          fetchMLOverview();
          fetchMLTrainingStatus();
        }
      } catch (e) {
        console.error("pollMLTrainStatus error:", e);
      }
    }

    async function fetchMLTrainingStatus() {
      const list = document.getElementById('mlCheckpointsList');
      if (!list) return;

      try {
        const res = await fetch('/api/ml/models');
        const data = await res.json();
        if (!data.success || !data.active_model) return;

        const m = data.active_model;
        list.innerHTML = `
          <div class="p-3.5 rounded-xl bg-purple-950/20 border border-purple-500/40 space-y-2">
            <div class="flex justify-between items-center">
              <strong class="text-white">${m.version} (Active Checkpoint)</strong>
              <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">CALIBRATED</span>
            </div>
            <div class="text-[11px] text-slate-400">Algorithm: ${m.algorithm || 'LightGBM / Calibrated Ensemble'}</div>
            <div class="flex justify-between text-[11px] pt-1 border-t border-bordercol/40">
              <span class="text-slate-400">Accuracy: <strong class="text-emerald-400">${(m.accuracy * 100).toFixed(1)}%</strong></span>
              <span class="text-slate-400">Brier Score: <strong class="text-purple-300">${m.brier_score}</strong></span>
              <span class="text-slate-400">AUC: <strong class="text-cyan-400">${m.roc_auc}</strong></span>
            </div>
          </div>
        `;
      } catch (err) {
        console.error("fetchMLTrainingStatus error:", err);
      }
    }

    function updateBtSliderLabel(val) {
      const el = document.getElementById('mlBtConfLabel');
      if (el) el.innerText = val + '%';
    }

    async function runMLBacktestCustom() {
      const slider = document.getElementById('mlBtConfSlider');
      const minC = slider ? slider.value : 60;
      const btn = document.getElementById('btnRunMLBacktest');
      if (btn) btn.disabled = true;

      try {
        const res = await fetch('/api/ml/backtest/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ min_confidence: minC })
        });
        const data = await res.json();
        if (data.success && data.backtest) {
          renderBacktestTable(data.backtest);
        }
      } catch (err) {
        alert("Backtest error: " + err.message);
      } finally {
        if (btn) btn.disabled = false;
      }
    }

    async function fetchMLBacktest() {
      try {
        const res = await fetch('/api/ml/backtest');
        const data = await res.json();
        if (data.success && data.backtest) {
          renderBacktestTable(data.backtest);
        }
      } catch (err) {
        console.error("fetchMLBacktest error:", err);
      }
    }

    function renderBacktestTable(bt) {
      const tbody = document.getElementById('mlBacktestTbody');
      if (!tbody) return;

      const base = bt.baseline_strategy || {};
      const ml = bt.ml_enhanced_strategy || {};

      tbody.innerHTML = `
        <tr class="hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">Total Completed Trades</td>
          <td class="py-3 px-4 text-center text-slate-300">${base.total_trades || 0}</td>
          <td class="py-3 px-4 text-center text-purple-300 font-bold">${ml.total_trades || 0}</td>
          <td class="py-3 px-4 text-right text-slate-400">-${bt.trades_filtered_pct}% filtered (low confidence removed)</td>
        </tr>
        <tr class="hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">Win Rate %</td>
          <td class="py-3 px-4 text-center text-slate-300">${base.win_rate || 0}%</td>
          <td class="py-3 px-4 text-center text-emerald-400 font-bold">${ml.win_rate || 0}%</td>
          <td class="py-3 px-4 text-right text-emerald-400 font-bold">+${bt.win_rate_delta}% Win Rate Surge</td>
        </tr>
        <tr class="hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">Profit Factor</td>
          <td class="py-3 px-4 text-center text-slate-300">${base.profit_factor || 0}</td>
          <td class="py-3 px-4 text-center text-purple-300 font-bold">${ml.profit_factor || 0}</td>
          <td class="py-3 px-4 text-right text-purple-300 font-bold">+${bt.profit_factor_delta}</td>
        </tr>
        <tr class="hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">Net Return (R-Multiple)</td>
          <td class="py-3 px-4 text-center text-slate-300">${base.net_profit_r || 0}R</td>
          <td class="py-3 px-4 text-center text-cyan-400 font-bold">${ml.net_profit_r || 0}R</td>
          <td class="py-3 px-4 text-right text-cyan-400 font-bold">+$${(ml.net_profit_dollars || 0).toFixed(2)} Net</td>
        </tr>
        <tr class="hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">Max Drawdown %</td>
          <td class="py-3 px-4 text-center text-rose-400">${base.max_drawdown_pct || 0}%</td>
          <td class="py-3 px-4 text-center text-emerald-400 font-bold">${ml.max_drawdown_pct || 0}%</td>
          <td class="py-3 px-4 text-right text-emerald-400 font-bold">-${((base.max_drawdown_pct || 0) - (ml.max_drawdown_pct || 0)).toFixed(1)}% Drawdown Reduction</td>
        </tr>
        <tr class="hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">Sharpe Ratio</td>
          <td class="py-3 px-4 text-center text-slate-300">${base.sharpe_ratio || 0}</td>
          <td class="py-3 px-4 text-center text-purple-300 font-bold">${ml.sharpe_ratio || 0}</td>
          <td class="py-3 px-4 text-right text-purple-300 font-bold">+${((ml.sharpe_ratio || 0) - (base.sharpe_ratio || 0)).toFixed(2)}</td>
        </tr>
      `;
    }

    async function fetchMLPerformance() {
      try {
        const res = await fetch('/api/ml/performance');
        const data = await res.json();
        if (!data.success) return;

        const calibBox = document.getElementById('mlCalibrationTable');
        if (calibBox && data.metrics && data.metrics.calibration_curve) {
          let html = '<table class="w-full text-left"><thead><tr class="text-slate-500 border-b border-bordercol"><th>Decile Bin</th><th>Predicted Prob</th><th>Observed Win Rate</th><th>Samples</th></tr></thead><tbody>';
          data.metrics.calibration_curve.forEach(c => {
            html += `<tr class="border-b border-bordercol/40">
              <td class="py-1.5 text-white">Bin ${c.bin + 1}</td>
              <td class="py-1.5 text-purple-300">${(c.predicted * 100).toFixed(1)}%</td>
              <td class="py-1.5 text-emerald-400">${(c.actual * 100).toFixed(1)}%</td>
              <td class="py-1.5 text-slate-400">${c.count}</td>
            </tr>`;
          });
          html += '</tbody></table>';
          calibBox.innerHTML = html;
        }

        const driftCard = document.getElementById('mlDriftCard');
        if (driftCard && data.drift) {
          const d = data.drift;
          driftCard.innerHTML = `
            <div class="flex justify-between">
              <span class="text-slate-400">Drift Health Status:</span>
              <strong class="${d.status === 'HEALTHY' ? 'text-emerald-400' : 'text-amber-400'}">${d.status}</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Training In-Sample Accuracy:</span>
              <strong class="text-white">${(d.training_accuracy * 100).toFixed(1)}%</strong>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Recent Realized Accuracy:</span>
              <strong class="text-purple-300">${(d.recent_accuracy * 100).toFixed(1)}%</strong>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-900 border border-bordercol text-slate-300">
              ${d.message}
            </div>
          `;
        }
      } catch (err) {
        console.error("fetchMLPerformance error:", err);
      }
    }

    async function fetchMLJournal() {
      const tbody = document.getElementById('mlJournalTbody');
      const countEl = document.getElementById('mlJournalCount');
      if (!tbody) return;

      try {
        const res = await fetch('/api/ml/journal');
        const data = await res.json();
        if (!data.success || !data.journal) return;

        const preds = data.journal.predictions || [];
        if (countEl) countEl.innerText = `${preds.length} Predictions Stored`;

        if (preds.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" class="py-8 text-center text-slate-500 font-mono">No predictions logged yet. Execute recommendations to populate journal audit trail.</td></tr>';
          return;
        }

        let html = '';
        preds.slice().reverse().forEach(p => {
          html += `
            <tr class="hover:bg-slate-800/40">
              <td class="py-2.5 px-4 text-slate-400">${(p.recorded_at || '').slice(11, 19)}</td>
              <td class="py-2.5 px-4 font-bold text-white">${p.strategy_code || 'Strategy'}</td>
              <td class="py-2.5 px-4 font-bold ${p.direction === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}">${p.direction}</td>
              <td class="py-2.5 px-4 text-purple-300">${((p.win_probability || 0.6) * 100).toFixed(1)}%</td>
              <td class="py-2.5 px-4 text-slate-300">${p.expected_value_r || '+0.2R'}</td>
              <td class="py-2.5 px-4 text-slate-300">${p.outcome || p.status || 'PENDING'}</td>
              <td class="py-2.5 px-4 text-right font-bold ${p.realized_pnl > 0 ? 'text-emerald-400' : (p.realized_pnl < 0 ? 'text-rose-400' : 'text-slate-400')}">
                ${p.realized_pnl ? `$${p.realized_pnl.toFixed(2)}` : '--'}
              </td>
            </tr>
          `;
        });
        tbody.innerHTML = html;
      } catch (err) {
        console.error("fetchMLJournal error:", err);
      }
    }

    async function fetchMLRisk() {
      try {
        const res = await fetch('/api/ml/risk');
        const data = await res.json();
        if (!data.success) return;

        const openEl = document.getElementById('mlRiskOpenCount');
        if (openEl) openEl.innerText = data.open_gold_positions;

        const spreadEl = document.getElementById('mlRiskCurrSpread');
        if (spreadEl) spreadEl.innerText = `${data.current_spread_pts} pts ($${(data.current_spread_pts / 100).toFixed(2)}/oz)`;

        const statusEl = document.getElementById('mlRiskCapStatus');
        if (statusEl) {
          if (data.open_gold_positions >= data.max_allowed) {
            statusEl.innerText = 'BLOCKED (Max 1 Position Limit Active)';
            statusEl.className = 'text-rose-400 font-bold';
          } else {
            statusEl.innerText = 'PASSED (Available for 1 Trade)';
            statusEl.className = 'text-emerald-400 font-bold';
          }
        }
      } catch (err) {
        console.error("fetchMLRisk error:", err);
      }
    }

    async function fetchMLSettings() {
      try {
        const res = await fetch('/api/ml/settings');
        const data = await res.json();
        if (!data.success || !data.settings) return;

        const cfg = data.settings;
        const minConfInput = document.getElementById('cfgMinConf');
        if (minConfInput) {
          minConfInput.value = Math.round((cfg.min_confidence_threshold || 0.60) * 100);
          document.getElementById('lblCfgMinConf').innerText = minConfInput.value + '%';
        }
        const minEV = document.getElementById('cfgMinEV');
        if (minEV) minEV.value = cfg.min_expected_value_r || 0.20;

        const riskPct = document.getElementById('cfgRiskPct');
        if (riskPct) riskPct.value = cfg.max_risk_per_trade_pct || 1.0;

        const pType = document.getElementById('cfgPullbackType');
        if (pType && cfg.chaser_option_b) pType.value = cfg.chaser_option_b.pullback_type || 'PERCENTAGE';

        const pThresh = document.getElementById('cfgPullbackThresh');
        if (pThresh && cfg.chaser_option_b) pThresh.value = cfg.chaser_option_b.pullback_threshold || 20;
      } catch (err) {
        console.error("fetchMLSettings error:", err);
      }
    }

    async function saveMLSettingsFromUI() {
      const minConf = document.getElementById('cfgMinConf').value;
      const minEV = document.getElementById('cfgMinEV').value;
      const riskPct = document.getElementById('cfgRiskPct').value;
      const pType = document.getElementById('cfgPullbackType').value;
      const pThresh = document.getElementById('cfgPullbackThresh').value;

      try {
        const res = await fetch('/api/ml/settings/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            min_confidence: minConf,
            min_ev: minEV,
            risk_pct: riskPct,
            pullback_type: pType,
            pullback_thresh: pThresh
          })
        });
        const data = await res.json();
        if (data.success) {
          alert("ML & Option B Settings Saved Successfully!");
          loadMLDashboard(true);
        } else {
          alert("Failed to save settings: " + (data.error || 'Unknown error'));
        }
      } catch (err) {
        alert("Error saving settings: " + err.message);
      }
    }
