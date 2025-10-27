from flask import Flask, render_template, request, jsonify, session
import os
import sys
import json
import threading
import queue
import time
from datetime import datetime
import sqlite3
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import the main assistant
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_voice_assistant import EnhancedVoiceAssistant
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global assistant instance
assistant = None
conversation_queue = queue.Queue()
is_listening = False

# Global reminder storage and notification queue
active_reminders = []  # List of {id, text, due_time, completed}
reminder_notifications = queue.Queue()  # Queue for reminder alerts

def initialize_assistant():
    """Initialize the voice assistant"""
    global assistant
    try:
        assistant = EnhancedVoiceAssistant()
        return True
    except Exception as e:
        print(f"Error initializing assistant: {e}")
        return False

# Try to initialize assistant at import time so the web UI can use it
try:
    # initialize in a background thread to avoid blocking Flask startup
    t = threading.Thread(target=initialize_assistant, daemon=True)
    t.start()
except Exception:
    pass

@app.route('/')
def index():
    """Main interface page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get assistant status"""
    return jsonify({
        'status': 'ready' if assistant else 'error',
        'is_listening': is_listening,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/listen', methods=['POST'])
def start_listening():
    """Start voice recognition"""
    global is_listening
    
    if not assistant:
        return jsonify({'error': 'Assistant not initialized'}), 500
    
    if is_listening:
        return jsonify({'error': 'Already listening'}), 400
    
    try:
        is_listening = True
        
        # Run voice recognition in a separate thread
        def listen_thread():
            global is_listening
            try:
                command = assistant.listen(timeout=10)
                if command != "none":
                    # Process the command
                    intent = assistant.process_natural_language(command)
                    response = process_intent_response(intent)
                    conversation_queue.put({
                        'type': 'response',
                        'content': response,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    conversation_queue.put({
                        'type': 'error',
                        'content': 'I didn\'t hear anything. Please try again.',
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                conversation_queue.put({
                    'type': 'error',
                    'content': f'Error: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            finally:
                is_listening = False
        
        thread = threading.Thread(target=listen_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'listening'})
        
    except Exception as e:
        is_listening = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_listening():
    """Stop voice recognition"""
    global is_listening
    is_listening = False
    return jsonify({'status': 'stopped'})

@app.route('/api/text', methods=['POST'])
def process_text():
    """Process text input"""
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    if not assistant:
        return jsonify({'error': 'Assistant not initialized'}), 500
    
    try:
        # Process the text command
        intent = assistant.process_natural_language(text)
        response = process_intent_response(intent)
        
        # Actually perform the actions
        if intent.type.value == "time":
            now = datetime.now()
            response = f"The current time is {now.strftime('%I:%M %p')}"
        
        elif intent.type.value == "date":
            now = datetime.now()
            response = f"Today is {now.strftime('%A, %B %d, %Y')}"
        
        elif intent.type.value == "reminder":
            # Extract reminder details from text
            reminder_match = re.search(r'remind me to (.+)', text, re.IGNORECASE)
            if reminder_match:
                reminder_text = reminder_match.group(1)
                # Try to extract time
                time_match = re.search(r'in (\d+) (minute|minutes|hour|hours)', text, re.IGNORECASE)
                if time_match:
                    time_value = int(time_match.group(1))
                    time_unit = time_match.group(2)
                    if 'hour' in time_unit:
                        time_value *= 60
                    response = f"Reminder set: '{reminder_text}' in {time_value} minutes"
                    # Schedule the reminder using the assistant's reminder monitor (in-memory)
                    try:
                        if not assistant:
                            # Try to initialize synchronously as a fallback
                            initialize_assistant()
                        if assistant:
                            due = time.time() + (time_value * 60)
                            rid = str(uuid.uuid4())
                            assistant.reminders.append((due, reminder_text, rid))
                            logging_info = f"[web_interface] Scheduled reminder {rid} in {time_value} minutes: {reminder_text}"
                            print(logging_info)
                        else:
                            response += " (Note: assistant not available to schedule reminder)"
                    except Exception as e:
                        print(f"Error scheduling reminder from web UI: {e}")
                else:
                    response = f"I'll remind you to {reminder_text}. How many minutes from now?"
            else:
                response = "What should I remind you about? Please say 'remind me to [task]'"
        
        elif intent.type.value == "search":
            query = intent.entities.get('query', '')
            if query:
                import webbrowser
                url = f"https://www.google.com/search?q={query}"
                webbrowser.open(url)
                response = f"I've opened a search for '{query}' in your browser."
        
        elif intent.type.value == "wiki":
            topic = intent.entities.get('topic', '')
            if topic:
                try:
                    import wikipedia
                    result = wikipedia.summary(topic, sentences=2)
                    response = f"According to Wikipedia: {result}"
                except wikipedia.exceptions.DisambiguationError:
                    response = f"There are multiple results for {topic}. Can you be more specific?"
                except wikipedia.exceptions.PageError:
                    response = f"Sorry, I couldn't find information about {topic} on Wikipedia."
                except Exception as e:
                    response = f"An error occurred while searching Wikipedia: {str(e)}"
        
        elif intent.type.value == "wiki":
            topic = intent.entities.get('topic', '')
            if topic:
                try:
                    import wikipedia
                    result = wikipedia.summary(topic, sentences=3)
                    response = f"According to Wikipedia: {result}"
                except wikipedia.exceptions.DisambiguationError:
                    response = f"There are multiple results for {topic}. Can you be more specific?"
                except wikipedia.exceptions.PageError:
                    response = f"Sorry, I couldn't find information about {topic} on Wikipedia."
                except Exception as e:
                    response = f"An error occurred while searching Wikipedia: {str(e)}"
            else:
                response = "What would you like to know about?"
        
        elif intent.type.value == "weather":
            city = intent.entities.get('city', '')
            if city:
                try:
                    import requests
                    api_key = os.getenv("OPENWEATHER_API_KEY", "2118f4d5069acc918a62465f175ae59f")
                    if api_key:
                        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
                        response_weather = requests.get(url, timeout=10)
                        data = response_weather.json()
                        
                        if data["cod"] != "404":
                            temp = data["main"]["temp"]
                            description = data["weather"][0]["description"]
                            humidity = data["main"]["humidity"]
                            response = f"The weather in {city} is {description} with a temperature of {temp}°C and humidity of {humidity}%"
                        else:
                            response = f"Sorry, I couldn't find weather data for {city}"
                    else:
                        response = f"Weather service is not configured. Please add your OpenWeatherMap API key."
                except Exception as e:
                    response = f"I couldn't get the weather information: {str(e)}"
        
        elif intent.type.value == "email":
            # Email functionality - parse and send
            sender_email = os.getenv("SENDER_EMAIL", "")
            sender_password = os.getenv("SENDER_APP_PASSWORD", "")
            
            if not sender_email or not sender_password:
                response = "Email functionality is not configured. Please set your email credentials in the .env file."
            else:
                # Try to parse email details from the text
                email_data = parse_email_from_text(text)
                
                if email_data and email_data.get('recipient') and email_data.get('subject') and email_data.get('body'):
                    # Send the email
                    try:
                        send_email_smtp(sender_email, sender_password, email_data['recipient'], 
                                       email_data['subject'], email_data['body'])
                        response = f"Email sent successfully to {email_data['recipient']}!"
                    except Exception as e:
                        response = f"Failed to send email: {str(e)}"
                else:
                    response = "Please provide email in this format: 'Send email to name@example.com with subject YOUR_SUBJECT and message YOUR_MESSAGE'"
        
        elif intent.type.value == "reminder":
            # Reminder functionality
            response = "Reminder functionality is available. I can help you set reminders, but this requires additional setup."
        
        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation')
def get_conversation():
    """Get conversation history"""
    if not assistant or not assistant.user_context:
        return jsonify({'conversation': []})
    
    return jsonify({
        'conversation': assistant.user_context.conversation_history[-20:]  # Last 20 messages
    })

@app.route('/api/settings', methods=['GET', 'POST'])
def settings():
    """Handle settings"""
    if request.method == 'GET':
        return jsonify({
            'assistant_name': os.getenv('ASSISTANT_NAME', 'Siri'),
            'wake_mode': os.getenv('WAKE_MODE_ENABLED', 'true').lower() == 'true',
            'text_fallback': os.getenv('TEXT_FALLBACK_ENABLED', 'true').lower() == 'true'
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        # Update settings (in a real app, save to database)
        return jsonify({'status': 'updated'})

def parse_email_from_text(text):
    """Parse email details from natural language text"""
    email_data = {}
    
    # Try to find email address pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, text)
    if email_match:
        email_data['recipient'] = email_match.group(0)
    
    # Try to extract subject
    subject_patterns = [
        r'(?:with subject|subject is|subject:)\s+([\w\s]+?)(?:\s+and|\s+with|$)',
        r'(?:subject|topic)\s+([\w\s]+?)(?:\s+and|\s+message|$)'
    ]
    for pattern in subject_patterns:
        subject_match = re.search(pattern, text, re.IGNORECASE)
        if subject_match:
            email_data['subject'] = subject_match.group(1).strip()
            break
    
    # Try to extract message/body
    message_patterns = [
        r'(?:message|body|content|saying|text)\s+(.+)$',
        r'(?:and message|with message)\s+(.+)$'
    ]
    for pattern in message_patterns:
        message_match = re.search(pattern, text, re.IGNORECASE)
        if message_match:
            email_data['body'] = message_match.group(1).strip()
            break
    
    return email_data

def send_email_smtp(sender_email, sender_password, recipient, subject, body):
    """Send email using SMTP"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        return True
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")

def process_intent_response(intent):
    """Process intent and return response text"""
    try:
        if intent.type.value == "greet":
            hour = datetime.now().hour
            if 0 <= hour < 12:
                greeting = "Good morning!"
            elif 12 <= hour < 18:
                greeting = "Good afternoon!"
            else:
                greeting = "Good evening!"
            return f"{greeting} I'm your voice assistant. How can I help you today?"
        elif intent.type.value == "time":
            now = datetime.now()
            return f"The current time is {now.strftime('%I:%M %p')}"
        elif intent.type.value == "date":
            now = datetime.now()
            return f"Today is {now.strftime('%A, %B %d, %Y')}"
        elif intent.type.value == "help":
            return """Available prompts:
            
• "What time is it?" - Get current time
• "What's the weather like?" - Get weather information
• "Search for [topic]" - Search on Google
• "Tell me about [topic]" - Get Wikipedia information
• "Send an email" - Send an email
• "Set a reminder" - Create a reminder
• "What date is it?" - Get current date

Just ask me anything!"""
        elif intent.type.value == "weather":
            city = intent.entities.get('city', '')
            if city:
                return f"Getting weather for {city}..."
            else:
                return "Which city's weather would you like to know? Just say the city name."
        elif intent.type.value == "search":
            query = intent.entities.get('query', '')
            if query:
                return f"Searching for {query}..."
            else:
                return "What would you like me to search for?"
        elif intent.type.value == "wiki":
            topic = intent.entities.get('topic', '')
            if topic:
                return f"Looking up information about {topic}..."
            else:
                return "What would you like to know about?"
        elif intent.type.value == "email":
            return "Email feature ready. Please specify: recipient email, subject, and message. For example: 'Send email to john@example.com with subject Meeting and message See you tomorrow'"
        elif intent.type.value == "reminder":
            return "What should I remind you about?"
        elif intent.type.value == "smart_home":
            action = intent.entities.get('action', '')
            device = intent.entities.get('device', '')
            if action and device:
                return f"I would {action} the {device}, but smart home integration needs to be configured."
            else:
                return "Smart home control is not configured yet."
        elif intent.type.value == "exit":
            return "Goodbye! Have a great day!"
        else:
            return "I understand you want help with something. Could you be more specific?"
            
    except Exception as e:
        return f"I encountered an error: {str(e)}"

if __name__ == '__main__':
    # Initialize assistant
    if initialize_assistant():
        print("Voice assistant initialized successfully!")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Failed to initialize voice assistant!")
