# -*- encoding: utf-8 -*-
"""
Flask App with Twilio Integration
Copyright (c) 2019 - present AppSeed.us
"""

import os
from flask import Flask, jsonify
from flask import Flask, request, jsonify, render_template
from flask_migrate import Migrate
from flask_minify import Minify
from twilio.rest import Client
from sys import exit
from apps.config import config_dict
from apps import create_app, db
from dotenv import load_dotenv
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os
import logging
import json


os.makedirs('data', exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(_name_)
logger = logging.getLogger(__name__)


latest_helmet_data = {}

# Load environment variables
load_dotenv()

# WARNING: Don't run with debug turned on in production!
DEBUG = (os.getenv('DEBUG', 'False') == 'True')

# Configure app mode
get_config_mode = 'Debug' if DEBUG else 'Production'

try:
    # Load the app configuration
    app_config = config_dict[get_config_mode.capitalize()]
except KeyError:
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

# Initialize Flask app
app = create_app(app_config)

# Database migration setup
Migrate(app, db)

# Minify setup (only in production)
if not DEBUG:
    Minify(app=app, html=True, js=False, cssless=False)

# Logging setup in debug mode
if DEBUG:
    app.logger.info('DEBUG            = ' + str(DEBUG))
    app.logger.info('Page Compression = ' + 'FALSE' if DEBUG else 'TRUE')
    app.logger.info('DBMS             = ' + app_config.SQLALCHEMY_DATABASE_URI)
    app.logger.info('ASSETS_ROOT      = ' + app_config.ASSETS_ROOT)

# Twilio credentials from environment variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID', 'ACc1ba0a48cb0ddae6c72c6146492d5bd9')  # Replace with your Account SID
auth_token = os.getenv('TWILIO_AUTH_TOKEN', '6336806d01669c81599de47f229d04af')  # Replace with your Auth Token
client = Client(account_sid, auth_token)

# Function to initiate a Twilio voice call
def initiate_twilio_call():
    """
    Initiates a Twilio voice call to the specified number.
    Returns the Call SID on success or an error message on failure.
    """
    try:
        call = client.calls.create(
            url="http://demo.twilio.com/docs/voice.xml",  # TwiML instructions
            to="+918923834362",  # Recipient's phone number
            from_="+13613493717"  # Your Twilio phone number
        )
        return call.sid
    except Exception as e:
        return str(e)

# Route to trigger the Twilio voice call
@app.route('/make-call', methods=['GET'])
def make_call():
    """
    Endpoint to make an emergency voice call.
    """
    call_sid = initiate_twilio_call()
    if call_sid.startswith("CA"):  # Twilio Call SID typically starts with 'CA'
        return jsonify({"message": "Emergency call initiated", "Call SID": call_sid}), 200
    else:
        return jsonify({"error": "Failed to initiate call", "details": call_sid}), 500
    


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
    return render_template('home/helmet.html')

# Band (health monitoring) dashboard

@app.route('/fitness')
def band_dashboard():
    return render_template('home/fitness.html')


# Main entry point for the Flask app
if __name__ == "__main__":
    app.run(debug=DEBUG)
