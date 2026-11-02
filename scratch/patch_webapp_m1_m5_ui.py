import re

def patch_webapp():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add lightweight-charts to <head>
    head_target = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
    head_replace = '''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>'''

    if head_target in content and 'lightweight-charts' not in content:
        content = content.replace(head_target, head_replace, 1)
        print("Patched <head> with lightweight-charts library")

    # 2. Add Live Chart & Timeframe Toggles in goldView right above Recommended Trade Setups
    chart_html_target = '      <!-- 2. Recommended Trade Setups & Technical Invalidation Notes (User Requirement #2) -->'
    chart_html_block = '''      <!-- LIVE TRADINGVIEW LIGHTWEIGHT CANDLESTICK CHART & STRATEGY OVERLAYS -->
      <section class="rounded-2xl bg-panel border border-bordercol p-5 shadow-xl space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <h3 class="text-sm font-bold text-white flex items-center gap-2">
              <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"></path></svg>
              XAUUSD Live Candlestick Chart &amp; Strategy Overlays
            </h3>
            <span id="chartLiveQuote" class="text-xs font-mono text-slate-300 bg-slate-900 border border-bordercol px-2.5 py-0.5 rounded">XAUUSD: --</span>
            <span id="chartBeBadge" class="hidden text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded-full flex items-center gap-1">🛡️ AUTO BREAK-EVEN ACTIVE (+1.0R PROTECTED)</span>
          </div>
          <!-- Timeframe Switcher: M1, M5, M15, H1, H4 -->
          <div class="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-bordercol text-xs font-mono">
            <span class="text-[10px] text-slate-500 uppercase px-1">TF:</span>
            <button id="btnTfM1" onclick="switchGoldChartTf('M1')" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">M1</button>
            <button id="btnTfM5" onclick="switchGoldChartTf('M5')" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">M5</button>
            <button id="btnTfM15" onclick="switchGoldChartTf('M15')" class="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40">M15</button>
            <button id="btnTfH1" onclick="switchGoldChartTf('H1')" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">H1</button>
            <button id="btnTfH4" onclick="switchGoldChartTf('H4')" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">H4</button>
          </div>
        </div>
        <div id="goldTradingChart" class="w-full h-[420px] rounded-xl overflow-hidden bg-slate-950 border border-slate-900 relative">
          <!-- TradingView Lightweight Chart canvas renders here -->
        </div>
      </section>

      <!-- 2. Recommended Trade Setups & Technical Invalidation Notes (User Requirement #2) -->'''

    if chart_html_target in content and 'id="goldTradingChart"' not in content:
        content = content.replace(chart_html_target, chart_html_block, 1)
        print("Inserted goldTradingChart HTML section into goldView")

    # 3. Add Timeframe Filter Pills to Recommended Trade Setups Header
    setups_header_target = '''            <h3 class="text-base font-bold text-white flex items-center gap-2">
              <svg class="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              Recommended Trade Setups &amp; Technical Invalidation Notes
            </h3>
            <p class="text-xs text-slate-400">Actionable institutional signals with explicit setup, stop-loss, and time-based invalidation boundaries.</p>
          </div>
          <span class="px-2.5 py-1 rounded-lg text-xs font-mono bg-slate-900 border border-bordercol text-slate-300">
            Min Confidence: <strong class="text-emeraldaccent">90%</strong>
          </span>'''

    setups_header_replace = '''            <h3 class="text-base font-bold text-white flex items-center gap-2">
              <svg class="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              Recommended Trade Setups &amp; Technical Invalidation Notes
            </h3>
            <p class="text-xs text-slate-400">Actionable institutional signals across M1 Scalp, M5 Momentum, M15 Intraday, and H1 Swing.</p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <!-- Timeframe Filter Buttons -->
            <div class="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-bordercol text-xs font-mono">
              <span class="text-[10px] text-slate-500 uppercase px-1.5 font-bold">Filter:</span>
              <button id="filterSetupAll" onclick="filterGoldSetups('ALL')" class="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40">All (<span id="countAllSetups">7</span>)</button>
              <button id="filterSetupM1" onclick="filterGoldSetups('M1')" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">⚡ 1M Scalp</button>
              <button id="filterSetupM5" onclick="filterGoldSetups('M5')" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">⚡ 5M Momentum</button>
              <button id="filterSetupM15" onclick="filterGoldSetups('M15')" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">M15 Intraday</button>
              <button id="filterSetupH1" onclick="filterGoldSetups('H1')" class="px-2.5 py-1 rounded text-slate-400 hover:text-white transition">H1 Swing</button>
            </div>
            <span class="px-2.5 py-1.5 rounded-lg text-xs font-mono bg-slate-900 border border-bordercol text-slate-300">
              Min Confidence: <strong class="text-emeraldaccent">90%</strong>
            </span>
          </div>'''

    if setups_header_target in content:
        content = content.replace(setups_header_target, setups_header_replace, 1)
        print("Updated Recommended Trade Setups header with timeframe filter buttons")

    # 4. Update switchGoldChartTf to handle btnTfM1
    old_switch_tf = """    async function switchGoldChartTf(tf) {
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
    }"""

    new_switch_tf = """    async function switchGoldChartTf(tf) {
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
    }"""

    if old_switch_tf in content:
        content = content.replace(old_switch_tf, new_switch_tf, 1)
        print("Updated switchGoldChartTf to include btnTfM1")

    # 5. Add filterGoldSetups & update renderGoldSetups
    old_render_setups = """    function renderGoldSetups(setups) {
      const container = document.getElementById('goldSetupsContainer');
      if (!container) return;
      if (!setups || setups.length === 0) {
        container.innerHTML = `<div class="p-6 rounded-xl bg-slate-900 border border-bordercol text-center text-slate-400 text-xs">No active Gold trade setups currently qualifying for strict 90%+ institutional criteria.</div>`;
        return;
      }

      container.innerHTML = setups.map(s => {"""

    new_render_setups = """    let cachedGoldSetups = [];
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

      container.innerHTML = filtered.map(s => {"""

    if old_render_setups in content:
        content = content.replace(old_render_setups, new_render_setups, 1)
        print("Updated renderGoldSetups to support interactive timeframe filtering")

    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: web_app.py patched completely!")
    return True

if __name__ == '__main__':
    patch_webapp()
