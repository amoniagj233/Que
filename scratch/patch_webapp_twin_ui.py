import re

def patch_webapp_twin():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add Backend Endpoints: /api/gold/execute_twin and /api/gold/close_all
    exec_target = '        elif url.path == "/api/gold/execute_now":'
    exec_block = '''        elif url.path == "/api/gold/execute_twin":
            action = data.get("direction", "BUY").upper()
            lot = float(data.get("lot", 0.01))
            tf = data.get("timeframe", "M1").upper()
            strat = data.get("strategy", f"Manual {tf} Twin Scalp")
            conf = int(data.get("confidence", 92))
            sl = float(data.get("sl", 0.0))
            tp_fixed = float(data.get("tp_fixed", data.get("tp", 0.0)))
            trail_dist = float(data.get("trail_dist", 0.0))

            res = gold_auto_trader.execute_twin_gold_orders(
                action=action,
                lot=lot,
                sl=sl,
                tp_fixed=tp_fixed,
                trail_dist=trail_dist,
                confidence_score=conf,
                strategy_name=strat,
                timeframe=tf,
                notes=f"Manual {tf} Twin Trade Execution",
                is_auto=False
            ) if gold_auto_trader else {"success": False, "message": "GoldAutoTrader not initialized"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/gold/close_all":
            closed_count = 0
            errs = []
            if mt5 is not None:
                with mt5_lock:
                    open_pos = mt5.positions_get(symbol="XAUUSD")
                    if open_pos:
                        tick = mt5.symbol_info_tick("XAUUSD")
                        for p in open_pos:
                            action = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                            price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
                            req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "symbol": "XAUUSD",
                                "volume": p.volume,
                                "type": action,
                                "position": p.ticket,
                                "price": price,
                                "deviation": 40,
                                "magic": 777199,
                                "comment": "Close Gold Twin",
                                "type_time": mt5.ORDER_TIME_GTC,
                                "type_filling": mt5.ORDER_FILLING_IOC
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                closed_count += 1
                            else:
                                errs.append(getattr(res, "comment", "Failed"))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "closed_count": closed_count, "errors": errs}).encode("utf-8"))

        elif url.path == "/api/gold/execute_now":'''

    if exec_target in content and '/api/gold/execute_twin' not in content:
        content = content.replace(exec_target, exec_block, 1)
        print("Added /api/gold/execute_twin and /api/gold/close_all backend endpoints")

    # 2. Add Target Timeframe and Twin Trade Mode to Autonomous Control Station
    auto_ctrl_target = '''              <span class="text-[10px] font-mono text-slate-400 px-2">TP Mode:</span>
              <select id="goldTpSelect" onchange="updateGoldAutoSettings()" class="bg-slate-900 text-amber-300 font-mono text-xs px-2 py-1 rounded border border-slate-800 font-bold">
                <option value="RANDOM_TP1_TP2">Random TP1/TP2 (Rule #2)</option>
                <option value="TP1_CONSERVATIVE">TP1 (1.8R Conservative)</option>
                <option value="TP2_RUNNER">TP2 (4.0R Runner)</option>
              </select>'''

    auto_ctrl_replace = '''              <span class="text-[10px] font-mono text-slate-400 px-2">Auto Target:</span>
              <select id="goldAutoTfSelect" onchange="updateGoldAutoSettings()" class="bg-slate-900 text-amber-300 font-mono text-xs px-2 py-1 rounded border border-slate-800 font-bold">
                <option value="M1_M5">⚡ 1M & 5M Fast Setups (Recommended)</option>
                <option value="M1">⚡ 1M Scalp Only</option>
                <option value="M5">⚡ 5M Momentum Only</option>
                <option value="ALL">All Setups (M1 – H1)</option>
              </select>'''

    if auto_ctrl_target in content:
        content = content.replace(auto_ctrl_target, auto_ctrl_replace, 1)
        print("Updated Autonomous Control Station with Auto Target Timeframe filter")

    # Also update metric badge in Auto Station
    metric_target = '''          <div class="p-2.5 rounded-lg bg-slate-950/60 border border-bordercol">
            <span class="text-[10px] text-slate-400 uppercase block">TP Target Mode</span>
            <span id="goldCfgTp" class="font-bold text-amber-300">Random TP1/TP2</span>
          </div>'''

    metric_replace = '''          <div class="p-2.5 rounded-lg bg-slate-950/60 border border-bordercol">
            <span class="text-[10px] text-slate-400 uppercase block">Execution Mode</span>
            <span id="goldCfgTp" class="font-bold text-emeraldaccent">TWIN TRADE (2 LEGS)</span>
          </div>'''

    if metric_target in content:
        content = content.replace(metric_target, metric_replace, 1)
        print("Updated TP Target Mode display to TWIN TRADE (2 LEGS)")

    # 3. Insert Gold High-Frequency Trading Terminal right after Autonomous Control Station
    terminal_insert_target = '      <!-- LIVE TRADINGVIEW LIGHTWEIGHT CANDLESTICK CHART & STRATEGY OVERLAYS -->'
    terminal_block = '''      <!-- GOLD HIGH-FREQUENCY TRADING TERMINAL & TWIN-ORDER EXECUTION (User Requirement) -->
      <section class="rounded-2xl bg-gradient-to-br from-panel via-slate-900 to-panel border border-amber-500/50 p-6 shadow-2xl space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-bordercol/80 pb-4">
          <div class="flex items-center gap-3.5">
            <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-amber-400 to-yellow-600 flex items-center justify-center text-xl shadow-lg shadow-amber-500/20 font-black text-slate-950">
              ⚡
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h3 class="text-base font-black text-white tracking-tight flex items-center gap-2">
                  GOLD HIGH-FREQUENCY TRADING TERMINAL
                </h3>
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-emerald-500/20 text-emeraldaccent border border-emerald-500/30">
                  TWIN-ORDER MODE (1 FIXED TP + 1 TRAILING TP)
                </span>
              </div>
              <p class="text-xs text-slate-400 mt-0.5">
                Manual &amp; Autonomous Scalp Execution &bull; Opens 2 Orders Every Trade &bull; Trade 1: Hard Fixed TP1 &bull; Trade 2: Dynamic Trailing Runner
              </p>
            </div>
          </div>
          
          <div class="flex items-center gap-3">
            <div class="text-right px-3.5 py-1.5 rounded-xl bg-slate-950/80 border border-bordercol">
              <span class="text-[10px] uppercase font-mono text-slate-400 block font-bold">Terminal Mode</span>
              <span id="activeTerminalTfDisplay" class="text-xs font-mono font-black text-amber-300">⚡ M1 SCALP MODE</span>
            </div>
            <button onclick="closeAllGoldPositions()" class="px-3.5 py-2 rounded-xl bg-rose-600/15 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 text-xs font-bold transition flex items-center gap-1.5">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              Close All Gold
            </button>
          </div>
        </div>

        <!-- Trading Controls Row -->
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
          <!-- Timeframe & Lot selector (5 Cols) -->
          <div class="md:col-span-5 space-y-3">
            <div class="space-y-1.5">
              <label class="block text-[11px] font-mono text-slate-400 uppercase font-bold">Execution Strategy Timeframe:</label>
              <div class="grid grid-cols-3 gap-2 text-xs font-mono">
                <button type="button" id="btnTerminalM1" onclick="setManualTradeTf('M1')" class="py-2 px-2.5 rounded-xl bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 text-center transition flex flex-col items-center">
                  <span class="font-bold">⚡ 1M Scalp</span>
                  <span class="text-[10px] text-slate-400 font-normal">SL $3.50 | TP 1.5R</span>
                </button>
                <button type="button" id="btnTerminalM5" onclick="setManualTradeTf('M5')" class="py-2 px-2.5 rounded-xl bg-slate-950 text-slate-400 hover:text-white border border-bordercol text-center transition flex flex-col items-center">
                  <span class="font-bold">⚡ 5M Momentum</span>
                  <span class="text-[10px] text-slate-400 font-normal">SL $4.50 | TP 1.8R</span>
                </button>
                <button type="button" id="btnTerminalM15" onclick="setManualTradeTf('M15')" class="py-2 px-2.5 rounded-xl bg-slate-950 text-slate-400 hover:text-white border border-bordercol text-center transition flex flex-col items-center">
                  <span class="font-bold">M15 Intraday</span>
                  <span class="text-[10px] text-slate-400 font-normal">SL $6.00 | TP 2.5R</span>
                </button>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3 text-xs font-mono">
              <div class="space-y-1">
                <label class="block text-[10px] text-slate-400 uppercase font-bold">Volume per Leg:</label>
                <select id="terminalLotSelect" onchange="updateTerminalPreview()" class="w-full bg-slate-950 text-white font-mono text-xs px-3 py-2 rounded-xl border border-slate-800">
                  <option value="0.01">0.01 Lot (1 oz)</option>
                  <option value="0.02">0.02 Lot (2 oz)</option>
                  <option value="0.05">0.05 Lot (5 oz)</option>
                  <option value="0.10">0.10 Lot (10 oz)</option>
                </select>
              </div>
              <div class="space-y-1">
                <label class="block text-[10px] text-slate-400 uppercase font-bold">Total Exposure (2 Legs):</label>
                <div id="terminalTotalLot" class="w-full bg-slate-950 text-amber-300 font-bold font-mono text-xs px-3 py-2 rounded-xl border border-slate-800">
                  0.02 Lot (2 oz total)
                </div>
              </div>
            </div>
          </div>

          <!-- Twin-Order Specification Preview (7 Cols) -->
          <div class="md:col-span-7 bg-slate-950/80 rounded-xl border border-bordercol p-4 space-y-3">
            <div class="flex items-center justify-between text-xs font-mono border-b border-bordercol/60 pb-2">
              <span class="text-slate-400 font-bold uppercase text-[10px]">Dual-Order Blueprint (Rule #1 &amp; #2):</span>
              <span class="text-emeraldaccent font-bold">Shared Protective Risk</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <!-- Leg 1 -->
              <div class="p-3 rounded-lg bg-slate-900 border border-blue-500/30 space-y-1">
                <div class="flex items-center justify-between">
                  <span class="text-blue-400 font-bold">TRADE 1: FIXED TARGET</span>
                  <span class="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-300 font-bold">LEG 1</span>
                </div>
                <div class="text-[11px] text-slate-300">
                  Target: <strong id="previewLeg1Tp" class="text-emeraldaccent">+1.5R Fixed TP1</strong>
                </div>
                <div class="text-[10px] text-slate-400">
                  Automatically fills &amp; locks in profits on broker limit target.
                </div>
              </div>

              <!-- Leg 2 -->
              <div class="p-3 rounded-lg bg-slate-900 border border-amber-500/30 space-y-1">
                <div class="flex items-center justify-between">
                  <span class="text-amber-400 font-bold">TRADE 2: TRAILING RUNNER</span>
                  <span class="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-bold">LEG 2</span>
                </div>
                <div class="text-[11px] text-slate-300">
                  Target: <strong id="previewLeg2Tp" class="text-amber-300">Dynamic Trailing Stop</strong>
                </div>
                <div class="text-[10px] text-slate-400">
                  Break-Even at +1.0R &bull; Trails price to ride major trend expansions.
                </div>
              </div>
            </div>

            <!-- Instant Dual Execution Action Buttons -->
            <div class="grid grid-cols-2 gap-3 pt-1">
              <button onclick="executeManualGoldTrade('BUY')" class="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-slate-950 font-black text-xs transition shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 10l7-7m0 0l7 7m-7-7v18"></path></svg>
                BUY XAUUSD (TWIN TRADE)
              </button>
              <button onclick="executeManualGoldTrade('SELL')" class="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white font-black text-xs transition shadow-lg shadow-rose-600/20 flex items-center justify-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
                SELL XAUUSD (TWIN TRADE)
              </button>
            </div>
          </div>
        </div>

        <!-- Live Open Gold Twin Positions & Trailing Monitor -->
        <div class="pt-3 border-t border-bordercol/60">
          <div class="flex items-center justify-between pb-2">
            <span class="text-[11px] font-mono text-slate-400 uppercase font-bold flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
              Live Gold Positions &amp; Dynamic Trailing Status:
            </span>
            <span id="goldOpenLegsCount" class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-bordercol text-slate-300">0 Active Legs</span>
          </div>
          <div id="goldPositionsTableContainer" class="overflow-x-auto custom-scroll">
            <table class="w-full text-left text-xs font-mono">
              <thead class="bg-slate-950/80 text-slate-400 uppercase text-[10px] border-b border-bordercol">
                <tr>
                  <th class="py-2 px-3">Ticket</th>
                  <th class="py-2 px-3">Leg Role</th>
                  <th class="py-2 px-3">Type</th>
                  <th class="py-2 px-3">Volume</th>
                  <th class="py-2 px-3">Entry</th>
                  <th class="py-2 px-3">Live Price</th>
                  <th class="py-2 px-3">Stop Loss</th>
                  <th class="py-2 px-3">Take Profit</th>
                  <th class="py-2 px-3">Floating P/L</th>
                  <th class="py-2 px-3">Trailing Telemetry</th>
                </tr>
              </thead>
              <tbody id="goldPositionsTbody" class="divide-y divide-bordercol/60 text-slate-300">
                <tr><td colspan="10" class="py-4 text-center text-slate-500">No open Gold positions currently.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- LIVE TRADINGVIEW LIGHTWEIGHT CANDLESTICK CHART & STRATEGY OVERLAYS -->'''

    if terminal_insert_target in content and 'GOLD HIGH-FREQUENCY TRADING TERMINAL' not in content:
        content = content.replace(terminal_insert_target, terminal_block, 1)
        print("Inserted GOLD HIGH-FREQUENCY TRADING TERMINAL into goldView")

    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: Part 1 of web_app.py patch applied!")
    return True

if __name__ == '__main__':
    patch_webapp_twin()
