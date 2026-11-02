import pandas as pd
df = pd.read_csv("data_cache/XAUUSD_H1_5000.csv")
df["dt"] = pd.to_datetime(df["time"])
start_6m = df["dt"].max() - pd.DateOffset(months=6)
df_6m = df[df["dt"] >= start_6m]
p_start = df_6m["close"].iloc[0]
p_end = df_6m["close"].iloc[-1]
p_min = df_6m["close"].min()
p_max = df_6m["close"].max()
print("Gold 6M Start:", p_start)
print("Gold 6M End:", p_end)
print("Net change:", p_end - p_start)
print("Min price:", p_min)
print("Max price:", p_max)
print("Total range:", p_max - p_min)
