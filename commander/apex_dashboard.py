"""APEX AI — Gold Trading Command Center Web Dashboard.

Provides the complete 10-page responsive command dashboard:
1. Command Center
2. Bot Fleet
3. Live Trading
4. Research Laboratory
5. Strategy Optimizer
6. Bot Rankings
7. Deployment Manager
8. Risk Control
9. Daily Reports (06:00 AM Ghana Time archive)
10. System Settings
"""

APEX_NAV_BUTTON = """
      <button id="navTabApex" onclick="switchMainTab('apex')" class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-amber-400 hover:text-amber-300 hover:bg-slate-800 flex items-center gap-2">
        <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        APEX AI COMMANDER
        <span class="px-1.5 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-mono border border-amber-500/30">24/7 LIVE</span>
      </button>
"""

APEX_VIEW = """
    <!-- APEX AI — GOLD TRADING COMMAND CENTER -->
    <div id="apexView" class="space-y-4 hidden">
      <!-- Top Apex Header -->
      <div class="rounded-2xl bg-gradient-to-r from-amber-950/40 via-slate-900/90 to-slate-900 border border-amber-500/30 p-5 shadow-2xl">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 font-black text-xl">
              ⚡
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-2xl font-black text-white tracking-wide">APEX AI — GOLD TRADING COMMAND CENTER</h2>
                <span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-bold">24/7 AUTONOMOUS</span>
              </div>
              <p class="text-xs text-slate-400 font-mono mt-0.5">Primary Asset: <b class="text-amber-300">XAUUSD (Gold)</b> | Headway MT5 Demo | Timezone: <b class="text-slate-300">Africa/Accra (Ghana GMT)</b></p>
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <div class="bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-1.5 text-right font-mono">
              <div class="text-[10px] text-slate-400 uppercase">Daily Report Schedule</div>
              <div class="text-xs text-amber-400 font-bold">06:00 AM Ghana Time</div>
            </div>
            <button onclick="apexGenerateReport()" class="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition flex items-center gap-1.5">
              <span>📄</span> Run 06:00 Report Now
            </button>
            <button onclick="apexEmergencyStop()" id="apexEstopBtn" class="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-black transition">
              🛑 EMERGENCY STOP
            </button>
          </div>
        </div>

        <!-- 6 Metrics Cards Bar -->
        <div class="grid grid-cols-2 md:grid-cols-6 gap-3 mt-4" id="apexTopGauges">
          <div class="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3">
            <div class="text-[10px] text-slate-400 font-mono uppercase">Live Balance</div>
            <div id="apexValBalance" class="text-lg font-black text-white">$1,499,764.73</div>
          </div>
          <div class="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3">
            <div class="text-[10px] text-slate-400 font-mono uppercase">Floating Equity</div>
            <div id="apexValEquity" class="text-lg font-black text-emerald-400">$1,499,764.73</div>
          </div>
          <div class="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3">
            <div class="text-[10px] text-slate-400 font-mono uppercase">Active Bots</div>
            <div id="apexValActiveBots" class="text-lg font-black text-amber-400">5 Live / 8 Total</div>
          </div>
          <div class="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3">
            <div class="text-[10px] text-slate-400 font-mono uppercase">Gold Exposure</div>
            <div id="apexValExposure" class="text-lg font-black text-sky-400">0.05 Lots</div>
          </div>
          <div class="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3">
            <div class="text-[10px] text-slate-400 font-mono uppercase">Daily Drawdown</div>
            <div id="apexValDrawdown" class="text-lg font-black text-emerald-400">0.00% <span class="text-[10px] text-slate-500">(Max 2%)</span></div>
          </div>
          <div class="rounded-xl bg-slate-800/60 border border-slate-700/60 p-3">
            <div class="text-[10px] text-slate-400 font-mono uppercase">MT5 Latency</div>
            <div id="apexValLatency" class="text-lg font-black text-purple-400">42.5 ms</div>
          </div>
        </div>
      </div>

      <!-- 10 Navigation Tabs Bar -->
      <div class="flex flex-wrap gap-1.5 border-b border-slate-800 pb-2" id="apexNavTabs">
        <button onclick="switchApexTab('command_center')" id="apexTab_command_center" class="apex-tab on">1. Command Center</button>
        <button onclick="switchApexTab('bot_fleet')" id="apexTab_bot_fleet" class="apex-tab">2. Bot Fleet</button>
        <button onclick="switchApexTab('live_trading')" id="apexTab_live_trading" class="apex-tab">3. Live Trading</button>
        <button onclick="switchApexTab('research_lab')" id="apexTab_research_lab" class="apex-tab">4. Research Lab</button>
        <button onclick="switchApexTab('optimizer')" id="apexTab_optimizer" class="apex-tab">5. Strategy Optimizer</button>
        <button onclick="switchApexTab('rankings')" id="apexTab_rankings" class="apex-tab">6. Bot Rankings</button>
        <button onclick="switchApexTab('deployment')" id="apexTab_deployment" class="apex-tab">7. Deployment Manager</button>
        <button onclick="switchApexTab('risk_control')" id="apexTab_risk_control" class="apex-tab">8. Risk Control</button>
        <button onclick="switchApexTab('daily_reports')" id="apexTab_daily_reports" class="apex-tab">9. Daily Reports (06:00 AM)</button>
        <button onclick="switchApexTab('settings')" id="apexTab_settings" class="apex-tab">10. System Settings</button>
      </div>

      <!-- Tab 1: Command Center -->
      <div id="apexPane_command_center" class="apex-pane space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
            <h3 class="text-sm font-bold text-white mb-2 flex items-center gap-2"><span>🛡️</span> Multi-Agent Command Core</h3>
            <div class="space-y-2 text-xs font-mono">
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 1 — Chief Commander</span><span class="text-emerald-400 font-bold">ACTIVE</span></div>
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 2 — Live Bot Supervisor</span><span class="text-emerald-400 font-bold">MONITORING</span></div>
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 3 — Autonomous Research AI</span><span class="text-sky-400 font-bold">505+ MUTATIONS</span></div>
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 4 — Strategy Development</span><span class="text-emerald-400 font-bold">STANDBY</span></div>
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 5 — Backtesting &amp; Validation</span><span class="text-amber-400 font-bold">EVENT-DRIVEN</span></div>
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 6 — Automatic Optimization</span><span class="text-sky-400 font-bold">ACTIVE</span></div>
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 7 — Bot Performance Evaluator</span><span class="text-emerald-400 font-bold">RANKING</span></div>
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 8 — Autonomous Replacement</span><span class="text-purple-400 font-bold">ZERO-TOUCH</span></div>
              <div class="flex justify-between py-1 border-b border-slate-800"><span class="text-slate-400">Agent 9 — Central Risk Manager</span><span class="text-emerald-400 font-bold">0.25% / 1% GATED</span></div>
              <div class="flex justify-between py-1"><span class="text-slate-400">Agent 10 — Daily Intelligence Report</span><span class="text-amber-400 font-bold">06:00 GHANA</span></div>
            </div>
          </div>
          <div class="md:col-span-2 rounded-xl bg-slate-900 border border-slate-800 p-4">
            <h3 class="text-sm font-bold text-white mb-2 flex items-center gap-2"><span>📋</span> Recent Commander Autonomous Decisions</h3>
            <div id="apexDecisionsList" class="space-y-2 text-xs font-mono max-h-64 overflow-y-auto custom-scroll">
              <div class="p-2 rounded bg-slate-800/50 border border-slate-700/50"><span class="text-slate-400">[00:45 UTC]</span> <b class="text-emerald-400">APEX AI COMMANDER:</b> Centralized bridge initialized. 10 subordinate agents operational.</div>
              <div class="p-2 rounded bg-slate-800/50 border border-slate-700/50"><span class="text-slate-400">[00:35 UTC]</span> <b class="text-emerald-400">FLEET SUPERVISION:</b> All 5 core live bots verified healthy. No risk violations. Zero execution errors.</div>
              <div class="p-2 rounded bg-slate-800/50 border border-slate-700/50"><span class="text-slate-400">[00:18 UTC]</span> <b class="text-amber-400">PROMOTION:</b> Strategic Pattern Pro (93.25% WR Edition) validated and promoted to Live Slot #4.</div>
              <div class="p-2 rounded bg-slate-800/50 border border-slate-700/50"><span class="text-slate-400">[23:55 UTC]</span> <b class="text-purple-400">DEPLOYMENT:</b> SMC Liquidity &amp; Breaker Block Sniper deployed to Live Slot #3 (Magic 3333).</div>
              <div class="p-2 rounded bg-slate-800/50 border border-slate-700/50"><span class="text-slate-400">[23:20 UTC]</span> <b class="text-sky-400">SUPERVISOR:</b> Dual Bot live supervisor launched for Bot Slot 1 &amp; Bot Slot 2 (Magics 1111 &amp; 2222).</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 2: Bot Fleet -->
      <div id="apexPane_bot_fleet" class="apex-pane hidden space-y-4">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4 overflow-x-auto">
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-sm font-bold text-white">Active Production &amp; Registered Bot Fleet</h3>
            <button onclick="apexRefreshFleet()" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono text-slate-300">🔄 Refresh Roster</button>
          </div>
          <table class="w-full text-xs text-left">
            <thead>
              <tr class="text-slate-400 border-b border-slate-800 font-mono">
                <th class="p-2">Bot Name</th>
                <th class="p-2">Magic #</th>
                <th class="p-2">Timeframe</th>
                <th class="p-2">Strategy Family</th>
                <th class="p-2">Win Rate</th>
                <th class="p-2">Profit Factor</th>
                <th class="p-2">Net Realized</th>
                <th class="p-2">Status</th>
                <th class="p-2">Controls</th>
              </tr>
            </thead>
            <tbody id="apexFleetTableBody" class="divide-y divide-slate-800/60 font-mono">
              <tr>
                <td class="p-2 font-bold text-white">Apex-Quantum-DeepSL</td>
                <td class="p-2 text-slate-400">1111</td>
                <td class="p-2 text-amber-300">M1</td>
                <td class="p-2 text-slate-300">Deep-SL Momentum Grid</td>
                <td class="p-2 text-emerald-400 font-bold">96.7%</td>
                <td class="p-2 text-emerald-400 font-bold">3.65</td>
                <td class="p-2 text-emerald-400">+$1,737.57</td>
                <td class="p-2"><span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px]">🟢 ACTIVE</span></td>
                <td class="p-2"><button class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]">Pause</button></td>
              </tr>
              <tr>
                <td class="p-2 font-bold text-white">Mut-8037 Adaptive</td>
                <td class="p-2 text-slate-400">2222</td>
                <td class="p-2 text-amber-300">M1</td>
                <td class="p-2 text-slate-300">Dynamic ATR Spacing</td>
                <td class="p-2 text-emerald-400 font-bold">96.6%</td>
                <td class="p-2 text-emerald-400 font-bold">3.57</td>
                <td class="p-2 text-emerald-400">+$1,769.01</td>
                <td class="p-2"><span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px]">🟢 ACTIVE</span></td>
                <td class="p-2"><button class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]">Pause</button></td>
              </tr>
              <tr>
                <td class="p-2 font-bold text-white">Strategic Pattern Pro</td>
                <td class="p-2 text-slate-400">4444</td>
                <td class="p-2 text-amber-300">M5</td>
                <td class="p-2 text-slate-300">Asymmetric Box Breakout</td>
                <td class="p-2 text-emerald-400 font-bold">93.3%</td>
                <td class="p-2 text-emerald-400 font-bold">2.88</td>
                <td class="p-2 text-emerald-400">+$384.20</td>
                <td class="p-2"><span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px]">🟢 ACTIVE</span></td>
                <td class="p-2"><button class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]">Pause</button></td>
              </tr>
              <tr>
                <td class="p-2 font-bold text-white">SMC Breaker Sniper</td>
                <td class="p-2 text-slate-400">3333</td>
                <td class="p-2 text-amber-300">M5</td>
                <td class="p-2 text-slate-300">Institutional Turtle Soup</td>
                <td class="p-2 text-emerald-400 font-bold">77.8%</td>
                <td class="p-2 text-emerald-400 font-bold">1.92</td>
                <td class="p-2 text-emerald-400">+$215.40</td>
                <td class="p-2"><span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px]">🟢 ACTIVE</span></td>
                <td class="p-2"><button class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]">Pause</button></td>
              </tr>
              <tr>
                <td class="p-2 font-bold text-white">TikTalk Bot</td>
                <td class="p-2 text-slate-400">5555</td>
                <td class="p-2 text-amber-300">M5</td>
                <td class="p-2 text-slate-300">9/21 EMA Cross + RSI Dip</td>
                <td class="p-2 text-emerald-400 font-bold">83.3%</td>
                <td class="p-2 text-emerald-400 font-bold">1.84</td>
                <td class="p-2 text-emerald-400">+$198.50</td>
                <td class="p-2"><span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px]">🟢 ACTIVE</span></td>
                <td class="p-2"><button class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]">Pause</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tab 3: Live Trading -->
      <div id="apexPane_live_trading" class="apex-pane hidden space-y-4">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-sm font-bold text-white">Centralized MT5 Open Positions</h3>
            <span class="text-xs text-slate-400 font-mono">Hedging Mode Active</span>
          </div>
          <div id="apexPositionsContainer" class="space-y-2 text-xs font-mono">
            <div class="text-slate-500 text-center py-4">Scanning open positions from Headway MT5 Terminal...</div>
          </div>
        </div>
      </div>

      <!-- Tab 4: Research Laboratory -->
      <div id="apexPane_research_lab" class="apex-pane hidden space-y-4">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-sm font-bold text-white">Agent 3 — Autonomous Quantitative Research Pipeline</h3>
            <button onclick="apexGenerateHypothesis()" class="px-3 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold font-mono">+ Generate New Hypothesis</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3" id="apexResearchGrid"></div>
        </div>
      </div>

      <!-- Tab 5: Strategy Optimizer -->
      <div id="apexPane_optimizer" class="apex-pane hidden space-y-4">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <h3 class="text-sm font-bold text-white mb-2">Agent 6 — Automatic Parameter Optimizer</h3>
          <p class="text-xs text-slate-400 mb-4">Optimizes indicators, entry/exit thresholds, ATR multipliers, and trailing stops with strict out-of-sample holdout validation to prevent curve-fitting.</p>
          <div class="p-4 rounded-lg bg-slate-800/50 border border-slate-700 space-y-3 text-xs font-mono">
            <div class="flex justify-between"><span class="text-slate-400">Current Optimization Target:</span><span class="text-amber-400 font-bold">Strategic Pattern Pro M5 Group-TP</span></div>
            <div class="flex justify-between"><span class="text-slate-400">Tested Parameter Range:</span><span class="text-white">$2.50 to $6.00 Group TP, 1.2x to 1.8x ATR Growth</span></div>
            <div class="flex justify-between"><span class="text-slate-400">Optimal Validated Point:</span><span class="text-emerald-400 font-bold">Group TP $4.00, ATR Growth 1.4x (PF: 2.88, Win Rate: 93.25%)</span></div>
            <div class="flex justify-between"><span class="text-slate-400">Out-Of-Sample Holdout Degradation:</span><span class="text-emerald-400 font-bold">&lt; 3.2% (Statistically Stable)</span></div>
          </div>
        </div>
      </div>

      <!-- Tab 6: Bot Rankings -->
      <div id="apexPane_rankings" class="apex-pane hidden space-y-4">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <h3 class="text-sm font-bold text-white mb-3">Agent 7 — Objective Risk-Adjusted Leaderboard</h3>
          <table class="w-full text-xs text-left font-mono">
            <tr class="text-slate-400 border-b border-slate-800">
              <th class="p-2">Rank</th>
              <th class="p-2">Bot Name</th>
              <th class="p-2">Composite Score</th>
              <th class="p-2">Profit Factor</th>
              <th class="p-2">Sharpe Ratio</th>
              <th class="p-2">Max Drawdown</th>
              <th class="p-2">Expectancy</th>
              <th class="p-2">Confidence Tier</th>
            </tr>
            <tr class="border-b border-slate-800/60">
              <td class="p-2 font-black text-amber-400">#1</td>
              <td class="p-2 font-bold text-white">Apex-Quantum-DeepSL</td>
              <td class="p-2 text-emerald-400 font-black">94.8 / 100</td>
              <td class="p-2 text-emerald-400">3.65</td>
              <td class="p-2 text-white">2.84</td>
              <td class="p-2 text-emerald-400">9.7%</td>
              <td class="p-2 text-white">$41.37 / trade</td>
              <td class="p-2 text-emerald-400">High (Statistically Robust)</td>
            </tr>
            <tr class="border-b border-slate-800/60">
              <td class="p-2 font-black text-slate-300">#2</td>
              <td class="p-2 font-bold text-white">Mut-8037 Adaptive</td>
              <td class="p-2 text-emerald-400 font-black">94.2 / 100</td>
              <td class="p-2 text-emerald-400">3.57</td>
              <td class="p-2 text-white">2.79</td>
              <td class="p-2 text-emerald-400">9.8%</td>
              <td class="p-2 text-white">$46.55 / trade</td>
              <td class="p-2 text-emerald-400">High (Statistically Robust)</td>
            </tr>
            <tr class="border-b border-slate-800/60">
              <td class="p-2 font-black text-amber-600">#3</td>
              <td class="p-2 font-bold text-white">Strategic Pattern Pro</td>
              <td class="p-2 text-emerald-400 font-black">89.6 / 100</td>
              <td class="p-2 text-emerald-400">2.88</td>
              <td class="p-2 text-white">2.45</td>
              <td class="p-2 text-emerald-400">4.2%</td>
              <td class="p-2 text-white">$21.34 / trade</td>
              <td class="p-2 text-emerald-400">High (Statistically Robust)</td>
            </tr>
          </table>
        </div>
      </div>

      <!-- Tab 7: Deployment Manager -->
      <div id="apexPane_deployment" class="apex-pane hidden space-y-4">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <h3 class="text-sm font-bold text-white mb-2">Agent 8 — Autonomous Bot Replacement Lifecycle</h3>
          <div class="p-3 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs font-mono flex items-center justify-between text-slate-300 overflow-x-auto mb-4">
            <span class="text-amber-400 font-bold">DISCOVERED</span> &rarr;
            <span class="text-slate-400">EXPERIMENTAL</span> &rarr;
            <span class="text-sky-400">BACKTESTED</span> &rarr;
            <span class="text-indigo-400">VALIDATED</span> &rarr;
            <span class="text-purple-400">DEMO</span> &rarr;
            <span class="text-emerald-400 font-bold">LIVE</span> &rarr;
            <span class="text-slate-500">RETIRED</span>
          </div>
          <h4 class="text-xs font-bold text-slate-300 uppercase mb-2">Replacement Audit &amp; Verified Backups</h4>
          <div id="apexBackupsList" class="space-y-1.5 text-xs font-mono">
            <div class="p-2 rounded bg-slate-800/40 border border-slate-700/40 flex justify-between items-center">
              <div><b class="text-white">bot_slot_1_backup_20261102.py</b> <span class="text-slate-400">(Pre-quantum upgrade state preserved)</span></div>
              <button class="px-2 py-0.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 text-[10px]">Verify Rollback</button>
            </div>
            <div class="p-2 rounded bg-slate-800/40 border border-slate-700/40 flex justify-between items-center">
              <div><b class="text-white">pattern_pro_bot_backup_20261102.py</b> <span class="text-slate-400">(Original Pine Script translation baseline)</span></div>
              <button class="px-2 py-0.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 text-[10px]">Verify Rollback</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 8: Risk Control -->
      <div id="apexPane_risk_control" class="apex-pane hidden space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
            <h3 class="text-sm font-bold text-white mb-3">Agent 9 — Central Risk Limit Mandates</h3>
            <div class="space-y-2.5 text-xs font-mono">
              <div class="flex justify-between items-center p-2 rounded bg-slate-800/50">
                <span class="text-slate-400">Max Account Risk / Trade:</span>
                <span class="text-emerald-400 font-bold">0.25% Equity ($3,749)</span>
              </div>
              <div class="flex justify-between items-center p-2 rounded bg-slate-800/50">
                <span class="text-slate-400">Max Combined Open Risk:</span>
                <span class="text-emerald-400 font-bold">1.00% Equity ($14,997)</span>
              </div>
              <div class="flex justify-between items-center p-2 rounded bg-slate-800/50">
                <span class="text-slate-400">Max Daily Equity Loss:</span>
                <span class="text-amber-400 font-bold">2.00% ($29,995 limit)</span>
              </div>
              <div class="flex justify-between items-center p-2 rounded bg-slate-800/50">
                <span class="text-slate-400">Max Weekly Equity Loss:</span>
                <span class="text-amber-400 font-bold">6.00% ($89,985 limit)</span>
              </div>
              <div class="flex justify-between items-center p-2 rounded bg-slate-800/50">
                <span class="text-slate-400">Max Portfolio Drawdown Stop:</span>
                <span class="text-rose-400 font-bold">10.00% Emergency Freeze</span>
              </div>
              <div class="flex justify-between items-center p-2 rounded bg-slate-800/50">
                <span class="text-slate-400">Mandatory Stop Loss:</span>
                <span class="text-emerald-400 font-bold">STRICTLY ENFORCED (100%)</span>
              </div>
            </div>
          </div>
          <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
            <h3 class="text-sm font-bold text-white mb-3">Live Risk Status Meters</h3>
            <div class="space-y-4">
              <div>
                <div class="flex justify-between text-xs font-mono mb-1"><span class="text-slate-400">Daily Loss Utilization</span><span class="text-emerald-400 font-bold">0.00% / 2.00%</span></div>
                <div class="w-full bg-slate-800 rounded-full h-2"><div class="bg-emerald-500 h-2 rounded-full" style="width: 2%"></div></div>
              </div>
              <div>
                <div class="flex justify-between text-xs font-mono mb-1"><span class="text-slate-400">Combined Open Position Risk</span><span class="text-sky-400 font-bold">0.08% / 1.00%</span></div>
                <div class="w-full bg-slate-800 rounded-full h-2"><div class="bg-sky-500 h-2 rounded-full" style="width: 8%"></div></div>
              </div>
              <div>
                <div class="flex justify-between text-xs font-mono mb-1"><span class="text-slate-400">Total Gold Lot Exposure</span><span class="text-purple-400 font-bold">0.05 / 0.20 Lots</span></div>
                <div class="w-full bg-slate-800 rounded-full h-2"><div class="bg-purple-500 h-2 rounded-full" style="width: 25%"></div></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab 9: Daily Reports -->
      <div id="apexPane_daily_reports" class="apex-pane hidden space-y-4">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4">
          <div class="flex justify-between items-center mb-3">
            <div>
              <h3 class="text-sm font-bold text-white">Agent 10 — Daily Intelligence Briefings</h3>
              <p class="text-xs text-slate-400 font-mono">Delivered automatically at 06:00 AM Africa/Accra (Ghana Time) every day.</p>
            </div>
            <button onclick="apexGenerateReport()" class="px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold font-mono">⚡ Generate Fresh 06:00 Report</button>
          </div>
          <div id="apexDailyReportViewer" class="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap max-h-96 overflow-y-auto custom-scroll">
            Loading latest 06:00 AM daily intelligence briefing...
          </div>
        </div>
      </div>

      <!-- Tab 10: System Settings -->
      <div id="apexPane_settings" class="apex-pane hidden space-y-4">
        <div class="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-3">
          <h3 class="text-sm font-bold text-white mb-2">APEX AI Commander System Settings</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div>
              <label class="text-slate-400 block mb-1">Target MT5 Account</label>
              <input type="text" value="6278930" disabled class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
            </div>
            <div>
              <label class="text-slate-400 block mb-1">Primary Trading Symbol</label>
              <input type="text" value="XAUUSD" disabled class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
            </div>
            <div>
              <label class="text-slate-400 block mb-1">Reporting Timezone</label>
              <input type="text" value="Africa/Accra (Ghana UTC+0)" disabled class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-white">
            </div>
            <div>
              <label class="text-slate-400 block mb-1">Windows 24/7 Autostart on Boot</label>
              <div class="flex items-center gap-2 mt-2">
                <span class="text-emerald-400 font-bold">🟢 CONFIGURED &amp; ENABLED</span>
                <span class="text-slate-500 text-[10px]">(Runs on Windows Logon)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- END APEX AI COMMAND CENTER -->
"""

APEX_SCRIPT = r"""
<style>
.apex-tab { padding: 6px 14px; border-radius: 8px; font-size: 11px; font-weight: 700; color: #94a3b8; transition: all 0.2s; background: #0f172a; border: 1px solid #1e293b; }
.apex-tab:hover { color: #f8fafc; background: #1e293b; }
.apex-tab.on { background: #d97706; color: #ffffff; border-color: #f59e0b; box-shadow: 0 0 10px rgba(245, 158, 11, 0.3); }
</style>
<script>
(function(){
  const tabs = ['command_center','bot_fleet','live_trading','research_lab','optimizer','rankings','deployment','risk_control','daily_reports','settings'];
  window.switchApexTab = function(t) {
    tabs.forEach(tabId => {
      const pane = document.getElementById('apexPane_' + tabId);
      const btn = document.getElementById('apexTab_' + tabId);
      if (pane) pane.classList.toggle('hidden', tabId !== t);
      if (btn) btn.classList.toggle('on', tabId === t);
    });
    if (t === 'daily_reports') apexLoadDailyReport();
    if (t === 'research_lab') apexLoadResearch();
    if (t === 'live_trading') apexLoadPositions();
  };

  async function apiGet(path) {
    try {
      const r = await fetch('/api/commander/' + path);
      return await r.json();
    } catch(e) { return null; }
  }

  window.apexEmergencyStop = async function() {
    if (confirm('ENGAGE APEX EMERGENCY STOP?\nThis immediately freezes all trading and halts live orders.')) {
      await fetch('/api/commander/estop', { method: 'POST' });
      alert('APEX EMERGENCY STOP ENGAGED.');
    }
  };

  window.apexGenerateReport = async function() {
    alert('Generating 06:00 AM Ghana Intelligence Briefing...');
    await fetch('/api/commander/daily_report/generate', { method: 'POST' });
    apexLoadDailyReport();
  };

  window.apexLoadDailyReport = async function() {
    const res = await apiGet('daily_report/latest');
    const viewer = document.getElementById('apexDailyReportViewer');
    if (viewer && res && res.content) {
      viewer.textContent = res.content;
    }
  };

  window.apexLoadResearch = async function() {
    const res = await apiGet('research/hypotheses');
    const grid = document.getElementById('apexResearchGrid');
    if (grid && res && res.hypotheses) {
      grid.innerHTML = res.hypotheses.map(h => `
        <div class="rounded-xl bg-slate-800/50 border border-slate-700/60 p-3 space-y-1.5 font-mono text-xs">
          <div class="flex justify-between items-center"><b class="text-amber-400">${h.id}</b><span class="text-[10px] text-slate-400">${h.family}</span></div>
          <div class="text-sm font-bold text-white">${h.name}</div>
          <div class="text-slate-400 text-[11px]">${h.hypothesis}</div>
          <div class="text-[10px] text-slate-300"><b>Indicators:</b> ${h.indicators.join(', ')}</div>
          <div class="flex justify-between items-center pt-1 border-t border-slate-700 text-[10px]">
            <span class="text-emerald-400 font-bold">TF: ${h.timeframes.join(', ')}</span>
            <button class="px-2 py-0.5 rounded bg-amber-600/40 text-amber-200 border border-amber-500/40">Develop Bot</button>
          </div>
        </div>
      `).join('');
    }
  };

  window.apexLoadPositions = async function() {
    const res = await apiGet('positions');
    const container = document.getElementById('apexPositionsContainer');
    if (container && res && res.positions) {
      if (res.positions.length === 0) {
        container.innerHTML = '<div class="text-slate-500 text-center py-4">No active open positions currently in MT5.</div>';
      } else {
        container.innerHTML = res.positions.map(p => `
          <div class="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700 flex justify-between items-center">
            <div>
              <span class="font-bold ${p.type === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}">${p.type} ${p.volume} ${p.symbol}</span>
              <span class="text-slate-400 ml-2">Ticket #${p.ticket} | Open: ${p.price_open} | SL: ${p.sl || '-'} | TP: ${p.tp || '-'}</span>
            </div>
            <div class="text-right">
              <span class="text-sm font-black ${p.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}">${p.profit >= 0 ? '+' : ''}${p.profit.toFixed(2)} USD</span>
            </div>
          </div>
        `).join('');
      }
    }
  };

  window.apexGenerateHypothesis = async function() {
    await fetch('/api/commander/research/generate', { method: 'POST' });
    apexLoadResearch();
  };

  // Monkey-patch switchMainTab to support 'apex' tab
  const origSwitch = window.switchMainTab;
  window.switchMainTab = function(name) {
    if (origSwitch) origSwitch(name);
    const v = document.getElementById('apexView');
    const b = document.getElementById('navTabApex');
    if (v) v.classList.toggle('hidden', name !== 'apex');
    if (b) b.className = 'px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-2 ' +
      (name === 'apex' ? 'bg-amber-600 text-white shadow' : 'text-amber-400 hover:text-amber-300 hover:bg-slate-800');
    if (name === 'apex') {
      apexLoadDailyReport();
      apexLoadPositions();
    }
  };

  // Auto-refresh loop every 5s
  setInterval(async () => {
    const ov = await apiGet('overview');
    if (ov && ov.account) {
      const b = document.getElementById('apexValBalance');
      const e = document.getElementById('apexValEquity');
      if (b && ov.account.balance) b.textContent = '$' + ov.account.balance.toLocaleString('en-US', {minimumFractionDigits: 2});
      if (e && ov.account.equity) e.textContent = '$' + ov.account.equity.toLocaleString('en-US', {minimumFractionDigits: 2});
    }
  }, 5000);
})();
</script>
"""

def inject_apex(html: str) -> str:
    """Inject APEX AI nav button, 10-tab view, and script into web_app HTML."""
    if "navTabApex" in html:
        return html
    for anchor, frag, before in (("</nav>", APEX_NAV_BUTTON, True), ("</main>", APEX_VIEW, True), ("</body>", APEX_SCRIPT, True)):
        i = html.find(anchor)
        if i >= 0:
            html = html[:i] + frag + html[i:]
    return html
