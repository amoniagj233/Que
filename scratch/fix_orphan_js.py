def fix_orphaned_block():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    orphan_block = """    }
      if (!confirm(`Execute 1 Gold trade (${direction} 0.01 lot XAUUSD)?\\nEntry: ~${entry}\\nSL: ${sl}\\nTP: ${tp}\\nConfidence: ${confidence}%\\nStrategy: ${strategy}\\nProtected by Smart Profit Chaser Option B.`)) {
        return;
      }
      try {
        const lotVal = parseFloat(document.getElementById('goldLotSelect') ? document.getElementById('goldLotSelect').value : 0.01);
        const res = await fetch('/api/gold/execute_now', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            direction: direction,
            lot: lotVal,
            sl: sl,
            tp: tp,
            confidence: confidence,
            strategy: strategy
          })
        });
        const out = await res.json();
        alert(out.message);
        loadGoldDashboard();
      } catch (err) {
        alert('Execution error: ' + err);
      }
    }"""

    if orphan_block in content:
        content = content.replace(orphan_block, "    }", 1)
        with open('web_app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("SUCCESS: Removed orphaned JS block from web_app.py!")
        return True
    else:
        print("ERROR: orphan_block not found exactly!")
        return False

if __name__ == '__main__':
    fix_orphaned_block()
