import sys
print(f"Python: {sys.version}")

for mod in ['sklearn', 'lightgbm', 'xgboost', 'numpy', 'pandas', 'scipy']:
    try:
        m = __import__(mod)
        ver = getattr(m, '__version__', 'installed')
        print(f"{mod}: {ver}")
    except ImportError:
        print(f"{mod}: NOT installed")
