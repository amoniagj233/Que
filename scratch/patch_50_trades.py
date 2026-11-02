def patch_50_trades():
    with open('gold_auto_trader.py', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('"max_daily_trades": 6,', '"max_daily_trades": 50,')
    content = content.replace('max_daily = self.config.get("max_daily_trades", 6)', 'max_daily = self.config.get("max_daily_trades", 50)')
    content = content.replace('"max_daily_trades": self.config.get("max_daily_trades", 3)', '"max_daily_trades": self.config.get("max_daily_trades", 50)')
    content = content.replace('"timeframe_filter", "M1_M5")', '"timeframe_filter", "M1")')

    with open('gold_auto_trader.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Patched gold_auto_trader.py for 50 max daily trades and M1 default!")

if __name__ == '__main__':
    patch_50_trades()
