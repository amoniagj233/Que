
    let derivState = {};
    let allSymbols = [];
    let currentFilteredSymbols = [];
    let currentCategory = 'ALL';
    let currentDirection = 'SELL';
    let activeSymbol = 'BTCUSD';
    let currentLoadedSetupId = null;
    let localSecondsLeft = 180;
    let autoTradeEnabled = false;

    function setDirection(dir) {
      currentDirection = dir;
      const bBuy = document.getElementById('btnBuy');
      const bSell = document.getElementById('btnSell');
      const submitBtn = document.getElementById('submitBtn');

      if (dir === 'BUY') {
        bBuy.className = 'py-2.5 rounded-lg bg-emeraldaccent text-white font-bold text-xs flex items-center justify-center gap-1 transition shadow-lg shadow-emerald-500/20';
        bSell.className = 'py-2.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white font-bold text-xs flex items-center justify-center gap-1 transition';
        submitBtn.className = 'w-full py-3.5 rounded-lg bg-emeraldaccent hover:bg-emerald-600 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-emerald-600/25 flex items-center justify-center gap-2';
        submitBtn.innerText = 'Execute Instant BUY Order on Deriv MT5';
      } else {
        bSell.className = 'py-2.5 rounded-lg bg-crimsonaccent text-white font-bold text-xs flex items-center justify-center gap-1 transition shadow-lg shadow-red-500/20';
        bBuy.className = 'py-2.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white font-bold text-xs flex items-center justify-center gap-1 transition';
        submitBtn.className = 'w-full py-3.5 rounded-lg bg-crimsonaccent hover:bg-red-600 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-red-600/25 flex items-center justify-center gap-2';
        submitBtn.innerText = 'Execute Instant SELL Order on Deriv MT5';
      }
      recalcSizer();
      updateMultiOrderPreview();
    }

    function setTradeCount(n) {
      document.getElementById('tradesCount').value = n;
      updateMultiOrderPreview();
    }

    function updateMultiOrderPreview() {
      const count = parseInt(document.getElementById('tradesCount').value) || 1;
      const mode = document.getElementById('volumeMode').value;
      const vol = parseFloat(document.getElementById('tradeVolume').value) || 0.1;
      const preview = document.getElementById('multiOrderPreview');
      const submitBtn = document.getElementById('submitBtn');

      if (count <= 1) {
        preview.innerText = `Single order: Opening 1 trade of ${vol.toFixed(2)} lots.`;
        submitBtn.innerText = `Execute Instant ${currentDirection} Order on Deriv MT5`;
      } else if (mode === 'split') {
        const perTrade = (vol / count).toFixed(2);
        preview.innerText = `Split execution: Will open ${count} separate trades of ${perTrade} lots each (Total: ${vol.toFixed(2)} lots). Ideal for multi-TP scaling!`;
        submitBtn.innerText = `Execute ${count}x Split ${currentDirection} Orders on Deriv MT5`;
      } else {
        const total = (vol * count).toFixed(2);
        preview.innerText = `Stacked execution: Will open ${count} separate trades of ${vol.toFixed(2)} lots each (Total: ${total} lots).`;
        submitBtn.innerText = `Execute ${count}x Stacked ${currentDirection} Orders on Deriv MT5`;
      }
    }

    async function loadSymbolsCatalog() {
      try {
        const res = await fetch('/api/symbols');
        allSymbols = await res.json();
        currentFilteredSymbols = allSymbols;
        populateSymbolsDropdown(allSymbols);
      } catch (err) {
        console.error('Symbols load error:', err);
      }
    }

    function filterCategory(cat) {
      currentCategory = cat;
      document.querySelectorAll('.cat-pill').forEach(btn => {
        if ((cat === 'ALL' && btn.innerText.includes('All')) || btn.innerText.includes(cat.split(' ')[0])) {
          btn.className = 'cat-pill px-2.5 py-1 rounded bg-brand text-white font-medium';
        } else {
          btn.className = 'cat-pill px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white font-medium';
        }
      });

      if (cat === 'ALL') {
        currentFilteredSymbols = allSymbols;
      } else {
        currentFilteredSymbols = allSymbols.filter(s => s.category.toLowerCase().includes(cat.toLowerCase()) || s.path.toLowerCase().includes(cat.toLowerCase()));
      }
      populateSymbolsDropdown(currentFilteredSymbols);
    }

    function onSymbolSearch(query) {
      const q = query.trim().toLowerCase();
      let list = currentFilteredSymbols;
      if (q) {
        list = allSymbols.filter(s => s.symbol.toLowerCase().includes(q) || s.description.toLowerCase().includes(q));
      }
      populateSymbolsDropdown(list);
    }

    function populateSymbolsDropdown(list) {
      const select = document.getElementById('allSymbolsSelect');
      const maxShow = 200;
      const slice = list.slice(0, maxShow);
      select.innerHTML = slice.map(s => `
        <option value="${s.symbol}" ${s.symbol === activeSymbol ? 'selected' : ''}>
          ${s.symbol} &bull; ${s.description} (${s.category})
        </option>
      `).join('');
    }

    async function onSymbolDropdownSelect(sym) {
      activeSymbol = sym;
      await fetchAndApplySymbolQuote(sym);
    }

    async function fetchAndApplySymbolQuote(sym) {
      try {
        const res = await fetch(`/api/quote?symbol=${encodeURIComponent(sym)}`);
        const q = await res.json();
        if (q.success) {
          document.getElementById('curSymName').innerText = q.symbol;
          document.getElementById('curSymBid').innerText = q.bid;
          document.getElementById('curSymAsk').innerText = q.ask;
          document.getElementById('curSymSpread').innerText = q.spread;
          document.getElementById('curSymMinLot').innerText = q.min_lot;
          
          document.getElementById('tradeEntry').value = currentDirection === 'BUY' ? q.ask : q.bid;
          recalcSizer();
        }
      } catch (err) {
        console.error('Quote fetch error:', err);
      }
    }

    function selectSymbol(sym) {
      activeSymbol = sym;
      const select = document.getElementById('allSymbolsSelect');
      if (select) {
        select.value = sym;
      }
      fetchAndApplySymbolQuote(sym);
    }

    async function toggleAutoTrade() {
      try {
        const res = await fetch('/api/auto_trade_toggle', { method: 'POST' });
        const data = await res.json();
        autoTradeEnabled = data.auto_trade_enabled;
        renderAutoTradeButton(autoTradeEnabled);
        fetchSetups();
      } catch (err) {
        alert('Toggle error: ' + err);
      }
    }

    async function toggleProfitGuardian() {
      try {
        const res = await fetch('/api/profit_guardian/toggle', { method: 'POST' });
        const data = await res.json();
        renderGuardianButton(data.enabled);
      } catch (err) {
        alert('Profit Guardian error: ' + err);
      }
    }

    function renderGuardianButton(enabled) {
      const btn = document.getElementById('guardianBtn');
      if (!btn) return;
      if (enabled) {
        btn.className = 'px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1.5 bg-emerald-500/20 text-emeraldaccent border border-emerald-500/50 shadow-sm shadow-emerald-500/20';
        btn.innerHTML = '<span class="w-2 h-2 rounded-full bg-emeraldaccent animate-pulse"></span><span>ARMED (ACTIVE)</span>';
      } else {
        btn.className = 'px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1.5 bg-slate-800 text-slate-400 border border-slate-700';
        btn.innerHTML = '<span class="w-2 h-2 rounded-full bg-slate-500"></span><span>DISABLED</span>';
      }
    }

    function renderAutoTradeButton(enabled) {
      const btn = document.getElementById('autoTradeBtn');
      const dot = document.getElementById('autoTradeDot');
      const txt = document.getElementById('autoTradeText');
      if (!btn) return;

      if (enabled) {
        btn.className = 'px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1.5 bg-emerald-500/20 text-emeraldaccent border border-emerald-500/50 shadow-sm shadow-emerald-500/20';
        dot.className = 'w-2 h-2 rounded-full bg-emeraldaccent animate-pulse';
        txt.innerText = 'AUTO-TRADING ACTIVE (1 Symbol at a Time)';
      } else {
        btn.className = 'px-2.5 py-1 rounded text-[11px] font-bold transition flex items-center gap-1.5 bg-slate-800 text-slate-400 border border-slate-700';
        dot.className = 'w-2 h-2 rounded-full bg-slate-500';
        txt.innerText = 'DISABLED';
      }
    }

    /* AUTOMATED 3-MINUTE SCANNER FETCH & RENDER (Rules 1-4) */
    async function fetchSetups() {
      const grid = document.getElementById('setupsGrid');
      const badge = document.getElementById('scannerStatusBadge');
      const lastScanEl = document.getElementById('lastScanTime');

      try {
        const res = await fetch('/api/setups');
        const data = await res.json();
        
        localSecondsLeft = data.next_scan_seconds || 180;
        autoTradeEnabled = data.auto_trade_enabled || false;
        renderAutoTradeButton(autoTradeEnabled);

        if (lastScanEl) lastScanEl.innerText = data.last_scan_time || '--';
        
        renderJournal(data.journal || []);
        renderAudit(data.filtered_reasons || {});

        const setups = data.setups || [];

        // Rule 10: No Forced Recommendations
        if (setups.length === 0 || data.status === 'WAITING_FOR_CONFIRMATION') {
          if (badge) {
            badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amberaccent border border-amber-500/20 font-mono font-semibold';
            badge.innerText = 'WAITING CONFIRMATION';
          }
          grid.innerHTML = `
            <div class="col-span-full py-10 px-6 text-center bg-slate-900/60 rounded-xl border border-dashed border-bordercol space-y-3">
              <div class="w-12 h-12 mx-auto rounded-full bg-amber-500/10 text-amberaccent flex items-center justify-center font-bold text-xl">
                ⏳
              </div>
              <h3 class="text-sm font-bold text-slate-100 uppercase tracking-wider">
                No Valid Trade Setups Available – Waiting for Confirmation
              </h3>
              <p class="text-xs text-slate-400 max-w-xl mx-auto leading-relaxed">
                The automated 3-minute background scanner evaluated all candidate pairs. Active positions are already running, closed markets (forex/metals) are deactivated, or untraded pairs have not formed clean M15 trend confirmation. No low-quality signals generated.
              </p>
              <div class="flex items-center justify-center gap-3 pt-2">
                <button onclick="triggerImmediateRescan()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition border border-bordercol">
                  Force Instant Rescan
                </button>
                <button onclick="toggleAuditModal()" class="px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 text-xs font-bold transition border border-blue-500/20">
                  Inspect Filtered Reasons
                </button>
              </div>
            </div>
          `;
          return;
        }

        if (badge) {
          badge.className = 'text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20 font-mono font-semibold';
          badge.innerText = `${setups.length} ACTIVE SETUPS`;
        }

        // Render setups with Confidence and Invalidation (Rules 2, 3, 4)
        grid.innerHTML = setups.map(s => {
          const isBuy = s.action === 'BUY';
          const badgeClass = isBuy ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/20' : 'bg-red-500/10 text-crimsonaccent border-red-500/20';
          const isHighConf = s.confidence_score >= 88;
          const confBadgeClass = isHighConf ? 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 shadow-sm shadow-emerald-500/20 font-black' : 'bg-blue-500/10 text-blue-400 font-mono';

          return `
            <div id="setup-card-${s.id}" class="p-4 rounded-xl bg-slate-900 border ${isHighConf ? 'border-emerald-500/40' : 'border-bordercol'} hover:border-slate-700 transition flex flex-col justify-between space-y-3 shadow-sm">
              <div>
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-white font-mono text-sm">${s.symbol}</span>
                    <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">${s.category}</span>
                    <span class="text-[9px] px-1.5 py-0.5 rounded font-mono font-bold border ${s.is_market_open ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/30' : 'bg-amber-500/10 text-amberaccent border-amber-500/30'}">${s.is_market_open ? 'LIVE 24/7' : 'WEEKEND ANALYSIS'}</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span class="text-[10px] px-2 py-0.5 rounded font-mono font-bold border ${badgeClass}">${s.action}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded border ${confBadgeClass}">${isHighConf ? '⭐ ' : ''}${s.conviction}</span>
                  </div>
                </div>
                <div class="text-xs font-bold text-slate-200 mt-1 flex items-center justify-between">
                  <span>${s.setup_name}</span>
                  ${isHighConf ? '<span class="text-[10px] text-emeraldaccent font-mono font-bold">88-100% CONFIDENCE</span>' : ''}
                </div>
              </div>

              <!-- Symbol MT5 Performance Profile (Requirement 6) -->
              ${s.symbol_perf ? `
                <div class="p-2 rounded bg-slate-950/70 border border-slate-800 flex items-center justify-between text-[11px] font-mono">
                  <div class="flex items-center gap-1.5">
                    <span>${s.symbol_perf.priority_num === 1 ? '⭐' : (s.symbol_perf.priority_num === 2 ? '✅' : (s.symbol_perf.priority_num === 5 ? '🛑' : '🔍'))}</span>
                    <span class="px-1.5 py-0.5 rounded text-[10px] border ${
                      s.symbol_perf.priority_num === 1 ? 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 font-bold' :
                      (s.symbol_perf.priority_num === 2 ? 'bg-cyan-500/10 text-cyanaccent border-cyan-500/30 font-bold' :
                      (s.symbol_perf.priority_num === 5 ? 'bg-red-500/20 text-crimsonaccent border-red-500/40 font-bold animate-pulse' : 'bg-slate-800 text-slate-300 border-slate-700'))
                    }">${s.symbol_perf.recommendation.split('—')[0].trim()}</span>
                  </div>
                  <div class="text-[10px] text-slate-400 flex items-center gap-2">
                    <span>Win: <b class="text-white">${s.symbol_perf.win_rate}%</b></span>
                    <span>PF: <b class="text-white">${s.symbol_perf.profit_factor}</b></span>
                    <span>Net: <b class="${s.symbol_perf.net_pnl >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}">${s.symbol_perf.net_pnl >= 0 ? '+' : ''}$${s.symbol_perf.net_pnl}</b></span>
                  </div>
                </div>
                ${s.symbol_perf.priority_num === 5 ? `
                  <div class="p-2 rounded bg-red-950/40 border border-red-800/60 text-[10px] text-rose-300 font-sans flex items-start gap-1.5">
                    <span class="text-crimsonaccent font-bold">⚠️ SYMBOL RISK WARNING:</span>
                    Negative historical expectancy on Deriv MT5 (Net $${s.symbol_perf.net_pnl}, PF ${s.symbol_perf.profit_factor}). High drawdown risk.
                  </div>
                ` : ''}
              ` : ''}

              <!-- Technical Signals Box -->
              <div class="p-2.5 rounded bg-slate-950/80 border border-slate-800 text-[11px] text-slate-300 leading-relaxed font-sans">
                <span class="text-emeraldaccent font-bold">Signals:</span> ${s.technical_signals}
              </div>

              <!-- Technical Invalidation Box (Rule 4) -->
              <div class="p-2.5 rounded bg-red-950/20 border border-red-900/50 text-[11px] text-rose-300 leading-relaxed font-sans">
                <span class="text-crimsonaccent font-bold flex items-center gap-1 mb-0.5">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                  Technical Invalidation:
                </span>
                ${s.invalidation_condition}
              </div>

              <!-- Trade Parameters Grid (2 TPs Kept: TP1 & TP2) -->
              <div class="grid grid-cols-4 gap-1.5 text-[11px] font-mono bg-slate-950/50 p-2 rounded">
                <div><span class="text-slate-500 block text-[9px]">ENTRY</span><span class="text-white font-bold">${s.entry}</span></div>
                <div><span class="text-slate-500 block text-[9px]">STOP LOSS</span><span class="text-crimsonaccent font-bold">${s.sl}</span></div>
                <div><span class="text-slate-500 block text-[9px]">TP1 (1.8x)</span><span class="text-emeraldaccent font-bold">${s.tp1 || s.tp}</span></div>
                <div><span class="text-slate-500 block text-[9px]">TP2 (4.0x)</span><span class="text-cyanaccent font-bold">${s.tp2 || (s.tp * 1.01).toFixed(2)}</span></div>
              </div>

              <!-- 1 Trade Policy & Random Allocation Note -->
              <div class="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-400 flex items-center justify-between">
                <span>🎯 Policy: 1 Trade Per Symbol</span>
                <span class="text-amberaccent font-semibold">Random TP1 or TP2</span>
              </div>

              <!-- Auto-Trade Status Banner if High Confidence -->
              ${isHighConf ? `
                <div class="p-2 rounded bg-emerald-950/30 border border-emerald-900/40 text-[10px] text-emerald-300 font-mono flex items-center justify-between">
                  <span>⚡ 88-100% Setup Trigger</span>
                  <span class="font-bold">${autoTradeEnabled ? 'ARMED FOR AUTO-EXECUTE' : 'Auto-Trade is OFF'}</span>
                </div>
              ` : ''}

              <!-- Action Buttons -->
              <div class="space-y-1.5 pt-1">
                <button type="button" onclick='executeMtpDirectlyFromSetup(${JSON.stringify(s)})' class="w-full py-2 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emeraldaccent border border-emerald-500/40 font-bold text-xs transition flex items-center justify-center gap-1.5 shadow-sm">
                  ⚡ Execute 1 Trade (Random TP1/TP2)
                </button>
                <div class="grid grid-cols-3 gap-1.5">
                  <button type="button" onclick='loadSetupIntoForm(${JSON.stringify(s)})' class="py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition flex items-center justify-center gap-1 border border-bordercol">
                    Load Setup
                  </button>
                  <button type="button" onclick='executeSetupDirectly(${JSON.stringify(s)})' class="py-1.5 rounded-lg ${isBuy ? 'bg-emeraldaccent hover:bg-emerald-600' : 'bg-crimsonaccent hover:bg-red-600'} text-white font-bold text-xs transition shadow flex items-center justify-center gap-1">
                    1-Click
                  </button>
                  <button type="button" onclick='dismissSetupCard("${s.id}", "${s.symbol}", "${s.action}")' class="py-1.5 rounded-lg bg-slate-800/80 hover:bg-red-500/20 text-slate-400 hover:text-red-400 font-bold text-xs transition flex items-center justify-center gap-1 border border-bordercol" title="Dismiss / Remove this Setup">
                    ✕ Dismiss
                  </button>
                </div>
              </div>
            </div>
          `;
        }).join('');
      } catch (err) {
        console.error('Fetch setups error:', err);
      }
    }

    function renderJournal(list) {
      const tbody = document.getElementById('journalTbody');
      const countEl = document.getElementById('journalCount');
      if (!tbody) return;
      if (countEl) countEl.innerText = `${list.length} Logged`;

      if (!list || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="py-4 text-center text-slate-500 font-sans">No executed setups logged yet.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(j => {
        const isOpen = j.status === 'OPEN';
        const statusBadge = isOpen ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/20' : 'bg-slate-800 text-slate-400';
        const isAuto = j.execution_type && j.execution_type.includes('AUTO');
        const typeBadge = isAuto ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20' : 'bg-blue-500/10 text-blue-400';

        return `
          <tr class="hover:bg-slate-900/60 transition">
            <td class="py-1.5 px-2 font-bold text-white">${j.symbol}</td>
            <td class="py-1.5 px-2"><span class="px-1.5 py-0.2 rounded text-[9px] font-bold ${j.direction === 'BUY' ? 'bg-emerald-500/10 text-emeraldaccent' : 'bg-red-500/10 text-crimsonaccent'}">${j.direction}</span></td>
            <td class="py-1.5 px-2 text-slate-300">${j.volume}</td>
            <td class="py-1.5 px-2 font-bold text-white">${j.confidence || '--'}</td>
            <td class="py-1.5 px-2"><span class="px-1.5 py-0.2 rounded text-[9px] font-mono ${typeBadge}">${isAuto ? 'AUTO' : 'MANUAL'}</span></td>
            <td class="py-1.5 px-2"><span class="px-1.5 py-0.2 rounded text-[9px] font-bold border ${statusBadge}">${j.status}</span></td>
            <td class="py-1.5 px-2 text-right text-slate-500 text-[10px]">${j.execution_time.split(' ')[1] || j.execution_time}</td>
          </tr>
        `;
      }).join('');
    }

    function renderAudit(reasons) {
      const container = document.getElementById('auditContent');
      if (!container) return;
      const entries = Object.entries(reasons);
      if (entries.length === 0) {
        container.innerHTML = '<div>All candidate instruments analyzed.</div>';
        return;
      }
      container.innerHTML = entries.map(([sym, r]) => `
        <div class="p-2 rounded bg-slate-900 border border-bordercol/60 flex items-start gap-1.5">
          <span class="text-amberaccent font-bold">${sym}:</span>
          <span class="text-slate-400">${r}</span>
        </div>
      `).join('');
    }

    function toggleAuditModal() {
      const el = document.getElementById('auditSection');
      el.classList.toggle('hidden');
    }

    async function triggerImmediateRescan() {
      const btn = event?.currentTarget;
      if (btn) btn.innerText = 'Scanning...';
      try {
        await fetch('/api/rescan', { method: 'POST' });
        await fetchSetups();
      } catch (err) {
        console.error('Rescan error:', err);
      } finally {
        if (btn) btn.innerText = 'Re-Scan Now';
      }
    }

    async function dismissSetupCard(setupId, symbol, action) {
      // Smooth fade out and remove card from DOM
      const card = document.getElementById(`setup-card-${setupId}`) || document.querySelector(`[data-setup-id="${setupId}"]`);
      if (card) {
        card.style.transition = 'all 0.35s ease-out';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.95)';
        setTimeout(() => card.remove(), 350);
      }
      try {
        await fetch('/api/setups/dismiss', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ setup_id: setupId, symbol: symbol, action: action })
        });
      } catch (err) {
        console.error('Error dismissing setup:', err);
      }
    }

    function loadSetupIntoForm(s) {
      currentLoadedSetupId = s.id;
      selectSymbol(s.symbol);
      setDirection(s.action);
      document.getElementById('tradeEntry').value = s.entry;
      document.getElementById('tradeSL').value = s.sl;
      document.getElementById('tradeTP').value = s.tp;
      document.getElementById('tradeVolume').value = s.recommended_lots;
      document.getElementById('tradesCount').value = s.suggested_trades || 2;
      document.getElementById('volumeMode').value = 'split';
      updateMultiOrderPreview();
      recalcSizer();
      
      const formEl = document.getElementById('orderForm');
      formEl.scrollIntoView({ behavior: 'smooth' });
      formEl.classList.add('ring-2', 'ring-brand');
      setTimeout(() => formEl.classList.remove('ring-2', 'ring-brand'), 1500);
    }

    async function executeSetupDirectly(s) {
      if (!confirm(`Execute Recommended Setup on ${s.symbol}?\nAction: ${s.action}\nLots: ${s.recommended_lots} (Split into ${s.suggested_trades} trades)\nSL: ${s.sl} | TP: ${s.tp}\nConfidence: ${s.conviction}`)) {
        return;
      }
      
      const statusBox = document.getElementById('orderStatusMsg');
      statusBox.className = 'text-xs p-3 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20';
      statusBox.innerText = `Executing 1-Click setup on ${s.symbol} into Deriv MT5...`;
      statusBox.classList.remove('hidden');

      const payload = {
        symbol: s.symbol,
        action: s.action,
        volume: s.recommended_lots,
        sl: s.sl,
        tp: s.tp,
        trades_count: s.suggested_trades || 2,
        volume_mode: 'split',
        setup_id: s.id,
        confidence: s.conviction,
        reason: s.technical_signals,
        comment: `Headway 1-Click (${s.conviction})`
      };

      try {
        const res = await fetch('/api/order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const out = await res.json();
        if (out.success) {
          statusBox.className = 'text-xs p-3 rounded-lg bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20';
          statusBox.innerText = '✅ ' + out.message;
          dismissSetupCard(s.id, s.symbol, s.action);
          refreshAll();
        } else {
          statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
          statusBox.innerText = '❌ ' + out.message;
        }
      } catch (err) {
        statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
        statusBox.innerText = 'Error: ' + err;
      }
    }

    async function fetchProfitChaser() {
      try {
        const res = await fetch('/api/profit_chaser/dashboard');
        const data = await res.json();
        renderProfitChaserDashboard(data);
      } catch (e) {
        console.error('Profit chaser fetch error:', e);
      }
    }

    function renderProfitChaserDashboard(data) {
      const positions = data.positions || [];
      const events = data.recent_events || [];
      const config = data.config || {};

      const countEl = document.getElementById('chaserPositionsCount');
      if (countEl) countEl.innerText = `${positions.length} TRADES MONITORED`;

      const totRecoveries = positions.reduce((acc, p) => acc + (p.recovery_count || 0), 0);
      const recBadge = document.getElementById('chaserRecoveryBadge');
      if (recBadge) recBadge.innerText = `${totRecoveries} RECOVERIES COMPLETED`;

      const pbMethodEl = document.getElementById('chaserPullbackMethod');
      if (pbMethodEl) pbMethodEl.innerText = `${config.pullback_value || 25}% OF PEAK`;

      const trMethodEl = document.getElementById('chaserTrailingMethod');
      if (trMethodEl) trMethodEl.innerText = `MAX ${config.max_giveback_pct || 35}% GIVEBACK`;

      const tbody = document.getElementById('chaserPositionsBody');
      if (tbody) {
        if (positions.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" class="py-4 text-center text-slate-500">No active positions currently open in MT5. New entries are auto-registered.</td></tr>';
        } else {
          tbody.innerHTML = positions.map(p => {
            const isBuy = p.direction === 'BUY';
            const dirClass = isBuy ? 'text-emeraldaccent bg-emerald-500/10 border-emerald-500/30' : 'text-roseaccent bg-rose-500/10 border-rose-500/30';
            const profitClass = p.current_profit >= 0 ? 'text-emeraldaccent font-bold' : 'text-roseaccent font-bold';
            
            // Dynamic status badge styling
            let statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">TRACKING</span>';
            if (p.status_label === 'TRACKING NEW HIGH') {
              statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyanaccent border border-cyan-500/40 animate-pulse">✨ TRACKING NEW HIGH</span>';
            } else if (p.status_label === 'PULLBACK DETECTED') {
              statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amberaccent border border-amber-500/40 animate-pulse">⚠️ PULLBACK DETECTED</span>';
            } else if (p.status_label === 'WAITING FOR RECOVERY') {
              statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">⏳ WAITING FOR RECOVERY</span>';
            } else if (p.status_label === 'RECOVERY COMPLETED') {
              statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emeraldaccent border border-emerald-500/40 shadow-sm shadow-emerald-500/20">🌟 RECOVERY COMPLETED (Option B)</span>';
            } else if (p.status_label === 'NEW PEAK RECORDED') {
              statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 font-bold">🚀 NEW PEAK RECORDED</span>';
            } else if (p.status_label === 'PROFIT PROTECTION TRIGGERED') {
              statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-roseaccent border border-rose-500/40">🛡️ PROTECTION TRIGGERED</span>';
            }

            return `
              <tr class="border-b border-bordercol/30 hover:bg-slate-800/20 transition">
                <td class="py-2.5 px-3">
                  <div class="flex items-center gap-1.5">
                    <span class="font-bold text-white">${p.symbol}</span>
                    <span class="px-1.5 py-0.2 rounded text-[10px] border ${dirClass}">${p.direction}</span>
                    <span class="text-slate-500 text-[10px]">#${p.ticket} (${p.volume})</span>
                  </div>
                </td>
                <td class="py-2.5 px-3 ${profitClass}">$${p.current_profit.toFixed(2)}</td>
                <td class="py-2.5 px-3 text-cyanaccent font-bold">$${p.highest_profit.toFixed(2)}</td>
                <td class="py-2.5 px-3">
                  <span class="${p.current_pullback > 0 ? 'text-amberaccent' : 'text-slate-400'}">
                    -$${p.current_pullback.toFixed(2)} (${p.current_pullback_pct.toFixed(1)}%)
                  </span>
                </td>
                <td class="py-2.5 px-3 text-slate-300">
                  ${p.recovery_target > 0 ? '$' + p.recovery_target.toFixed(2) + ' (Rec: ' + p.recovery_count + ')' : '--'}
                </td>
                <td class="py-2.5 px-3 text-emeraldaccent">
                  ${p.protected_floor > 0 ? '$' + p.protected_floor.toFixed(2) : '<span class="text-slate-500">Arming at $' + (config.activation_threshold || 10) + '</span>'}
                </td>
                <td class="py-2.5 px-3">
                  ${statusBadge}
                </td>
              </tr>
            `;
          }).join('');
        }
      }

      const streamEl = document.getElementById('chaserEventStream');
      if (streamEl && events.length > 0) {
        streamEl.innerHTML = events.slice(0, 8).map(e => {
          let col = 'text-slate-300';
          if (e.event_type === 'RECOVERY_COMPLETED') col = 'text-emeraldaccent font-bold';
          else if (e.event_type === 'PULLBACK_DETECTED') col = 'text-amberaccent';
          else if (e.event_type === 'NEW_PEAK_RECORDED') col = 'text-cyanaccent font-bold';
          else if (e.event_type === 'PROTECTION_TRIGGERED') col = 'text-roseaccent font-bold';
          return `<div class="flex items-center gap-2"><span class="text-slate-500">${e.time.split(' ')[1]}</span> <span class="${col}">${e.note}</span></div>`;
        }).join('');
      }
    }

    async function fetchState() {
      fetchProfitChaser();
      try {
        const res = await fetch('/api/state');
        const data = await res.json();
        derivState = data;
        renderAccount(data.account);
        renderPositions(data.positions);
        renderQuotes(data.quotes);
        renderImm(data.imm_dates);
      } catch (err) {
        console.error('Fetch error:', err);
      }
    }

    function renderAccount(acc) {
      if (!acc) return;
      document.getElementById('headerLogin').innerText = acc.login || '6314782';
      document.getElementById('headerServer').innerText = acc.server || 'Deriv-Demo';
      document.getElementById('connPing').innerText = `PING: ${acc.ping || 160}ms`;

      document.getElementById('accBalance').innerText = `$${(acc.balance || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('accEquity').innerText = `$${(acc.equity || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('accMargin').innerText = `$${(acc.margin_free || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}`;
      document.getElementById('accMarginLevel').innerText = `Margin Level: ${(acc.margin_level || 0).toFixed(2)}%`;

      const pBox = document.getElementById('accProfit');
      const pVal = acc.profit || 0;
      pBox.innerText = `${pVal >= 0 ? '+' : ''}$${pVal.toFixed(2)}`;
      pBox.className = `text-2xl font-black font-mono ${pVal >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}`;

      const dollarRisk = (acc.balance || 7150) * 0.01;
      document.getElementById('calcRiskDollar').innerText = `$${dollarRisk.toFixed(2)}`;
    }

    function renderPositions(positions) {
      const tbody = document.getElementById('positionsTbody');
      const countBadge = document.getElementById('posCount');
      const netVolume = document.getElementById('netVolume');

      countBadge.innerText = `${positions.length} active`;
      let totalLots = 0;

      if (!positions || positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="py-6 text-center text-slate-500 font-sans">No open positions on Deriv MT5. Ready for new trades.</td></tr>';
        netVolume.innerText = '0.00';
        return;
      }

      tbody.innerHTML = '';
      positions.forEach(p => {
        totalLots += p.volume;
        const isProfit = p.profit >= 0;
        const pClass = isProfit ? 'text-emeraldaccent font-bold' : 'text-crimsonaccent font-bold';
        const typeBadge = p.type === 'BUY' ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/20' : 'bg-red-500/10 text-crimsonaccent border-red-500/20';

        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-900/60 font-mono transition';
        tr.innerHTML = `
          <td class="py-2.5 px-4 text-slate-400">#${p.ticket}</td>
          <td class="py-2.5 px-4 font-bold text-white font-sans">
            ${p.symbol}
            ${p.guardian_armed ? `<span class="ml-1 text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emeraldaccent border border-emerald-500/40 font-mono font-bold" title="Peak: +$${p.guardian_peak.toFixed(2)} | Floor: +$${p.guardian_floor.toFixed(2)}">🛡️ +$${p.guardian_floor.toFixed(2)} FLOOR</span>` : ''}
          </td>
          <td class="py-2.5 px-4"><span class="px-2 py-0.5 rounded text-[10px] font-bold border ${typeBadge}">${p.type}</span></td>
          <td class="py-2.5 px-4 font-bold text-slate-200">${p.volume}</td>
          <td class="py-2.5 px-4 text-slate-400">${p.price_open}</td>
          <td class="py-2.5 px-4 text-white">${p.price_current}</td>
          <td class="py-2.5 px-4 text-slate-400">${p.sl || '-'}</td>
          <td class="py-2.5 px-4 text-slate-400">${p.tp || '-'}</td>
          <td class="py-2.5 px-4 ${pClass}">
            ${isProfit ? '+' : ''}$${p.profit.toFixed(2)}
            ${p.guardian_armed ? `<span class="block text-[9px] text-emeraldaccent font-mono font-normal">Floor: +$${p.guardian_floor.toFixed(2)} (Peak: +$${p.guardian_peak.toFixed(2)})</span>` : ''}
          </td>
          <td class="py-2.5 px-4 text-right font-sans">
            <button onclick="closeOrder(${p.ticket})" class="px-2.5 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-crimsonaccent border border-red-500/30 text-[11px] font-medium transition">
              Close Trade
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      netVolume.innerText = totalLots.toFixed(2);
    }

    function renderQuotes(quotes) {
      const bar = document.getElementById('tickerBar');
      if (!quotes) return;

      bar.innerHTML = Object.entries(quotes).map(([sym, q]) => `
        <div onclick="selectSymbol('${sym}')" class="cursor-pointer hover:bg-slate-900 px-2 py-1 rounded border border-transparent hover:border-bordercol transition flex items-center gap-2">
          <span class="font-bold text-slate-200 font-sans">${sym}</span>
          <span class="text-slate-400">${q.bid}</span>
          <span class="text-[10px] px-1 rounded bg-slate-800 text-slate-500">Spread ${q.spread}</span>
        </div>
      `).join('<span class="text-slate-700">&bull;</span>');
    }

    function renderImm(immList) {
      const container = document.getElementById('immContainer');
      if (!immList || !container) return;
      container.innerHTML = immList.map(item => `
        <div class="p-2.5 rounded-lg bg-slate-900/90 border border-bordercol">
          <div class="flex items-center justify-between text-slate-400 text-[11px]">
            <span>${item.quarter}</span>
            <span class="text-cyanaccent">${item.days_left}d</span>
          </div>
          <div class="text-sm font-bold text-white mt-1">${item.date}</div>
        </div>
      `).join('');
    }

    function recalcSizer() {
      const balance = (derivState.account && derivState.account.balance) || 7150;
      const riskPct = parseFloat(document.getElementById('tradeRiskPct').value) || 1.0;
      const entry = parseFloat(document.getElementById('tradeEntry').value);
      const sl = parseFloat(document.getElementById('tradeSL').value);

      const dollarRisk = balance * (riskPct / 100);
      document.getElementById('calcRiskDollar').innerText = `$${dollarRisk.toFixed(2)}`;

      if (entry && sl && entry !== sl) {
        const dist = Math.abs(entry - sl);
        document.getElementById('calcStopDist').innerText = `${dist.toFixed(2)} pts`;
        
        let lots = dollarRisk / dist;
        if (lots > 10.0) lots = 10.0;
        if (lots < 0.01) lots = 0.01;
        document.getElementById('calcLots').innerText = `${lots.toFixed(2)} lots`;
        document.getElementById('tradeVolume').value = lots.toFixed(2);
        updateMultiOrderPreview();
      }
    }

    async function closeOrder(ticket) {
      if (!confirm(`Close position #${ticket} on Deriv MT5?`)) return;
      try {
        const res = await fetch('/api/close', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticket: ticket })
        });
        const out = await res.json();
        alert(out.message);
        refreshAll();
      } catch (err) {
        alert('Close error: ' + err);
      }
    }

    async function emergencyCloseAll() {
      if (!confirm('⚠️ WARNING: Close ALL open positions on Deriv MT5 immediately?')) return;
      try {
        const res = await fetch('/api/close_all', { method: 'POST' });
        const out = await res.json();
        alert(out.message);
        refreshAll();
      } catch (err) {
        alert('Panic close error: ' + err);
      }
    }

    async function submitDerivOrder(e) {
      e.preventDefault();
      const statusBox = document.getElementById('orderStatusMsg');
      statusBox.className = 'text-xs p-3 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20';
      statusBox.innerText = 'Transmitting order(s) directly to Deriv MT5 terminal...';
      statusBox.classList.remove('hidden');

      const payload = {
        symbol: activeSymbol,
        action: currentDirection,
        volume: parseFloat(document.getElementById('tradeVolume').value),
        sl: parseFloat(document.getElementById('tradeSL').value) || 0.0,
        tp: parseFloat(document.getElementById('tradeTP').value) || 0.0,
        trades_count: parseInt(document.getElementById('tradesCount').value) || 1,
        volume_mode: document.getElementById('volumeMode').value,
        setup_id: currentLoadedSetupId,
        confidence: "Manual Form",
        reason: "User Discretionary Execution",
        comment: "Headway User"
      };

      try {
        const res = await fetch('/api/order', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const out = await res.json();
        if (out.success) {
          statusBox.className = 'text-xs p-3 rounded-lg bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20';
          statusBox.innerText = '✅ ' + out.message;
          currentLoadedSetupId = null;
          refreshAll();
          fetchSetups();
        } else {
          statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
          statusBox.innerText = '❌ ' + out.message;
        }
      } catch (err) {
        statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
        statusBox.innerText = 'Error: ' + err;
      }
    }

    function refreshAll() {
      fetchState();
    }

    // 1-second countdown loop synchronized with background scanner
    function updateCountdown() {
      // Automatic 2-minute periodic rescan is permanently REMOVED as requested.
      // Re-scan is strictly manual / on demand via 'Re-Scan Now' button.
      const countdownEl = document.getElementById('rescanCountdown');
      if (countdownEl) {
        countdownEl.innerText = 'ON DEMAND (Manual)';
      }
    }

    // ==============================================================================
    // SYMBOL PERFORMANCE DASHBOARD JAVASCRIPT CONTROLLER
    // ==============================================================================
    let currentMainTab = 'station';
    let currentPerfTimeframe = 'all';
    let perfRawData = null;
    let perfDisplayedSymbols = [];
    let perfSortCol = 'score';
    let perfSortAsc = false;
    let chartPnlInstance = null;
    let chartWinRateInstance = null;
    let chartCumEquityInstance = null;

    function switchMainTab(tab) {
      currentMainTab = tab;
      const stationView = document.getElementById('stationView');
      const perfView = document.getElementById('performanceView');
      const goldView = document.getElementById('goldView');
      const mlView = document.getElementById('mlView');
      const tabStationBtn = document.getElementById('navTabStation');
      const tabPerfBtn = document.getElementById('navTabPerformance');
      const tabGoldBtn = document.getElementById('navTabGold');
      const tabMLBtn = document.getElementById('navTabML');

      // Hide all views
      if (stationView) stationView.classList.add('hidden');
      if (perfView) perfView.classList.add('hidden');
      if (goldView) goldView.classList.add('hidden');
      if (mlView) mlView.classList.add('hidden');

      // Reset button styles
      if (tabStationBtn) tabStationBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-slate-400 hover:text-white hover:bg-slate-800 flex items-center gap-2';
      if (tabPerfBtn) tabPerfBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-slate-400 hover:text-white hover:bg-slate-800 flex items-center gap-2';
      if (tabGoldBtn) tabGoldBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-amber-400 hover:text-amber-300 hover:bg-slate-800 flex items-center gap-2';
      if (tabMLBtn) tabMLBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-purple-400 hover:text-purple-300 hover:bg-slate-800 flex items-center gap-2';

      if (tab === 'station') {
        if (stationView) stationView.classList.remove('hidden');
        if (tabStationBtn) tabStationBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-brand text-white shadow flex items-center gap-2';
      } else if (tab === 'performance') {
        if (perfView) perfView.classList.remove('hidden');
        if (tabPerfBtn) tabPerfBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-brand text-white shadow flex items-center gap-2';
        loadPerformanceDashboard();
      } else if (tab === 'gold') {
        if (goldView) goldView.classList.remove('hidden');
        if (tabGoldBtn) tabGoldBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-amber-500 text-slate-950 shadow flex items-center gap-2 font-black';
        loadGoldDashboard();
      } else if (tab === 'ml') {
        if (mlView) mlView.classList.remove('hidden');
        if (tabMLBtn) tabMLBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition bg-purple-600 text-white shadow flex items-center gap-2 font-black';
        loadMLDashboard();
      }
    }

    function setPerfTimeframe(tf) {
      currentPerfTimeframe = tf;
      document.querySelectorAll('.perf-tf-btn').forEach(btn => {
        if (btn.getAttribute('data-tf') === tf) {
          btn.className = 'perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold bg-brand text-white shadow';
        } else {
          btn.className = 'perf-tf-btn px-2.5 py-1 rounded text-[11px] font-bold text-slate-400 hover:text-white';
        }
      });
      loadPerformanceDashboard(true);
    }

    async function loadPerformanceDashboard(force=false) {
      const syncEl = document.getElementById('perfSyncTime');
      const syncIcon = document.getElementById('perfSyncIcon');
      if (syncIcon) syncIcon.classList.add('animate-spin');

      try {
        const res = await fetch(`/api/performance?timeframe=${currentPerfTimeframe}&resync=${force ? '1' : '0'}`);
        perfRawData = await res.json();
        
        if (syncEl && perfRawData.summary) {
          syncEl.innerText = `${perfRawData.summary.timestamp} (${currentPerfTimeframe.toUpperCase()})`;
        }

        const topBadge = document.getElementById('p1TopBadge');
        if (topBadge && perfRawData.summary) {
          topBadge.innerText = `${perfRawData.summary.p1_count} Focus / Best: ${perfRawData.summary.best_symbol}`;
        }

        renderPerformanceSummary(perfRawData.summary);
        renderPerformanceAlerts(perfRawData.alerts || []);
        renderPriorityBuckets(
          perfRawData.p1_symbols || [],
          perfRawData.p2_symbols || [],
          perfRawData.p3_symbols || [],
          perfRawData.p4_symbols || [],
          perfRawData.p5_symbols || []
        );
        renderPerformanceCharts(perfRawData.symbols || []);
        applyPerfFilters();

      } catch (err) {
        console.error('Error loading performance dashboard:', err);
      } finally {
        if (syncIcon) syncIcon.classList.remove('animate-spin');
      }
    }

    function renderPerformanceSummary(s) {
      if (!s) return;
      document.getElementById('perfKpiTrades').innerText = (s.total_deals_analyzed || 0).toLocaleString();
      document.getElementById('perfKpiSymbolsTraded').innerText = `Across ${s.total_symbols_traded || 0} traded symbols`;

      const pnlEl = document.getElementById('perfKpiNetPnl');
      const pnl = s.total_net_pnl || 0;
      pnlEl.innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      pnlEl.className = `text-2xl font-black font-mono ${pnl >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}`;

      document.getElementById('perfKpiWinRate').innerText = `${s.overall_win_rate || 0}%`;
      const grossWins = s.total_gross_profit || 0;
      const grossLoss = s.total_gross_loss || 0;
      document.getElementById('perfKpiWinLoss').innerText = `Gross: +$${grossWins.toFixed(0)} / -$${grossLoss.toFixed(0)}`;

      document.getElementById('perfKpiPf').innerText = `${s.overall_profit_factor || 0}`;

      const bestEl = document.getElementById('perfKpiBestSymbol');
      bestEl.innerText = s.best_symbol || 'None';
      document.getElementById('perfKpiBestDetails').innerText = `${s.p1_count || 0} Priority 1 symbols`;

      // Live open floating
      let totalOpenPnl = 0;
      let totalOpenCount = 0;
      if (derivState && derivState.positions) {
        totalOpenCount = derivState.positions.length;
        totalOpenPnl = derivState.positions.reduce((acc, p) => acc + (p.profit || 0), 0);
      }
      const openPnlEl = document.getElementById('perfKpiOpenPnl');
      openPnlEl.innerText = `${totalOpenPnl >= 0 ? '+' : ''}$${totalOpenPnl.toFixed(2)}`;
      openPnlEl.className = `text-2xl font-black font-mono ${totalOpenPnl >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}`;
      document.getElementById('perfKpiOpenCount').innerText = `${totalOpenCount} Active Open Trades`;
    }

    function renderPerformanceAlerts(alerts) {
      const container = document.getElementById('perfAlertsContainer');
      if (!container) return;
      if (!alerts || alerts.length === 0) {
        container.innerHTML = '';
        return;
      }

      container.innerHTML = alerts.map(a => {
        let borderClass = 'border-slate-800 bg-slate-900/90 text-slate-300';
        let icon = 'ℹ️';
        if (a.type === 'success') {
          borderClass = 'border-emerald-500/40 bg-emerald-950/25 text-emerald-200';
          icon = '🏆';
        } else if (a.type === 'warning') {
          borderClass = 'border-amber-500/40 bg-amber-950/25 text-amber-200';
          icon = '⚠️';
        } else if (a.type === 'danger') {
          borderClass = 'border-rose-500/40 bg-rose-950/25 text-rose-200';
          icon = '🛑';
        }
        return `
          <div class="p-3 rounded-xl border ${borderClass} shadow-sm flex items-start gap-3">
            <span class="text-lg leading-none mt-0.5">${icon}</span>
            <div class="text-xs leading-relaxed font-sans">
              <strong class="font-bold text-white block">${a.title}</strong>
              <span class="text-slate-300">${a.message}</span>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderPriorityBuckets(p1, p2, p3, p4, p5) {
      const grid = document.getElementById('priorityBucketsGrid');
      if (!grid) return;

      const makeCard = (title, badgeClass, borderClass, bgClass, desc, items, priorityNum) => `
        <div class="p-4 rounded-xl border ${borderClass} ${bgClass} flex flex-col justify-between space-y-3 shadow-sm">
          <div>
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded border ${badgeClass}">${title}</span>
              <span class="text-xs font-mono font-bold text-white">${items.length} Symbols</span>
            </div>
            <p class="text-[11px] text-slate-400 mt-2 font-sans">${desc}</p>
          </div>
          <div class="space-y-1.5 custom-scroll max-h-56 overflow-y-auto pr-1">
            ${items.length === 0 ? '<div class="text-[11px] text-slate-500 italic py-2">No symbols in this category.</div>' : items.map(s => `
              <div onclick="jumpToTradeSymbol('${s.symbol}')" class="p-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-bordercol cursor-pointer transition flex items-center justify-between text-xs font-mono group">
                <div>
                  <span class="font-bold text-white font-sans group-hover:text-cyanaccent">${s.symbol}</span>
                  <div class="text-[10px] text-slate-400">
                    <span>${s.total_trades}T</span> &bull; 
                    <span class="${s.win_rate >= 50 ? 'text-emeraldaccent' : 'text-slate-400'}">${s.win_rate}% Win</span>
                  </div>
                </div>
                <div class="text-right">
                  <span class="font-bold block ${s.net_pnl >= 0 ? 'text-emeraldaccent' : 'text-crimsonaccent'}">${s.net_pnl >= 0 ? '+' : ''}$${s.net_pnl.toFixed(1)}</span>
                  <span class="text-[10px] text-slate-500">PF ${s.profit_factor}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;

      grid.innerHTML = `
        ${makeCard('PRIORITY 1 — FOCUS', 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40', 'border-emerald-500/40', 'bg-emerald-950/10', 'Strong consistent positive expectancy (N ≥ 10 validated). Highest research & trading priority.', p1, 1)}
        ${makeCard('PRIORITY 2 — MAINTAIN', 'bg-cyan-500/10 text-cyanaccent border-cyan-500/30', 'border-cyan-500/30', 'bg-cyan-950/10', 'Profitable with acceptable risk profile. Maintain trading exposure.', p2, 2)}
        ${makeCard('PRIORITY 3 — MONITOR', 'bg-amber-500/10 text-amberaccent border-amber-500/20', 'border-bordercol', 'bg-panel', 'Promising performance but insufficient sample size (N < 5). Monitor for confirmation.', p3, 3)}
        ${makeCard('PRIORITY 4 — REDUCE', 'bg-orange-500/10 text-orange-400 border-orange-500/20', 'border-bordercol', 'bg-panel', 'Weak or deteriorating expectancy. Reduce position sizing or tighten setups.', p4, 4)}
        ${makeCard('PRIORITY 5 — AVOID', 'bg-red-500/20 text-crimsonaccent border-red-500/40', 'border-red-500/40', 'bg-red-950/10', 'Severe historical negative expectancy or devastating drawdown. Restrict exposure.', p5, 5)}
      `;
    }

    function renderPerformanceCharts(symbols) {
      if (!symbols || symbols.length === 0 || !window.Chart) return;

      const topSyms = symbols.slice(0, 10);
      const labels = topSyms.map(s => s.symbol);
      const pnlValues = topSyms.map(s => s.net_pnl);
      const pnlColors = pnlValues.map(v => v >= 0 ? 'rgba(0, 192, 135, 0.8)' : 'rgba(255, 68, 79, 0.8)');

      // Chart 1: PnL
      const ctxPnl = document.getElementById('chartPnlBySymbol');
      if (ctxPnl) {
        if (chartPnlInstance) chartPnlInstance.destroy();
        chartPnlInstance = new Chart(ctxPnl, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [{
              label: 'Net Realized P&L ($)',
              data: pnlValues,
              backgroundColor: pnlColors,
              borderRadius: 4
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
              y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: '#1E2638' } }
            }
          }
        });
      }

      // Chart 2: Win Rate % & Profit Factor
      const ctxWr = document.getElementById('chartWinRatePf');
      if (ctxWr) {
        if (chartWinRateInstance) chartWinRateInstance.destroy();
        chartWinRateInstance = new Chart(ctxWr, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [
              {
                label: 'Win Rate (%)',
                data: topSyms.map(s => s.win_rate),
                backgroundColor: 'rgba(6, 182, 212, 0.7)',
                borderRadius: 4,
                yAxisID: 'y'
              },
              {
                label: 'Profit Factor',
                data: topSyms.map(s => Math.min(s.profit_factor, 10.0)),
                backgroundColor: 'rgba(245, 158, 11, 0.7)',
                borderRadius: 4,
                yAxisID: 'y1'
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
              y: { type: 'linear', position: 'left', ticks: { color: '#06B6D4' }, grid: { color: '#1E2638' }, max: 100 },
              y1: { type: 'linear', position: 'right', ticks: { color: '#F59E0B' }, grid: { display: false }, min: 0 }
            },
            plugins: { legend: { labels: { color: '#e2e8f0', font: { size: 10 } } } }
          }
        });
      }

      // Chart 3: Top Symbols Cumulative Curves
      const ctxEq = document.getElementById('chartCumEquity');
      if (ctxEq) {
        if (chartCumEquityInstance) chartCumEquityInstance.destroy();
        const curveSymbols = symbols.filter(s => s.total_trades >= 5).slice(0, 4);
        const palette = ['#00C087', '#06B6D4', '#F59E0B', '#FF444F'];
        const datasets = curveSymbols.map((s, idx) => {
          const pts = (s.cum_curve || []).map(p => p.cum_pnl);
          return {
            label: s.symbol,
            data: pts,
            borderColor: palette[idx % palette.length],
            backgroundColor: 'transparent',
            tension: 0.25,
            borderWidth: 2,
            pointRadius: 1
          };
        });

        const maxLen = Math.max(...curveSymbols.map(s => (s.cum_curve || []).length), 10);
        const labelsX = Array.from({length: maxLen}, (_, i) => `T-${maxLen - i}`);

        chartCumEquityInstance = new Chart(ctxEq, {
          type: 'line',
          data: {
            labels: labelsX,
            datasets: datasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { display: false } },
              y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: '#1E2638' } }
            },
            plugins: { legend: { labels: { color: '#e2e8f0', font: { size: 10 } } } }
          }
        });
      }
    }

    function applyPerfFilters() {
      if (!perfRawData || !perfRawData.symbols) return;
      const relVal = document.getElementById('filterReliabilitySelect').value;
      const prioVal = document.getElementById('filterPrioritySelect').value;
      const searchVal = (document.getElementById('perfSearchInput').value || '').trim().toUpperCase();

      perfDisplayedSymbols = perfRawData.symbols.filter(s => {
        if (relVal === 'STAT' && s.reliability !== 'STATISTICALLY_VALID') return false;
        if (relVal === 'MOD' && s.total_trades < 5) return false;
        if (prioVal !== 'ALL' && s.priority_num.toString() !== prioVal) return false;
        if (searchVal && !s.symbol.toUpperCase().includes(searchVal)) return false;
        return true;
      });

      // Sort
      perfDisplayedSymbols.sort((a, b) => {
        let vA = a[perfSortCol];
        let vB = b[perfSortCol];
        if (typeof vA === 'string') {
          return perfSortAsc ? vA.localeCompare(vB) : vB.localeCompare(vA);
        }
        return perfSortAsc ? (vA - vB) : (vB - vA);
      });

      renderPerformanceTable(perfDisplayedSymbols);
    }

    function sortPerfTable(col) {
      if (perfSortCol === col) {
        perfSortAsc = !perfSortAsc;
      } else {
        perfSortCol = col;
        perfSortAsc = false;
      }
      applyPerfFilters();
    }

    function renderPerformanceTable(symbols) {
      const tbody = document.getElementById('perfTableTbody');
      if (!tbody) return;

      if (!symbols || symbols.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="py-6 text-center text-slate-500 font-sans">No symbols match the selected filters.</td></tr>';
        return;
      }

      tbody.innerHTML = symbols.map(s => {
        let pBadgeClass = 'bg-slate-800 text-slate-300 border-slate-700';
        let pIcon = '🔍';
        if (s.priority_num === 1) {
          pBadgeClass = 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 font-bold';
          pIcon = '⭐';
        } else if (s.priority_num === 2) {
          pBadgeClass = 'bg-cyan-500/10 text-cyanaccent border-cyan-500/30 font-bold';
          pIcon = '✅';
        } else if (s.priority_num === 3) {
          pBadgeClass = 'bg-amber-500/10 text-amberaccent border-amber-500/20';
          pIcon = '👀';
        } else if (s.priority_num === 4) {
          pBadgeClass = 'bg-orange-500/10 text-orange-400 border-orange-500/20';
          pIcon = '⚠️';
        } else if (s.priority_num === 5) {
          pBadgeClass = 'bg-red-500/20 text-crimsonaccent border-red-500/40 font-bold';
          pIcon = '🛑';
        }

        const isProfit = s.net_pnl >= 0;
        const pnlClass = isProfit ? 'text-emeraldaccent font-bold' : 'text-crimsonaccent font-bold';

        return `
          <tr class="hover:bg-slate-900/60 font-mono transition">
            <td class="py-2.5 px-3 text-slate-500">#${s.rank}</td>
            <td class="py-2.5 px-3">
              <span onclick="jumpToTradeSymbol('${s.symbol}')" class="font-bold text-white font-sans hover:text-cyanaccent cursor-pointer transition flex items-center gap-1.5">
                ${s.symbol}
                ${s.open_positions > 0 ? `<span class="px-1.5 py-0.2 rounded-full bg-blue-500/20 text-cyanaccent text-[9px] font-mono">${s.open_positions} open</span>` : ''}
              </span>
            </td>
            <td class="py-2.5 px-3">
              <span class="px-2 py-0.5 rounded text-[10px] border ${pBadgeClass}">
                ${pIcon} ${s.recommendation}
              </span>
            </td>
            <td class="py-2.5 px-3">
              <span class="px-2 py-0.5 rounded text-[10px] border ${s.stat_badge}">${s.stat_label}</span>
            </td>
            <td class="py-2.5 px-3">
              <div class="flex items-center gap-2">
                <div class="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-cyanaccent h-1.5 rounded-full" style="width: ${s.win_rate}%"></div>
                </div>
                <span class="font-bold text-white">${s.win_rate}%</span>
                <span class="text-[10px] text-slate-500">(${s.winning_trades}W/${s.losing_trades}L)</span>
              </div>
            </td>
            <td class="py-2.5 px-3 ${pnlClass}">
              ${isProfit ? '+' : ''}$${s.net_pnl.toFixed(2)}
            </td>
            <td class="py-2.5 px-3 font-bold ${s.profit_factor >= 1.3 ? 'text-emeraldaccent' : (s.profit_factor >= 1.0 ? 'text-slate-200' : 'text-crimsonaccent')}">
              ${s.profit_factor}
            </td>
            <td class="py-2.5 px-3 ${s.avg_profit_per_trade >= 0 ? 'text-slate-300' : 'text-crimsonaccent'}">
              ${s.avg_profit_per_trade >= 0 ? '+' : ''}$${s.avg_profit_per_trade}
            </td>
            <td class="py-2.5 px-3 text-slate-400">
              ${s.rr_performance}:1
            </td>
            <td class="py-2.5 px-3 text-crimsonaccent">
              ${s.max_drawdown > 0 ? `-$${s.max_drawdown}` : '$0.00'}
            </td>
            <td class="py-2.5 px-3">
              <div class="flex items-center gap-1.5">
                <span class="font-black text-white text-xs">${s.score}</span>
                <div class="w-8 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div class="bg-emeraldaccent h-1.5 rounded-full" style="width: ${s.score}%"></div>
                </div>
              </div>
            </td>
            <td class="py-2.5 px-3 text-right font-sans">
              <button onclick="jumpToTradeSymbol('${s.symbol}')" class="px-2.5 py-1 rounded bg-brand/10 hover:bg-brand text-brand hover:text-white border border-brand/30 text-[11px] font-bold transition">
                Trade Symbol &rarr;
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    function jumpToTradeSymbol(sym) {
      switchMainTab('station');
      selectSymbol(sym);
      const formEl = document.getElementById('orderForm');
      if (formEl) {
        formEl.scrollIntoView({ behavior: 'smooth' });
        formEl.classList.add('ring-2', 'ring-brand');
        setTimeout(() => formEl.classList.remove('ring-2', 'ring-brand'), 1500);
      }
    }

    function jumpToTradeSymbol(sym) {
      switchMainTab('station');
      selectSymbol(sym);
      const formEl = document.getElementById('orderForm');
      if (formEl) {
        formEl.scrollIntoView({ behavior: 'smooth' });
        formEl.classList.add('ring-2', 'ring-brand');
        setTimeout(() => formEl.classList.remove('ring-2', 'ring-brand'), 1500);
      }
    }

    // ==============================================================================
    // 5-TRADE MULTI-TP SYSTEM JAVASCRIPT CONTROLLER (Requirements 1 - 8)
    // ==============================================================================
    let multiTpGroups = [];

    function updateMtpRiskPreview() {
      const refInput = document.getElementById('mtpRefBalanceInput');
      const badge = document.getElementById('mtpRiskDollarBadge');
      const ref = parseFloat(refInput ? refInput.value : 1000) || 1000;
      const risk = (ref * 0.05).toFixed(2);
      const riskPerTrade = (risk / 3.0).toFixed(2);
      if (badge) {
        badge.innerText = `5.0% ($${risk} max, $${riskPerTrade}/pos)`;
      }

      // Update Order Ticket preview cards
      const t1 = document.getElementById('otMtpT1Target');
      const t2 = document.getElementById('otMtpT2Target');
      const t3 = document.getElementById('otMtpT3Target');
      const otRisk = document.getElementById('otMtpRiskBadge');
      if (t1) t1.innerText = `+$${(ref * 0.02).toFixed(2)} Target`;
      if (t2) t2.innerText = `+$${(ref * 0.05).toFixed(2)} Target`;
      if (t3) t3.innerText = `+$${(ref * 0.15).toFixed(2)}+ Runner`;
      if (otRisk) otRisk.innerText = `Risk: $${risk} Max ($${riskPerTrade}/pos)`;
    }

    function useLiveBalanceForMtp() {
      const balance = (derivState && derivState.account && derivState.account.balance) || 1000;
      const refInput = document.getElementById('mtpRefBalanceInput');
      if (refInput) {
        refInput.value = balance.toFixed(2);
        updateMtpRiskPreview();
      }
    }

    async function fetchMultiTpGroups() {
      try {
        const res = await fetch('/api/multi_tp/groups');
        multiTpGroups = await res.json();
        renderMultiTpGroups(multiTpGroups);
      } catch (err) {
        console.error('Error fetching multi-tp groups:', err);
      }
    }

    function renderMultiTpGroups(groups) {
      const container = document.getElementById('mtpGroupsContainer');
      const badge = document.getElementById('mtpGroupsBadge');
      if (!container) return;

      const activeGroups = (groups || []).filter(g => g.status === 'ACTIVE');
      if (badge) {
        badge.innerText = `${activeGroups.length} ACTIVE / ${(groups || []).length} TOTAL`;
        badge.className = `text-xs px-2.5 py-0.5 rounded-full font-mono font-semibold border ${activeGroups.length > 0 ? 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40' : 'bg-slate-800 text-slate-400 border-slate-700'}`;
      }

      if (!groups || groups.length === 0) {
        container.innerHTML = `
          <div class="py-8 px-4 text-center bg-slate-900/40 rounded-xl border border-dashed border-bordercol space-y-2">
            <span class="text-2xl block">⚡</span>
            <div class="text-xs font-bold text-slate-200 uppercase tracking-wider">No Active Multi-TP Trade Groups</div>
            <p class="text-[11px] text-slate-400 max-w-md mx-auto">
              Execute a 3-Trade Multi-TP opportunity from the Order Ticket or Active Setups cards. Each opportunity opens 2 separate positions: Trade 1 (Fixed Target 1.8x range / Quick Bank) and Trade 2 (AI Dynamic Runner 4.0x range with infinite upside) with a shared Stop Loss, staying well within the 15-position account limit.
            </p>
          </div>
        `;
        return;
      }

      container.innerHTML = groups.map(g => {
        const isBuy = g.action === 'BUY';
        const badgeClass = isBuy ? 'bg-emerald-500/10 text-emeraldaccent border-emerald-500/20' : 'bg-red-500/10 text-crimsonaccent border-red-500/20';
        const isActive = g.status === 'ACTIVE';
        const totalPnl = g.total_profit || 0;
        const pnlClass = totalPnl >= 0 ? 'text-emeraldaccent font-bold' : 'text-crimsonaccent font-bold';

        return `
          <div class="p-4 rounded-xl bg-slate-900/90 border ${isActive ? 'border-emerald-500/30 shadow-md shadow-emerald-500/5' : 'border-bordercol'} space-y-3.5 transition">
            
            <!-- Group Header -->
            <div class="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-bordercol/80">
              <div class="flex items-center gap-3">
                <span class="px-2 py-0.5 rounded text-xs font-mono font-bold border ${badgeClass}">${g.action}</span>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-white text-sm font-sans">${g.symbol}</span>
                    <span class="text-[10px] px-2 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">ID: ${g.group_id}</span>
                  </div>
                  <div class="text-[11px] text-slate-400 font-mono mt-0.5">
                    Entry: <b class="text-slate-200">${g.entry_price}</b> &bull; Shared SL: <b class="text-crimsonaccent">${g.shared_sl}</b> (Planned Risk: $${g.total_risk_dollar} / ${g.total_risk_pct}%)
                  </div>
                </div>
              </div>

              <!-- Realized & Floating Group PnL Summary -->
              <div class="flex items-center gap-4">
                <div class="text-right font-mono">
                  <div class="text-[10px] text-slate-500">GROUP TOTAL P&L</div>
                  <div class="text-base font-black ${pnlClass}">${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}</div>
                  <div class="text-[10px] text-slate-400">Realized: $${g.realized_profit} | Floating: $${g.floating_profit}</div>
                </div>

                <div class="flex items-center gap-2">
                  <span class="text-[10px] px-2 py-1 rounded font-mono font-bold border ${isActive ? 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 animate-pulse' : 'bg-slate-800 text-slate-400 border-slate-700'}">
                    ${g.status}
                  </span>
                  ${isActive ? `
                    <button onclick="closeMtpGroup('${g.group_id}')" class="px-2.5 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-crimsonaccent border border-red-500/30 text-xs font-bold transition">
                      Close Group
                    </button>
                  ` : ''}
                </div>
              </div>
            </div>

            <!-- Individual Positions Grid (Dynamic 3-Column Power Layout) -->
            <div class="grid grid-cols-1 ${(g.positions && g.positions.length <= 3) ? 'md:grid-cols-3' : 'md:grid-cols-5'} gap-3 text-xs font-mono">
              ${(g.positions || []).map(p => {
                const isPosActive = p.status === 'ACTIVE';
                const posPnl = isPosActive ? (p.floating_profit || 0) : (p.realized_profit || 0);
                const posPnlClass = posPnl >= 0 ? 'text-emeraldaccent font-bold' : 'text-crimsonaccent font-bold';
                let statusBadge = 'bg-slate-800 text-slate-400 border-slate-700';
                if (isPosActive) {
                  statusBadge = 'bg-blue-500/10 text-cyanaccent border-blue-500/30';
                } else if (p.status.includes('TP REACHED')) {
                  statusBadge = 'bg-emerald-500/20 text-emeraldaccent border-emerald-500/40 font-bold';
                } else if (p.status.includes('STOP LOSS')) {
                  statusBadge = 'bg-red-500/20 text-crimsonaccent border-red-500/40 font-bold';
                }

                return `
                  <div class="p-2.5 rounded-lg bg-slate-950/70 border ${isPosActive ? 'border-bordercol' : 'border-slate-800/60 opacity-90'} space-y-2 flex flex-col justify-between">
                    <div>
                      <div class="flex items-center justify-between pb-1.5 border-b border-slate-800/80">
                        <span class="font-bold text-white text-[11px]">${p.name}</span>
                        <span class="text-[9px] text-slate-500">#${p.ticket}</span>
                      </div>
                      <div class="space-y-1 text-[10px] mt-1.5">
                        <div class="flex justify-between"><span class="text-slate-500">Target Dollar:</span><span class="text-emeraldaccent font-bold">+$${p.target_dollar} (${p.target_pct})</span></div>
                        <div class="flex justify-between"><span class="text-slate-500">TP Price:</span><span class="text-white font-bold">${p.tp}</span></div>
                        <div class="flex justify-between"><span class="text-slate-500">Shared SL:</span><span class="text-crimsonaccent">${p.sl} (-$${p.planned_risk_dollar})</span></div>
                        <div class="flex justify-between"><span class="text-slate-500">Volume:</span><span class="text-slate-300">${p.lot} lots</span></div>
                      </div>
                    </div>

                    <div class="pt-1.5 border-t border-slate-800/80 flex items-center justify-between">
                      <div>
                        <span class="text-[9px] text-slate-500 block leading-none">${isPosActive ? 'FLOATING' : 'REALIZED'}</span>
                        <span class="${posPnlClass} text-xs">${posPnl >= 0 ? '+' : ''}$${posPnl.toFixed(2)}</span>
                      </div>
                      ${isPosActive ? `
                        <button onclick="closeMtpTrade(${p.ticket})" class="px-2 py-0.5 rounded bg-red-500/10 hover:bg-red-500/20 text-crimsonaccent border border-red-500/20 text-[10px] transition">
                          Close
                        </button>
                      ` : `
                        <span class="px-1.5 py-0.5 rounded text-[9px] border ${statusBadge}">${p.status.split('(')[0].trim()}</span>
                      `}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>

            <!-- Notes -->
            ${g.ai_notes ? `
              <div class="text-[10px] text-slate-400 font-sans px-1 flex items-center gap-1.5">
                <span class="text-cyanaccent font-bold">System Strategy:</span> ${g.ai_notes}
              </div>
            ` : ''}

          </div>
        `;
      }).join('');
    }

    async function executeMtpFromCurrentForm() {
      const sym = activeSymbol;
      const action = currentDirection;
      const refInput = document.getElementById('mtpRefBalanceInput');
      const refBalance = parseFloat(refInput ? refInput.value : 1000) || 1000;
      const lotInput = document.getElementById('tradeVolume');
      const lotPerTrade = parseFloat(lotInput ? lotInput.value : 0.01) || 0.01;

      const riskDollar = (refBalance * 0.05).toFixed(2);
      const riskPerTrade = (refBalance * 0.01).toFixed(2);

      if (!confirm(`Execute 2-Trade Multi-TP Power System on ${sym} (${action})?\n\n` +
                   `• 3 Separate Positions: ${(lotPerTrade * 3).toFixed(2)} total lots (${lotPerTrade} lots each)\n` +
                   `• Shared Stop Loss: 5% maximum planned risk ($${riskDollar} total, $${(riskDollar/3).toFixed(2)} per position)\n` +
                   `• Trade 1: TP 2% (+$${(refBalance*0.02).toFixed(0)} Target) - High hit rate, banks quick profit\n` +
                   `• Trade 2: TP 5% (+$${(refBalance*0.05).toFixed(0)} Target) - Core trend move capture\n` +
                   `• Trade 3: Dynamic AI Runner (Infinite Upside / Trailing Stop)\n\n` +
                   `Transmit all 3 orders directly to Deriv MT5 terminal?`)) {
        return;
      }

      const statusBox = document.getElementById('orderStatusMsg');
      statusBox.className = 'text-xs p-3 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20';
      statusBox.innerText = `Transmitting 2-Trade Multi-TP group on ${sym} to Deriv MT5...`;
      statusBox.classList.remove('hidden');

      try {
        const res = await fetch('/api/multi_tp/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol: sym,
            action: action,
            ref_balance: refBalance,
            lot_per_trade: lotPerTrade,
            ai_notes: `Manual Execution via Form (${sym} ${action})`
          })
        });
        const out = await res.json();
        if (out.success) {
          statusBox.className = 'text-xs p-3 rounded-lg bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20';
          statusBox.innerText = `✅ ${out.message}`;
          fetchMultiTpGroups();
          refreshAll();
        } else {
          statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
          statusBox.innerText = `❌ ${out.message}`;
        }
      } catch (err) {
        statusBox.className = 'text-xs p-3 rounded-lg bg-red-500/10 text-crimsonaccent border border-red-500/20';
        statusBox.innerText = 'Multi-TP execution error: ' + err;
      }
    }

    async function executeMtpDirectlyFromSetup(s) {
      const sym = s.symbol;
      const action = s.action;
      const refInput = document.getElementById('mtpRefBalanceInput');
      const refBalance = parseFloat(refInput ? refInput.value : 1000) || 1000;
      const riskDollar = (refBalance * 0.05).toFixed(2);

      if (!confirm(`Execute 1-Trade Setup on ${sym} (${action})?\n\n` +
                   `• Symbol: ${sym} (${action})\n` +
                   `• Policy: Exactly 1 Trade Per Symbol\n` +
                   `• Dual-TP Options: TP1 (${s.tp1 || s.tp}) or TP2 (${s.tp2 || s.tp}) - randomly allocated\n` +
                   `• Risk Stop Loss: ${s.sl}\n` +
                   `• Confidence Score: ${s.conviction}\n\n` +
                   `Proceed with execution on Headway MT5?`)) {
        return;
      }

      try {
        const res = await fetch('/api/multi_tp/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol: sym,
            action: action,
            ref_balance: refBalance,
            lot_per_trade: 0.01,
            ai_notes: `Setup: ${s.setup_name} (${s.conviction}) - ${s.technical_signals}`
          })
        });
        const out = await res.json();
        alert(out.message);
        // Immediately remove taken setup card from Recommended Setups
        dismissSetupCard(s.id, s.symbol, s.action);
        fetchMultiTpGroups();
        refreshAll();
      } catch (err) {
        alert('Multi-TP execution error: ' + err);
      }
    }

    async function closeMtpGroup(gid) {
      if (!confirm(`Close all remaining active positions in Multi-TP Group ${gid}?`)) return;
      try {
        const res = await fetch('/api/multi_tp/close_group', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ group_id: gid })
        });
        const out = await res.json();
        alert(out.message);
        fetchMultiTpGroups();
        refreshAll();
      } catch (err) {
        alert('Close group error: ' + err);
      }
    }

    async function closeMtpTrade(ticket) {
      if (!confirm(`Close position #${ticket} on Deriv MT5?`)) return;
      try {
        const res = await fetch('/api/multi_tp/close_trade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticket: ticket })
        });
        const out = await res.json();
        alert(out.message);
        fetchMultiTpGroups();
        refreshAll();
      } catch (err) {
        alert('Close trade error: ' + err);
      }
    }

    // ==============================================================================
    // GOLD TRADING INTELLIGENCE CONTROLLER
    // ==============================================================================
    let goldBacktestData = null;

    // --------------------------------------------------------------------------
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
      ['btnTfM1', 'btnTfM5', 'btnTfM15', 'btnTfH1', 'btnTfH4'].forEach(id => {
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
      }
      const syncIcon = document.getElementById('goldSyncIcon');
      if (syncIcon) syncIcon.classList.add('animate-spin');

      try {
        // 0. Fetch Auto-Trade Status
        const autoRes = await fetch('/api/gold/auto_trade/status');
        if (autoRes.ok) {
          const autoSt = await autoRes.json();
          renderGoldAutoStatus(autoSt);
        }

        // 1. Fetch Overview
        const overviewRes = await fetch('/api/gold/overview');
        if (overviewRes.ok) {
          const ov = await overviewRes.json();
          renderGoldOverview(ov);
        }

        // 2. Fetch Setups
        const setupsRes = await fetch('/api/gold/setups');
        if (setupsRes.ok) {
          const setups = await setupsRes.json();
          renderGoldSetups(setups);
        }

        // 3. Fetch Multi-Timeframe Matrix
        const matrixRes = await fetch('/api/gold/matrix');
        if (matrixRes.ok) {
          const matrix = await matrixRes.json();
          renderGoldMtfMatrix(matrix);
        }

        // 4. Fetch Backtest Results
        const btRes = await fetch('/api/gold/backtest/results');
        if (btRes.ok) {
          goldBacktestData = await btRes.json();
          renderGoldBacktest(goldBacktestData);
        }

        // 5. Fetch Macro Events
        const macroRes = await fetch('/api/gold/macro');
        if (macroRes.ok) {
          const events = await macroRes.json();
          renderGoldMacroEvents(events);
        }
      } catch (err) {
        console.error('Error loading Gold dashboard:', err);
      } finally {
        if (syncIcon) syncIcon.classList.remove('animate-spin');
      }
    }

    function renderGoldAutoStatus(st) {
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
      }

      const logContainer = document.getElementById('goldAuditLogContainer');
      if (logContainer && st.recent_logs) {
        if (st.recent_logs.length === 0) {
          logContainer.innerHTML = `<div class="p-4 text-center text-slate-500">No autonomous activity recorded yet. Engine initialized and standing by.</div>`;
        } else {
          logContainer.innerHTML = st.recent_logs.map(log => {
            const isFilled = log.status === 'FILLED';
            const isErr = log.status === 'ERROR';
            const statusColor = isFilled ? 'text-emeraldaccent' : (isErr ? 'text-rose-400' : 'text-blue-400');
            return `
              <div class="p-2.5 px-4 flex items-center justify-between gap-4 hover:bg-slate-900/60 transition">
                <div class="flex items-center gap-3">
                  <span class="w-2 h-2 rounded-full ${isFilled ? 'bg-emeraldaccent' : (isErr ? 'bg-rose-500' : 'bg-blue-400')}"></span>
                  <span class="text-slate-400 font-mono text-[11px]">${log.time || '--'}</span>
                  <span class="font-bold ${statusColor} text-[11px]">[${log.type || 'INFO'}]</span>
                  <span class="text-slate-200">${log.message || ''}</span>
                </div>
                ${log.ticket ? `<span class="px-2 py-0.5 rounded bg-slate-900 border border-bordercol text-[10px] text-amber-300 font-bold">Ticket #${log.ticket}</span>` : ''}
              </div>
            `;
          }).join('');
        }
      }
    }

    async function toggleGoldAutoTrade() {
      try {
        const res = await fetch('/api/gold/auto_trade/toggle', { method: 'POST' });
        const out = await res.json();
        loadGoldDashboard();
      } catch (err) {
        alert('Toggle error: ' + err);
      }
    }

    async function updateGoldAutoSettings() {
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
    }

    // --------------------------------------------------------------------------
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

      const confirmMsg = `⚡ CONFIRM TWIN TRADE EXECUTION ON GOLD (XAUUSD)?\n\n` +
                         `• Direction: ${action}\n` +
                         `• Timeframe: ${currentManualTradeTf}\n` +
                         `• Volume: ${lotVal} lot per leg (Total: ${(lotVal * 2).toFixed(2)} lots)\n` +
                         `• Trade 1: Hard Fixed Take Profit (TP1 ${tp1 || '~1.5R'})\n` +
                         `• Trade 2: Dynamic Trailing Take Profit (Runner)\n` +
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
    async function executeGoldSetupNow(direction, entry, sl, tp, confidence, strategy, timeframe='M1') {
      const lotVal = parseFloat(document.getElementById('goldLotSelect') ? document.getElementById('goldLotSelect').value : 0.01);
      const confirmMsg = `⚡ EXECUTE TWIN TRADES ON GOLD (${strategy})?\n\n` +
                         `• Direction: ${direction} (${lotVal} lot x 2)\n` +
                         `• Entry Zone: ~${entry}\n` +
                         `• Trade 1: Fixed Target TP1 @ ${tp}\n` +
                         `• Trade 2: Dynamic Trailing Stop Runner\n` +
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
    }

    function renderGoldOverview(ov) {
      const bidAskEl = document.getElementById('goldBidAsk');
      if (bidAskEl) bidAskEl.innerText = `${ov.bid} / ${ov.ask}`;
      const spreadEl = document.getElementById('goldSpreadDisplay');
      if (spreadEl) spreadEl.innerText = `$${ov.spread_usd.toFixed(2)} (${ov.spread_points} pts)`;
      const regimeTextEl = document.getElementById('goldRegimeText');
      if (regimeTextEl) regimeTextEl.innerText = ov.regime.replace(/_/g, ' ');
      const atrEl = document.getElementById('goldAtrDisplay');
      if (atrEl) atrEl.innerText = `$${ov.atr_14.toFixed(2)}`;
      const rsiEl = document.getElementById('goldRsiDisplay');
      if (rsiEl) rsiEl.innerText = ov.rsi_14.toFixed(1);
      const asianRangeEl = document.getElementById('goldAsianRange');
      if (asianRangeEl) asianRangeEl.innerText = `$${ov.asian_low} - $${ov.asian_high}`;
      const asianStatusEl = document.getElementById('goldAsianStatus');
      if (asianStatusEl) asianStatusEl.innerText = ov.asian_status.replace(/_/g, ' ');

      const badge = document.getElementById('goldRegimeBadge');
      if (badge) {
        if (ov.bias === 'BULLISH') {
          badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-500/20 text-emeraldaccent border border-emerald-500/30';
          badge.innerText = 'BULLISH BIAS';
        } else if (ov.bias === 'BEARISH') {
          badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-rose-500/20 text-rose-400 border border-rose-500/30';
          badge.innerText = 'BEARISH BIAS';
        } else {
          badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30';
          badge.innerText = 'NEUTRAL / RANGE';
        }
      }
    }

    let cachedGoldSetups = [];
    let currentGoldSetupFilter = 'ALL';

    function filterGoldSetups(tfFilter) {
      currentGoldSetupFilter = tfFilter;
      ['filterSetupAll', 'filterSetupM1', 'filterSetupM5', 'filterSetupM15', 'filterSetupH1'].forEach(id => {
        const b = document.getElementById(id);
        if (b) b.className = 'px-2.5 py-1 rounded text-slate-400 hover:text-white transition';
      });
      const activeId = tfFilter === 'ALL' ? 'filterSetupAll' : ('filterSetup' + tfFilter);
      const activeBtn = document.getElementById(activeId);
      if (activeBtn) {
        activeBtn.className = 'px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40';
      }
      renderGoldSetupsList();
    }

    function renderGoldSetups(setups) {
      cachedGoldSetups = setups || [];
      const countEl = document.getElementById('countAllSetups');
      if (countEl) countEl.innerText = cachedGoldSetups.length;
      renderGoldSetupsList();
    }

    function renderGoldSetupsList() {
      const container = document.getElementById('goldSetupsContainer');
      if (!container) return;

      let filtered = cachedGoldSetups;
      if (currentGoldSetupFilter === 'M1') {
        filtered = cachedGoldSetups.filter(s => s.timeframe === 'M1');
      } else if (currentGoldSetupFilter === 'M5') {
        filtered = cachedGoldSetups.filter(s => s.timeframe === 'M5');
      } else if (currentGoldSetupFilter === 'M15') {
        filtered = cachedGoldSetups.filter(s => s.timeframe.includes('M15'));
      } else if (currentGoldSetupFilter === 'H1') {
        filtered = cachedGoldSetups.filter(s => s.timeframe.includes('H1'));
      }

      if (!filtered || filtered.length === 0) {
        container.innerHTML = `<div class="p-6 rounded-xl bg-slate-900 border border-bordercol text-center text-slate-400 text-xs">No trade setups found for filter '${currentGoldSetupFilter}'.</div>`;
        return;
      }

      container.innerHTML = filtered.map(s => {
        const isBuy = s.direction === 'BUY';
        const isSell = s.direction === 'SELL';
        const badgeBg = isBuy ? 'bg-emerald-500 text-slate-950' : (isSell ? 'bg-rose-600 text-white' : 'bg-slate-700 text-slate-300');

        return `
          <div class="rounded-2xl bg-panel border ${isBuy ? 'border-emerald-500/30' : (isSell ? 'border-rose-500/30' : 'border-bordercol')} p-6 shadow-xl space-y-4">
            <div class="flex flex-wrap items-center justify-between gap-3 border-b border-bordercol/80 pb-4">
              <div class="flex items-center gap-3">
                <span class="px-3 py-1 rounded-lg text-xs font-black font-mono tracking-wider ${badgeBg}">
                  ${s.direction}
                </span>
                <div>
                  <h4 class="text-base font-bold text-white flex items-center gap-2">
                    ${s.strategy}
                    <span class="text-xs font-mono font-normal text-slate-400">(${s.methodology})</span>
                  </h4>
                  <span class="text-xs text-slate-400 font-mono">Timeframe: <strong class="text-slate-200">${s.timeframe}</strong> &bull; R:R: <strong class="text-amber-400">${s.rr_ratio}</strong></span>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <div class="text-right">
                  <span class="text-[10px] uppercase tracking-wider text-slate-400 font-bold block">Validated Confidence</span>
                  <span class="text-sm font-mono font-black text-emeraldaccent">${s.confidence_score}%</span>
                </div>
                ${s.direction !== 'NO TRADE' ? `
                  <button onclick="executeGoldSetupNow('${s.direction}', ${s.entry}, ${s.sl}, ${s.tp1}, ${s.confidence_score}, '${(s.strategy||'').replace(/'/g, "\\'")}', '${s.timeframe}')" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black transition shadow-lg shadow-amber-500/20 flex items-center gap-1.5">
                    ⚡ Execute Twin Trade (Fixed + Trailing)
                  </button>
                ` : ''}
              </div>
            </div>

            <!-- Price Level Grid -->
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div class="p-3 rounded-xl bg-slate-950/70 border border-bordercol">
                <span class="text-[10px] text-slate-400 font-mono uppercase block">Entry Zone</span>
                <span class="text-xs font-mono font-bold text-white">${s.entry_zone || s.entry}</span>
              </div>
              <div class="p-3 rounded-xl bg-slate-950/70 border border-rose-500/20">
                <span class="text-[10px] text-rose-400 font-mono uppercase block">Stop Loss (SL)</span>
                <span class="text-xs font-mono font-bold text-rose-300">${s.sl}</span>
              </div>
              <div class="p-3 rounded-xl bg-slate-950/70 border border-emerald-500/20">
                <span class="text-[10px] text-emeraldaccent font-mono uppercase block">Take Profit 1</span>
                <span class="text-xs font-mono font-bold text-emeraldaccent">${s.tp1}</span>
              </div>
              <div class="p-3 rounded-xl bg-slate-950/70 border border-emerald-500/20">
                <span class="text-[10px] text-emeraldaccent font-mono uppercase block">Take Profit 2</span>
                <span class="text-xs font-mono font-bold text-emeraldaccent">${s.tp2}</span>
              </div>
              <div class="p-3 rounded-xl bg-slate-950/70 border border-emerald-500/20">
                <span class="text-[10px] text-emeraldaccent font-mono uppercase block">Take Profit 3</span>
                <span class="text-xs font-mono font-bold text-emeraldaccent">${s.tp3}</span>
              </div>
            </div>

            <!-- Technical Invalidation Box (Requirement 2C) -->
            <div class="p-4 rounded-xl bg-slate-950 border border-rose-500/30 space-y-2">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-rose-500"></span>
                <h5 class="text-xs font-bold uppercase tracking-wider text-rose-400 font-mono">Technical Invalidation Notes</h5>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div class="p-2.5 rounded-lg bg-slate-900 border border-bordercol/80">
                  <span class="text-[10px] text-slate-400 font-bold block mb-1">🚫 SETUP INVALIDATION</span>
                  <p class="text-slate-300">${s.invalidation ? s.invalidation.setup_invalidation : '--'}</p>
                </div>
                <div class="p-2.5 rounded-lg bg-slate-900 border border-bordercol/80">
                  <span class="text-[10px] text-rose-400 font-bold block mb-1">🛑 STOP-LOSS INVALIDATION</span>
                  <p class="text-slate-300">${s.invalidation ? s.invalidation.stop_loss_invalidation : '--'}</p>
                </div>
                <div class="p-2.5 rounded-lg bg-slate-900 border border-bordercol/80">
                  <span class="text-[10px] text-amber-400 font-bold block mb-1">⏳ TIME-BASED INVALIDATION</span>
                  <p class="text-slate-300">${s.invalidation ? s.invalidation.time_invalidation : '--'}</p>
                </div>
              </div>
            </div>

            <!-- Supporting Indicators & Rationale -->
            <div class="p-3 rounded-xl bg-slate-950/40 border border-bordercol/60 text-xs text-slate-300 space-y-1.5">
              <span class="text-[10px] uppercase font-bold text-slate-400 font-mono block">Institutional Thesis & Confluence</span>
              <p class="text-slate-300">${s.rationale}</p>
              ${s.supporting_signals && s.supporting_signals.length > 0 ? `
                <div class="flex flex-wrap gap-2 pt-1">
                  ${s.supporting_signals.map(sig => `<span class="px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-bordercol text-[10px] font-mono">&bull; ${sig}</span>`).join('')}
                </div>
              ` : ''}
            </div>
          </div>
        `;
      }).join('');
    }

    function renderGoldMtfMatrix(matrix) {
      const grid = document.getElementById('goldMtfGrid');
      const scoreEl = document.getElementById('goldMtfScore');
      if (!matrix || !matrix.timeframes || !grid) return;

      if (scoreEl) {
        scoreEl.innerText = `${matrix.composite_score}% (${matrix.overall_bias})`;
        if (matrix.overall_bias === 'BULLISH') {
          scoreEl.className = 'px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/20 text-emeraldaccent border border-emerald-500/30';
        } else if (matrix.overall_bias === 'BEARISH') {
          scoreEl.className = 'px-3 py-1 rounded-full text-xs font-mono font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30';
        } else {
          scoreEl.className = 'px-3 py-1 rounded-full text-xs font-mono font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30';
        }
      }

      const tfs = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'];
      grid.innerHTML = tfs.map(tf => {
        const item = matrix.timeframes[tf] || { trend: 'NEUTRAL', rsi: 50.0, atr: 0.0, structure: 'Neutral' };
        const isBull = item.trend === 'BULLISH';
        const isBear = item.trend === 'BEARISH';
        const badgeColor = isBull ? 'text-emeraldaccent bg-emerald-500/10 border-emerald-500/30' : (isBear ? 'text-rose-400 bg-rose-500/10 border-rose-500/30' : 'text-slate-400 bg-slate-800 border-bordercol');

        return `
          <div class="p-3.5 rounded-xl bg-slate-950/70 border border-bordercol space-y-2 text-center">
            <span class="text-xs font-black font-mono text-white block">${tf}</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono border block ${badgeColor}">
              ${item.trend}
            </span>
            <div class="text-[10px] font-mono text-slate-400 space-y-0.5 pt-1">
              <div>RSI: <strong class="text-slate-200">${item.rsi || 50}</strong></div>
              <div>ATR: <strong class="text-slate-200">$${item.atr ? item.atr.toFixed(1) : '--'}</strong></div>
              <div class="truncate text-[9px] text-slate-500">${item.structure || '--'}</div>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderGoldBacktest(data) {
      if (!data || !data.leaderboard) return;
      const tbody = document.getElementById('goldLeaderboardTbody');
      if (!tbody) return;
      tbody.innerHTML = data.leaderboard.map((item, idx) => {
        const isPositive = item.net_profit >= 0;
        return `
          <tr class="hover:bg-slate-900/60 font-mono transition">
            <td class="py-3 px-4 font-bold text-white flex items-center gap-2">
              <span class="w-5 h-5 rounded-full ${idx === 0 ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400'} flex items-center justify-center text-[10px] font-black">${idx + 1}</span>
              ${item.name}
            </td>
            <td class="py-3 px-4 font-bold ${item.win_rate >= 50 ? 'text-emeraldaccent' : 'text-slate-300'}">${item.win_rate.toFixed(1)}%</td>
            <td class="py-3 px-4 font-bold ${item.profit_factor >= 1.0 ? 'text-emeraldaccent' : 'text-slate-400'}">${item.profit_factor.toFixed(2)}</td>
            <td class="py-3 px-4 font-bold ${isPositive ? 'text-emeraldaccent' : 'text-rose-400'}">${isPositive ? '+' : ''}$${item.net_profit.toFixed(2)}</td>
            <td class="py-3 px-4 text-rose-400">${item.max_drawdown_pct.toFixed(1)}%</td>
            <td class="py-3 px-4 text-slate-300">${item.total_trades}</td>
            <td class="py-3 px-4 text-slate-300">$${item.expectancy.toFixed(2)}</td>
            <td class="py-3 px-4 text-slate-300">${item.recovery_factor.toFixed(2)}</td>
            <td class="py-3 px-4 text-right">
              <button onclick="selectGoldStrategyCurve('${item.strategy}')" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-bold transition border border-bordercol">
                View Curve
              </button>
            </td>
          </tr>
        `;
      }).join('');

      const best = data.best_strategy || (data.leaderboard[0] ? data.leaderboard[0].strategy : null);
      if (best) {
        selectGoldStrategyCurve(best);
      }
    }

    function selectGoldStrategyCurve(strategyKey) {
      if (!goldBacktestData || !goldBacktestData.strategies || !goldBacktestData.strategies[strategyKey]) return;
      const strat = goldBacktestData.strategies[strategyKey];
      const titleEl = document.getElementById('goldEquityCurveTitle');
      if (titleEl) titleEl.innerText = `${strat.strategy_name.toUpperCase()} — EQUITY CURVE (5,000 BARS)`;
      renderGoldEquitySvg(strat.equity_curve || []);
    }

    function renderGoldEquitySvg(curve) {
      const container = document.getElementById('goldEquitySvgContainer');
      if (!container) return;
      if (!curve || curve.length < 2) {
        container.innerHTML = `<span class="text-xs text-slate-500 font-mono">No curve points available</span>`;
        return;
      }

      const balances = curve.map(p => p.balance);
      const minB = Math.min(...balances);
      const maxB = Math.max(...balances);
      const range = (maxB - minB) || 1.0;

      const w = 800;
      const h = 160;
      const pad = 15;

      const pts = curve.map((p, idx) => {
        const x = pad + (idx / (curve.length - 1)) * (w - 2 * pad);
        const y = h - pad - ((p.balance - minB) / range) * (h - 2 * pad);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      });

      const pathStr = `M ${pts.join(' L ')}`;
      const fillStr = `M ${pts[0]} L ${pts.join(' L ')} L ${w - pad},${h - pad} L ${pad},${h - pad} Z`;
      const isProfitable = balances[balances.length - 1] >= balances[0];
      const strokeColor = isProfitable ? '#10b981' : '#f43f5e';

      container.innerHTML = `
        <svg viewBox="0 0 ${w} ${h}" class="w-full h-full overflow-visible">
          <defs>
            <linearGradient id="curveGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.25"/>
              <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          <path d="${fillStr}" fill="url(#curveGrad)"/>
          <path d="${pathStr}" fill="none" stroke="${strokeColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          <text x="${pad}" y="${h - 2}" fill="#64748b" font-size="10" font-family="monospace">Start: $${balances[0].toFixed(2)}</text>
          <text x="${w - pad}" y="${h - 2}" text-anchor="end" fill="${strokeColor}" font-size="10" font-family="monospace" font-weight="bold">End: $${balances[balances.length - 1].toFixed(2)}</text>
        </svg>
      `;
    }

    async function triggerGoldBacktest() {
      const btn = document.getElementById('btnRunGoldBacktest');
      const spinner = document.getElementById('backtestSpinner');
      if (btn) btn.disabled = true;
      if (spinner) spinner.classList.remove('hidden');

      try {
        const res = await fetch('/api/gold/backtest/run', { method: 'POST' });
        if (res.ok) {
          goldBacktestData = await res.json();
          renderGoldBacktest(goldBacktestData);
          alert('Gold historical backtest completed across 5,000 real M15 bars!');
        } else {
          alert('Failed to execute backtest');
        }
      } catch (err) {
        alert('Backtest error: ' + err);
      } finally {
        if (btn) btn.disabled = false;
        if (spinner) spinner.classList.add('hidden');
      }
    }

    function renderGoldMacroEvents(events) {
      const container = document.getElementById('goldMacroEventsContainer');
      if (!container || !events || events.length === 0) return;

      container.innerHTML = events.map(ev => {
        const isCritical = ev.impact === 'CRITICAL';
        return `
          <div class="p-4 rounded-xl bg-slate-950 border ${isCritical ? 'border-rose-500/40' : 'border-amber-500/30'} space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-white">${ev.event}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold ${isCritical ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'}">
                ${ev.impact} IMPACT
              </span>
            </div>
            <div class="text-[11px] font-mono text-slate-400">Scheduled: <strong class="text-slate-200">${ev.time_utc}</strong> &bull; Currency: <strong class="text-amber-400">${ev.currency}</strong></div>
            <p class="text-xs text-slate-300">${ev.historical_impact}</p>
            <div class="p-2 rounded bg-slate-900 border border-bordercol text-[11px] text-amber-300 font-mono">
              <strong>Rule:</strong> ${ev.rule}
            </div>
          </div>
        `;
      }).join('');
    }

    function executeGoldSetup(action, entry, sl, tp) {
      switchMainTab('station');
      fetchAndApplySymbolQuote('XAUUSD');
      const actionInput = document.getElementById('orderAction');
      const slInput = document.getElementById('orderSl');
      const tpInput = document.getElementById('orderTp');
      if (actionInput) actionInput.value = action;
      if (slInput) slInput.value = sl;
      if (tpInput) tpInput.value = tp;
      alert(`Pre-filled order form with Gold ${action} setup at ${entry} (SL: ${sl}, TP: ${tp})`);
    }

    loadSymbolsCatalog();
    fetchAndApplySymbolQuote('BTCUSD');
    fetchSetups();
    loadPerformanceDashboard();
    fetchMultiTpGroups();
    refreshAll();
    
    // Intervals
    setInterval(fetchState, 2000);
    setInterval(updateCountdown, 1000);
    setInterval(fetchSetups, 15000);
    setInterval(fetchMultiTpGroups, 3000);
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


    setInterval(() => { if (currentMainTab === 'gold') loadGoldDashboard(); }, 5000);
    setInterval(() => { if (currentMainTab === 'ml') loadMLDashboard(); }, 5000);
  