"""
scratch/create_theme_images.py
Creates 5 ultra-modern, high-definition SVG artworks with 3D metallic gradients,
laser grids, and living financial elements for each of the 5 themes.
"""

from pathlib import Path

img_dir = Path("static/images")
img_dir.mkdir(parents=True, exist_ok=True)

# 1. THEME 1: 24K Obsidian Gold
svg_gold = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%">
  <defs>
    <radialGradient id="bgGlowGold" cx="50%" cy="30%" r="70%">
      <stop offset="0%" stop-color="#2a1f07" stop-opacity="0.9"/>
      <stop offset="50%" stop-color="#120e03" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#07090e" stop-opacity="1"/>
    </radialGradient>
    <linearGradient id="goldBarGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fffbeb"/>
      <stop offset="25%" stop-color="#fde68a"/>
      <stop offset="50%" stop-color="#f59e0b"/>
      <stop offset="85%" stop-color="#b45309"/>
      <stop offset="100%" stop-color="#78350f"/>
    </linearGradient>
    <linearGradient id="goldBarGrad2" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#fbbf24"/>
      <stop offset="40%" stop-color="#d97706"/>
      <stop offset="80%" stop-color="#92400e"/>
      <stop offset="100%" stop-color="#fffbeb"/>
    </linearGradient>
    <linearGradient id="goldLaser" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#fbbf24" stop-opacity="0"/>
      <stop offset="50%" stop-color="#fbbf24" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>
    </linearGradient>
    <filter id="goldGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="800" height="450" fill="url(#bgGlowGold)"/>

  <!-- Subtle Perspective Grid -->
  <g stroke="#f59e0b" stroke-opacity="0.1" stroke-width="1">
    <line x1="0" y1="350" x2="800" y2="350"/>
    <line x1="0" y1="380" x2="800" y2="380"/>
    <line x1="0" y1="410" x2="800" y2="410"/>
    <line x1="0" y1="435" x2="800" y2="435"/>
    <line x1="400" y1="300" x2="100" y2="450"/>
    <line x1="400" y1="300" x2="250" y2="450"/>
    <line x1="400" y1="300" x2="400" y2="450"/>
    <line x1="400" y1="300" x2="550" y2="450"/>
    <line x1="400" y1="300" x2="700" y2="450"/>
  </g>

  <!-- Golden Laser Trend Wave in Background -->
  <path d="M 0,280 Q 200,320 350,220 T 600,160 T 800,90" fill="none" stroke="url(#goldLaser)" stroke-width="3" filter="url(#goldGlow)"/>
  <path d="M 0,280 Q 200,320 350,220 T 600,160 T 800,90 L 800,450 L 0,450 Z" fill="url(#goldLaser)" opacity="0.08"/>

  <!-- Candlesticks in Gold Aura -->
  <g opacity="0.4">
    <line x1="580" y1="120" x2="580" y2="200" stroke="#fbbf24" stroke-width="1.5"/>
    <rect x="575" y="140" width="10" height="40" fill="#fbbf24" rx="1"/>
    <line x1="640" y1="90" x2="640" y2="180" stroke="#34d399" stroke-width="1.5"/>
    <rect x="635" y="110" width="10" height="50" fill="#34d399" rx="1"/>
    <line x1="700" y1="60" x2="700" y2="150" stroke="#34d399" stroke-width="1.5"/>
    <rect x="695" y="75" width="10" height="55" fill="#34d399" rx="1"/>
  </g>

  <!-- 3D Gold Bullion Bar 1 (Bottom Left) -->
  <g transform="translate(140, 240)">
    <!-- Base shadow -->
    <ellipse cx="140" cy="90" rx="130" ry="25" fill="#000" opacity="0.7" filter="blur(6px)"/>
    <!-- Front Face -->
    <polygon points="40,40 220,40 200,85 20,85" fill="url(#goldBarGrad2)" stroke="#fde68a" stroke-width="1"/>
    <!-- Top Face -->
    <polygon points="65,10 245,10 220,40 40,40" fill="url(#goldBarGrad1)" stroke="#fff" stroke-width="0.75"/>
    <!-- Right Face -->
    <polygon points="245,10 265,55 200,85 220,40" fill="#92400e" stroke="#f59e0b" stroke-width="0.75"/>
    <!-- Stamp -->
    <text x="130" y="32" font-family="monospace" font-size="11" font-weight="900" fill="#78350f" text-anchor="middle" letter-spacing="3" transform="skewX(-15)">999.9 FINE GOLD</text>
    <text x="130" y="70" font-family="monospace" font-size="14" font-weight="900" fill="#78350f" text-anchor="middle" letter-spacing="4" transform="skewX(-15)">1 KILO</text>
  </g>

  <!-- 3D Gold Bullion Bar 2 (Top Stack) -->
  <g transform="translate(220, 190)">
    <polygon points="40,40 220,40 200,85 20,85" fill="url(#goldBarGrad1)" stroke="#fde68a" stroke-width="1"/>
    <polygon points="65,10 245,10 220,40 40,40" fill="#fef3c7" stroke="#fff" stroke-width="0.75"/>
    <polygon points="245,10 265,55 200,85 220,40" fill="#b45309" stroke="#f59e0b" stroke-width="0.75"/>
    <text x="130" y="32" font-family="monospace" font-size="11" font-weight="900" fill="#92400e" text-anchor="middle" letter-spacing="3" transform="skewX(-15)">SWISS VAULT</text>
    <text x="130" y="70" font-family="monospace" font-size="14" font-weight="900" fill="#92400e" text-anchor="middle" letter-spacing="4" transform="skewX(-15)">XAU • 24K</text>
  </g>

  <!-- Glowing Particles -->
  <circle cx="200" cy="150" r="3" fill="#fff" filter="url(#goldGlow)"/>
  <circle cx="480" cy="180" r="2.5" fill="#fde68a" filter="url(#goldGlow)"/>
  <circle cx="340" cy="120" r="2" fill="#fbbf24" filter="url(#goldGlow)"/>
  <circle cx="160" cy="220" r="2" fill="#fff"/>
  <circle cx="530" cy="240" r="3" fill="#f59e0b" filter="url(#goldGlow)"/>

  <!-- Institutional Typography Badge -->
  <rect x="520" y="340" width="240" height="50" rx="12" fill="#0d111a" stroke="#f59e0b" stroke-width="1.5" filter="drop-shadow(0 10px 15px rgba(0,0,0,0.8))"/>
  <text x="540" y="362" font-family="sans-serif" font-size="11" font-weight="900" fill="#fbbf24" letter-spacing="1">INSTITUTIONAL BULLION DESK</text>
  <text x="540" y="378" font-family="monospace" font-size="10" fill="#fef3c7" opacity="0.8">XAUUSD • 1:1000 SWISS GRADE</text>
</svg>'''

with open(img_dir / "theme_gold_obsidian.svg", "w", encoding="utf-8") as f:
    f.write(svg_gold)

# 2. THEME 2: Cyberpunk Tokyo Neon
svg_cyber = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%">
  <defs>
    <radialGradient id="cyberBg" cx="60%" cy="20%" r="80%">
      <stop offset="0%" stop-color="#1e0b36"/>
      <stop offset="50%" stop-color="#0a071c"/>
      <stop offset="100%" stop-color="#05050f"/>
    </radialGradient>
    <linearGradient id="neonCyan" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f0ff"/>
      <stop offset="100%" stop-color="#0066ff"/>
    </linearGradient>
    <linearGradient id="neonPink" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ff007f"/>
      <stop offset="100%" stop-color="#a855f7"/>
    </linearGradient>
    <filter id="neonGlowCyan">
      <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="neonGlowPink">
      <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <rect width="800" height="450" fill="url(#cyberBg)"/>

  <!-- Cyber Horizon Grid -->
  <g stroke="#00f0ff" stroke-opacity="0.15" stroke-width="1">
    <line x1="0" y1="280" x2="800" y2="280"/>
    <line x1="0" y1="310" x2="800" y2="310"/>
    <line x1="0" y1="350" x2="800" y2="350"/>
    <line x1="0" y1="400" x2="800" y2="400"/>
    <line x1="400" y1="240" x2="0" y2="450"/>
    <line x1="400" y1="240" x2="150" y2="450"/>
    <line x1="400" y1="240" x2="300" y2="450"/>
    <line x1="400" y1="240" x2="500" y2="450"/>
    <line x1="400" y1="240" x2="650" y2="450"/>
    <line x1="400" y1="240" x2="800" y2="450"/>
  </g>

  <!-- Futuristic Holographic Reticle HUD -->
  <circle cx="400" cy="200" r="130" fill="none" stroke="#ff007f" stroke-width="1.5" stroke-dasharray="10 15" opacity="0.4" filter="url(#neonGlowPink)"/>
  <circle cx="400" cy="200" r="90" fill="none" stroke="#00f0ff" stroke-width="2" stroke-dasharray="25 8" filter="url(#neonGlowCyan)"/>
  <circle cx="400" cy="200" r="40" fill="none" stroke="#00f0ff" stroke-width="1" opacity="0.6"/>

  <!-- High-Frequency Wave Pulse -->
  <path d="M 50,220 L 180,220 L 220,150 L 250,270 L 290,190 L 330,220 L 460,220 L 490,120 L 520,310 L 560,170 L 600,220 L 750,220" fill="none" stroke="#00f0ff" stroke-width="3" filter="url(#neonGlowCyan)"/>
  <path d="M 50,240 L 190,240 L 230,180 L 260,280 L 300,210 L 480,240 L 510,140 L 540,290 L 580,240 L 750,240" fill="none" stroke="#ff007f" stroke-width="2" opacity="0.7" filter="url(#neonGlowPink)"/>

  <!-- Digital Kanji / Cyber Badges -->
  <rect x="80" y="60" width="160" height="42" rx="8" fill="#0d0824" stroke="#00f0ff" stroke-width="1.5" filter="url(#neonGlowCyan)"/>
  <text x="95" y="86" font-family="monospace" font-size="13" font-weight="900" fill="#00f0ff" letter-spacing="2">QUANTUM//2077</text>

  <rect x="560" y="60" width="160" height="42" rx="8" fill="#180a2b" stroke="#ff007f" stroke-width="1.5" filter="url(#neonGlowPink)"/>
  <text x="580" y="86" font-family="monospace" font-size="13" font-weight="900" fill="#ff007f" letter-spacing="2">HFT_AI ACTIVE</text>
</svg>'''

with open(img_dir / "theme_cyberpunk_neon.svg", "w", encoding="utf-8") as f:
    f.write(svg_cyber)

# 3. THEME 3: Emerald Matrix Alpha
svg_emerald = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%">
  <defs>
    <radialGradient id="emeraldBg" cx="50%" cy="30%" r="75%">
      <stop offset="0%" stop-color="#0a291a"/>
      <stop offset="50%" stop-color="#05140d"/>
      <stop offset="100%" stop-color="#030805"/>
    </radialGradient>
    <linearGradient id="mintLaser" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00f59b" stop-opacity="0"/>
      <stop offset="50%" stop-color="#00f59b" stop-opacity="1"/>
      <stop offset="100%" stop-color="#10b981" stop-opacity="0"/>
    </linearGradient>
    <filter id="emeraldGlow">
      <feGaussianBlur stdDeviation="8" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <rect width="800" height="450" fill="url(#emeraldBg)"/>

  <!-- Binary Data Streams -->
  <g font-family="monospace" font-size="9" fill="#10b981" opacity="0.15">
    <text x="40" y="80">01010011 01001101 01000011</text>
    <text x="40" y="100">01011000 01000001 01010101</text>
    <text x="40" y="120">WIN_RATE=94.2% PROFIT=1.06</text>
    <text x="600" y="80">ORDER_BLOCK_MITIGATED</text>
    <text x="600" y="100">LIQUIDITY_POOLS_CAPTURED</text>
    <text x="600" y="120">ALGO_ALPHA_ACTIVE</text>
  </g>

  <!-- 3D Geometric Crystal Prism -->
  <g transform="translate(400, 210)" filter="url(#emeraldGlow)">
    <polygon points="0,-100 80,-20 0,60 -80,-20" fill="#00f59b" fill-opacity="0.3" stroke="#00f59b" stroke-width="2"/>
    <polygon points="0,60 80,-20 0,110 -80,-20" fill="#10b981" fill-opacity="0.4" stroke="#34d399" stroke-width="2"/>
    <polygon points="0,-100 0,110" stroke="#fff" stroke-width="1.5" opacity="0.7"/>
    <circle cx="0" cy="-20" r="15" fill="#fff" filter="url(#emeraldGlow)"/>
  </g>

  <!-- Massive Upward Profit Vector -->
  <path d="M 50,340 Q 250,360 400,240 T 750,70" fill="none" stroke="#00f59b" stroke-width="4" filter="url(#emeraldGlow)"/>
  <path d="M 50,340 Q 250,360 400,240 T 750,70 L 750,450 L 50,450 Z" fill="#10b981" fill-opacity="0.08"/>

  <polygon points="750,70 730,75 745,90" fill="#00f59b"/>
</svg>'''

with open(img_dir / "theme_emerald_matrix.svg", "w", encoding="utf-8") as f:
    f.write(svg_emerald)

# 4. THEME 4: Sapphire Nordic Frost
svg_sapphire = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%">
  <defs>
    <radialGradient id="sapphireBg" cx="50%" cy="20%" r="80%">
      <stop offset="0%" stop-color="#142647"/>
      <stop offset="50%" stop-color="#0a1529"/>
      <stop offset="100%" stop-color="#060c17"/>
    </radialGradient>
    <filter id="iceGlow">
      <feGaussianBlur stdDeviation="6" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <rect width="800" height="450" fill="url(#sapphireBg)"/>

  <!-- Clean Precision Horizon Lines -->
  <g stroke="#38bdf8" stroke-opacity="0.2" stroke-width="1">
    <line x1="50" y1="120" x2="750" y2="120"/>
    <line x1="50" y1="220" x2="750" y2="220"/>
    <line x1="50" y1="320" x2="750" y2="320"/>
  </g>

  <!-- Floating Minimalist FinTech Prisms -->
  <g transform="translate(400, 200)" filter="url(#iceGlow)">
    <rect x="-90" y="-70" width="180" height="140" rx="20" fill="#0f1f3d" fill-opacity="0.7" stroke="#38bdf8" stroke-width="2"/>
    <circle cx="-50" cy="-30" r="14" fill="#3b82f6"/>
    <line x1="-20" y1="-30" x2="50" y2="-30" stroke="#fff" stroke-width="3" stroke-linecap="round"/>
    <path d="M -50,30 L -10,0 L 20,20 L 50,-10" fill="none" stroke="#38bdf8" stroke-width="3" stroke-linecap="round"/>
  </g>

  <text x="400" y="380" font-family="sans-serif" font-size="14" font-weight="800" fill="#e0f2fe" text-anchor="middle" letter-spacing="4">NORDIC FROST • STRIPE ULTRA FINTECH</text>
</svg>'''

with open(img_dir / "theme_sapphire_nordic.svg", "w", encoding="utf-8") as f:
    f.write(svg_sapphire)

# 5. THEME 5: Solar Forge
svg_solar = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%">
  <defs>
    <radialGradient id="solarBg" cx="50%" cy="40%" r="70%">
      <stop offset="0%" stop-color="#3d1508"/>
      <stop offset="50%" stop-color="#1c0a05"/>
      <stop offset="100%" stop-color="#0a0504"/>
    </radialGradient>
    <filter id="fireGlow">
      <feGaussianBlur stdDeviation="10" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <rect width="800" height="450" fill="url(#solarBg)"/>

  <!-- Flame Core Waves -->
  <path d="M 0,380 Q 200,280 400,320 T 800,180" fill="none" stroke="#f97316" stroke-width="4" filter="url(#fireGlow)"/>
  <path d="M 0,400 Q 250,290 450,330 T 800,210" fill="none" stroke="#ef4444" stroke-width="3" filter="url(#fireGlow)"/>
  <path d="M 0,380 Q 200,280 400,320 T 800,180 L 800,450 L 0,450 Z" fill="#ff5722" fill-opacity="0.15"/>

  <!-- Volcanic Core -->
  <circle cx="400" cy="220" r="80" fill="#f97316" fill-opacity="0.25" filter="url(#fireGlow)"/>
  <circle cx="400" cy="220" r="45" fill="#fde047" fill-opacity="0.6" filter="url(#fireGlow)"/>

  <text x="400" y="225" font-family="monospace" font-size="28" font-weight="900" fill="#fff" text-anchor="middle" letter-spacing="4">VOLATILITY</text>
  <text x="400" y="250" font-family="monospace" font-size="12" font-weight="700" fill="#ffedd5" text-anchor="middle" letter-spacing="2">AGGRESSIVE BREAKOUT ENGINE</text>
</svg>'''

with open(img_dir / "theme_solar_forge.svg", "w", encoding="utf-8") as f:
    f.write(svg_solar)

# 6. Hero Wide Banner for Gold Intelligence
svg_gold_banner = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 240" width="100%" height="100%">
  <defs>
    <linearGradient id="goldBannerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#120c02"/>
      <stop offset="40%" stop-color="#1e1405"/>
      <stop offset="70%" stop-color="#140d02"/>
      <stop offset="100%" stop-color="#0a0a0f"/>
    </linearGradient>
    <filter id="bannerGlow">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <rect width="1200" height="240" rx="16" fill="url(#goldBannerGrad)" stroke="#f59e0b" stroke-opacity="0.3" stroke-width="1.5"/>

  <!-- Subtle Gold Bullion stack silhouette on left -->
  <g transform="translate(40, 40)" opacity="0.85">
    <polygon points="20,50 140,50 125,85 10,85" fill="#f59e0b" stroke="#fde68a" stroke-width="1"/>
    <polygon points="40,25 160,25 140,50 20,50" fill="#fef3c7" stroke="#fff" stroke-width="0.75"/>
    <polygon points="160,25 175,60 125,85 140,50" fill="#b45309" stroke="#f59e0b" stroke-width="0.75"/>
    <text x="80" y="42" font-family="monospace" font-size="10" font-weight="900" fill="#78350f" text-anchor="middle">999.9 FINE GOLD</text>
    
    <polygon points="50,85 170,85 155,120 40,120" fill="#d97706" stroke="#fde68a" stroke-width="1"/>
    <polygon points="70,60 190,60 170,85 50,85" fill="#fde68a" stroke="#fff" stroke-width="0.75"/>
    <polygon points="190,60 205,95 155,120 170,85" fill="#92400e" stroke="#f59e0b" stroke-width="0.75"/>
  </g>

  <!-- Title & Typography -->
  <text x="280" y="90" font-family="sans-serif" font-size="26" font-weight="900" fill="#fff" letter-spacing="0.5">
    GOLD INTELLIGENCE &amp; AUTONOMOUS TERMINAL
  </text>
  <text x="280" y="125" font-family="monospace" font-size="13" font-weight="700" fill="#fbbf24" letter-spacing="1.5">
    XAUUSD • 5-TRADE CONCURRENCY CAP • DYNAMIC TRAILING &amp; INSTANT TP REPLACEMENT
  </text>
  <text x="280" y="155" font-family="sans-serif" font-size="12" fill="#94a3b8">
    Institutional Smart Money Concepts (SMC) • Liquidity Sweep Hunting • Multi-Timeframe Algorithmic Confluence
  </text>

  <!-- Live Market Status Tag -->
  <rect x="950" y="65" width="200" height="55" rx="10" fill="#000" fill-opacity="0.5" stroke="#fbbf24" stroke-width="1"/>
  <circle cx="975" cy="92" r="5" fill="#10b981" filter="url(#bannerGlow)"/>
  <text x="990" y="87" font-family="monospace" font-size="10" font-weight="800" fill="#94a3b8">LIVE ENGINE</text>
  <text x="990" y="105" font-family="monospace" font-size="13" font-weight="900" fill="#10b981">SYSTEM ONLINE</text>
</svg>'''

with open(img_dir / "gold_banner_wide.svg", "w", encoding="utf-8") as f:
    f.write(svg_gold_banner)

print("All 6 high-definition trading artworks generated successfully in static/images/!")
