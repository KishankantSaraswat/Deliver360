from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os
import logging
import json

app = Flask(_name_)
CORS(app)

# Ensure database directory exists
os.makedirs('data', exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(_name_)

# Global variable to store the latest helmet data
latest_helmet_data = {}

# Initialize SQLite database for health data
def init_database():
    conn = sqlite3.connect('data/health_monitoring.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS health_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        heart_rate REAL,
        spo2 REAL,
        object_temp REAL,
        ambient_temp REAL
    )
    ''')
    conn.commit()
    conn.close()

# Insert health data into SQLite database
def insert_health_data(heart_rate, spo2, object_temp, ambient_temp):
    conn = sqlite3.connect('data/health_monitoring.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO health_readings 
    (heart_rate, spo2, object_temp, ambient_temp) 
    VALUES (?, ?, ?, ?)
    ''', (heart_rate, spo2, object_temp, ambient_temp))
    conn.commit()
    conn.close()

# Retrieve recent health readings
def get_recent_readings(limit=20):
    conn = sqlite3.connect('data/health_monitoring.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT timestamp, heart_rate, spo2, object_temp, ambient_temp 
    FROM health_readings 
    ORDER BY timestamp DESC 
    LIMIT ?
    ''', (limit,))
    readings = cursor.fetchall()
    conn.close()
    return readings

# Helmet data route
@app.route('/helmet-data', methods=['POST'])
def receive_helmet_data():
    global latest_helmet_data
    try:
        data = request.get_json()
        data['timestamp'] = datetime.now().isoformat()
        latest_helmet_data = data
        logger.info(f"Received helmet data: {json.dumps(data, indent=2)}")
        return jsonify({"status": "success", "message": "Data received successfully"}), 200
    except Exception as e:
        logger.error(f"Error processing helmet data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/get-latest-helmet-data', methods=['GET'])
def get_latest_helmet_data():
    if latest_helmet_data:
        return jsonify(latest_helmet_data)
    else:
        return jsonify({"status": "error", "message": "No data received yet"}), 404

# Health data (band) routes
@app.route('/health-data', methods=['POST'])
def receive_health_data():
    data = request.json
    try:
        insert_health_data(
            data.get('heartRate', 0),
            data.get('spO2', 0),
            data.get('objectTemp', 0),
            data.get('ambientTemp', 0)
        )
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/readings', methods=['GET'])
def get_readings():
    readings = get_recent_readings()
    formatted_readings = [{
        'timestamp': reading[0],
        'heart_rate': reading[1],
        'spo2': reading[2],
        'object_temp': reading[3],
        'ambient_temp': reading[4]
    } for reading in readings]
    return jsonify(formatted_readings)

# Helmet dashboard
@app.route('/helmet')
def helmet_dashboard():
    return render_template('helmet.html')

# Band (health monitoring) dashboard
@app.route('/band')
def band_dashboard():
    return render_template('band.html')

if _name_ == '_main_':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)