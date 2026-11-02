def patch_get_status():
    with open('gold_auto_trader.py', 'r', encoding='utf-8') as f:
        content = f.read()

    target = '''    def get_status(self) -> Dict[str, Any]:
        """Provides complete real-time dashboard data for Gold auto-trading UI."""
        with self.lock:
            open_pos = self.get_open_gold_positions()'''

    replace = '''    def get_status(self) -> Dict[str, Any]:
        """Provides complete real-time dashboard data for Gold auto-trading UI."""
        open_pos = self.get_open_gold_positions()
        with self.lock:'''

    if target in content:
        content = content.replace(target, replace, 1)
        with open('gold_auto_trader.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("SUCCESS: Fixed lock order in get_status!")
        return True
    else:
        print("Target not found")
        return False

if __name__ == '__main__':
    patch_get_status()
