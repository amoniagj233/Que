import subprocess

try:
    out = subprocess.check_output(["tasklist"], text=True)
    for line in out.splitlines():
        if "terminal64" in line.lower() or "meta" in line.lower():
            print("Found process:", line)
except Exception as e:
    print("Error:", e)
