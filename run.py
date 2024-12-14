# -*- encoding: utf-8 -*-
"""
Flask App with Twilio Integration
Copyright (c) 2019 - present AppSeed.us
"""

import os
from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_minify import Minify
from twilio.rest import Client
from sys import exit
from apps.config import config_dict
from apps import create_app, db
from dotenv import load_dotenv

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

# Main entry point for the Flask app
if __name__ == "__main__":
    app.run(debug=DEBUG)
