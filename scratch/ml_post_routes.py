        elif url.path == "/api/ml/train":
            def train_worker():
                global ml_training_state
                ml_training_state["is_training"] = True
                ml_training_state["progress"] = 10
                ml_training_state["message"] = "Loading 5,000 M15 and H1 candles..."
                try:
                    m15_path = CACHE_DIR / "XAUUSD_M15_5000.csv"
                    h1_path = CACHE_DIR / "XAUUSD_H1_5000.csv"
                    df_m15 = pd.read_csv(m15_path) if m15_path.exists() else None
                    df_h1 = pd.read_csv(h1_path) if h1_path.exists() else None
                    if df_m15 is None:
                        raise ValueError("Cached XAUUSD_M15_5000.csv not found.")

                    ml_training_state["progress"] = 35
                    ml_training_state["message"] = "Extracting 28 quantitative & SMC features with purged CV..."
                    time.sleep(0.5)

                    v_num = f"v{int(time.time())}"
                    model = MLTradingModel(version=v_num)
                    ml_training_state["progress"] = 65
                    ml_training_state["message"] = "Fitting ensemble classifier with Platt probability calibration..."
                    meta = model.train(df_m15, df_h1)

                    ml_training_state["progress"] = 100
                    ml_training_state["message"] = f"Training completed successfully! Accuracy: {meta.get('accuracy', 0)*100:.1f}%, Brier: {meta.get('brier_score', 0)}"
                    ml_training_state["last_result"] = meta
                    ml_training_state["is_training"] = False

                    # Update active model in settings
                    settings = load_ml_settings()
                    settings["active_model_version"] = v_num
                    save_ml_settings(settings)
                except Exception as e:
                    ml_training_state["is_training"] = False
                    ml_training_state["message"] = f"Training error: {str(e)}"

            threading.Thread(target=train_worker, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "ML training initiated in background."}).encode("utf-8"))

        elif url.path == "/api/ml/backtest/run":
            try:
                min_c = float(data.get("min_confidence", 60)) / 100.0
                m15_path = CACHE_DIR / "XAUUSD_M15_5000.csv"
                h1_path = CACHE_DIR / "XAUUSD_H1_5000.csv"
                df_m15 = pd.read_csv(m15_path) if m15_path.exists() else None
                df_h1 = pd.read_csv(h1_path) if h1_path.exists() else None
                bt = run_ml_backtest(df_m15, df_h1, min_confidence=min_c) if df_m15 is not None else {}
                res = {"success": True, "backtest": bt}
            except Exception as e:
                res = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/ml/recommendations/execute":
            try:
                rec_data = data.get("recommendation", {})
                action = rec_data.get("direction", "BUY")
                lot = float(rec_data.get("recommended_lot_size", 0.01))
                sl = float(rec_data.get("stop_loss", 0.0))
                tp = float(rec_data.get("tp2", 0.0))
                strat = rec_data.get("strategy_name", "ML Intelligence Setup")
                conf = int(float(rec_data.get("win_probability", 0.70)) * 100)

                # Check Risk Gate
                open_gold = 0
                if mt5 and mt5.initialize():
                    pos = mt5.positions_get(symbol="XAUUSD")
                    if pos:
                        open_gold = len(pos)

                passed, reason = evaluate_risk_gate({"balance": 10000.0}, rec_data, current_spread_pts=380, open_gold_positions_count=open_gold)
                if not passed:
                    res = {"success": False, "message": reason}
                else:
                    if gold_auto_trader:
                        res = gold_auto_trader.execute_gold_order(
                            action=action, lot=lot, sl=sl, tp=tp,
                            confidence_score=conf, strategy_name=strat,
                            notes=f"1-Click AI Execution ({rec_data.get('expected_value_r', '+0.4R')})", is_auto=False
                        )
                        # Record in journal
                        record_ml_prediction({
                            "strategy_code": rec_data.get("strategy_code", "Strategy A"),
                            "direction": action,
                            "win_probability": rec_data.get("win_probability", 0.7),
                            "expected_value_r": rec_data.get("expected_value_r", "+0.4R"),
                            "entry_price": rec_data.get("entry_price", 0),
                            "sl": sl,
                            "tp": tp,
                            "status": "EXECUTED"
                        })
                    else:
                        res = {"success": False, "message": "GoldAutoTrader engine not ready"}
            except Exception as e:
                res = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/ml/strategies/toggle":
            try:
                code = data.get("strategy_code")
                enabled = bool(data.get("enabled", True))
                cfg = load_ml_settings()
                if "enabled_strategies" not in cfg:
                    cfg["enabled_strategies"] = {}
                cfg["enabled_strategies"][code] = enabled
                save_ml_settings(cfg)
                res = {"success": True, "strategy": code, "enabled": enabled}
            except Exception as e:
                res = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif url.path == "/api/ml/settings/update":
            try:
                cfg = load_ml_settings()
                if "min_confidence" in data:
                    cfg["min_confidence_threshold"] = float(data["min_confidence"]) / 100.0
                if "min_ev" in data:
                    cfg["min_expected_value_r"] = float(data["min_ev"])
                if "risk_pct" in data:
                    cfg["max_risk_per_trade_pct"] = float(data["risk_pct"])
                if "pullback_type" in data:
                    cfg["chaser_option_b"]["pullback_type"] = data["pullback_type"]
                if "pullback_thresh" in data:
                    cfg["chaser_option_b"]["pullback_threshold"] = float(data["pullback_thresh"])
                save_ml_settings(cfg)
                res = {"success": True, "settings": cfg}
            except Exception as e:
                res = {"success": False, "error": str(e)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
