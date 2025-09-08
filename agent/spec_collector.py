import platform
import socket
import psutil
import json
import uuid
import hashlib
from datetime import datetime
import requests
import subprocess
import os
import sys
import tempfile
import logging
from typing import Dict, Any, Optional

# === CONFIGURATION ===
API_ENDPOINT = "https://specscorex.onrender.com/api/full-system-info"
SEND_TO_API = True  # Set to False for debug mode
ANONYMIZE_DATA = True  # Set to True to hash sensitive identifiers
LOG_LEVEL = logging.INFO

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enhanced PowerShell script with better error handling
POWERSHELL_SCRIPT = '''
$ProgressPreference = "SilentlyContinue"
$VerbosePreference = "SilentlyContinue" 
$WarningPreference = "SilentlyContinue"

function Get-SafeValue {
    param($Value, $Default = "Unknown")
    return if ($null -eq $Value -or $Value -eq "") { $Default } else { $Value }
}

function Convert-BytesToGB {
    param([long]$Bytes)
    return if ($Bytes -gt 0) { [math]::Round($Bytes / 1GB, 2) } else { 0 }
}

try {
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
    
    # OS Information with error handling
    try {
        $osInfo = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        $os = @{
            name = Get-SafeValue $osInfo.Caption
            version = Get-SafeValue $osInfo.Version
            build_number = Get-SafeValue $osInfo.BuildNumber
            architecture = Get-SafeValue $osInfo.OSArchitecture
            install_date = if ($osInfo.InstallDate) { $osInfo.InstallDate.ToString("yyyy-MM-dd") } else { "Unknown" }
            last_boot = if ($osInfo.LastBootUpTime) { $osInfo.LastBootUpTime.ToString("yyyy-MM-dd HH:mm:ss") } else { "Unknown" }
            timezone = Get-SafeValue (Get-TimeZone).Id
        }
    } catch {
        $os = @{error = "Failed to get OS info: $($_.Exception.Message)"}
    }
    
    # Computer System
    try {
        $computerInfo = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
        $computer = @{
            manufacturer = Get-SafeValue $computerInfo.Manufacturer
            model = Get-SafeValue $computerInfo.Model
            system_type = Get-SafeValue $computerInfo.SystemType
            total_physical_memory_gb = Convert-BytesToGB $computerInfo.TotalPhysicalMemory
            domain_role = switch ($computerInfo.DomainRole) {
                0 { "Standalone Workstation" }
                1 { "Member Workstation" }
                2 { "Standalone Server" }
                3 { "Member Server" }
                4 { "Backup Domain Controller" }
                5 { "Primary Domain Controller" }
                default { "Unknown" }
            }
        }
    } catch {
        $computer = @{error = "Failed to get computer info: $($_.Exception.Message)"}
    }
    
    # Processor Information
    try {
        $processorInfo = Get-CimInstance Win32_Processor -ErrorAction Stop
        $processors = @()
        foreach ($proc in $processorInfo) {
            $processors += @{
                name = Get-SafeValue $proc.Name
                manufacturer = Get-SafeValue $proc.Manufacturer
                cores = Get-SafeValue $proc.NumberOfCores 0
                logical_processors = Get-SafeValue $proc.NumberOfLogicalProcessors 0
                max_clock_speed_mhz = Get-SafeValue $proc.MaxClockSpeed 0
                current_clock_speed_mhz = Get-SafeValue $proc.CurrentClockSpeed 0
                architecture = switch ($proc.Architecture) {
                    0 { "x86" }
                    6 { "Intel Itanium" }
                    9 { "x64" }
                    default { "Unknown" }
                }
                l2_cache_size_kb = Get-SafeValue $proc.L2CacheSize 0
                l3_cache_size_kb = Get-SafeValue $proc.L3CacheSize 0
            }
        }
    } catch {
        $processors = @{error = "Failed to get processor info: $($_.Exception.Message)"}
    }
    
    # Memory Information
    try {
        $memoryInfo = Get-CimInstance Win32_PhysicalMemory -ErrorAction Stop
        $memory = @()
        foreach ($mem in $memoryInfo) {
            $memory += @{
                capacity_gb = Convert-BytesToGB $mem.Capacity
                manufacturer = Get-SafeValue $mem.Manufacturer
                speed_mhz = Get-SafeValue $mem.Speed 0
                memory_type = switch ($mem.MemoryType) {
                    20 { "DDR" }
                    21 { "DDR2" }
                    24 { "DDR3" }
                    26 { "DDR4" }
                    default { "Unknown" }
                }
                form_factor = switch ($mem.FormFactor) {
                    8 { "DIMM" }
                    12 { "SO-DIMM" }
                    default { "Unknown" }
                }
                bank_label = Get-SafeValue $mem.BankLabel
            }
        }
    } catch {
        $memory = @{error = "Failed to get memory info: $($_.Exception.Message)"}
    }
    
    # Storage Information
    try {
        $logicalDiskInfo = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 } -ErrorAction Stop
        $logicalDisks = @()
        foreach ($disk in $logicalDiskInfo) {
            $logicalDisks += @{
                drive_letter = Get-SafeValue $disk.DeviceID
                file_system = Get-SafeValue $disk.FileSystem
                size_gb = Convert-BytesToGB $disk.Size
                free_gb = Convert-BytesToGB $disk.FreeSpace
                free_percent = if ($disk.Size -gt 0) { [math]::Round(($disk.FreeSpace / $disk.Size) * 100, 2) } else { 0 }
            }
        }
        
        $physicalDiskInfo = Get-CimInstance Win32_DiskDrive -ErrorAction Stop
        $physicalDisks = @()
        foreach ($disk in $physicalDiskInfo) {
            $physicalDisks += @{
                model = Get-SafeValue $disk.Model
                interface_type = Get-SafeValue $disk.InterfaceType
                size_gb = Convert-BytesToGB $disk.Size
                media_type = Get-SafeValue $disk.MediaType
            }
        }
        
        $storage = @{
            logical_disks = $logicalDisks
            physical_disks = $physicalDisks
        }
    } catch {
        $storage = @{error = "Failed to get storage info: $($_.Exception.Message)"}
    }
    
    # Graphics Information
    try {
        $gpuInfo = Get-CimInstance Win32_VideoController -ErrorAction Stop
        $gpus = @()
        foreach ($gpu in $gpuInfo) {
            $gpus += @{
                name = Get-SafeValue $gpu.Name
                adapter_ram_gb = Convert-BytesToGB $gpu.AdapterRAM
                driver_version = Get-SafeValue $gpu.DriverVersion
                current_horizontal_resolution = Get-SafeValue $gpu.CurrentHorizontalResolution 0
                current_vertical_resolution = Get-SafeValue $gpu.CurrentVerticalResolution 0
            }
        }
    } catch {
        $gpus = @{error = "Failed to get GPU info: $($_.Exception.Message)"}
    }
    
    # Network Information (basic, non-sensitive)
    try {
        $networkInfo = Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true } -ErrorAction Stop
        $networkAdapters = @()
        foreach ($adapter in $networkInfo) {
            $networkAdapters += @{
                description = Get-SafeValue $adapter.Description
                dhcp_enabled = Get-SafeValue $adapter.DHCPEnabled $false
                ip_count = if ($adapter.IPAddress) { $adapter.IPAddress.Count } else { 0 }
            }
        }
    } catch {
        $networkAdapters = @{error = "Failed to get network info: $($_.Exception.Message)"}
    }
    
    # Build system info object
    $systemInfo = @{
        timestamp = $timestamp
        system = @{
            operating_system = $os
            computer_system = $computer
        }
        hardware = @{
            processors = $processors
            memory_modules = $memory
        }
        storage = $storage
        graphics = @{
            video_controllers = $gpus
        }
        network = @{
            adapters = $networkAdapters
        }
    }
    
    $systemInfo | ConvertTo-Json -Depth 10 -Compress
    
} catch {
    $errorObj = @{
        error = "PowerShell execution error: $($_.Exception.Message)"
        timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
    }
    Write-Output ($errorObj | ConvertTo-Json -Compress)
    exit 1
}
'''

def anonymize_sensitive_data(value: str) -> str:
    """Hash sensitive data for privacy while maintaining uniqueness"""
    if not value or value.lower() in ['unknown', 'n/a', '']:
        return value
    return hashlib.sha256(value.encode()).hexdigest()[:16]

def run_powershell_script() -> Dict[str, Any]:
    """Execute PowerShell script with improved error handling"""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(POWERSHELL_SCRIPT)
            temp_script_path = temp_file.name
        
        try:
            logger.info("Executing PowerShell script...")
            result = subprocess.run([
                "powershell", 
                "-ExecutionPolicy", "Bypass", 
                "-NoProfile", 
                "-NonInteractive",
                "-File", temp_script_path
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"PowerShell failed with exit code {result.returncode}")
                return {"error": f"PowerShell script failed: {result.stderr}"}
            
            # Parse JSON output
            output = result.stdout.strip()
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_content = output[json_start:json_end]
                return json.loads(json_content)
            else:
                return {"error": "No valid JSON found in PowerShell output"}
                
        finally:
            try:
                os.unlink(temp_script_path)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        logger.error("PowerShell script execution timed out")
        return {"error": "PowerShell script execution timed out"}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from PowerShell: {e}")
        return {"error": f"Invalid JSON from PowerShell: {str(e)}"}
    except Exception as e:
        logger.error(f"PowerShell script error: {e}")
        return {"error": f"PowerShell script error: {str(e)}"}

def get_python_system_info() -> Dict[str, Any]:
    """Collect system information using Python libraries"""
    try:
        # Get disk information
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_size_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
                    "usage_percent": round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0
                })
            except (PermissionError, FileNotFoundError):
                continue

        # Get network interface info (non-sensitive)
        network_stats = psutil.net_if_stats()
        network_info = []
        for interface, stats in network_stats.items():
            if stats.isup:
                network_info.append({
                    "interface": interface,
                    "is_up": stats.isup,
                    "speed_mbps": stats.speed if stats.speed > 0 else None,
                    "mtu": stats.mtu
                })

        # Get basic system info
        hostname = socket.gethostname()
        if ANONYMIZE_DATA:
            hostname = anonymize_sensitive_data(hostname)

        return {
            "timestamp": datetime.now().isoformat(),
            "collection_method": "python",
            "system": {
                "hostname": hostname,
                "os": platform.system(),
                "os_version": platform.version(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            },
            "hardware": {
                "cpu_cores_physical": psutil.cpu_count(logical=False),
                "cpu_cores_logical": psutil.cpu_count(logical=True),
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
                "total_ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
                "available_ram_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
                "ram_usage_percent": psutil.virtual_memory().percent
            },
            "storage": {
                "disk_partitions": disk_info
            },
            "network": {
                "interfaces": network_info
            },
            "process_info": {
                "total_processes": len(psutil.pids()),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Error collecting Python system info: {e}")
        return {"error": f"Python system info collection failed: {str(e)}"}

def apply_privacy_filters(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply privacy filters to sensitive data if anonymization is enabled"""
    if not ANONYMIZE_DATA:
        return data
    
    logger.info("Applying privacy filters to sensitive data...")
    
    def anonymize_recursive(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in ['serial_number', 'mac_address', 'hostname', 'name', 'username']:
                    if isinstance(value, str):
                        obj[key] = anonymize_sensitive_data(value)
                elif isinstance(value, (dict, list)):
                    anonymize_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                anonymize_recursive(item)
    
    anonymize_recursive(data)
    return data

def send_data_to_api(data: Dict[str, Any], retries: int = 3) -> bool:
    """Send data to API with retry logic and better error handling"""
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'SpecScoreX-Agent/1.0'
    }
    
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Sending data to API (attempt {attempt}/{retries})...")
            response = requests.post(
                API_ENDPOINT, 
                json=data, 
                headers=headers, 
                timeout=30,
                verify=True  # Ensure SSL certificate verification
            )
            response.raise_for_status()
            
            logger.info("Data sent successfully to API")
            logger.info(f"Server response: {response.text[:200]}...")
            return True
            
        except requests.exceptions.Timeout:
            logger.warning(f"API request timeout on attempt {attempt}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error on attempt {attempt}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error on attempt {attempt}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Server response: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt}: {e}")
    
    logger.error("All API send attempts failed")
    return False

def main():
    """Main execution function"""
    logger.info("Starting enhanced system information collector...")
    logger.info(f"Anonymization: {'ENABLED' if ANONYMIZE_DATA else 'DISABLED'}")
    
    # Collect data from both sources
    python_data = get_python_system_info()
    powershell_data = run_powershell_script()
    
    # Merge the data
    final_data = {
        "agent_info": {
            "name": "SpecScoreX Enhanced Agent",
            "version": "2.0",
            "timestamp": datetime.now().isoformat(),
            "privacy_mode": ANONYMIZE_DATA
        },
        "python_collected": python_data,
        "powershell_collected": powershell_data
    }
    
    # Apply privacy filters
    final_data = apply_privacy_filters(final_data)
    
    if SEND_TO_API:
        success = send_data_to_api(final_data)
        if success:
            logger.info("Opening results page...")
            try:
                import webbrowser
                webbrowser.open("https://specscorex.onrender.com/report")
            except Exception as e:
                logger.warning(f"Could not open browser: {e}")
        else:
            logger.error("Failed to send data to API")
    else:
        logger.info("Debug mode - displaying collected data:")
        print(json.dumps(final_data, indent=2, default=str))

if __name__ == "__main__":
    main()