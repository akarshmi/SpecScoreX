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
}