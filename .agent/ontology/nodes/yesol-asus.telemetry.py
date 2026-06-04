import json
import time
from datetime import datetime
import subprocess

def get_local_telemetry():
    start = time.time()
    
    # PowerShell command to get CPU, RAM, and C Drive Space
    script = """
    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
    
    $cpuLoad = [int]$cpu.LoadPercentage
    $ramFreeGB = [math]::Round($os.FreePhysicalMemory / 1024 / 1024, 1)
    $diskFreeGB = [math]::Round($drive.FreeSpace / 1GB, 1)
    
    Write-Output "$cpuLoad|$ramFreeGB|$diskFreeGB"
    """
    
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, check=True)
        out = result.stdout.strip()
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if lines and '|' in lines[-1]:
            cpu, ram, disk = lines[-1].split('|')
            data = {
                "status": "online",
                "cpu_percent": int(cpu),
                "free_ram_gb": float(ram),
                "c_drive_free_gb": float(disk)
            }
        else:
            data = {"status": "error", "message": "Failed to parse"}
    except Exception as e:
        data = {"status": "error", "message": str(e)}

    return {
        "timestamp": datetime.now().isoformat(),
        "scan_duration_sec": round(time.time() - start, 3),
        "node": "yesol-asus",
        "telemetry": data
    }

if __name__ == "__main__":
    import sys
    state = get_local_telemetry()
    print(json.dumps(state, indent=2))
