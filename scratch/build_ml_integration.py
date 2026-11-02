# scratch/build_ml_integration.py
"""
Builds and integrates the ML Trading Intelligence System into web_app.py.
"""
import sys

with open("web_app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports from ml_trading_engine
import_marker = "from gold_auto_trader import GoldAutoTrader"
ml_imports = """from gold_auto_trader import GoldAutoTrader
from ml_trading_engine import (
    get_active_model,
    detect_market_regime,
    analyze_multi_timeframe,
    evaluate_all_strategies,
    generate_ai_trade_recommendations,
    run_ml_backtest,
    evaluate_risk_gate,
    get_model_drift_analysis,
    load_ml_settings,
    save_ml_settings,
    load_ml_journal,
    record_ml_prediction,
    update_ml_trade_outcome,
    MLTradingModel,
    REGIMES,
    FEATURE_NAMES
)

ml_training_state = {
    "is_training": False,
    "progress": 0,
    "message": "Idle",
    "last_result": None
}
"""

if import_marker in content and "from ml_trading_engine import" not in content:
    content = content.replace(import_marker, ml_imports, 1)
    print("[+] Added ML imports and training state.")

# 2. Add Top Navigation Button
nav_gold_marker = """      <button id="navTabGold" onclick="switchMainTab('gold')" class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-amber-400 hover:text-amber-300 hover:bg-slate-800 flex items-center gap-2">
        <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        Gold Intelligence
        <span class="px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-mono border border-amber-500/30">XAUUSD</span>
      </button>"""

nav_ml_button = """      <button id="navTabGold" onclick="switchMainTab('gold')" class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-amber-400 hover:text-amber-300 hover:bg-slate-800 flex items-center gap-2">
        <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        Gold Intelligence
        <span class="px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-mono border border-amber-500/30">XAUUSD</span>
      </button>
      <button id="navTabML" onclick="switchMainTab('ml')" class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-purple-400 hover:text-purple-300 hover:bg-slate-800 flex items-center gap-2">
        <svg class="w-3.5 h-3.5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
        AI / ML Intelligence
        <span class="px-1.5 py-0.2 rounded-full bg-purple-500/20 text-purple-300 text-[10px] font-mono border border-purple-500/30">ML ENGINE</span>
      </button>"""

if nav_gold_marker in content and 'id="navTabML"' not in content:
    content = content.replace(nav_gold_marker, nav_ml_button, 1)
    print("[+] Added top navigation button for AI / ML Intelligence.")

# 3. Add #mlView container after goldView
gold_view_end_marker = "    </div> <!-- End goldView -->"

with open("scratch/ml_view_template.html", "r", encoding="utf-8") as f:
    ml_view_html = f.read()

if gold_view_end_marker in content and 'id="mlView"' not in content:
    content = content.replace(gold_view_end_marker, gold_view_end_marker + "\n\n" + ml_view_html, 1)
    print("[+] Added #mlView HTML container.")

# 4. Add switchMainTab support & JS controller
switch_tab_marker = """      const goldView = document.getElementById('goldView');
      const tabStationBtn = document.getElementById('navTabStation');
      const tabPerfBtn = document.getElementById('navTabPerformance');
      const tabGoldBtn = document.getElementById('navTabGold');

      // Hide all views
      if (stationView) stationView.classList.add('hidden');
      if (perfView) perfView.classList.add('hidden');
      if (goldView) goldView.classList.add('hidden');

      // Reset button styles
      if (tabStationBtn) tabStationBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-slate-400 hover:text-white hover:bg-slate-800 flex items-center gap-2';
      if (tabPerfBtn) tabPerfBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-slate-400 hover:text-white hover:bg-slate-800 flex items-center gap-2';
      if (tabGoldBtn) tabGoldBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-amber-400 hover:text-amber-300 hover:bg-slate-800 flex items-center gap-2';

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
      }"""

switch_tab_replacement = """      const goldView = document.getElementById('goldView');
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
      }"""

if switch_tab_marker in content and "tab === 'ml'" not in content:
    content = content.replace(switch_tab_marker, switch_tab_replacement, 1)
    print("[+] Updated switchMainTab with 'ml' view handler.")

# 5. Add JavaScript controller functions for ML
with open("scratch/ml_js_controller.js", "r", encoding="utf-8") as f:
    ml_js = f.read()

js_insert_marker = "    // -----------------------------------------------------------------\n    // INITIALIZATION\n    // -----------------------------------------------------------------"
if js_insert_marker in content and "function loadMLDashboard" not in content:
    content = content.replace(js_insert_marker, ml_js + "\n\n" + js_insert_marker, 1)
    print("[+] Added ML JavaScript controller functions.")

# 6. Add API routes in do_GET and do_POST
get_marker = """        elif url.path == "/api/gold/auto_trade/status":
            st = gold_auto_trader.get_status() if gold_auto_trader else {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(st).encode("utf-8"))"""

post_marker = """        elif url.path == "/api/gold/execute_now":
            action = data.get("direction", "BUY")
            lot = float(data.get("lot", 0.01))
            sl = float(data.get("sl", 0.0))
            tp = float(data.get("tp", 0.0))
            conf = int(data.get("confidence", 90))
            strat = data.get("strategy", "Gold Intelligence Setup")
            res = gold_auto_trader.execute_gold_order(
                action=action, lot=lot, sl=sl, tp=tp,
                confidence_score=conf, strategy_name=strat,
                notes="Manual Instant Execution via Gold Page", is_auto=False
            ) if gold_auto_trader else {"success": False, "message": "GoldAutoTrader not initialized"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))"""

with open("scratch/ml_get_routes.py", "r", encoding="utf-8") as f:
    ml_get_routes = f.read()

with open("scratch/ml_post_routes.py", "r", encoding="utf-8") as f:
    ml_post_routes = f.read()

if get_marker in content and "url.path == \"/api/ml/overview\"" not in content:
    content = content.replace(get_marker, get_marker + "\n" + ml_get_routes, 1)
    print("[+] Added /api/ml/* routes to do_GET.")

if post_marker in content and "url.path == \"/api/ml/train\"" not in content:
    content = content.replace(post_marker, post_marker + "\n" + ml_post_routes, 1)
    print("[+] Added /api/ml/* routes to do_POST.")

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("[+] web_app.py updated successfully.")
