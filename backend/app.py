from flask import Flask, request, jsonify, render_template, redirect
from flask import send_from_directory

from flask_cors import CORS
import json
import sqlite3
from datetime import datetime
import logging
import os
from typing import Dict, Any, List

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Load data from JSON file
def load_data():
    try:
        with open('data.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Add static file route
@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

@app.route('/')
def home():
    data = load_data()
    if not data:
        return render_template('index.html', system={}, hardware={}, storage={}, network={}, motherboard={})
    
    extractor = SystemDataExtractor(data)
    full_data = extractor.get_full_data()
    
    return render_template('index.html', 
                         system=full_data['system'],
                         hardware=full_data['hardware'],
                         storage=full_data['storage'],
                         network=full_data['network'],
                         motherboard=full_data['motherboard'])

@app.errorhandler(404)
def page_not_found(e):
    return redirect('/')

# Setup logging to file
logging.basicConfig(
    filename='./logs/system_info.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@app.route('/full-system-info', methods=['GET'])
def download_agent():
    return send_from_directory("static", "AgentX.exe", as_attachment=True)

@app.route('/api/full-system-info', methods=['POST'])
def receive_system_info():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON payload received"}), 400

        # Log raw data
        timestamp = datetime.now().isoformat()
        app.logger.info(f"[{timestamp}] System Info Received:\n{json.dumps(data, indent=2)}")

        # Save the data to a file
        with open('data.json', 'w') as f:
            json.dump(data, f)

        # Create extractor object
        extractor = SystemDataExtractor(data)
        full_data = extractor.get_full_data()

        # Return structured data
        return jsonify(full_data), 200

    except Exception as e:
        app.logger.error(f"[ERROR] Failed to process system info: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API endpoints for AJAX calls
@app.route('/api/system', methods=['GET'])
def get_system_info():
    data = load_data()
    if not data:
        return jsonify({"error": "No data available"}), 404
    
    extractor = SystemDataExtractor(data)
    return jsonify(extractor.get_system_overview())

@app.route('/api/hardware', methods=['GET'])
def get_hardware_info():
    data = load_data()
    if not data:
        return jsonify({"error": "No data available"}), 404
    
    extractor = SystemDataExtractor(data)
    return jsonify(extractor.get_hardware_info())

@app.route('/api/storage', methods=['GET'])
def get_storage_info():
    data = load_data()
    if not data:
        return jsonify({"error": "No data available"}), 404
    
    extractor = SystemDataExtractor(data)
    return jsonify(extractor.get_storage_info())

@app.route('/api/network', methods=['GET'])
def get_network_info():
    data = load_data()
    if not data:
        return jsonify({"error": "No data available"}), 404
    
    extractor = SystemDataExtractor(data)
    return jsonify(extractor.get_network_info())

@app.route('/api/motherboard', methods=['GET'])
def get_motherboard_info():
    data = load_data()
    if not data:
        return jsonify({"error": "No data available"}), 404
    
    extractor = SystemDataExtractor(data)
    return jsonify(extractor.get_motherboard_info())

class SystemDataExtractor:
    def __init__(self, json_data):
        self.data = json_data

    def safe_get(self, data: dict, keys: List[str], default=None):
        """Safely navigate nested dictionary keys"""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def get_system_overview(self):
        # Handle both old and new data structures
        python_data = self.data.get('python_collected', {})
        metadata = self.data.get('metadata', {})
        
        # New structure support
        if 'system' in self.data:
            system_data = self.data['system']
            os_data = system_data.get('operating_system', {})
            computer_data = system_data.get('computer_system', {})
            
            return {
                'hostname': computer_data.get('name', metadata.get('hostname', 'Unknown')),
                'os': os_data.get('name', 'Unknown'),
                'os_version': f"{os_data.get('version', '')} Build {os_data.get('build_number', '')}".strip(),
                'architecture': os_data.get('architecture', 'Unknown'),
                'processor': self.get_primary_processor_name(),
                'timestamp': metadata.get('timestamp', datetime.now().isoformat()),
                'uptime': os_data.get('uptime', {}),
                'domain': computer_data.get('domain', 'N/A'),
                'last_boot': os_data.get('last_boot', 'Unknown')
            }
        
        # Fallback to old structure
        system_data = python_data.get('system', {})
        return {
            'hostname': system_data.get('hostname', 'Unknown'),
            'os': f"{system_data.get('os', 'Unknown')} {system_data.get('os_release', '')}",
            'os_version': system_data.get('os_version', 'Unknown'),
            'architecture': system_data.get('architecture', 'Unknown'),
            'processor': system_data.get('processor', 'Unknown'),
            'timestamp': python_data.get('timestamp', 'Unknown')
        }

    def get_primary_processor_name(self):
        """Get the primary processor name from the hardware data"""
        processors = self.safe_get(self.data, ['hardware', 'processors'], [])
        if processors and len(processors) > 0:
            return processors[0].get('name', 'Unknown Processor')
        
        # Fallback to old structure
        powershell_processors = self.safe_get(self.data, ['powershell_collected', 'system', 'processors'])
        if isinstance(powershell_processors, list) and len(powershell_processors) > 0:
            return powershell_processors[0].get('Name', 'Unknown Processor')
        elif isinstance(powershell_processors, dict):
            return powershell_processors.get('Name', 'Unknown Processor')
        
        return 'Unknown Processor'

    def get_hardware_info(self):
        # Handle new structure
        if 'hardware' in self.data:
            hardware = self.data['hardware']
            processors = hardware.get('processors', [])
            memory_modules = hardware.get('memory_modules', [])
            graphics = self.data.get('graphics', {}).get('video_controllers', [])
            
            # Calculate totals
            total_memory_gb = sum(mem.get('capacity_gb', 0) for mem in memory_modules)
            
            primary_cpu = processors[0] if processors else {}
            
            return {
                'cpu': {
                    'name': primary_cpu.get('name', 'Unknown Processor'),
                    'manufacturer': primary_cpu.get('manufacturer', 'Unknown'),
                    'cores': primary_cpu.get('cores', 0),
                    'logical_processors': primary_cpu.get('logical_processors', 0),
                    'max_clock_speed_mhz': primary_cpu.get('max_clock_speed_mhz', 0),
                    'architecture': primary_cpu.get('architecture', 'Unknown'),
                    'l2_cache_kb': primary_cpu.get('l2_cache_size_kb', 0),
                    'l3_cache_kb': primary_cpu.get('l3_cache_size_kb', 0)
                },
                'memory': {
                    'total_ram_gb': total_memory_gb,
                    'module_count': len(memory_modules),
                    'modules': memory_modules
                },
                'graphics': graphics,
                'all_processors': processors
            }

        # Fallback to old structure
        hardware = self.data.get('python_collected', {}).get('hardware', {})
        powershell_system = self.data.get('powershell_collected', {}).get('system', {})
        graphics_data = self.data.get('powershell_collected', {}).get('graphics', {}).get('gpus', [])
        
        processors = powershell_system.get('processors', {})
        if isinstance(processors, list) and len(processors) > 0:
            processors = processors[0]

        return {
            'cpu': {
                'cores': hardware.get('cpu_cores', 0),
                'threads': hardware.get('cpu_threads', 0),
                'usage': hardware.get('cpu_usage', 0),
                'name': processors.get('Name', 'Unknown Processor').strip() if processors else 'Unknown',
                'max_clock_speed': processors.get('MaxClockSpeed', 0) if processors else 0
            },
            'memory': {
                'total_ram': hardware.get('total_ram', 0),
                'available_ram': hardware.get('available_ram', 0),
                'used_ram': round(hardware.get('total_ram', 0) - hardware.get('available_ram', 0), 2),
                'usage_percent': round((1 - hardware.get('available_ram', 0) / hardware.get('total_ram', 1)) * 100, 1),
                'module_info': powershell_system.get('memory_modules', {})
            },
            'graphics': graphics_data
        }

    def get_storage_info(self):
        # Handle new structure
        if 'storage' in self.data:
            storage = self.data['storage']
            logical_disks = storage.get('logical_disks', [])
            physical_disks = storage.get('physical_disks', [])
            
            return {
                'logical_disks': logical_disks,
                'physical_disks': physical_disks,
                'total_storage_gb': sum(disk.get('size_gb', 0) for disk in physical_disks),
                'total_used_gb': sum(disk.get('used_gb', 0) for disk in logical_disks)
            }

        # Fallback to old structure
        python_hardware = self.data.get('python_collected', {}).get('hardware', {})
        python_disks = python_hardware.get('disk_info', [])
        powershell_storage = self.data.get('powershell_collected', {}).get('storage', {})
        
        storage_data = []
        for disk in python_disks:
            total_size = disk.get('total_size', 0)
            used = disk.get('used', 0)
            usage_percent = round((used / total_size) * 100, 1) if total_size > 0 else 0
            
            storage_data.append({
                'device': disk.get('device', 'Unknown'),
                'mountpoint': disk.get('mountpoint', 'Unknown'),
                'filesystem': disk.get('fstype', 'Unknown'),
                'total_size': total_size,
                'used': used,
                'free': disk.get('free', 0),
                'usage_percent': usage_percent
            })

        return {
            'logical_disks': storage_data,
            'physical_disks': powershell_storage.get('physical_disks', [])
        }

    def get_network_info(self):
        # Handle new structure
        if 'network' in self.data:
            network = self.data['network']
            configured_adapters = network.get('configured_adapters', [])
            physical_adapters = network.get('physical_adapters', [])
            
            # Get primary adapter info
            primary_adapter = configured_adapters[0] if configured_adapters else {}
            primary_ip = primary_adapter.get('ip_addresses', ['Unknown'])[0] if primary_adapter.get('ip_addresses') else 'Unknown'
            
            return {
                'primary_ip': primary_ip,
                'primary_mac': primary_adapter.get('mac_address', 'Unknown'),
                'configured_adapters': configured_adapters,
                'physical_adapters': physical_adapters,
                'adapter_count': len(configured_adapters)
            }

        # Fallback to old structure
        python_network = self.data.get('python_collected', {}).get('network', {})
        powershell_network = self.data.get('powershell_collected', {}).get('network', {})
        adapters = powershell_network.get('adapters', [])

        # Handle both list and single adapter cases
        if isinstance(adapters, list):
            adapter_info = []
            primary_adapter = adapters[0] if adapters else {}
            
            for adapter in adapters:
                adapter_info.append({
                    'description': adapter.get('Description', 'Unknown'),
                    'mac_address': adapter.get('MACAddress', 'Unknown'),
                    'ip_addresses': adapter.get('IPAddress', []),
                    'gateway': adapter.get('DefaultIPGateway', []),
                    'dns_servers': adapter.get('DNSServerSearchOrder', [])
                })
            
            return {
                'primary_ip': python_network.get('ip_address', 'Unknown'),
                'primary_mac': python_network.get('mac_address', 'Unknown'),
                'adapters': adapter_info,
                'primary_adapter': {
                    'description': primary_adapter.get('Description', 'Unknown'),
                    'mac_address': primary_adapter.get('MACAddress', 'Unknown'),
                    'ip_addresses': primary_adapter.get('IPAddress', []),
                    'gateway': primary_adapter.get('DefaultIPGateway', []),
                    'dns_servers': primary_adapter.get('DNSServerSearchOrder', [])
                }
            }
        else:
            # Handle single adapter (old format)
            return {
                'primary_ip': python_network.get('ip_address', 'Unknown'),
                'primary_mac': python_network.get('mac_address', 'Unknown'),
                'adapter_info': {
                    'description': adapters.get('Description', 'Unknown'),
                    'mac_address': adapters.get('MACAddress', 'Unknown'),
                    'ip_addresses': adapters.get('IPAddress', []),
                    'gateway': adapters.get('DefaultIPGateway', []),
                    'dns_servers': adapters.get('DNSServerSearchOrder', [])
                }
            }

    def get_motherboard_info(self):
        # Handle new structure
        if 'hardware' in self.data:
            hardware = self.data['hardware']
            system_data = self.data.get('system', {})
            power_data = self.data.get('power', {})
            
            return {
                'motherboard': hardware.get('motherboard', {}),
                'computer_system': system_data.get('computer_system', {}),
                'bios': hardware.get('bios', {}),
                'operating_system': system_data.get('operating_system', {}),
                'battery': power_data.get('battery_info', []),
                'power_schemes': power_data.get('power_schemes', {}),
                'performance': system_data.get('performance', {})
            }

        # Fallback to old structure
        system_info = self.data.get('powershell_collected', {}).get('system', {})
        power_info = self.data.get('powershell_collected', {}).get('power', {})
        
        return {
            'motherboard': system_info.get('motherboard', {}),
            'computer_system': system_info.get('computer_system', {}),
            'bios': system_info.get('bios', {}),
            'operating_system': system_info.get('operating_system', {}),
            'battery': power_info.get('battery', {})
        }

    def get_full_data(self):
        return {
            'system': self.get_system_overview(),
            'hardware': self.get_hardware_info(),
            'storage': self.get_storage_info(),
            'network': self.get_network_info(),
            'motherboard': self.get_motherboard_info()
        }

@app.route('/report')
def report_page():
    data = load_data()
    if not data:
        return render_template('report_template.html', system={}, hardware={}, storage={}, network={}, motherboard={})
    
    extractor = SystemDataExtractor(data)
    full_data = extractor.get_full_data()

    return render_template(
        'report_template.html',
        system=full_data['system'],
        hardware=full_data['hardware'],
        storage=full_data['storage'],
        network=full_data['network'],
        motherboard=full_data['motherboard']
    )

@app.route('/api/raw-data', methods=['GET'])
def get_raw_data():
    """Endpoint to get raw JSON data for debugging"""
    data = load_data()
    return jsonify(data) if data else jsonify({"error": "No data available"}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "data_available": bool(load_data())
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)