def update_setup_cards():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    target = """                  <button onclick="executeGoldSetupNow('${s.direction}', ${s.entry}, ${s.sl}, ${s.tp1}, ${s.confidence_score}, '${(s.strategy||'').replace(/'/g, "\\\\'")}')" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black transition shadow-lg shadow-amber-500/20 flex items-center gap-1.5">
                    ⚡ Instant Execute (1 Trade)
                  </button>"""

    replace = """                  <button onclick="executeGoldSetupNow('${s.direction}', ${s.entry}, ${s.sl}, ${s.tp1}, ${s.confidence_score}, '${(s.strategy||'').replace(/'/g, "\\\\'")}', '${s.timeframe}')" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black transition shadow-lg shadow-amber-500/20 flex items-center gap-1.5">
                    ⚡ Execute Twin Trade (Fixed + Trailing)
                  </button>"""

    if target in content:
        content = content.replace(target, replace, 1)
        with open('web_app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated setup card button to 'Execute Twin Trade (Fixed + Trailing)'")
        return True
    else:
        print("Target not found!")
        return False

if __name__ == '__main__':
    update_setup_cards()
