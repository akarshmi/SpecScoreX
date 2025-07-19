import platform
import socket
import psutil
import json
import uuid
from datetime import datetime
import requests
import subprocess
import os
import sys
import tempfile

# === CONFIGURATION ===
API_ENDPOINT = "http://localhost:5000/api/full-system-info"
SEND_TO_API = True  # Set to False for debug mode without sending

# Robust PowerShell script without auto-elevation
POWERSHELL_SCRIPT = '''
# Suppress progress bars and verbose output
$ProgressPreference = "SilentlyContinue"
$VerbosePreference = "SilentlyContinue"
$WarningPreference = "SilentlyContinue"

try {
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    
    # Operating System - with error handling
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop | Select-Object Caption, Version, OSArchitecture, LastBootUpTime, BuildNumber, InstallDate
    } catch {
        $os = @{error = "Failed to get OS info: $($_.Exception.Message)"}
    }
    
    # Computer System
    try {
        $computer = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop | Select-Object Manufacturer, Model, Name, TotalPhysicalMemory, SystemType
    } catch {
        $computer = @{error = "Failed to get computer info: $($_.Exception.Message)"}
    }
    
    # Processor Info
    try {
        $processors = Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed
    } catch {
        $processors = @{error = "Failed to get processor info: $($_.Exception.Message)"}
    }
    
    # Physical Memory (RAM Modules)
    try {
        $memory = Get-CimInstance Win32_PhysicalMemory -ErrorAction Stop | Select-Object Capacity, Manufacturer, Speed, PartNumber, SerialNumber
    } catch {
        $memory = @{error = "Failed to get memory info: $($_.Exception.Message)"}
    }
    
    # BIOS Info
    try {
        $bios = Get-CimInstance Win32_BIOS -ErrorAction Stop | Select-Object Manufacturer, SerialNumber, SMBIOSBIOSVersion, ReleaseDate
    } catch {
        $bios = @{error = "Failed to get BIOS info: $($_.Exception.Message)"}
    }
    
    # Motherboard / Baseboard
    try {
        $motherboard = Get-CimInstance Win32_BaseBoard -ErrorAction Stop | Select-Object Manufacturer, Product, SerialNumber
    } catch {
        $motherboard = @{error = "Failed to get motherboard info: $($_.Exception.Message)"}
    }
    
    # Logical Disks (Volumes)
    try {
        $logicalDisks = Get-CimInstance Win32_LogicalDisk -ErrorAction Stop | Where-Object { $_.DriveType -eq 3 } | 
            Select-Object DeviceID, VolumeName, 
                @{Name="SizeGB";Expression={if ($_.Size) {[math]::Round($_.Size / 1GB, 2)} else {0}}}, 
                @{Name="FreeGB";Expression={if ($_.FreeSpace) {[math]::Round($_.FreeSpace / 1GB, 2)} else {0}}}
    } catch {
        $logicalDisks = @{error = "Failed to get logical disk info: $($_.Exception.Message)"}
    }
    
    # Physical Disks
    try {
        $physicalDisks = Get-CimInstance Win32_DiskDrive -ErrorAction Stop | Select-Object Model, InterfaceType, 
            @{Name="SizeGB";Expression={if ($_.Size) {[math]::Round($_.Size / 1GB, 2)} else {0}}}
    } catch {
        $physicalDisks = @{error = "Failed to get physical disk info: $($_.Exception.Message)"}
    }
    
    # GPU / Video Controller
    try {
        $gpus = Get-CimInstance Win32_VideoController -ErrorAction Stop | Select-Object Name, DriverVersion, 
            @{Name="AdapterRAMGB";Expression={if ($_.AdapterRAM -and $_.AdapterRAM -gt 0) {[math]::Round($_.AdapterRAM / 1GB, 2)} else {0}}}
    } catch {
        $gpus = @{error = "Failed to get GPU info: $($_.Exception.Message)"}
    }
    
    # Network Adapters
    try {
        $networkAdapters = Get-CimInstance Win32_NetworkAdapterConfiguration -ErrorAction Stop | Where-Object { $_.IPEnabled -eq $true } |
            Select-Object Description, MACAddress, IPAddress, DefaultIPGateway, DNSServerSearchOrder
    } catch {
        $networkAdapters = @{error = "Failed to get network adapter info: $($_.Exception.Message)"}
    }
    
    # Battery Info (if available)
    try {
        $battery = Get-CimInstance Win32_Battery -ErrorAction Stop | Select-Object Name, EstimatedChargeRemaining, BatteryStatus, DesignVoltage
        if (-not $battery) {
            $battery = @{info = "No battery detected (desktop system)"}
        }
    } catch {
        $battery = @{error = "Failed to get battery info: $($_.Exception.Message)"}
    }
    
    # Build the complete system info object
    $systemInfo = @{
        timestamp = $timestamp
        system = @{
            operating_system = $os
            computer_system = $computer
            processors = $processors
            memory_modules = $memory
            bios = $bios
            motherboard = $motherboard
        }
        storage = @{
            logical_disks = $logicalDisks
            physical_disks = $physicalDisks
        }
        graphics = @{
            gpus = $gpus
        }
        network = @{
            adapters = $networkAdapters
        }
        power = @{
            battery = $battery
        }
    }
    
    # Convert to JSON with proper depth and formatting
    $json = $systemInfo | ConvertTo-Json -Depth 10 -Compress
    Write-Output $json
    
} catch {
    $errorObj = @{
        error = "PowerShell execution error: $($_.Exception.Message)"
        line = if ($_.InvocationInfo.ScriptLineNumber) { $_.InvocationInfo.ScriptLineNumber } else { "Unknown" }
        position = if ($_.InvocationInfo.OffsetInLine) { $_.InvocationInfo.OffsetInLine } else { "Unknown" }
    }
    Write-Output ($errorObj | ConvertTo-Json -Compress)
    exit 1
}
'''

def run_embedded_powershell_script():
    """Create temporary PowerShell script and run it with better error handling"""
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(POWERSHELL_SCRIPT)
            temp_script_path = temp_file.name
        
        try:
            # Run PowerShell with better parameters
            result = subprocess.run([
                "powershell", 
                "-ExecutionPolicy", "Bypass", 
                "-NoProfile", 
                "-NonInteractive",
                "-File", temp_script_path
            ], capture_output=True, text=True, timeout=30)
            
            print(f"[DEBUG] PowerShell exit code: {result.returncode}")
            print(f"[DEBUG] PowerShell stdout: {result.stdout[:500]}...")
            print(f"[DEBUG] PowerShell stderr: {result.stderr[:500]}...")
            
            if result.returncode != 0:
                return {"error": f"PowerShell script failed with exit code {result.returncode}: {result.stderr}"}
            
            # Clean the output - remove any extra whitespace or non-JSON content
            output = result.stdout.strip()
            
            # Find the JSON content (in case there are other messages)
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_content = output[json_start:json_end]
                return json.loads(json_content)
            else:
                return {"error": "No valid JSON found in PowerShell output"}
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_script_path)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        return {"error": "PowerShell script execution timed out"}
    except subprocess.CalledProcessError as e:
        print("[!] PowerShell execution failed:\n", e.stderr)
        return {"error": f"PowerShell script execution failed: {e.stderr}"}
    except json.JSONDecodeError as e:
        print("[!] PowerShell returned invalid JSON:")
        print(f"Output: {result.stdout}")
        print(f"Error: {e}")
        return {"error": f"Invalid JSON from PowerShell: {str(e)}"}
    except Exception as e:
        print("[!] Error running PowerShell script:", str(e))
        return {"error": f"PowerShell script error: {str(e)}"}

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
            "timestamp": datetime.now().isoformat(),
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

def test_powershell_directly():
    """Test PowerShell execution directly for debugging"""
    print("[*] Testing PowerShell execution...")
    
    # Simple test script
    test_script = '''
    try {
        $info = @{
            test = "success"
            timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
        }
        $info | ConvertTo-Json -Compress
    } catch {
        Write-Output "Error: $($_.Exception.Message)"
    }
    '''
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(test_script)
            temp_script_path = temp_file.name
        
        result = subprocess.run([
            "powershell", 
            "-ExecutionPolicy", "Bypass", 
            "-NoProfile", 
            "-NonInteractive",
            "-File", temp_script_path
        ], capture_output=True, text=True, timeout=10)
        
        print(f"[DEBUG] Test exit code: {result.returncode}")
        print(f"[DEBUG] Test stdout: {result.stdout}")
        print(f"[DEBUG] Test stderr: {result.stderr}")
        
        os.unlink(temp_script_path)
        
        if result.returncode == 0:
            print("[+] PowerShell test successful!")
            return True
        else:
            print("[!] PowerShell test failed!")
            return False
            
    except Exception as e:
        print(f"[!] PowerShell test error: {e}")
        return False

if __name__ == "__main__":
    print("[*] Starting system info agent...")
    
    # Test PowerShell first
    if not test_powershell_directly():
        print("[!] PowerShell test failed. Continuing with Python-only data...")
    
    python_info = collect_python_system_info()
    powershell_info = run_embedded_powershell_script()
    final_data = merge_data(python_info, powershell_info)

    if SEND_TO_API:
        if send_to_backend(final_data):
            import webbrowser
            webbrowser.open("http://localhost:5000/report")
    else:
        print("[*] Debug Mode Output:\n")
        print(json.dumps(final_data, indent=2))