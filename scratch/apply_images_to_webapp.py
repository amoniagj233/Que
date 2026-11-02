"""
scratch/apply_images_to_webapp.py
=================================
Wires static image file serving and injects rich imagery into:
1. Theme Demo Gallery Modal (real images for all 5 themes)
2. Gold Intelligence Hero Banner (3D Bullion render)
"""

with open("web_app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add static file handler to do_GET
static_handler_code = """        elif url.path.startswith("/static/"):
            rel_path = url.path.lstrip("/").replace("/", os.sep)
            local_file = Path(rel_path)
            if local_file.exists() and local_file.is_file():
                ext = local_file.suffix.lower()
                content_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".svg": "image/svg+xml",
                    ".webp": "image/webp",
                    ".gif": "image/gif",
                    ".css": "text/css",
                    ".js": "application/javascript"
                }
                c_type = content_types.get(ext, "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", c_type)
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                with open(local_file, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return"""

target_do_get_after = """        if url.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))"""

assert target_do_get_after in code, "target_do_get_after not found"
code = code.replace(target_do_get_after, target_do_get_after + "\n" + static_handler_code)

# 2. Update Theme Cards in Theme Gallery Modal with rich images
old_gold_header = """            <div class="h-28 rounded-xl bg-gradient-to-br from-amber-950/70 via-black to-slate-950 border border-amber-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-amber-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-bold">THEME 01</span>
                <h3 class="text-base font-black text-white mt-1">24K Obsidian Gold</h3>
                <p class="text-[11px] text-amber-200/80">Swiss Quant &amp; Bullion Desk</p>
              </div>
              <div class="text-4xl filter drop-shadow">👑</div>
            </div>"""

new_gold_header = """            <div class="h-32 rounded-xl overflow-hidden border border-amber-500/40 relative group">
              <img src="/static/images/gold_bullion_3d.jpg" alt="24K Obsidian Gold" class="w-full h-full object-cover filter brightness-85 group-hover:scale-105 transition duration-500">
              <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"></div>
              <div class="absolute bottom-2.5 left-3 right-3 flex items-end justify-between">
                <div>
                  <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/30 text-amber-300 font-bold border border-amber-500/40">THEME 01</span>
                  <h3 class="text-sm font-black text-white">24K Obsidian Gold</h3>
                </div>
                <div class="text-2xl filter drop-shadow">👑</div>
              </div>
            </div>"""

assert old_gold_header in code, "old_gold_header not found"
code = code.replace(old_gold_header, new_gold_header)

old_cyber_header = """            <div class="h-28 rounded-xl bg-gradient-to-br from-indigo-950/80 via-black to-slate-950 border border-cyan-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-cyan-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold">THEME 02</span>
                <h3 class="text-base font-black text-white mt-1">Cyberpunk Neon</h3>
                <p class="text-[11px] text-cyan-200/80">Tokyo 2077 Quant Terminal</p>
              </div>
              <div class="text-4xl filter drop-shadow">⚡</div>
            </div>"""

new_cyber_header = """            <div class="h-32 rounded-xl overflow-hidden border border-cyan-500/40 relative group">
              <img src="/static/images/theme_cyberpunk_neon.svg" alt="Cyberpunk Neon" class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
              <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"></div>
              <div class="absolute bottom-2.5 left-3 right-3 flex items-end justify-between">
                <div>
                  <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-cyan-500/30 text-cyan-300 font-bold border border-cyan-500/40">THEME 02</span>
                  <h3 class="text-sm font-black text-white">Cyberpunk Neon</h3>
                </div>
                <div class="text-2xl filter drop-shadow">⚡</div>
              </div>
            </div>"""

assert old_cyber_header in code, "old_cyber_header not found"
code = code.replace(old_cyber_header, new_cyber_header)

old_emerald_header = """            <div class="h-28 rounded-xl bg-gradient-to-br from-emerald-950/80 via-black to-slate-950 border border-emerald-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-emerald-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">THEME 03</span>
                <h3 class="text-base font-black text-white mt-1">Emerald Matrix</h3>
                <p class="text-[11px] text-emerald-200/80">Peak Profit &amp; Algorithmic Alpha</p>
              </div>
              <div class="text-4xl filter drop-shadow">💎</div>
            </div>"""

new_emerald_header = """            <div class="h-32 rounded-xl overflow-hidden border border-emerald-500/40 relative group">
              <img src="/static/images/theme_emerald_matrix.svg" alt="Emerald Matrix" class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
              <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"></div>
              <div class="absolute bottom-2.5 left-3 right-3 flex items-end justify-between">
                <div>
                  <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/30 text-emerald-300 font-bold border border-emerald-500/40">THEME 03</span>
                  <h3 class="text-sm font-black text-white">Emerald Matrix</h3>
                </div>
                <div class="text-2xl filter drop-shadow">💎</div>
              </div>
            </div>"""

assert old_emerald_header in code, "old_emerald_header not found"
code = code.replace(old_emerald_header, new_emerald_header)

old_sapphire_header = """            <div class="h-28 rounded-xl bg-gradient-to-br from-blue-950/80 via-black to-slate-950 border border-sky-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-blue-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 font-bold">THEME 04</span>
                <h3 class="text-base font-black text-white mt-1">Sapphire Horizon</h3>
                <p class="text-[11px] text-sky-200/80">Nordic Frost &amp; Linear Precision</p>
              </div>
              <div class="text-4xl filter drop-shadow">🌊</div>
            </div>"""

new_sapphire_header = """            <div class="h-32 rounded-xl overflow-hidden border border-sky-500/40 relative group">
              <img src="/static/images/theme_sapphire_nordic.svg" alt="Sapphire Horizon" class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
              <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"></div>
              <div class="absolute bottom-2.5 left-3 right-3 flex items-end justify-between">
                <div>
                  <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-sky-500/30 text-sky-300 font-bold border border-sky-500/40">THEME 04</span>
                  <h3 class="text-sm font-black text-white">Sapphire Horizon</h3>
                </div>
                <div class="text-2xl filter drop-shadow">🌊</div>
              </div>
            </div>"""

assert old_sapphire_header in code, "old_sapphire_header not found"
code = code.replace(old_sapphire_header, new_sapphire_header)

old_solar_header = """            <div class="h-28 rounded-xl bg-gradient-to-br from-orange-950/80 via-black to-slate-950 border border-orange-500/30 p-3 flex items-center justify-between relative overflow-hidden">
              <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-orange-500/20 rounded-full blur-xl"></div>
              <div>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-orange-500/20 text-orange-300 border border-orange-500/30 font-bold">THEME 05</span>
                <h3 class="text-base font-black text-white mt-1">Solar Forge</h3>
                <p class="text-[11px] text-orange-200/80">Volcanic Momentum &amp; Breakouts</p>
              </div>
              <div class="text-4xl filter drop-shadow">🔥</div>
            </div>"""

new_solar_header = """            <div class="h-32 rounded-xl overflow-hidden border border-orange-500/40 relative group">
              <img src="/static/images/theme_solar_forge.svg" alt="Solar Forge" class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
              <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent"></div>
              <div class="absolute bottom-2.5 left-3 right-3 flex items-end justify-between">
                <div>
                  <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-orange-500/30 text-orange-300 font-bold border border-orange-500/40">THEME 05</span>
                  <h3 class="text-sm font-black text-white">Solar Forge</h3>
                </div>
                <div class="text-2xl filter drop-shadow">🔥</div>
              </div>
            </div>"""

assert old_solar_header in code, "old_solar_header not found"
code = code.replace(old_solar_header, new_solar_header)

# 3. Add 3D Bullion Hero Banner to Gold Intelligence view
target_gold_view = '<div id="goldView" class="space-y-6 hidden">'
gold_banner_html = """<div id="goldView" class="space-y-6 hidden">
      <!-- 3D Gold Bullion Hero Banner -->
      <div class="rounded-3xl border border-amber-500/40 overflow-hidden shadow-2xl relative bg-slate-950">
        <div class="relative h-44 sm:h-52 w-full overflow-hidden">
          <img src="/static/images/gold_bullion_3d.jpg" alt="Gold Bullion" class="w-full h-full object-cover filter brightness-90 contrast-110 hover:scale-105 transition duration-700">
          <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent"></div>
          <div class="absolute bottom-4 left-6 right-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <div class="flex items-center gap-2 mb-1">
                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow">INSTITUTIONAL GRADE</span>
                <span class="text-xs text-amber-200/90 font-mono">XAUUSD &bull; 999.9 FINE GOLD &bull; 1:1000 LEVERAGE</span>
              </div>
              <h2 class="text-2xl sm:text-3xl font-black text-white tracking-tight drop-shadow-md">Gold Intelligence &amp; Autonomous Scalp Station</h2>
            </div>
            <div class="bg-slate-950/80 backdrop-blur-md px-4 py-2.5 rounded-2xl border border-amber-500/30 font-mono text-right shadow-lg">
              <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Active Concurrency Rule</div>
              <div class="text-sm font-black text-emeraldaccent flex items-center gap-1.5 justify-end mt-0.5">
                <span class="w-2 h-2 rounded-full bg-emeraldaccent animate-pulse"></span>
                5 TRADES MAX &bull; AUTO-REPLACE ON TP
              </div>
            </div>
          </div>
        </div>
      </div>"""

assert target_gold_view in code, "target_gold_view not found"
code = code.replace(target_gold_view, gold_banner_html, 1)

with open("web_app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Images successfully integrated into web_app.py!")
