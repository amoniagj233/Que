import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Set dark theme style matching trading platforms (TradingView / Bloomberg style)
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(14, 8), dpi=200)

fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

# Synthesize a realistic Gold uptrend with a pullback testing Higher Low
np.random.seed(42)

# Key Price Points
# Point 0: Base Swing Low (HL1) at 4030
# Point 1: Rally to Swing High (HH1) at 4048
# Point 2: Pullback to Higher Low (HL2) at 4038
# Point 3: Pullback dip where Grid Layers 1, 2, 3 accumulate
# Point 4: Resumption to new Higher High (HH2) at 4055 hitting Basket TP

times = np.linspace(0, 100, 100)
# Price trajectory
trend = 4030 + 0.25 * times
noise = np.sin(times / 6.0) * 6.0 + np.random.normal(0, 0.6, 100)
# Create a dip between index 35 and 55
noise[35:55] -= np.linspace(0, 7, 20)
noise[45:65] += np.linspace(0, 12, 20)
prices = trend + noise

# Plot main price line / candles
ax.plot(times, prices, color='#58a6ff', linewidth=2.2, label='XAUUSD M15 Price Action', zorder=3)

# Highlight Swing Pivots
# 1. Previous Higher Low (HL1)
hl1_idx = 10
ax.scatter(times[hl1_idx], prices[hl1_idx]-1.5, color='#3fb950', s=140, zorder=5, marker='^')
ax.annotate('Higher Low (HL1)\n$4032.50', (times[hl1_idx], prices[hl1_idx]-4.5),
            color='#3fb950', fontsize=10, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#3fb950', lw=1.2))

# 2. Previous Higher High (HH1)
hh1_idx = 32
ax.scatter(times[hh1_idx], prices[hh1_idx]+1.5, color='#3fb950', s=140, zorder=5, marker='v')
ax.annotate('Higher High (HH1)\n$4047.80', (times[hh1_idx], prices[hh1_idx]+3.0),
            color='#3fb950', fontsize=10, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#3fb950', lw=1.2))

# 3. Pullback Zone with Smart Grid Layers
# Layer 1
l1_idx = 38
ax.scatter(times[l1_idx], prices[l1_idx], color='#f0883e', s=120, zorder=6, marker='o')
ax.annotate('Layer 1 (0.01 Lot)\n$4043.20 (Pullback Start)', (times[l1_idx]+3, prices[l1_idx]+2.5),
            color='#f0883e', fontsize=9, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#f0883e', lw=1.2),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#f0883e', lw=1))

# Layer 2
l2_idx = 45
ax.scatter(times[l2_idx], prices[l2_idx], color='#f0883e', s=130, zorder=6, marker='o')
ax.annotate('Layer 2 (0.01 Lot)\n$4039.50 (1.2x ATR Spacing)', (times[l2_idx]+3, prices[l2_idx]-3.5),
            color='#f0883e', fontsize=9, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#f0883e', lw=1.2),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#f0883e', lw=1))

# Layer 3
l3_idx = 50
ax.scatter(times[l3_idx], prices[l3_idx], color='#f0883e', s=150, zorder=6, marker='o')
ax.annotate('Layer 3 (0.02 Lot)\n$4036.80 (HL Support Test)', (times[l3_idx]+4, prices[l3_idx]-4.5),
            color='#f0883e', fontsize=9, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#f0883e', lw=1.2),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#f0883e', lw=1))

# Weighted Breakeven Line
be_price = (4043.20*0.01 + 4039.50*0.01 + 4036.80*0.02) / 0.04 # = 4039.075
ax.axhline(be_price, color='#a371f7', linestyle='--', linewidth=1.8, label=f'Blended Breakeven Line (${be_price:.2f})', zorder=4)

# Take Profit Target Line
tp_price = be_price + 3.50
ax.axhline(tp_price, color='#2ea043', linestyle='-', linewidth=2.2, label=f'Basket Take Profit Target (+${3.50} @ ${tp_price:.2f})', zorder=4)
ax.annotate('TARGET PROFIT HIT!\nEntire Basket Liquidated\n+$3.50 Net Gain Locked', (times[78], tp_price+1.5),
            color='#3fb950', fontsize=10, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#161b22', edgecolor='#2ea043', lw=1.5))

# Structural Invalidation Stop Loss Line (Below HL1)
sl_price = 4032.00
ax.axhline(sl_price, color='#da3633', linestyle='-', linewidth=2.0, label=f'Structural Invalidation Stop (${sl_price:.2f} below HL1)', zorder=4)
ax.annotate('STRUCTURAL STOP LOSS\n(Cuts entire basket if trend structure breaks)\nZERO MARGIN CALL RISK', (times[20], sl_price-2.8),
            color='#f85149', fontsize=9, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#da3633', lw=1.2))

# Fill Zones
# Profit Zone
ax.axhspan(be_price, tp_price, color='#238636', alpha=0.12, label='Profit Accumulation Zone')
# Protected Risk Zone
ax.axhspan(sl_price, be_price, color='#da3633', alpha=0.08, label='Protected Drawdown Zone (Max -$25)')

# Formatting & Titles
ax.set_title('STRUCTUREGRID PRO : MARKET STRUCTURE (HH / LL) + SMART DCA HYBRID', fontsize=14, fontweight='bold', color='#f0f6fc', pad=15)
ax.set_xlabel('Time (M15 Candles)', color='#8b949e', fontsize=11)
ax.set_ylabel('Gold Price (USD / oz)', color='#8b949e', fontsize=11)
ax.tick_params(colors='#8b949e', labelsize=10)
ax.grid(color='#21262d', linestyle=':', linewidth=0.8, alpha=0.7)

# Legend
leg = ax.legend(loc='upper left', frameon=True, facecolor='#161b22', edgecolor='#30363d', fontsize=9)
for text in leg.get_texts():
    text.set_color('#c9d1d9')

# Save graphic
output_path = r"C:\Users\amoni\OneDrive\Desktop\Headway trader\structure_grid_bot_diagram.png"
plt.tight_layout()
plt.savefig(output_path, facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()

print(f"Chart diagram successfully generated at: {output_path}")
