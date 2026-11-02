with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update metric box
old_box = """          <div class="p-2.5 rounded-lg bg-slate-950/60 border border-bordercol">
            <span class="text-[10px] text-slate-400 uppercase block">Open Gold Position</span>
            <span id="goldOpenPosStatus" class="font-bold text-slate-300">None (0/1)</span>
          </div>"""

new_box = """          <div class="p-2.5 rounded-lg bg-slate-950/60 border border-bordercol">
            <span class="text-[10px] text-slate-400 uppercase block">Active Concurrency</span>
            <span id="goldOpenPosStatus" class="font-bold text-amber-300">0 / 5 Trades (Auto-Replace on TP)</span>
          </div>"""

assert old_box.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_box not found"
code = code.replace(old_box.replace("\r\n", "\n"), new_box) if "\r\n" not in code else code.replace(old_box.replace("\n", "\r\n"), new_box.replace("\n", "\r\n"))

# 2. Update renderGoldAutoStatus
old_status_func = """      const openPosEl = document.getElementById('goldOpenPosStatus');
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
      }"""

new_status_func = """      const openPosEl = document.getElementById('goldOpenPosStatus');
      const legsCountEl = document.getElementById('goldOpenLegsCount');
      const maxCap = st.max_concurrent_trades || 5;
      if (legsCountEl) {
        legsCountEl.innerText = `${openPositions.length} / ${maxCap} Active Trades ${openPositions.length >= maxCap ? '⚡ CAP FULL (5/5)' : '⚡ AUTO-REPLACE ON TP ACTIVE'}`;
      }

      if (openPosEl) {
        if (openPositions.length > 0) {
          openPosEl.className = 'font-bold text-emeraldaccent';
          openPosEl.innerText = `${openPositions.length} / ${maxCap} Active Trades (${openPositions.map(p => `#${p.ticket} $${p.profit}`).join(', ')})`;
        } else {
          openPosEl.className = 'font-bold text-slate-400';
          openPosEl.innerText = `0 / ${maxCap} Active (Auto-Replace Ready)`;
        }
      }"""

assert old_status_func.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_status_func not found"
code = code.replace(old_status_func.replace("\r\n", "\n"), new_status_func) if "\r\n" not in code else code.replace(old_status_func.replace("\n", "\r\n"), new_status_func.replace("\n", "\r\n"))

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("web_app.py updated successfully!")
