with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace H avatar with 3D bullion emblem
old_avatar = """      <div class="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/20 font-black text-white text-lg">
        H
      </div>"""

new_avatar = """      <div class="w-10 h-10 rounded-xl overflow-hidden border border-amber-500/40 shadow-lg shadow-amber-500/20 relative group">
        <img src="/static/images/gold_bullion_3d.jpg" alt="Headway Institutional" class="w-full h-full object-cover filter brightness-105">
      </div>"""

assert old_avatar in code, "old_avatar not found"
code = code.replace(old_avatar, new_avatar)

# Enhance renderQuotes with symbol badges
old_quotes_map = """      bar.innerHTML = Object.entries(quotes).map(([sym, q]) => `
        <div onclick="selectSymbol('${sym}')" class="cursor-pointer hover:bg-slate-900 px-2 py-1 rounded border border-transparent hover:border-bordercol transition flex items-center gap-2">
          <span class="font-bold text-slate-200 font-sans">${sym}</span>
          <span class="text-slate-400">${q.bid}</span>
          <span class="text-[10px] px-1 rounded bg-slate-800 text-slate-500">Spread ${q.spread}</span>
        </div>
      `).join('<span class="text-slate-700">&bull;</span>');"""

new_quotes_map = """      const symIcons = { 'XAUUSD': '🟡', 'BTCUSD': '🟠', 'ETHUSD': '🔷', 'SOLUSD': '🟣', 'EURUSD': '💶', 'GBPUSD': '💷', 'USDJPY': '💴' };
      bar.innerHTML = Object.entries(quotes).map(([sym, q]) => `
        <div onclick="selectSymbol('${sym}')" class="cursor-pointer hover:bg-slate-900 px-2.5 py-1 rounded-lg border border-transparent hover:border-bordercol transition flex items-center gap-2">
          <span class="text-xs">${symIcons[sym] || '📊'}</span>
          <span class="font-bold text-slate-200 font-sans text-xs">${sym}</span>
          <span class="text-slate-300 font-mono text-xs font-bold">${q.bid}</span>
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 font-mono">Spr ${q.spread}</span>
        </div>
      `).join('<span class="text-slate-700">&bull;</span>');"""

assert old_quotes_map in code, "old_quotes_map not found"
code = code.replace(old_quotes_map, new_quotes_map)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Header emblem and ticker badges applied!")
