import platform
import socket
import psutil
import json
import uuid
from datetime import datetime  # FIXED: Changed from 'import datetime'
import requests
import subprocess
import os
import sys

# === CONFIGURATION ===
POWERSHELL_SCRIPT_PATH = "spec_collector.ps1"
API_ENDPOINT = "http://localhost:5000/api/full-system-info"
SEND_TO_API = True  # Set to False for debug mode without sending

def run_powershell_script(script_path):
    """Run PowerShell script and return JSON output"""
    if not os.path.exists(script_path):
        print(f"[!] PowerShell script not found: {script_path}")
        return {"error": "PowerShell script missing"}
    
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
            capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("[!] PowerShell execution failed:\n", e.stderr)
        return {"error": "PowerShell script execution failed"}
    except json.JSONDecodeError as e:
        print("[!] PowerShell returned invalid JSON:\n", result.stdout)
        return {"error": "Invalid JSON from PowerShell"}

def get_ip_address():
    """Get the current machine's non-localhost IP"""
    try:
        ip = socket.gethostbyname(socket.getfqdn())
        if ip.startswith("127."):
            # fallback using socket connect
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
        return ip
    except Exception:
        return "127.0.0.1"

def collect_python_system_info():
    """Collect system information using Python"""
    try:
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_size": round(usage.total / (1024 ** 3), 2),
                    "used": round(usage.used / (1024 ** 3), 2),
                    "free": round(usage.free / (1024 ** 3), 2)
                })
            except Exception:
                continue

        return {
            "timestamp": datetime.now().isoformat(),  # FIXED: Changed from datetime.datetime.now()
            "system": {
                "hostname": socket.gethostname(),
                "os": platform.system(),
                "os_version": platform.version(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "host_id": str(uuid.getnode())
            },
            "hardware": {
                "cpu_cores": psutil.cpu_count(logical=False),
                "cpu_threads": psutil.cpu_count(logical=True),
                "cpu_usage": psutil.cpu_percent(interval=1),
                "total_ram": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "available_ram": round(psutil.virtual_memory().available / (1024 ** 3), 2),
                "disk_info": disk_info
            },
            "network": {
                "ip_address": get_ip_address(),
                "mac_address": ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                                        for ele in range(0, 2 * 6, 2)][::-1])
            }
        }

    except Exception as e:
        print("[!] Error collecting system info:", str(e))
        return {"error": f"System info collection failed: {str(e)}"}

def merge_data(python_data, powershell_data):
    """Merge Python and PowerShell data"""
    return {
        "agent_source": "SpecScoreX Agent",
        "python_collected": python_data,
        "powershell_collected": powershell_data
    }

def send_to_backend(data, retries=3):
    """Send merged data to backend with retry support"""
    headers = {'Content-Type': 'application/json'}
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(API_ENDPOINT, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            print("[+] Data sent successfully.")
            print("[Server Response]:", response.text)
            return True
        except requests.exceptions.RequestException as e:
            print(f"[!] Attempt {attempt} failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print("[Server Response]:", e.response.text)
    
    print("[!] All attempts to send data failed.")
    return False

if __name__ == "__main__":
    print("[*] Starting system info agent...")

    python_info = collect_python_system_info()
    powershell_info = run_powershell_script(POWERSHELL_SCRIPT_PATH)
    final_data = merge_data(python_info, powershell_info)

    if SEND_TO_API:
        send_to_backend(final_data)
    else:
        print("[*] Debug Mode Output:\n")
        print(json.dumps(final_data, indent=2))