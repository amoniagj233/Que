import os
import shutil
import subprocess

src = r"c:\Users\amoni\OneDrive\Desktop\Headway trader\CRT_GOLD_PRO\mt5_indicator\CRT_Gold_Pro_Indicator.mq5"
dest_dir = r"C:\Users\amoni\AppData\Roaming\MetaQuotes\Terminal\0A509A325471F5C180C55A7585ABD80D\MQL5\Indicators"
dest = os.path.join(dest_dir, "CRT_Gold_Pro_Indicator.mq5")
shutil.copy2(src, dest)
print("Copied to:", dest)

metaeditor = r"C:\Program Files\Headway MT5 Terminal\metaeditor64.exe"
log_file = r"c:\Users\amoni\OneDrive\Desktop\Headway trader\CRT_GOLD_PRO\mt5_indicator\compile.log"

cmd = f'"{metaeditor}" /compile:"{dest}" /log:"{log_file}"'
print("Running compiler command...")
proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)

if os.path.exists(log_file):
    try:
        with open(log_file, "r", encoding="utf-16", errors="ignore") as fp:
            log_text = fp.read()
    except:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as fp:
            log_text = fp.read()
    print("=== COMPILE LOG ===")
    print(log_text.encode("ascii", errors="replace").decode("ascii"))

ex5_file = dest.replace(".mq5", ".ex5")
print("Compiled EX5 exists:", os.path.exists(ex5_file))
if os.path.exists(ex5_file):
    shutil.copy2(ex5_file, r"c:\Users\amoni\OneDrive\Desktop\Headway trader\CRT_GOLD_PRO\mt5_indicator\CRT_Gold_Pro_Indicator.ex5")
    print("SUCCESS: Copied CRT_Gold_Pro_Indicator.ex5 back to project directory!")
