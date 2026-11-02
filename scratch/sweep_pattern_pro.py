from scratch.optimize_pattern_pro import run_simulation

print("Executing parameter sweep on Strategic Pattern Pro V2...")
best_wr = 0.0
best_params = {}

for tp in [3.00, 3.50, 4.00, 4.50]:
    for sl in [6.50, 7.50, 8.50, 10.00]:
        for be in [1.20, 1.50, 1.80]:
            res = run_simulation("v2_filtered", tp_dist=tp, sl_dist=sl, be_trigger=be, be_lock=0.20)
            if res["wr"] > best_wr and res["net_pnl"] > 0:
                best_wr = res["wr"]
                best_params = {"tp": tp, "sl": sl, "be": be, "res": res}

print("\n=== TOP OPTIMIZED CONFIGURATION FOUND ===")
r = best_params["res"]
print(f"Optimal Settings: TP: ${best_params['tp']:.2f} | SL: ${best_params['sl']:.2f} | BE Trigger: +${best_params['be']:.2f}")
print(f"Win Rate        : {r['wr']:.2f}% (90%+ TARGET)")
print(f"Wins / Losses   : {r['wins']} Wins / {r['losses']} Losses (Total: {r['total']} trades)")
print(f"Net Profit      : +${r['net_pnl']:.2f}")
print(f"Profit Factor   : {r['pf']:.2f}")
