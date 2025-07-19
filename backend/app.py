from flask import Flask, request, jsonify, render_template, redirect
from flask import send_from_directory

from flask_cors import CORS
import json
import sqlite3
from datetime import datetime
import logging
import os
from typing import Dict, Any

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

    def get_system_overview(self):
        python_data = self.data.get('python_collected', {})
        system_data = python_data.get('system', {})
        
        return {
            'hostname': system_data.get('hostname', 'Unknown'),
            'os': f"{system_data.get('os', 'Unknown')} {system_data.get('os_release', '')}",
            'os_version': system_data.get('os_version', 'Unknown'),
            'architecture': system_data.get('architecture', 'Unknown'),
            'processor': system_data.get('processor', 'Unknown'),
            'timestamp': python_data.get('timestamp', 'Unknown')
        }

    def get_hardware_info(self):
        hardware = self.data.get('python_collected', {}).get('hardware', {})
        powershell_system = self.data.get('powershell_collected', {}).get('system', {})

        # Safe access to graphics
        graphics_data = []
        powershell_graphics = self.data.get('powershell_collected', {}).get('graphics', {})
        if 'gpus' in powershell_graphics:
            graphics_data = powershell_graphics['gpus']

        # Safe access to processor data
        processors = powershell_system.get('processors', {})
        
        return {
            'cpu': {
                'cores': hardware.get('cpu_cores', 0),
                'threads': hardware.get('cpu_threads', 0),
                'usage': hardware.get('cpu_usage', 0),
                'name': processors.get('Name', 'Unknown Processor').strip(),
                'max_clock_speed': processors.get('MaxClockSpeed', 0)
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
        python_network = self.data.get('python_collected', {}).get('network', {})
        powershell_network = self.data.get('powershell_collected', {}).get('network', {})
        adapters = powershell_network.get('adapters', {})

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)