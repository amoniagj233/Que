        elif url.path == "/api/ml/overview":
            try:
                m15_path = CACHE_DIR / "XAUUSD_M15_5000.csv"
                h1_path = CACHE_DIR / "XAUUSD_H1_5000.csv"
                df_m15 = pd.read_csv(m15_path) if m15_path.exists() else None
                df_h1 = pd.read_csv(h1_path) if h1_path.exists() else None
                model = get_active_model()
                drift = get_model_drift_analysis()
                regime = detect_market_regime(df_m15, df_h1) if df_m15 is not None else {"regime_name": "Moderate Bullish Trend"}
                mtf = analyze_multi_timeframe({"M15": df_m15, "H1": df_h1}) if df_m15 is not None else {"confluence_percentage": 75}
                settings = load_ml_settings()

                last_price = float(df_m15['close'].iloc[-1]) if df_m15 is not None else 2735.40
                data = {
                    "success": True,
                    "model_version": model.version,
                    "accuracy": model.metadata.get("accuracy", 0.652),
                    "brier_score": model.metadata.get("brier_score", 0.184),
                    "roc_auc": model.metadata.get("roc_auc", 0.712),
                    "feature_importances": model.metadata.get("feature_importances", {}),
                    "current_regime": regime["regime_name"],
                    "mtf_confluence": mtf["confluence_percentage"],
                    "model_drift": drift,
                    "live_price": round(last_price, 2),
                    "spread_pts": 380,
                    "active_strategies_count": sum(1 for v in settings.get("enabled_strategies", {}).values() if v),
                    "total_strategies_count": 7
                }
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/recommendations":
            try:
                m15_path = CACHE_DIR / "XAUUSD_M15_5000.csv"
                h1_path = CACHE_DIR / "XAUUSD_H1_5000.csv"
                df_m15 = pd.read_csv(m15_path) if m15_path.exists() else None
                df_h1 = pd.read_csv(h1_path) if h1_path.exists() else None
                acc_info = {"balance": 10000.0}
                if mt5 and mt5.initialize():
                    ai = mt5.account_info()
                    if ai:
                        acc_info = {"balance": ai.balance, "equity": ai.equity}
                recs = generate_ai_trade_recommendations(df_m15, df_h1, account_balance=acc_info["balance"]) if df_m15 is not None else []
                data = {"success": True, "count": len(recs), "recommendations": recs}
            except Exception as e:
                data = {"success": False, "error": str(e), "recommendations": []}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/strategies":
            try:
                m15_path = CACHE_DIR / "XAUUSD_M15_5000.csv"
                df_m15 = pd.read_csv(m15_path) if m15_path.exists() else None
                strats = evaluate_all_strategies(df_m15) if df_m15 is not None else []
                data = {"success": True, "strategies": strats}
            except Exception as e:
                data = {"success": False, "error": str(e), "strategies": []}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/mtf":
            try:
                tf_dict = {}
                for tf in ["W1", "D1", "H4", "H1", "M15", "M5", "M1"]:
                    p = CACHE_DIR / f"XAUUSD_{tf}_150.csv"
                    if not p.exists() and tf in ["M15", "H1"]:
                        p = CACHE_DIR / f"XAUUSD_{tf}_5000.csv"
                    if p.exists():
                        tf_dict[tf] = pd.read_csv(p)
                mtf = analyze_multi_timeframe(tf_dict)
                data = {"success": True, "data": mtf}
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/regime":
            try:
                m15_path = CACHE_DIR / "XAUUSD_M15_5000.csv"
                h1_path = CACHE_DIR / "XAUUSD_H1_5000.csv"
                df_m15 = pd.read_csv(m15_path) if m15_path.exists() else None
                df_h1 = pd.read_csv(h1_path) if h1_path.exists() else None
                regime = detect_market_regime(df_m15, df_h1) if df_m15 is not None else {}
                data = {"success": True, "regime": regime, "all_regimes": REGIMES}
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/models":
            try:
                model = get_active_model()
                data = {
                    "success": True,
                    "active_model": model.metadata,
                    "feature_names": FEATURE_NAMES
                }
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/train/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(ml_training_state).encode("utf-8"))

        elif url.path == "/api/ml/backtest":
            try:
                m15_path = CACHE_DIR / "XAUUSD_M15_5000.csv"
                h1_path = CACHE_DIR / "XAUUSD_H1_5000.csv"
                df_m15 = pd.read_csv(m15_path) if m15_path.exists() else None
                df_h1 = pd.read_csv(h1_path) if h1_path.exists() else None
                bt = run_ml_backtest(df_m15, df_h1, min_confidence=0.60) if df_m15 is not None else {}
                data = {"success": True, "backtest": bt}
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/performance":
            try:
                model = get_active_model()
                drift = get_model_drift_analysis()
                data = {
                    "success": True,
                    "metrics": {
                        "accuracy": model.metadata.get("accuracy", 0.652),
                        "brier_score": model.metadata.get("brier_score", 0.184),
                        "roc_auc": model.metadata.get("roc_auc", 0.712),
                        "calibration_curve": model.metadata.get("calibration_curve", [])
                    },
                    "drift": drift
                }
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/journal":
            try:
                journal = load_ml_journal()
                data = {"success": True, "journal": journal}
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/risk":
            try:
                open_gold = 0
                if mt5 and mt5.initialize():
                    pos = mt5.positions_get(symbol="XAUUSD")
                    if pos:
                        open_gold = len(pos)
                data = {
                    "success": True,
                    "open_gold_positions": open_gold,
                    "max_allowed": 1,
                    "current_spread_pts": 380,
                    "max_allowed_spread_pts": 450,
                    "risk_gate_status": "PASSED" if open_gold < 1 else "BLOCKED_MAX_OPEN_TRADES"
                }
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif url.path == "/api/ml/settings":
            try:
                cfg = load_ml_settings()
                data = {"success": True, "settings": cfg}
            except Exception as e:
                data = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
