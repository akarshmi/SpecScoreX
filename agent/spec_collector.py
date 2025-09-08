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
API_ENDPOINT = "https://specscorex.onrender.com/api/full-system-info"
SEND_TO_API = True  # Set to False for debug mode without sending

# Robust PowerShell script without auto-elevation
POWERSHELL_SCRIPT = '''

<#
.SYNOPSIS
    Gathers complete system specification information in JSON format.
.DESCRIPTION
    This script collects OS, hardware, processor, disk, network, GPU, BIOS, and memory info.
    It auto-prompts for admin privileges if needed and outputs JSON for API integration.
.OUTPUTS
    JSON-formatted system information
#>

# ========== Auto-Elevation Block ==========
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Restarting script as administrator..."
    Start-Process powershell "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}
# ==========================================

function Get-SystemInfo {
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    
    # Operating System
    $os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, LastBootUpTime, BuildNumber, InstallDate
    
    # Computer System
    $computer = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, Name, TotalPhysicalMemory, SystemType
    
    # Processor Info
    $processors = Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed
    
    # Physical Memory (RAM Modules)
    $memory = Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity, Manufacturer, Speed, PartNumber, SerialNumber
    
    # BIOS Info
    $bios = Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SerialNumber, SMBIOSBIOSVersion, ReleaseDate
    
    # Motherboard / Baseboard
    $motherboard = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product, SerialNumber
    
    # Logical Disks (Volumes)
    $logicalDisks = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 } | 
        Select-Object DeviceID, VolumeName, 
            @{Name="SizeGB";Expression={[math]::Round($_.Size / 1GB, 2)}}, 
            @{Name="FreeGB";Expression={[math]::Round($_.FreeSpace / 1GB, 2)}}
    
    # Physical Disks
    $physicalDisks = Get-CimInstance Win32_DiskDrive | Select-Object Model, InterfaceType, 
        @{Name="SizeGB";Expression={[math]::Round($_.Size / 1GB, 2)}}
    
    # GPU / Video Controller
    $gpus = Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, 
        @{Name="AdapterRAMGB";Expression={[math]::Round($_.AdapterRAM / 1GB, 2)}}
    
    # Network Adapters
    $networkAdapters = Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true } |
        Select-Object Description, MACAddress, IPAddress, DefaultIPGateway, DNSServerSearchOrder
    
    # Battery Info (if available)
    $battery = Get-CimInstance Win32_Battery | Select-Object Name, EstimatedChargeRemaining, BatteryStatus, DesignVoltage
    
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
    
    return $systemInfo
}

# Main execution
try {
    $systemInfo = Get-SystemInfo
    # Convert to JSON with proper depth and formatting
    $systemInfo | ConvertTo-Json -Depth 10
} catch {
    Write-Output (@{"error" = $_.Exception.Message} | ConvertTo-Json)
    exit 1
}<#
.SYNOPSIS
    Gathers comprehensive system specification information in JSON format.
.DESCRIPTION
    This enhanced script collects detailed OS, hardware, processor, disk, network, GPU, BIOS, 
    memory, and performance information. It auto-prompts for admin privileges if needed and 
    outputs structured JSON for API integration with improved error handling.
.OUTPUTS
    JSON-formatted system information with enhanced data structure
.NOTES
    Requires PowerShell 5.1+ and administrative privileges for complete hardware access
#>

# ========== Auto-Elevation Block ==========
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Requesting administrator privileges..." -ForegroundColor Yellow
    try {
        Start-Process powershell "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs -Wait
    } catch {
        Write-Error "Failed to elevate privileges: $_"
    }
    exit
}
# ==========================================

function Get-SafeValue {
    param($Value, $Default = "Unknown")
    return if ($null -eq $Value -or $Value -eq "") { $Default } else { $Value }
}

function Convert-BytesToGB {
    param([long]$Bytes)
    return if ($Bytes -gt 0) { [math]::Round($Bytes / 1GB, 2) } else { 0 }
}

function Get-UptimeFormatted {
    param([datetime]$BootTime)
    $uptime = (Get-Date) - $BootTime
    return @{
        days = $uptime.Days
        hours = $uptime.Hours
        minutes = $uptime.Minutes
        total_hours = [math]::Round($uptime.TotalHours, 2)
    }
}

function Get-SystemInfo {
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
    Write-Host "Gathering system information..." -ForegroundColor Green
    
    try {
        # Operating System - Enhanced
        Write-Host "  - Operating System..." -ForegroundColor Cyan
        $osInfo = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        $os = @{
            name = Get-SafeValue $osInfo.Caption
            version = Get-SafeValue $osInfo.Version
            build_number = Get-SafeValue $osInfo.BuildNumber
            architecture = Get-SafeValue $osInfo.OSArchitecture
            install_date = if ($osInfo.InstallDate) { $osInfo.InstallDate.ToString("yyyy-MM-ddTHH:mm:ss") } else { "Unknown" }
            last_boot = if ($osInfo.LastBootUpTime) { $osInfo.LastBootUpTime.ToString("yyyy-MM-ddTHH:mm:ss") } else { "Unknown" }
            uptime = if ($osInfo.LastBootUpTime) { Get-UptimeFormatted $osInfo.LastBootUpTime } else { @{} }
            locale = Get-SafeValue $osInfo.Locale
            timezone = Get-SafeValue (Get-TimeZone).Id
            system_directory = Get-SafeValue $osInfo.SystemDirectory
            windows_directory = Get-SafeValue $osInfo.WindowsDirectory
        }

        # Computer System - Enhanced
        Write-Host "  - Computer System..." -ForegroundColor Cyan
        $computerInfo = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
        $computer = @{
            manufacturer = Get-SafeValue $computerInfo.Manufacturer
            model = Get-SafeValue $computerInfo.Model
            name = Get-SafeValue $computerInfo.Name
            domain = Get-SafeValue $computerInfo.Domain
            workgroup = Get-SafeValue $computerInfo.Workgroup
            system_type = Get-SafeValue $computerInfo.SystemType
            total_physical_memory_gb = Convert-BytesToGB $computerInfo.TotalPhysicalMemory
            username = Get-SafeValue $computerInfo.UserName
            power_state = Get-SafeValue $computerInfo.PowerState
            thermal_state = Get-SafeValue $computerInfo.ThermalState
        }

        # Processor Info - Enhanced
        Write-Host "  - Processors..." -ForegroundColor Cyan
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
                    1 { "MIPS" }
                    2 { "Alpha" }
                    3 { "PowerPC" }
                    6 { "Intel Itanium" }
                    9 { "x64" }
                    default { "Unknown" }
                }
                socket_designation = Get-SafeValue $proc.SocketDesignation
                family = Get-SafeValue $proc.Family
                l2_cache_size_kb = Get-SafeValue $proc.L2CacheSize 0
                l3_cache_size_kb = Get-SafeValue $proc.L3CacheSize 0
                voltage = Get-SafeValue $proc.CurrentVoltage
            }
        }

        # Physical Memory - Enhanced
        Write-Host "  - Memory Modules..." -ForegroundColor Cyan
        $memoryInfo = Get-CimInstance Win32_PhysicalMemory -ErrorAction Stop
        $memory = @()
        foreach ($mem in $memoryInfo) {
            $memory += @{
                capacity_gb = Convert-BytesToGB $mem.Capacity
                manufacturer = Get-SafeValue $mem.Manufacturer
                part_number = Get-SafeValue $mem.PartNumber
                serial_number = Get-SafeValue $mem.SerialNumber
                speed_mhz = Get-SafeValue $mem.Speed 0
                memory_type = switch ($mem.MemoryType) {
                    0 { "Unknown" }
                    20 { "DDR" }
                    21 { "DDR2" }
                    22 { "DDR2 FB-DIMM" }
                    24 { "DDR3" }
                    26 { "DDR4" }
                    default { "Other" }
                }
                form_factor = switch ($mem.FormFactor) {
                    8 { "DIMM" }
                    12 { "SO-DIMM" }
                    13 { "Micro-DIMM" }
                    default { "Unknown" }
                }
                bank_label = Get-SafeValue $mem.BankLabel
                device_locator = Get-SafeValue $mem.DeviceLocator
            }
        }

        # BIOS/UEFI Info - Enhanced
        Write-Host "  - BIOS/UEFI..." -ForegroundColor Cyan
        $biosInfo = Get-CimInstance Win32_BIOS -ErrorAction Stop
        $bios = @{
            manufacturer = Get-SafeValue $biosInfo.Manufacturer
            serial_number = Get-SafeValue $biosInfo.SerialNumber
            version = Get-SafeValue $biosInfo.SMBIOSBIOSVersion
            release_date = if ($biosInfo.ReleaseDate) { $biosInfo.ReleaseDate.ToString("yyyy-MM-dd") } else { "Unknown" }
            smbios_version = Get-SafeValue $biosInfo.SMBIOSMajorVersion, $biosInfo.SMBIOSMinorVersion -join "."
        }

        # Motherboard - Enhanced
        Write-Host "  - Motherboard..." -ForegroundColor Cyan
        $motherboardInfo = Get-CimInstance Win32_BaseBoard -ErrorAction Stop
        $motherboard = @{
            manufacturer = Get-SafeValue $motherboardInfo.Manufacturer
            product = Get-SafeValue $motherboardInfo.Product
            version = Get-SafeValue $motherboardInfo.Version
            serial_number = Get-SafeValue $motherboardInfo.SerialNumber
        }

        # Storage - Enhanced
        Write-Host "  - Storage Devices..." -ForegroundColor Cyan
        
        # Logical Disks
        $logicalDiskInfo = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 } -ErrorAction Stop
        $logicalDisks = @()
        foreach ($disk in $logicalDiskInfo) {
            $logicalDisks += @{
                drive_letter = Get-SafeValue $disk.DeviceID
                volume_name = Get-SafeValue $disk.VolumeName
                file_system = Get-SafeValue $disk.FileSystem
                size_gb = Convert-BytesToGB $disk.Size
                free_gb = Convert-BytesToGB $disk.FreeSpace
                used_gb = Convert-BytesToGB ($disk.Size - $disk.FreeSpace)
                free_percent = if ($disk.Size -gt 0) { [math]::Round(($disk.FreeSpace / $disk.Size) * 100, 2) } else { 0 }
            }
        }

        # Physical Disks
        $physicalDiskInfo = Get-CimInstance Win32_DiskDrive -ErrorAction Stop
        $physicalDisks = @()
        foreach ($disk in $physicalDiskInfo) {
            $physicalDisks += @{
                model = Get-SafeValue $disk.Model
                manufacturer = Get-SafeValue $disk.Manufacturer
                interface_type = Get-SafeValue $disk.InterfaceType
                size_gb = Convert-BytesToGB $disk.Size
                media_type = Get-SafeValue $disk.MediaType
                serial_number = Get-SafeValue $disk.SerialNumber
                firmware_revision = Get-SafeValue $disk.FirmwareRevision
                partitions = Get-SafeValue $disk.Partitions 0
            }
        }

        # Graphics - Enhanced
        Write-Host "  - Graphics Cards..." -ForegroundColor Cyan
        $gpuInfo = Get-CimInstance Win32_VideoController -ErrorAction Stop
        $gpus = @()
        foreach ($gpu in $gpuInfo) {
            $gpus += @{
                name = Get-SafeValue $gpu.Name
                driver_version = Get-SafeValue $gpu.DriverVersion
                driver_date = if ($gpu.DriverDate) { $gpu.DriverDate.ToString("yyyy-MM-dd") } else { "Unknown" }
                adapter_ram_gb = Convert-BytesToGB $gpu.AdapterRAM
                video_processor = Get-SafeValue $gpu.VideoProcessor
                video_mode_description = Get-SafeValue $gpu.VideoModeDescription
                current_horizontal_resolution = Get-SafeValue $gpu.CurrentHorizontalResolution 0
                current_vertical_resolution = Get-SafeValue $gpu.CurrentVerticalResolution 0
                current_refresh_rate = Get-SafeValue $gpu.CurrentRefreshRate 0
                max_refresh_rate = Get-SafeValue $gpu.MaxRefreshRate 0
                adapter_compatibility = Get-SafeValue $gpu.AdapterCompatibility
            }
        }

        # Network Adapters - Enhanced
        Write-Host "  - Network Adapters..." -ForegroundColor Cyan
        $networkInfo = Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true } -ErrorAction Stop
        $networkAdapters = @()
        foreach ($adapter in $networkInfo) {
            $networkAdapters += @{
                description = Get-SafeValue $adapter.Description
                mac_address = Get-SafeValue $adapter.MACAddress
                ip_addresses = if ($adapter.IPAddress) { $adapter.IPAddress } else { @() }
                subnet_masks = if ($adapter.IPSubnet) { $adapter.IPSubnet } else { @() }
                default_gateways = if ($adapter.DefaultIPGateway) { $adapter.DefaultIPGateway } else { @() }
                dns_servers = if ($adapter.DNSServerSearchOrder) { $adapter.DNSServerSearchOrder } else { @() }
                dhcp_enabled = Get-SafeValue $adapter.DHCPEnabled $false
                dhcp_server = Get-SafeValue $adapter.DHCPServer
                wins_primary_server = Get-SafeValue $adapter.WINSPrimaryServer
                domain_dns_registration_enabled = Get-SafeValue $adapter.DomainDNSRegistrationEnabled $false
            }
        }

        # Physical Network Adapters
        $physicalNetworkInfo = Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.PhysicalAdapter -eq $true -and $_.NetConnectionStatus -ne $null } -ErrorAction SilentlyContinue
        $physicalNetworkAdapters = @()
        foreach ($adapter in $physicalNetworkInfo) {
            $physicalNetworkAdapters += @{
                name = Get-SafeValue $adapter.Name
                manufacturer = Get-SafeValue $adapter.Manufacturer
                adapter_type = Get-SafeValue $adapter.AdapterType
                speed_mbps = if ($adapter.Speed) { [math]::Round($adapter.Speed / 1MB, 0) } else { 0 }
                connection_status = switch ($adapter.NetConnectionStatus) {
                    0 { "Disconnected" }
                    1 { "Connecting" }
                    2 { "Connected" }
                    3 { "Disconnecting" }
                    4 { "Hardware not present" }
                    5 { "Hardware disabled" }
                    6 { "Hardware malfunction" }
                    7 { "Media disconnected" }
                    8 { "Authenticating" }
                    9 { "Authentication succeeded" }
                    10 { "Authentication failed" }
                    11 { "Invalid address" }
                    12 { "Credentials required" }
                    default { "Unknown" }
                }
            }
        }

        # Battery Info - Enhanced
        Write-Host "  - Power/Battery..." -ForegroundColor Cyan
        $batteryInfo = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
        $battery = @()
        if ($batteryInfo) {
            foreach ($bat in $batteryInfo) {
                $battery += @{
                    name = Get-SafeValue $bat.Name
                    estimated_charge_remaining = Get-SafeValue $bat.EstimatedChargeRemaining 0
                    battery_status = switch ($bat.BatteryStatus) {
                        1 { "Discharging" }
                        2 { "On AC" }
                        3 { "Fully Charged" }
                        4 { "Low" }
                        5 { "Critical" }
                        6 { "Charging" }
                        7 { "Charging and High" }
                        8 { "Charging and Low" }
                        9 { "Charging and Critical" }
                        10 { "Undefined" }
                        11 { "Partially Charged" }
                        default { "Unknown" }
                    }
                    design_voltage = Get-SafeValue $bat.DesignVoltage 0
                    chemistry = switch ($bat.Chemistry) {
                        1 { "Other" }
                        2 { "Unknown" }
                        3 { "Lead Acid" }
                        4 { "Nickel Cadmium" }
                        5 { "Nickel Metal Hydride" }
                        6 { "Lithium Ion" }
                        7 { "Zinc Air" }
                        8 { "Lithium Polymer" }
                        default { "Unknown" }
                    }
                    estimated_run_time = Get-SafeValue $bat.EstimatedRunTime 0
                }
            }
        }

        # Performance Counters
        Write-Host "  - Performance Metrics..." -ForegroundColor Cyan
        $performance = @{
            cpu_usage_percent = try { (Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction Stop).CounterSamples.CookedValue } catch { 0 }
            available_memory_gb = try { Convert-BytesToGB ((Get-Counter '\Memory\Available Bytes' -ErrorAction Stop).CounterSamples.CookedValue) } catch { 0 }
            page_file_usage_percent = try { (Get-Counter '\Paging File(_Total)\% Usage' -ErrorAction Stop).CounterSamples.CookedValue } catch { 0 }
        }

        # System Services Status
        Write-Host "  - Critical Services..." -ForegroundColor Cyan
        $criticalServices = @('Winmgmt', 'EventLog', 'PlugPlay', 'RpcSs', 'Themes')
        $services = @()
        foreach ($serviceName in $criticalServices) {
            $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ($service) {
                $services += @{
                    name = $service.Name
                    display_name = $service.DisplayName
                    status = $service.Status.ToString()
                    start_type = $service.StartType.ToString()
                }
            }
        }

        # Build the complete system info object
        $systemInfo = @{
            metadata = @{
                timestamp = $timestamp
                script_version = "2.0"
                collection_time_ms = 0  # Will be calculated at the end
                hostname = $env:COMPUTERNAME
                user_context = $env:USERNAME
            }
            system = @{
                operating_system = $os
                computer_system = $computer
                performance = $performance
                critical_services = $services
            }
            hardware = @{
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
                video_controllers = $gpus
            }
            network = @{
                configured_adapters = $networkAdapters
                physical_adapters = $physicalNetworkAdapters
            }
            power = @{
                battery_info = $battery
                power_schemes = @{
                    active_scheme = try { (powercfg /getactivescheme).Split(':')[1].Trim() } catch { "Unknown" }
                }
            }
        }
        
        Write-Host "System information collection completed successfully!" -ForegroundColor Green
        return $systemInfo

    } catch {
        Write-Error "Error collecting system information: $_"
        return @{
            error = @{
                message = $_.Exception.Message
                timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
                script_line = $_.InvocationInfo.ScriptLineNumber
            }
        }
    }
}

# Main execution with enhanced error handling
Write-Host "=== Windows System Information Collector v2.0 ===" -ForegroundColor Yellow
Write-Host "Collecting comprehensive system information..." -ForegroundColor White

$startTime = Get-Date

try {
    $systemInfo = Get-SystemInfo
    
    # Calculate collection time
    $endTime = Get-Date
    $collectionTime = ($endTime - $startTime).TotalMilliseconds
    $systemInfo.metadata.collection_time_ms = [math]::Round($collectionTime, 2)
    
    # Convert to JSON with proper depth and formatting
    $jsonOutput = $systemInfo | ConvertTo-Json -Depth 15 -Compress:$false
    
    Write-Host "`nJSON output generated successfully!" -ForegroundColor Green
    Write-Host "Collection completed in $([math]::Round($collectionTime, 2)) ms" -ForegroundColor Green
    
    # Output the JSON
    $jsonOutput
    
} catch {
    Write-Error "Critical error in main execution: $_"
    
    # Output error in JSON format
    $errorOutput = @{
        error = @{
            message = $_.Exception.Message
            timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
            script_line = $_.InvocationInfo.ScriptLineNumber
            stack_trace = $_.ScriptStackTrace
        }
    } | ConvertTo-Json -Depth 5
    
    Write-Output $errorOutput
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
            webbrowser.open("https://specscorex.onrender.com/report")
    else:
        print("[*] Debug Mode Output:\n")
        print(json.dumps(final_data, indent=2))