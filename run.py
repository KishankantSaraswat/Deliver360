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
import requests
import random
from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from flask import session





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

# Load environment variables
groq_api_key = os.environ['GROQ_API_KEY']  # Ensure your API key is set in the environment variables

# Initialize Groq Langchain chat object
def get_conversation_chain(model_name):
    memory = ConversationBufferWindowMemory(k=5)  # Default memory length, can be adjusted
    groq_chat = ChatGroq(groq_api_key=groq_api_key, model_name=model_name)
    return ConversationChain(llm=groq_chat, memory=memory)

# Format user input to limit response length and enforce bullet points
def format_user_prompt(question):
    formatted_prompt = f"""
    {question}

    Please provide the answer, and the total response should not exceed 30 words.
    """
    return formatted_prompt

# Process and format the response for user
def process_response(response_text):
    # Check if response_text contains line breaks or bullet points
    points = response_text.split('\n')  # Assuming each point comes on a new line
    
    if len(points) == 1:
        # Try to split by periods if no line breaks are found
        points = response_text.split('. ')
    
    # Clean and reformat the response to remove any unwanted symbols and ensure proper format
    formatted_response = ''
    for i, point in enumerate(points):
        point = point.strip('- ')  # Strip unwanted symbols like dashes or extra spaces
        if point:
            formatted_response += f"{i+1}. {point}<br>"  # Add HTML line break and numbering

    return formatted_response


# Route to display the chatbot UI
@app.route('/chatbot', methods=['GET'])
def chatbot():
    """
    This route serves the chatbot interface when accessed by the user.
    It loads the chatbot page.
    """
    return render_template('home/chatbot.html')

# Route to handle chat requests from the frontend
# Route to handle chat requests from the frontend
@app.route('/chat', methods=['POST'])
def chat():
    user_question = request.json.get('message')
    selected_model = "mixtral-8x7b-32768"  # Example model, adjust as needed
    memory_length = 5  # Default memory length

    # Get conversation chain and process the user's message
    conversation_chain = get_conversation_chain(selected_model)
    conversation_chain.memory.k = memory_length

    # Format the question with word limit and bullet points
    formatted_prompt = format_user_prompt(user_question)
    
    try:
        # Invoke the conversation chain
        response = conversation_chain.invoke(formatted_prompt)
        
        # Check if response is valid and process it
        ai_response = process_response(response['response'])

    except Exception as e:
        ai_response = f"Error processing the response: {str(e)}"
        print(f"Error during conversation chain invoke: {str(e)}")

    # Update the chat history stored in the session
    chat_history = session.get('chat_history', [])
    chat_history.append({'human': user_question, 'AI': ai_response})
    session['chat_history'] = chat_history

    return jsonify({'response': ai_response})




GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/v1/chat/completions"

health_tips = [
    "Stay hydrated and take breaks during long deliveries.",
    "Avoid riding continuously for more than 2 hours; stretch to avoid fatigue.",
    "Wear breathable clothing to prevent overheating in hot weather.",
    "Always carry a small first-aid kit for minor injuries.",
    "Keep an energy bar and water bottle with you during shifts.",
    "Follow traffic rules and avoid sudden braking to prevent accidents.",
    "Check your vehicle's tires and brakes before starting your delivery."
]


@app.route('/get-suggestion', methods=['GET'])
def get_suggestion():
    """Fetch health suggestion based on IoT data or provide random delivery tips"""
    global latest_helmet_data

    if latest_helmet_data:
        # Generate health advice based on received data
        heart_rate = latest_helmet_data.get("heart_rate", 0)
        spo2 = latest_helmet_data.get("spo2", 0)
        object_temp = latest_helmet_data.get("object_temp", 0)
        ambient_temp = latest_helmet_data.get("ambient_temp", 0)

        prompt_variations = [
            f"Generate a unique health tip for a delivery boy with these readings: HR {heart_rate} BPM, SpO2 {spo2}%, Object Temp {object_temp}°C, Ambient Temp {ambient_temp}°C.",
            f"Suggest a health precaution for a delivery worker experiencing: HR {heart_rate}, SpO2 {spo2}, Temp {object_temp}°C. Keep the tip short and practical.",
            f"A delivery worker is exposed to {ambient_temp}°C. How should they stay safe while ensuring efficient deliveries? Provide actionable health advice.",
        ]
        prompt = random.choice(prompt_variations)
    else:
        # Provide a random general suggestion if no IoT data is available
        prompt = random.choice(health_tips)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "mixtral-8x7b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50,
        "temperature": 1.0  # Increases randomness in response
    }
    
    try:
        response = requests.post(GROQ_API_URL, json=data, headers=headers)
        result = response.json()
        if "choices" in result:
            suggestion = result["choices"][0]["message"]["content"]
        else:
            suggestion = random.choice(health_tips)  # Fall back to random health tips
    except Exception as e:
        suggestion = f"Error fetching suggestion: {str(e)}"
        print(f"Error during suggestion fetching: {str(e)}")

    return jsonify({"suggestion": suggestion})





# Main entry point for the Flask app
if __name__ == "__main__":
    app.run(debug=DEBUG)
