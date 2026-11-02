"""
apply_rescan_and_dismiss_update.py
==================================
Updates web_app.py to satisfy user requirements:
1. When a trade is taken from Recommended Trade Setups, immediately remove that setup from the list.
2. Remove the 2-minute / 3-minute automatic re-scan loop and countdown ticker so the scanner only runs on demand when the user clicks 'Re-Scan Now'.
3. Adds /api/setups/dismiss endpoint to permanently exclude taken/dismissed setups.
4. Adds quick dismiss (X) button on setup cards.
"""

from pathlib import Path

app_path = Path("web_app.py")
text = app_path.read_text(encoding="utf-8")

# 1. Update AutomatedSetupScanner.__init__ to disable auto rescan and add dismissed_setups
init_marker = '''        self.journal = self.load_journal()
        self.auto_trade_enabled = self.load_config()
        self.running = True'''

init_replacement = '''        self.journal = self.load_journal()
        self.auto_trade_enabled = self.load_config()
        self.auto_rescan_enabled = False  # Disabled: 2-min auto rescan removed as requested
        self.dismissed_setups = set()     # Set of (symbol, action) dismissed/taken setups
        self.running = True'''

assert init_marker in text, "init_marker not found"
text = text.replace(init_marker, init_replacement, 1)

# 2. Add dismiss_setup method to AutomatedSetupScanner
dismiss_method_code = '''    def dismiss_setup(self, setup_id=None, symbol=None, action=None):
        """Immediately removes a setup from current recommendations and adds to dismissed set."""
        with self.lock:
            self.current_setups = [
                s for s in self.current_setups
                if s.get("id") != setup_id and not (symbol and s.get("symbol") == symbol and s.get("action") == (action or "").upper())
            ]
            if symbol and action:
                self.dismissed_setups.add((symbol, action.upper()))
            elif symbol:
                self.dismissed_setups.add((symbol, "BUY"))
                self.dismissed_setups.add((symbol, "SELL"))
            self._update_status_message()
            print(f"[Scanner] Dismissed setup for {symbol} ({action}). Current active setups remaining: {len(self.current_setups)}")

    def record_execution(self, setup_id,'''

record_exec_marker = "    def record_execution(self, setup_id,"
assert record_exec_marker in text, "record_exec_marker not found"
text = text.replace(record_exec_marker, dismiss_method_code, 1)

# 3. In run_scan_now: check dismissed_setups
dismissed_check_marker = '''                # 1. LIVE POSITION AWARENESS (Rule 3): Prevent duplicates
                if (sym, bias) in open_pos:'''

dismissed_check_replacement = '''                # Check if setup was taken or dismissed by user
                if (sym, bias) in self.dismissed_setups:
                    filtered_reasons[sym] = f"Setup on {sym} ({bias}) was taken or dismissed by user"
                    continue

                # 1. LIVE POSITION AWARENESS (Rule 3): Prevent duplicates
                if (sym, bias) in open_pos:'''

assert dismissed_check_marker in text, "dismissed_check_marker not found"
text = text.replace(dismissed_check_marker, dismissed_check_replacement, 1)

# 4. In _run_loop: respect auto_rescan_enabled (stop auto re-scan every 2-3 mins)
loop_marker = '''    def _run_loop(self):
        """Continuous background thread executing every 3 minutes."""
        time.sleep(1)
        self.run_scan_now()
        
        while self.running:
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
                with self.lock:
                    if self.next_scan_seconds > 0:
                        self.next_scan_seconds -= 1
            if self.running:
                self.run_scan_now()'''

loop_replacement = '''    def _run_loop(self):
        """Initial startup scan, then re-scans ONLY if auto_rescan_enabled is True or user clicks Re-Scan."""
        time.sleep(1)
        self.run_scan_now()
        
        while self.running:
            if not self.auto_rescan_enabled:
                time.sleep(1.0)
                continue
            for _ in range(self.interval):
                if not self.running or not self.auto_rescan_enabled:
                    break
                time.sleep(1)
                with self.lock:
                    if self.next_scan_seconds > 0:
                        self.next_scan_seconds -= 1
            if self.running and self.auto_rescan_enabled:
                self.run_scan_now()'''

assert loop_marker in text, "loop_marker not found"
text = text.replace(loop_marker, loop_replacement, 1)

# 5. Add /api/setups/dismiss endpoint in DerivServer.do_POST
post_marker = '        elif url.path == "/api/profit_chaser/config":'
dismiss_post_route = '''        elif url.path == "/api/setups/dismiss":
            sid = data.get("setup_id")
            sym = data.get("symbol")
            act = data.get("action")
            if scanner:
                scanner.dismiss_setup(setup_id=sid, symbol=sym, action=act)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": f"Setup {sym} {act} dismissed"}).encode("utf-8"))
        elif url.path == "/api/profit_chaser/config":'''

assert post_marker in text, "post_marker not found"
text = text.replace(post_marker, dismiss_post_route, 1)

# 6. Update HTML: Replace Countdown ticker with clean "MANUAL ON DEMAND" badge
html_countdown_old = '''          <!-- Countdown badge -->
          <div class="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-bordercol text-slate-300">
            <span class="w-2 h-2 rounded-full bg-cyanaccent animate-pulse"></span>
            <span>Next Scan: <span id="rescanCountdown" class="text-white font-bold">03:00</span></span>
            <span class="text-slate-500 text-[10px] ml-1">(Last: <span id="lastScanTime" class="text-slate-400">--</span>)</span>
          </div>'''

html_countdown_new = '''          <!-- Scan Mode Badge (2-min auto rescan removed as requested) -->
          <div class="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-bordercol text-slate-300">
            <span class="w-2 h-2 rounded-full bg-emeraldaccent"></span>
            <span class="text-slate-400 font-sans">Scan Mode:</span>
            <span class="text-emeraldaccent font-bold" id="rescanCountdown">ON DEMAND (Manual)</span>
            <span class="text-slate-500 text-[10px] ml-1">(Last: <span id="lastScanTime" class="text-slate-400">--</span>)</span>
          </div>'''

assert html_countdown_old in text, "html_countdown_old not found"
text = text.replace(html_countdown_old, html_countdown_new, 1)

# 7. Update Action Buttons on setup cards: Add Dismiss button
old_buttons = '''                <div class="grid grid-cols-2 gap-2">
                  <button type="button" onclick='loadSetupIntoForm(${JSON.stringify(s)})' class="py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition flex items-center justify-center gap-1 border border-bordercol">
                    Load Setup
                  </button>
                  <button type="button" onclick='executeSetupDirectly(${JSON.stringify(s)})' class="py-1.5 rounded-lg ${isBuy ? 'bg-emeraldaccent hover:bg-emerald-600' : 'bg-crimsonaccent hover:bg-red-600'} text-white font-bold text-xs transition shadow flex items-center justify-center gap-1">
                    1-Click Single
                  </button>
                </div>'''

new_buttons = '''                <div class="grid grid-cols-3 gap-1.5">
                  <button type="button" onclick='loadSetupIntoForm(${JSON.stringify(s)})' class="py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition flex items-center justify-center gap-1 border border-bordercol">
                    Load Setup
                  </button>
                  <button type="button" onclick='executeSetupDirectly(${JSON.stringify(s)})' class="py-1.5 rounded-lg ${isBuy ? 'bg-emeraldaccent hover:bg-emerald-600' : 'bg-crimsonaccent hover:bg-red-600'} text-white font-bold text-xs transition shadow flex items-center justify-center gap-1">
                    1-Click
                  </button>
                  <button type="button" onclick='dismissSetupCard("${s.id}", "${s.symbol}", "${s.action}")' class="py-1.5 rounded-lg bg-slate-800/80 hover:bg-red-500/20 text-slate-400 hover:text-red-400 font-bold text-xs transition flex items-center justify-center gap-1 border border-bordercol" title="Dismiss / Remove this Setup">
                    ✕ Dismiss
                  </button>
                </div>'''

assert old_buttons in text, "old_buttons not found"
text = text.replace(old_buttons, new_buttons, 1)

# 8. Add dismissSetupCard function and update executeMtpDirectlyFromSetup
old_execute_mtp = '''        const out = await res.json();
        alert(out.message);
        fetchMultiTpGroups();
        fetchSetups();
        refreshAll();'''

new_execute_mtp = '''        const out = await res.json();
        alert(out.message);
        // Immediately remove taken setup card from Recommended Setups
        dismissSetupCard(s.id, s.symbol, s.action);
        fetchMultiTpGroups();
        refreshAll();'''

assert old_execute_mtp in text, "old_execute_mtp not found"
text = text.replace(old_execute_mtp, new_execute_mtp, 1)

# 9. Update executeSetupDirectly to dismiss setup card immediately
old_exec_direct = '''          const card = document.getElementById(`setup-card-${s.id}`);
          if (card) {
            card.style.transition = 'all 0.35s ease-out';
            card.style.opacity = '0';
            setTimeout(() => card.remove(), 350);
          }
          refreshAll();
          fetchSetups();'''

new_exec_direct = '''          dismissSetupCard(s.id, s.symbol, s.action);
          refreshAll();'''

assert old_exec_direct in text, "old_exec_direct not found"
text = text.replace(old_exec_direct, new_exec_direct, 1)

# 10. Add dismissSetupCard helper function into JS
js_helper_marker = "    function loadSetupIntoForm(s) {"
dismiss_js_func = '''    async function dismissSetupCard(setupId, symbol, action) {
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

    function loadSetupIntoForm(s) {'''

assert js_helper_marker in text, "js_helper_marker not found"
text = text.replace(js_helper_marker, dismiss_js_func, 1)

# 11. Disable updateCountdown from auto-triggering fetchSetups every 2-3 mins
old_update_countdown = '''    function updateCountdown() {
      const countdownEl = document.getElementById('rescanCountdown');
      if (localSecondsLeft <= 0) {
        localSecondsLeft = 180;
        fetchSetups();
      } else {
        localSecondsLeft--;
      }
      if (countdownEl) {
        const mins = Math.floor(localSecondsLeft / 60);
        const secs = localSecondsLeft % 60;
        countdownEl.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      }
    }'''

new_update_countdown = '''    function updateCountdown() {
      // Automatic 2-minute periodic rescan is permanently REMOVED as requested.
      // Re-scan is strictly manual / on demand via 'Re-Scan Now' button.
      const countdownEl = document.getElementById('rescanCountdown');
      if (countdownEl) {
        countdownEl.innerText = 'ON DEMAND (Manual)';
      }
    }'''

assert old_update_countdown in text, "old_update_countdown not found"
text = text.replace(old_update_countdown, new_update_countdown, 1)

app_path.write_text(text, encoding="utf-8")
print("[+] Successfully updated web_app.py: Taken setups removed + 2-min auto rescan removed!")
