from flask import Flask, request, jsonify ,render_template,redirect
from flask import send_from_directory

from flask_cors import CORS
import json
import sqlite3
from datetime import datetime  # FIXED: Changed from 'import datetime'
import logging
import os
from typing import Dict, Any

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# Add static file route
@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)


@app.route('/')
def home():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    # Redirect any 404 error to the home page
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
        timestamp = datetime.now().isoformat()  # FIXED: Now this will work
        app.logger.info(f"[{timestamp}] System Info Received:\n{json.dumps(data, indent=2)}")

        # OPTIONAL: Save to DB (future feature)
        # db.insert_system_info(data)

        return jsonify({"message": "System info received successfully"}), 200

    except Exception as e:
        app.logger.error(f"[ERROR] Failed to process system info: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)