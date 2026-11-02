"""
AGENT SETTINGS — SUPREME SETTINGS COMMANDER
Central Database Manager
SQLite engine storing EA Fleet metadata, performance records, optimization runs,
eliminations, champion vs challenger battles, market regimes, and audit logs.
"""

import sqlite3
import json
import os
import datetime
from typing import Dict, Any, List, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "agent_settings.db")

class SettingsDatabase:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. EA Fleet Master Registry
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS fleet_eas (
                ea_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                magic INTEGER NOT NULL UNIQUE,
                symbol TEXT DEFAULT 'XAUUSD',
                timeframe TEXT DEFAULT 'M5',
                bot_type TEXT NOT NULL,          -- 'python', 'mql5', 'hybrid'
                strategy_name TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',    -- 'ACTIVE', 'OPTIMIZING', 'SUSPENDED', 'RETIRED', 'REPLACED'
                script_path TEXT,
                ex5_path TEXT,
                current_settings TEXT,           -- JSON of parameters
                verified_win_rate REAL DEFAULT 0.0,
                total_trades INTEGER DEFAULT 0,
                net_profit REAL DEFAULT 0.0,
                profit_factor REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                expectancy REAL DEFAULT 0.0,
                last_optimization TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)

            # 2. Performance Tracking Ledger (Backtest, Demo, Live)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ea_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                mode TEXT NOT NULL,             -- 'BACKTEST', 'DEMO', 'LIVE'
                timeframe TEXT,
                total_trades INTEGER NOT NULL,
                wins INTEGER NOT NULL,
                losses INTEGER NOT NULL,
                win_rate REAL NOT NULL,
                net_profit REAL NOT NULL,
                profit_factor REAL,
                max_drawdown REAL,
                expectancy REAL,
                trade_frequency_daily REAL,
                details_json TEXT,
                FOREIGN KEY (ea_id) REFERENCES fleet_eas(ea_id)
            )
            """)

            # 3. Autonomous Optimization Runs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_runs (
                run_id TEXT PRIMARY KEY,
                ea_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                method TEXT NOT NULL,           -- 'GRID', 'BAYESIAN', 'GENETIC', 'WALK_FORWARD'
                bars_tested INTEGER NOT NULL,
                timeframe TEXT NOT NULL,
                initial_settings TEXT,          -- JSON
                best_settings TEXT,             -- JSON
                initial_win_rate REAL,
                optimized_win_rate REAL,
                initial_profit REAL,
                optimized_profit REAL,
                target_met INTEGER DEFAULT 0,   -- 1 if > 80% with positive profit
                status TEXT DEFAULT 'COMPLETED', -- 'IN_PROGRESS', 'COMPLETED', 'FAILED'
                notes TEXT,
                FOREIGN KEY (ea_id) REFERENCES fleet_eas(ea_id)
            )
            """)

            # 4. Elimination & Replacement Ledger (Strict 80% Policy)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS eliminations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ea_id TEXT NOT NULL,
                elimination_date TEXT NOT NULL,
                reason TEXT NOT NULL,           -- e.g. 'Rule C: Win Rate 64.2% < 80% with > 200 trades'
                verified_win_rate REAL NOT NULL,
                trade_count INTEGER NOT NULL,
                archived_path TEXT NOT NULL,
                replacement_ea_id TEXT,
                status TEXT DEFAULT 'RETIRED_AND_ARCHIVED'
            )
            """)

            # 5. Champion vs Challenger Arena
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS champion_challenger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                champion_id TEXT NOT NULL,
                challenger_id TEXT NOT NULL,
                symbol TEXT DEFAULT 'XAUUSD',
                champion_win_rate REAL,
                challenger_win_rate REAL,
                champion_profit REAL,
                challenger_profit REAL,
                arena_status TEXT DEFAULT 'EVALUATING', -- 'EVALUATING', 'CHALLENGER_PROMOTED', 'CHAMPION_RETAINED'
                started_at TEXT,
                concluded_at TEXT,
                metrics_json TEXT
            )
            """)

            # 6. Market Regime History
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_regimes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT DEFAULT 'XAUUSD',
                timeframe TEXT DEFAULT 'M5',
                regime_type TEXT NOT NULL,      -- 'TREND_BULL', 'TREND_BEAR', 'RANGE_CHOP', 'HIGH_VOLATILITY', 'SQUEEZE'
                atr_14 REAL,
                adx_14 REAL,
                rsi_14 REAL,
                volatility_rank TEXT,           -- 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
                recommendation TEXT
            )
            """)

            # 7. Audit & Activity Event Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,            -- 'INFO', 'OPTIMIZE', 'ELIMINATE', 'DEPLOY', 'ALERT'
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                details_json TEXT
            )
            """)
            
            conn.commit()

    def register_or_update_ea(self, ea_data: Dict[str, Any]):
        now = datetime.datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ea_id FROM fleet_eas WHERE ea_id = ?", (ea_data['ea_id'],))
            exists = cursor.fetchone()
            
            settings_str = json.dumps(ea_data.get('current_settings', {}))
            if exists:
                cursor.execute("""
                UPDATE fleet_eas SET
                    name = ?, magic = ?, symbol = ?, timeframe = ?, bot_type = ?,
                    strategy_name = ?, status = ?, script_path = ?, ex5_path = ?,
                    current_settings = ?, verified_win_rate = ?, total_trades = ?,
                    net_profit = ?, profit_factor = ?, max_drawdown = ?, expectancy = ?,
                    last_optimization = ?, updated_at = ?
                WHERE ea_id = ?
                """, (
                    ea_data['name'], ea_data['magic'], ea_data.get('symbol', 'XAUUSD'),
                    ea_data.get('timeframe', 'M5'), ea_data['bot_type'], ea_data['strategy_name'],
                    ea_data.get('status', 'ACTIVE'), ea_data.get('script_path', ''),
                    ea_data.get('ex5_path', ''), settings_str, ea_data.get('verified_win_rate', 0.0),
                    ea_data.get('total_trades', 0), ea_data.get('net_profit', 0.0),
                    ea_data.get('profit_factor', 0.0), ea_data.get('max_drawdown', 0.0),
                    ea_data.get('expectancy', 0.0), ea_data.get('last_optimization', now),
                    now, ea_data['ea_id']
                ))
            else:
                cursor.execute("""
                INSERT INTO fleet_eas (
                    ea_id, name, magic, symbol, timeframe, bot_type, strategy_name,
                    status, script_path, ex5_path, current_settings, verified_win_rate,
                    total_trades, net_profit, profit_factor, max_drawdown, expectancy,
                    last_optimization, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ea_data['ea_id'], ea_data['name'], ea_data['magic'], ea_data.get('symbol', 'XAUUSD'),
                    ea_data.get('timeframe', 'M5'), ea_data['bot_type'], ea_data['strategy_name'],
                    ea_data.get('status', 'ACTIVE'), ea_data.get('script_path', ''),
                    ea_data.get('ex5_path', ''), settings_str, ea_data.get('verified_win_rate', 0.0),
                    ea_data.get('total_trades', 0), ea_data.get('net_profit', 0.0),
                    ea_data.get('profit_factor', 0.0), ea_data.get('max_drawdown', 0.0),
                    ea_data.get('expectancy', 0.0), ea_data.get('last_optimization', now),
                    now, now
                ))
            conn.commit()

    def get_all_eas(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fleet_eas ORDER BY verified_win_rate DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_ea_by_magic(self, magic: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fleet_eas WHERE magic = ?", (magic,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def record_performance(self, record: Dict[str, Any]):
        now = datetime.datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO performance_records (
                ea_id, timestamp, mode, timeframe, total_trades, wins, losses,
                win_rate, net_profit, profit_factor, max_drawdown, expectancy,
                trade_frequency_daily, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record['ea_id'], record.get('timestamp', now), record['mode'],
                record.get('timeframe', 'M5'), record['total_trades'], record['wins'],
                record['losses'], record['win_rate'], record['net_profit'],
                record.get('profit_factor', 0.0), record.get('max_drawdown', 0.0),
                record.get('expectancy', 0.0), record.get('trade_frequency_daily', 0.0),
                json.dumps(record.get('details', {}))
            ))
            # Also update current performance in fleet_eas
            cursor.execute("""
            UPDATE fleet_eas SET
                verified_win_rate = ?, total_trades = ?, net_profit = ?,
                profit_factor = ?, max_drawdown = ?, expectancy = ?, updated_at = ?
            WHERE ea_id = ?
            """, (
                record['win_rate'], record['total_trades'], record['net_profit'],
                record.get('profit_factor', 0.0), record.get('max_drawdown', 0.0),
                record.get('expectancy', 0.0), now, record['ea_id']
            ))
            conn.commit()

    def record_optimization_run(self, run: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO optimization_runs (
                run_id, ea_id, timestamp, method, bars_tested, timeframe,
                initial_settings, best_settings, initial_win_rate, optimized_win_rate,
                initial_profit, optimized_profit, target_met, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run['run_id'], run['ea_id'], run.get('timestamp', datetime.datetime.utcnow().isoformat()),
                run['method'], run['bars_tested'], run.get('timeframe', 'M5'),
                json.dumps(run.get('initial_settings', {})),
                json.dumps(run.get('best_settings', {})),
                run.get('initial_win_rate', 0.0), run.get('optimized_win_rate', 0.0),
                run.get('initial_profit', 0.0), run.get('optimized_profit', 0.0),
                1 if run.get('optimized_win_rate', 0.0) > 80.0 and run.get('optimized_profit', 0.0) > 0 else 0,
                run.get('status', 'COMPLETED'), run.get('notes', '')
            ))
            conn.commit()

    def record_elimination(self, elim: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO eliminations (
                ea_id, elimination_date, reason, verified_win_rate,
                trade_count, archived_path, replacement_ea_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                elim['ea_id'], elim.get('elimination_date', datetime.datetime.utcnow().isoformat()),
                elim['reason'], elim['verified_win_rate'], elim['trade_count'],
                elim['archived_path'], elim.get('replacement_ea_id', ''),
                elim.get('status', 'RETIRED_AND_ARCHIVED')
            ))
            # Mark EA as RETIRED or REPLACED in master fleet
            status = 'REPLACED' if elim.get('replacement_ea_id') else 'RETIRED'
            cursor.execute("UPDATE fleet_eas SET status = ?, updated_at = ? WHERE ea_id = ?",
                           (status, datetime.datetime.utcnow().isoformat(), elim['ea_id']))
            conn.commit()

    def record_market_regime(self, regime: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO market_regimes (
                timestamp, symbol, timeframe, regime_type,
                atr_14, adx_14, rsi_14, volatility_rank, recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                regime.get('timestamp', datetime.datetime.utcnow().isoformat()),
                regime.get('symbol', 'XAUUSD'), regime.get('timeframe', 'M5'),
                regime['regime_type'], regime.get('atr_14', 0.0),
                regime.get('adx_14', 0.0), regime.get('rsi_14', 0.0),
                regime.get('volatility_rank', 'MEDIUM'), regime.get('recommendation', '')
            ))
            conn.commit()

    def log_activity(self, level: str, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO activity_log (timestamp, level, event_type, message, details_json)
            VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.datetime.utcnow().isoformat(), level, event_type, message,
                json.dumps(details or {})
            ))
            conn.commit()

    def get_recent_activities(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_dashboard_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) as total, sum(case when verified_win_rate > 80.0 then 1 else 0 end) as above_80, sum(case when status = 'ACTIVE' then 1 else 0 end) as active_count FROM fleet_eas")
            fleet_stats = dict(cursor.fetchone() or {})
            
            cursor.execute("SELECT count(*) as count FROM optimization_runs")
            opt_runs = cursor.fetchone()['count']
            
            cursor.execute("SELECT count(*) as count FROM eliminations")
            elim_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT * FROM market_regimes ORDER BY id DESC LIMIT 1")
            latest_regime = cursor.fetchone()
            regime_dict = dict(latest_regime) if latest_regime else {}
            
            return {
                "fleet_stats": fleet_stats,
                "total_optimizations": opt_runs,
                "total_eliminations": elim_count,
                "current_regime": regime_dict
            }
