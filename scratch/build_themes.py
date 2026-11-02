"""
scratch/build_themes.py
=======================
Injects 5 Modern Institutional Themes with visual artwork and interactive switcher:
1. 👑 Obsidian & 24K Bullion Gold (Luxury Swiss Quant)
2. ⚡ Cyberpunk Terminal & Tokyo Neon (High-Frequency 2077)
3. 💎 Emerald Matrix & Quantum Alpha (Peak Algorithmic Profit)
4. 🌊 Sapphire Horizon & Nordic Frost (Clean Stripe/Linear Ultra)
5. 🔥 Solar Flare & Crimson Forge (Aggressive Volatility Trader)
"""

with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. CSS Styles injection
css_themes = """
  <style>
    /* ------------------------------------------------------------- */
    /* THEME SYSTEM STYLES & DYNAMIC VARIABLES                       */
    /* ------------------------------------------------------------- */
    :root, html[data-theme="gold-obsidian"], html:not([data-theme]) {
      --bg-primary: #07090e;
      --bg-header: #0d111a;
      --bg-panel: #111622;
      --bg-card: rgba(18, 24, 38, 0.85);
      --border-main: rgba(245, 158, 11, 0.28);
      --border-glow: rgba(245, 158, 11, 0.4);
      --accent-primary: #f59e0b;
      --accent-secondary: #fbbf24;
      --accent-gradient: linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #b45309 100%);
      --accent-text: #fef3c7;
      --tag-bg: rgba(245, 158, 11, 0.15);
      --card-shadow: 0 10px 30px -10px rgba(245, 158, 11, 0.15);
      --hero-overlay: radial-gradient(circle at 50% 0%, rgba(245, 158, 11, 0.12) 0%, transparent 70%);
    }

    html[data-theme="cyberpunk-neon"] {
      --bg-primary: #05050f;
      --bg-header: #0a081a;
      --bg-panel: #0e0c24;
      --bg-card: rgba(18, 14, 40, 0.85);
      --border-main: rgba(0, 240, 255, 0.35);
      --border-glow: rgba(236, 72, 153, 0.4);
      --accent-primary: #00f0ff;
      --accent-secondary: #ec4899;
      --accent-gradient: linear-gradient(135deg, #00f0ff 0%, #a855f7 50%, #ec4899 100%);
      --accent-text: #cffafe;
      --tag-bg: rgba(0, 240, 255, 0.15);
      --card-shadow: 0 10px 30px -10px rgba(0, 240, 255, 0.22);
      --hero-overlay: radial-gradient(circle at 50% 0%, rgba(0, 240, 255, 0.15) 0%, rgba(236, 72, 153, 0.08) 50%, transparent 75%);
    }

    html[data-theme="emerald-matrix"] {
      --bg-primary: #040907;
      --bg-header: #07150e;
      --bg-panel: #0a1c13;
      --bg-card: rgba(12, 32, 22, 0.85);
      --border-main: rgba(16, 185, 129, 0.32);
      --border-glow: rgba(0, 245, 155, 0.4);
      --accent-primary: #10b981;
      --accent-secondary: #00f59b;
      --accent-gradient: linear-gradient(135deg, #34d399 0%, #10b981 50%, #047857 100%);
      --accent-text: #d1fae5;
      --tag-bg: rgba(16, 185, 129, 0.15);
      --card-shadow: 0 10px 30px -10px rgba(16, 185, 129, 0.18);
      --hero-overlay: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.15) 0%, transparent 70%);
    }

    html[data-theme="sapphire-nordic"] {
      --bg-primary: #070e1b;
      --bg-header: #0c172a;
      --bg-panel: #111f38;
      --bg-card: rgba(19, 34, 60, 0.85);
      --border-main: rgba(56, 189, 248, 0.32);
      --border-glow: rgba(59, 130, 246, 0.4);
      --accent-primary: #38bdf8;
      --accent-secondary: #3b82f6;
      --accent-gradient: linear-gradient(135deg, #38bdf8 0%, #3b82f6 50%, #1d4ed8 100%);
      --accent-text: #e0f2fe;
      --tag-bg: rgba(56, 189, 248, 0.15);
      --card-shadow: 0 10px 30px -10px rgba(59, 130, 246, 0.2);
      --hero-overlay: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.14) 0%, transparent 70%);
    }

    html[data-theme="solar-forge"] {
      --bg-primary: #0a0606;
      --bg-header: #140b0b;
      --bg-panel: #1c1010;
      --bg-card: rgba(32, 16, 16, 0.85);
      --border-main: rgba(249, 115, 22, 0.35);
      --border-glow: rgba(239, 68, 68, 0.4);
      --accent-primary: #f97316;
      --accent-secondary: #ef4444;
      --accent-gradient: linear-gradient(135deg, #fb923c 0%, #f97316 50%, #dc2626 100%);
      --accent-text: #ffedd5;
      --tag-bg: rgba(249, 115, 22, 0.15);
      --card-shadow: 0 10px 30px -10px rgba(249, 115, 22, 0.22);
      --hero-overlay: radial-gradient(circle at 50% 0%, rgba(249, 115, 22, 0.15) 0%, rgba(239, 68, 68, 0.08) 50%, transparent 70%);
    }

    body {
      background-color: var(--bg-primary) !important;
      background-image: var(--hero-overlay);
      background-attachment: fixed;
      color: #E5E7EB;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      transition: background-color 0.35s ease, background-image 0.35s ease;
    }
    
    header {
      background-color: var(--bg-header) !important;
      border-color: var(--border-main) !important;
      transition: all 0.35s ease;
    }
    
    .bg-panel {
      background-color: var(--bg-card) !important;
      border-color: var(--border-main) !important;
      box-shadow: var(--card-shadow) !important;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      transition: all 0.35s ease;
    }

    .border-bordercol {
      border-color: var(--border-main) !important;
    }

    .theme-active-pill {
      box-shadow: 0 0 15px var(--border-glow) !important;
      border-color: var(--accent-primary) !important;
      color: #ffffff !important;
      font-weight: 800 !important;
    }

    /* Modal Animation */
    .modal-enter {
      animation: modalFadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    @keyframes modalFadeIn {
      from { opacity: 0; transform: scale(0.96) translateY(10px); }
      to { opacity: 1; transform: scale(1) translateY(0); }
    }

    .custom-scroll::-webkit-scrollbar { width: 5px; height: 5px; }
    .custom-scroll::-webkit-scrollbar-track { background: var(--bg-primary); }
    .custom-scroll::-webkit-scrollbar-thumb { background: var(--border-main); border-radius: 3px; }
  </style>
"""

# Replace old style tag
old_style_target = """  <style>
    body { background-color: #0B0E14; color: #E5E7EB; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .custom-scroll::-webkit-scrollbar { width: 5px; height: 5px; }
    .custom-scroll::-webkit-scrollbar-track { background: #121722; }
    .custom-scroll::-webkit-scrollbar-thumb { background: #222C40; border-radius: 3px; }
  </style>"""

assert old_style_target.replace("\r\n", "\n") in code.replace("\r\n", "\n"), "old_style_target not found"
code = code.replace(old_style_target.replace("\r\n", "\n"), css_themes) if "\r\n" not in code else code.replace(old_style_target.replace("\n", "\r\n"), css_themes.replace("\n", "\r\n"))

# 2. Add Theme Bar and Gallery Modal right after </header>
theme_bar_html = """
  <!-- Interactive Theme Studio Bar (5 Modern Live Demos) -->
  <div class="border-b border-bordercol px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 shadow-md z-40 transition" style="background-color: var(--bg-header)">
    <div class="flex items-center gap-3">
      <div class="w-7 h-7 rounded-lg flex items-center justify-center text-sm shadow-inner" style="background: var(--tag-bg); border: 1px solid var(--border-main)">
        🎨
      </div>
      <div>
        <div class="flex items-center gap-2">
          <span class="text-xs font-black text-white uppercase tracking-wider">Modern Theme Studio</span>
          <span id="activeThemePillBadge" class="text-[10px] px-2 py-0.5 rounded-full font-mono font-bold" style="background: var(--tag-bg); color: var(--accent-primary); border: 1px solid var(--border-main)">
            👑 24K OBSIDIAN GOLD
          </span>
        </div>
        <p class="text-[11px] text-slate-400">Click any theme to transform the entire workstation in real time:</p>
      </div>
    </div>

    <!-- 5 Live Theme Pills -->
    <div class="flex items-center gap-2 overflow-x-auto custom-scroll pb-1">
      <button onclick="setAppTheme('gold-obsidian')" id="pill_gold-obsidian" class="theme-pill px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-amber-500/40 bg-amber-500/20 text-amber-300 shadow">
        <span>👑</span> <span>24K Gold</span>
      </button>
      <button onclick="setAppTheme('cyberpunk-neon')" id="pill_cyberpunk-neon" class="theme-pill px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-800 bg-slate-900/60 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40">
        <span>⚡</span> <span>Cyberpunk</span>
      </button>
      <button onclick="setAppTheme('emerald-matrix')" id="pill_emerald-matrix" class="theme-pill px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-800 bg-slate-900/60 text-slate-300 hover:text-emerald-300 hover:border-emerald-500/40">
        <span>💎</span> <span>Emerald Alpha</span>
      </button>
      <button onclick="setAppTheme('sapphire-nordic')" id="pill_sapphire-nordic" class="theme-pill px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-800 bg-slate-900/60 text-slate-300 hover:text-blue-300 hover:border-blue-500/40">
        <span>🌊</span> <span>Sapphire</span>
      </button>
      <button onclick="setAppTheme('solar-forge')" id="pill_solar-forge" class="theme-pill px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-800 bg-slate-900/60 text-slate-300 hover:text-orange-300 hover:border-orange-500/40">
        <span>🔥</span> <span>Solar Forge</span>
      </button>
      <button onclick="openThemeGalleryModal()" class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg flex items-center gap-1.5">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
        <span>Inspect All 5 Themes</span>
      </button>
    </div>
  </div>

  <!-- THEME DEMO GALLERY MODAL (Interactive Visual Showcase) -->
  <div id="themeGalleryModal" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md hidden flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
    <div class="modal-enter max-w-5xl w-full rounded-3xl bg-slate-900/95 border border-bordercol shadow-2xl p-6 sm:p-8 space-y-6 relative overflow-hidden max-h-[90vh] overflow-y-auto custom-scroll" style="background-color: var(--bg-panel); border-color: var(--border-main)">
      
      <!-- Modal Header -->
      <div class="flex items-center justify-between border-b border-bordercol pb-4">
        <div class="flex items-center gap-3.5">
          <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl shadow-lg" style="background: var(--accent-gradient); color: #000">
            🎨
          </div>
          <div>
            <h2 class="text-xl font-black text-white tracking-tight flex items-center gap-2">
              Modern Trading Theme Gallery
              <span class="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                5 BESPOKE DEMOS
              </span>
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">Explore each visual direction with custom artwork, color tokens, and sample cards. Click "Apply & Select" to activate.</p>
          </div>
        </div>
        <button onclick="closeThemeGalleryModal()" class="w-9 h-9 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-lg font-bold transition">
          &times;
        </button>
      </div>

      <!-- 5 Theme Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        
        <!-- CARD 1: 24K Obsidian Gold -->
        <div class="rounded-2xl border border-amber-500/40 bg-slate-950/80 p-5 space-y-4 hover:border-amber-400 transition shadow-xl relative overflow-hidden flex flex-col justify-between">
          <div class="space-y-3">
            <div class="h-28 rounded-xl bg-gradient-to-br from-amber-950/70 via-black to-slate-950 border border-amber-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-amber-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-bold">THEME 01</span>
                <h3 class="text-base font-black text-white mt-1">24K Obsidian Gold</h3>
                <p class="text-[11px] text-amber-200/80">Swiss Quant &amp; Bullion Desk</p>
              </div>
              <div class="text-4xl filter drop-shadow">👑</div>
            </div>
            
            <p class="text-xs text-slate-300 leading-relaxed">
              Deep celestial obsidian black canvas paired with metallic 24K Gold highlights and warm champagne text. Designed specifically for institutional Gold traders.
            </p>

            <div class="flex items-center gap-1.5 pt-1">
              <span class="w-4 h-4 rounded-full bg-[#fbbf24] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#f59e0b] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#07090e] border border-amber-500/50 shadow-sm"></span>
              <span class="text-[10px] font-mono text-slate-400 ml-1">#fbbf24 • #f59e0b • #07090e</span>
            </div>
          </div>

          <button onclick="setAppTheme('gold-obsidian'); closeThemeGalleryModal();" class="w-full py-2.5 rounded-xl font-black text-xs transition bg-gradient-to-r from-amber-500 to-yellow-600 hover:from-amber-400 hover:to-yellow-500 text-slate-950 shadow-lg shadow-amber-500/20">
            Apply 24K Obsidian Gold
          </button>
        </div>

        <!-- CARD 2: Cyberpunk Neon -->
        <div class="rounded-2xl border border-cyan-500/40 bg-slate-950/80 p-5 space-y-4 hover:border-cyan-400 transition shadow-xl relative overflow-hidden flex flex-col justify-between">
          <div class="space-y-3">
            <div class="h-28 rounded-xl bg-gradient-to-br from-indigo-950/80 via-black to-slate-950 border border-cyan-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-cyan-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold">THEME 02</span>
                <h3 class="text-base font-black text-white mt-1">Cyberpunk Neon</h3>
                <p class="text-[11px] text-cyan-200/80">Tokyo 2077 Quant Terminal</p>
              </div>
              <div class="text-4xl filter drop-shadow">⚡</div>
            </div>
            
            <p class="text-xs text-slate-300 leading-relaxed">
              Ultra-modern midnight violet canvas illuminated with electric cyan and neon fuchsia laser glow. Gives the station an adrenaline-fueled high-frequency feel.
            </p>

            <div class="flex items-center gap-1.5 pt-1">
              <span class="w-4 h-4 rounded-full bg-[#00f0ff] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#ec4899] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#05050f] border border-cyan-500/50 shadow-sm"></span>
              <span class="text-[10px] font-mono text-slate-400 ml-1">#00f0ff • #ec4899 • #05050f</span>
            </div>
          </div>

          <button onclick="setAppTheme('cyberpunk-neon'); closeThemeGalleryModal();" class="w-full py-2.5 rounded-xl font-black text-xs transition bg-gradient-to-r from-cyan-500 to-fuchsia-600 hover:from-cyan-400 hover:to-fuchsia-500 text-white shadow-lg shadow-cyan-500/20">
            Apply Cyberpunk Neon
          </button>
        </div>

        <!-- CARD 3: Emerald Matrix -->
        <div class="rounded-2xl border border-emerald-500/40 bg-slate-950/80 p-5 space-y-4 hover:border-emerald-400 transition shadow-xl relative overflow-hidden flex flex-col justify-between">
          <div class="space-y-3">
            <div class="h-28 rounded-xl bg-gradient-to-br from-emerald-950/80 via-black to-slate-950 border border-emerald-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-emerald-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">THEME 03</span>
                <h3 class="text-base font-black text-white mt-1">Emerald Matrix</h3>
                <p class="text-[11px] text-emerald-200/80">Peak Profit &amp; Algorithmic Alpha</p>
              </div>
              <div class="text-4xl filter drop-shadow">💎</div>
            </div>
            
            <p class="text-xs text-slate-300 leading-relaxed">
              Deep graphite obsidian with vivid cyber mint and emerald green HUD accents. Clean, authoritative, and laser-focused on win rate and equity growth.
            </p>

            <div class="flex items-center gap-1.5 pt-1">
              <span class="w-4 h-4 rounded-full bg-[#10b981] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#00f59b] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#040907] border border-emerald-500/50 shadow-sm"></span>
              <span class="text-[10px] font-mono text-slate-400 ml-1">#10b981 • #00f59b • #040907</span>
            </div>
          </div>

          <button onclick="setAppTheme('emerald-matrix'); closeThemeGalleryModal();" class="w-full py-2.5 rounded-xl font-black text-xs transition bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 shadow-lg shadow-emerald-500/20">
            Apply Emerald Matrix
          </button>
        </div>

        <!-- CARD 4: Sapphire Nordic -->
        <div class="rounded-2xl border border-sky-500/40 bg-slate-950/80 p-5 space-y-4 hover:border-sky-400 transition shadow-xl relative overflow-hidden flex flex-col justify-between">
          <div class="space-y-3">
            <div class="h-28 rounded-xl bg-gradient-to-br from-blue-950/80 via-black to-slate-950 border border-sky-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-blue-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 font-bold">THEME 04</span>
                <h3 class="text-base font-black text-white mt-1">Sapphire Horizon</h3>
                <p class="text-[11px] text-sky-200/80">Nordic Frost &amp; Linear Precision</p>
              </div>
              <div class="text-4xl filter drop-shadow">🌊</div>
            </div>
            
            <p class="text-xs text-slate-300 leading-relaxed">
              Oceanic deep navy slate paired with crisp frosted glass and sapphire blue accents. Inspired by top-tier modern Silicon Valley fintech interfaces (Linear, Stripe).
            </p>

            <div class="flex items-center gap-1.5 pt-1">
              <span class="w-4 h-4 rounded-full bg-[#38bdf8] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#3b82f6] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#070e1b] border border-sky-500/50 shadow-sm"></span>
              <span class="text-[10px] font-mono text-slate-400 ml-1">#38bdf8 • #3b82f6 • #070e1b</span>
            </div>
          </div>

          <button onclick="setAppTheme('sapphire-nordic'); closeThemeGalleryModal();" class="w-full py-2.5 rounded-xl font-black text-xs transition bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white shadow-lg shadow-sky-500/20">
            Apply Sapphire Horizon
          </button>
        </div>

        <!-- CARD 5: Solar Forge -->
        <div class="rounded-2xl border border-orange-500/40 bg-slate-950/80 p-5 space-y-4 hover:border-orange-400 transition shadow-xl relative overflow-hidden flex flex-col justify-between">
          <div class="space-y-3">
            <div class="h-28 rounded-xl bg-gradient-to-br from-orange-950/80 via-black to-slate-950 border border-orange-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-orange-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-500/30 font-bold">THEME 05</span>
                <h3 class="text-base font-black text-white mt-1">Solar Forge</h3>
                <p class="text-[11px] text-orange-200/80">Volcanic Momentum &amp; Breakouts</p>
              </div>
              <div class="text-4xl filter drop-shadow">🔥</div>
            </div>
            
            <p class="text-xs text-slate-300 leading-relaxed">
              Volcanic dark basalt with glowing solar flame and crimson forge accents. Built for aggressive momentum breakouts and fast-moving volatility surges.
            </p>

            <div class="flex items-center gap-1.5 pt-1">
              <span class="w-4 h-4 rounded-full bg-[#f97316] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#ef4444] shadow-sm"></span>
              <span class="w-4 h-4 rounded-full bg-[#0a0606] border border-orange-500/50 shadow-sm"></span>
              <span class="text-[10px] font-mono text-slate-400 ml-1">#f97316 • #ef4444 • #0a0606</span>
            </div>
          </div>

          <button onclick="setAppTheme('solar-forge'); closeThemeGalleryModal();" class="w-full py-2.5 rounded-xl font-black text-xs transition bg-gradient-to-r from-orange-500 to-rose-600 hover:from-orange-400 hover:to-rose-500 text-white shadow-lg shadow-orange-500/20">
            Apply Solar Forge
          </button>
        </div>

      </div>

      <!-- Modal Footer -->
      <div class="flex items-center justify-between border-t border-bordercol pt-4 text-xs font-mono text-slate-400">
        <span>Active Theme Stored in LocalStorage</span>
        <button onclick="closeThemeGalleryModal()" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold transition">
          Close Gallery
        </button>
      </div>

    </div>
  </div>
"""

target_header_end = '</header>'
assert target_header_end in code, "</header> not found"
code = code.replace(target_header_end, target_header_end + "\n" + theme_bar_html, 1)

# 3. Add JavaScript Controller for Theme Management
js_theme_controller = """
  // ==============================================================================
  // 5-THEME DYNAMIC ENGINE & LOCALSTORAGE PERSISTENCE
  // ==============================================================================
  const THEME_NAMES = {
    'gold-obsidian': '👑 24K OBSIDIAN GOLD',
    'cyberpunk-neon': '⚡ CYBERPUNK NEON',
    'emerald-matrix': '💎 EMERALD ALPHA',
    'sapphire-nordic': '🌊 SAPPHIRE HORIZON',
    'solar-forge': '🔥 SOLAR FORGE'
  };

  function setAppTheme(themeId) {
    if (!THEME_NAMES[themeId]) themeId = 'gold-obsidian';
    
    // Apply data-theme to root
    document.documentElement.setAttribute('data-theme', themeId);
    try {
      localStorage.setItem('headway_theme', themeId);
    } catch(e) {}

    // Update active badge in quick bar
    const badge = document.getElementById('activeThemePillBadge');
    if (badge) badge.innerText = THEME_NAMES[themeId];

    // Update pill buttons visual state
    ['gold-obsidian', 'cyberpunk-neon', 'emerald-matrix', 'sapphire-nordic', 'solar-forge'].forEach(id => {
      const btn = document.getElementById('pill_' + id);
      if (btn) {
        if (id === themeId) {
          btn.className = 'theme-pill px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 theme-active-pill';
        } else {
          btn.className = 'theme-pill px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white';
        }
      }
    });
  }

  function openThemeGalleryModal() {
    const modal = document.getElementById('themeGalleryModal');
    if (modal) modal.classList.remove('hidden');
  }

  function closeThemeGalleryModal() {
    const modal = document.getElementById('themeGalleryModal');
    if (modal) modal.classList.add('hidden');
  }

  // Load saved theme on boot
  (function initTheme() {
    let saved = 'gold-obsidian';
    try {
      saved = localStorage.getItem('headway_theme') || 'gold-obsidian';
    } catch(e) {}
    setAppTheme(saved);
  })();
"""

# Place JS right before </script> at the bottom
target_script_end = '</script>\n</body>'
if target_script_end not in code:
    target_script_end = '</script>\r\n</body>'

assert target_script_end in code, "target_script_end not found"
code = code.replace(target_script_end, js_theme_controller + "\n" + target_script_end)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Themes successfully built and injected into web_app.py!")
