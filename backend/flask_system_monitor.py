from flask import Flask, render_template, jsonify
import json
from datetime import datetime

app = Flask(__name__)

class SystemDataExtractor:
    def __init__(self, json_data):
        self.data = json_data
    
    def get_system_overview(self):
        """Extract key system information"""
        python_data = self.data['python_collected']
        powershell_data = self.data['powershell_collected']
        
        return {
            'hostname': python_data['system']['hostname'],
            'os': f"{python_data['system']['os']} {python_data['system']['os_release']}",
            'os_version': python_data['system']['os_version'],
            'architecture': python_data['system']['architecture'],
            'processor': python_data['system']['processor'],
            'timestamp': python_data['timestamp']
        }
    
    def get_hardware_info(self):
        """Extract hardware specifications"""
        hardware = self.data['python_collected']['hardware']
        powershell_system = self.data['powershell_collected']['system']
        
        return {
            'cpu': {
                'cores': hardware['cpu_cores'],
                'threads': hardware['cpu_threads'],
                'usage': hardware['cpu_usage'],
                'name': powershell_system['processors']['Name'].strip(),
                'max_clock_speed': powershell_system['processors']['MaxClockSpeed']
            },
            'memory': {
                'total_ram': hardware['total_ram'],
                'available_ram': hardware['available_ram'],
                'used_ram': round(hardware['total_ram'] - hardware['available_ram'], 2),
                'usage_percent': round((1 - hardware['available_ram'] / hardware['total_ram']) * 100, 1),
                'module_info': powershell_system['memory_modules']
            },
            'graphics': powershell_system['graphics']['gpus']
        }
    
    def get_storage_info(self):
        """Extract storage information"""
        python_disks = self.data['python_collected']['hardware']['disk_info']
        powershell_disks = self.data['powershell_collected']['storage']
        
        # Combine logical disk info
        storage_data = []
        for disk in python_disks:
            usage_percent = round((disk['used'] / disk['total_size']) * 100, 1)
            storage_data.append({
                'device': disk['device'],
                'mountpoint': disk['mountpoint'],
                'filesystem': disk['fstype'],
                'total_size': disk['total_size'],
                'used': disk['used'],
                'free': disk['free'],
                'usage_percent': usage_percent
            })
        
        return {
            'logical_disks': storage_data,
            'physical_disks': powershell_disks['physical_disks']
        }
    
    def get_network_info(self):
        """Extract network information"""
        python_network = self.data['python_collected']['network']
        powershell_network = self.data['powershell_collected']['network']['adapters']
        
        return {
            'primary_ip': python_network['ip_address'],
            'primary_mac': python_network['mac_address'],
            'adapter_info': {
                'description': powershell_network['Description'],
                'mac_address': powershell_network['MACAddress'],
                'ip_addresses': powershell_network['IPAddress'],
                'gateway': powershell_network['DefaultIPGateway'],
                'dns_servers': powershell_network['DNSServerSearchOrder']
            }
        }
    
    def get_motherboard_info(self):
        """Extract motherboard and system info"""
        system_info = self.data['powershell_collected']['system']
        
        return {
            'motherboard': system_info['motherboard'],
            'computer_system': system_info['computer_system'],
            'bios': system_info['bios'],
            'operating_system': system_info['operating_system'],
            'battery': self.data['powershell_collected']['power']['battery']
        }

# Sample data (you would load this from your JSON file)
sample_data = {
    "agent_source": "SpecScoreX Agent",
    "python_collected": {
        "timestamp": "2025-07-18T16:37:07.391781",
        "system": {
            "hostname": "Lucifer",
            "os": "Windows",
            "os_version": "10.0.26100",
            "os_release": "11",
            "architecture": "AMD64",
            "processor": "AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD",
            "host_id": "158394311017852"
        },
        "hardware": {
            "cpu_cores": 6,
            "cpu_threads": 12,
            "cpu_usage": 7.0,
            "total_ram": 7.37,
            "available_ram": 0.83,
            "disk_info": [
                {
                    "device": "C:\\",
                    "mountpoint": "C:\\",
                    "fstype": "NTFS",
                    "total_size": 465.11,
                    "used": 87.26,
                    "free": 377.85
                },
                {
                    "device": "D:\\",
                    "mountpoint": "D:\\",
                    "fstype": "NTFS",
                    "total_size": 203.14,
                    "used": 67.93,
                    "free": 135.21
                }
            ]
        },
        "network": {
            "ip_address": "10.177.167.42",
            "mac_address": "21:85:15:57:5f:7c"
        }
    },
    "powershell_collected": {
        "timestamp": "2025-07-18T16:37:08",
        "system": {
            "motherboard": {
                "Manufacturer": "LENOVO",
                "Product": "LNVNB161216",
                "SerialNumber": "PF2Y4SRP"
            },
            "processors": {
                "Name": "AMD Ryzen 5 4600H with Radeon Graphics ",
                "NumberOfCores": 6,
                "NumberOfLogicalProcessors": 12,
                "MaxClockSpeed": 3000
            },
            "memory_modules": {
                "Capacity": 8589934592,
                "Manufacturer": "Kingston",
                "Speed": 3200
            },
            "graphics": {
                "gpus": [
                    {
                        "Name": "AMD Radeon(TM) Graphics",
                        "DriverVersion": "27.20.11028.10001",
                        "AdapterRAMGB": 0.5
                    },
                    {
                        "Name": "NVIDIA GeForce GTX 1650",
                        "DriverVersion": "27.21.14.5749",
                        "AdapterRAMGB": 4
                    }
                ]
            }
        },
        "network": {
            "adapters": {
                "Description": "Realtek 8822CE Wireless LAN 802.11ac PCI-E NIC",
                "MACAddress": "90:0F:0C:A4:85:56",
                "IPAddress": ["10.177.167.42"],
                "DefaultIPGateway": ["10.177.167.205"],
                "DNSServerSearchOrder": ["10.177.167.205"]
            }
        },
        "storage": {
            "physical_disks": [
                {
                    "Model": "ST1000LM035-1RK172",
                    "InterfaceType": "IDE",
                    "SizeGB": 931.51
                }
            ]
        }
    }
}

# Initialize extractor
extractor = SystemDataExtractor(sample_data)

@app.route('/')
def dashboard():
    """Main dashboard"""
    system_overview = extractor.get_system_overview()
    hardware_info = extractor.get_hardware_info()
    return render_template('dashboard.html', 
                         system=system_overview,
                         hardware=hardware_info)

@app.route('/api/system')
def api_system():
    """API endpoint for system data"""
    return jsonify(extractor.get_system_overview())

@app.route('/api/hardware')
def api_hardware():
    """API endpoint for hardware data"""
    return jsonify(extractor.get_hardware_info())

@app.route('/api/storage')
def api_storage():
    """API endpoint for storage data"""
    return jsonify(extractor.get_storage_info())

@app.route('/api/network')
def api_network():
    """API endpoint for network data"""
    return jsonify(extractor.get_network_info())

@app.route('/storage')
def storage_page():
    """Storage details page"""
    storage_info = extractor.get_storage_info()
    return render_template('storage.html', storage=storage_info)

@app.route('/network')
def network_page():
    """Network details page"""
    network_info = extractor.get_network_info()
    return render_template('network.html', network=network_info)

if __name__ == '__main__':
    app.run(debug=True)
