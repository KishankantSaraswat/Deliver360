# -*- encoding: utf-8 -*-
"""
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


load_dotenv()

# WARNING: Don't run with debug turned on in production!
DEBUG = (os.getenv('DEBUG', 'False') == 'True')

# The configuration
get_config_mode = 'Debug' if DEBUG else 'Production'

try:
    # Load the configuration using the default values
    app_config = config_dict[get_config_mode.capitalize()]
except KeyError:
    exit('Error: Invalid <config_mode>. Expected values [Debug, Production] ')

# Initialize the Flask app
app = create_app(app_config)

# Migrate setup
Migrate(app, db)

# Minify setup (for production)
if not DEBUG:
    Minify(app=app, html=True, js=False, cssless=False)

# Logging setup for Debug mode
if DEBUG:
    app.logger.info('DEBUG            = ' + str(DEBUG))
    app.logger.info('Page Compression = ' + 'FALSE' if DEBUG else 'TRUE')
    app.logger.info('DBMS             = ' + app_config.SQLALCHEMY_DATABASE_URI)
    app.logger.info('ASSETS_ROOT      = ' + app_config.ASSETS_ROOT)

# Twilio Configuration
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

# Function to initiate the Twilio voice call
def initiate_twilio_call():
    try:
        # Create a call
        call = client.calls.create(
            url="http://demo.twilio.com/docs/voice.xml",  # Replace with your TwiML URL
            to=os.getenv('TO_PHONE_NUMBER'),  # The recipient's phone number
            from_=os.getenv('FROM_PHONE_NUMBER')  # Your Twilio phone number
        )
        return call.sid
    except Exception as e:
        return str(e)

# Define a route to trigger the Twilio voice call
@app.route('/make-call', methods=['GET'])
def make_call():
    # Call the function to initiate the call and get the SID
    call_sid = initiate_twilio_call()
    return jsonify({"Call SID": call_sid})

# Main entry point for Flask app
if __name__ == "__main__":
    app.run()
