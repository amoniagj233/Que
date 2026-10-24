"""
integrate_profit_chaser.py
==========================
Integrates smart_profit_chaser into web_app.py:
1. Instantiates SmartProfitChaser.
2. Connects live position polling and update loop.
3. Adds /api/profit_chaser/dashboard and /api/profit_chaser/config endpoints.
4. Adds the sleek Option-B Profit Chasing & Recovery Dashboard into HTML/JS.
"""

from pathlib import Path

app_path = Path("web_app.py")
text = app_path.read_text(encoding="utf-8")

# 1. Add import for SmartProfitChaser
import_marker = "import MetaTrader5 as mt5"
chaser_import = """import MetaTrader5 as mt5
from smart_profit_chaser import (
    SmartProfitChaser, ProfitChaserConfig, ProfitMode, PullbackMethod, TrailingMethod, PositionState
)"""

if "from smart_profit_chaser import" not in text:
    assert import_marker in text, "mt5 import not found"
    text = text.replace(import_marker, chaser_import, 1)

# 2. Add global profit_chaser instance
global_marker = "guardian = None"
global_chaser = """guardian = None
profit_chaser = SmartProfitChaser()"""

if "profit_chaser = SmartProfitChaser()" not in text:
    assert global_marker in text, "guardian = None not found"
    text = text.replace(global_marker, global_chaser, 1)

# 3. Connect live position updates in ProfitGuardian.check_positions
loop_marker = "            active_tickets = {p.ticket for p in positions}"
chaser_tick_code = """            active_tickets = {p.ticket for p in positions}
            if profit_chaser and profit_chaser.config.enabled:
                profit_chaser.sync_with_live_mt5_positions(list(active_tickets))
                for p in positions:
                    profit_chaser.register_position(
                        ticket=p.ticket,
                        symbol=p.symbol,
                        direction="BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                        volume=p.volume,
                        entry_price=p.price_open,
                        entry_equity=float(acc.equity if acc else 1000.0),
                        position_margin=float(getattr(p, "margin", 0.0) or 100.0),
                        point_size=0.01
                    )
                    profit_chaser.update_position(
                        ticket=p.ticket,
                        current_profit_currency=float(p.profit + p.swap),
                        current_price=float(p.price_current)
                    )"""

if "profit_chaser.sync_with_live_mt5_positions" not in text:
    assert loop_marker in text, "active_tickets loop marker not found"
    text = text.replace(loop_marker, chaser_tick_code, 1)

# 4. Add API routes in DerivServer.do_GET
get_marker = '        elif url.path == "/api/backtest/results":'
chaser_get_route = '''        elif url.path == "/api/profit_chaser/dashboard":
            data = profit_chaser.get_dashboard_data() if profit_chaser else {"positions": [], "recent_events": []}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif url.path == "/api/backtest/results":'''

if "/api/profit_chaser/dashboard" not in text:
    assert get_marker in text, "backtest results route marker not found"
    text = text.replace(get_marker, chaser_get_route, 1)

# 5. Add API route in DerivServer.do_POST
post_marker = '        elif url.path == "/api/profit_guardian/config":'
chaser_post_route = '''        elif url.path == "/api/profit_chaser/config":
            if profit_chaser:
                for k, v in data.items():
                    if hasattr(profit_chaser.config, k):
                        setattr(profit_chaser.config, k, v)
                profit_chaser.save_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "config": profit_chaser.get_dashboard_data()["config"] if profit_chaser else {}}).encode("utf-8"))
        elif url.path == "/api/profit_guardian/config":'''

if "/api/profit_chaser/config" not in text:
    assert post_marker in text, "guardian config post route marker not found"
    text = text.replace(post_marker, chaser_post_route, 1)

# 6. Add HTML Dashboard Section
html_section_marker = '    <!-- SECTION: MULTI-TP TRADE MANAGER'
chaser_dashboard_html = '''    <!-- ============================================================================== -->
    <!-- SECTION: SMART DYNAMIC PROFIT CHASING, PULLBACK & RECOVERY STATION (OPTION B)     -->
    <!-- ============================================================================== -->
    <section class="bg-panel border border-bordercol rounded-xl p-5 shadow-sm space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3 pb-3.5 border-b border-bordercol">
        <div>
          <div class="flex items-center gap-2.5">
            <h2 class="text-sm font-bold text-white flex items-center gap-2 font-sans">
              <svg class="w-4 h-4 text-cyanaccent" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
              Smart Dynamic Profit Chasing, Pullback & Recovery Engine (Option B)
            </h2>
            <span id="chaserPositionsCount" class="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyanaccent border border-cyan-500/20 font-mono font-semibold">0 TRADES MONITORED</span>
            <span id="chaserRecoveryBadge" class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emeraldaccent border border-emerald-500/20 font-mono font-semibold">0 RECOVERIES BANKED</span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5">Continuous peak profit tracking with Option-B pullback recovery. Never caps winners prematurely; ratchets trailing floor up.</p>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div class="px-3 py-1.5 rounded-lg bg-slate-900 border border-bordercol flex items-center gap-2 text-slate-300">
            <span class="text-slate-400">Pullback Mode:</span>
            <span class="font-bold text-amberaccent" id="chaserPullbackMethod">25% OF PEAK</span>
          </div>
          <div class="px-3 py-1.5 rounded-lg bg-slate-900 border border-bordercol flex items-center gap-2 text-slate-300">
            <span class="text-slate-400">Trailing Shield:</span>
            <span class="font-bold text-emeraldaccent" id="chaserTrailingMethod">MAX 35% GIVEBACK</span>
          </div>
        </div>
      </div>

      <!-- Live Chased Positions Table -->
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-mono">
          <thead>
            <tr class="text-slate-400 border-b border-bordercol/60 pb-2">
              <th class="py-2 px-3">Position</th>
              <th class="py-2 px-3">Current Profit</th>
              <th class="py-2 px-3">All-Time Peak</th>
              <th class="py-2 px-3">Pullback / Drop</th>
              <th class="py-2 px-3">Option B Recovery Target</th>
              <th class="py-2 px-3">Protected Floor</th>
              <th class="py-2 px-3">Status Machine</th>
            </tr>
          </thead>
          <tbody id="chaserPositionsBody">
            <tr>
              <td colspan="7" class="py-4 text-center text-slate-500">Scanning live MT5 open positions for profit chasing telemetry...</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Live Recovery & Peak Events Feed -->
      <div class="pt-2 border-t border-bordercol/40">
        <span class="text-[11px] font-mono text-slate-400 uppercase font-bold tracking-wider">Option-B Peak & Recovery Live Audit Stream:</span>
        <div id="chaserEventStream" class="mt-2 space-y-1.5 max-h-36 overflow-y-auto font-mono text-[11px] text-slate-300">
          <div class="text-slate-500 italic">No events logged yet. Active trades will log new highs, pullbacks, and Option-B recoveries here.</div>
        </div>
      </div>
    </section>

    <!-- SECTION: MULTI-TP TRADE MANAGER'''

if "Smart Dynamic Profit Chasing, Pullback & Recovery Engine (Option B)" not in text:
    assert html_section_marker in text, "html_section_marker not found"
    text = text.replace(html_section_marker, chaser_dashboard_html, 1)

# 7. Add JavaScript polling and rendering for Profit Chaser
js_marker = "    async function fetchState() {"
js_chaser_code = """    async function fetchProfitChaser() {
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
      fetchProfitChaser();"""

if "renderProfitChaserDashboard" not in text:
    assert js_marker in text, "js_marker fetchState not found"
    text = text.replace(js_marker, js_chaser_code, 1)

app_path.write_text(text, encoding="utf-8")
print("[+] Successfully integrated Smart Profit Chaser into web_app.py!")
