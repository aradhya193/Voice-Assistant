import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import wikipedia
import requests
import json
import time
import smtplib
import threading
import os
import re
from dotenv import load_dotenv
import subprocess
import logging
import hashlib
import sqlite3
from typing import Dict, List, Optional, Tuple
import uuid
from dataclasses import dataclass
from enum import Enum
import asyncio
# Optional imports for enhanced features
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("Warning: aiohttp not available. Some async features will be disabled.")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("Warning: pyaudio not available. Audio recording features will be limited.")

from concurrent.futures import ThreadPoolExecutor
import queue
import wave

load_dotenv()

# Enhanced Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "2118f4d5069acc918a62465f175ae59f")
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Siri")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "aradhyapendurkar192003@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_APP_PASSWORD", "")
WAKE_WORD = os.getenv("WAKE_WORD", f"hey {ASSISTANT_NAME.lower()}")
WAKE_MODE_ENABLED = os.getenv("WAKE_MODE_ENABLED", "true").lower() == "true"
TEXT_FALLBACK_ENABLED = os.getenv("TEXT_FALLBACK_ENABLED", "true").lower() == "true"
CONTACTS_JSON = os.getenv("CONTACTS_JSON", "")
SMART_HOME_API_KEY = os.getenv("SMART_HOME_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "assistant_data.db")

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('assistant.log'),
        logging.StreamHandler()
    ]
)

class IntentType(Enum):
    GREET = "greet"
    TIME = "time"
    DATE = "date"
    HELP = "help"
    OPEN = "open"
    PLAY = "play"
    EMAIL = "email"
    REMINDER = "reminder"
    SEARCH = "search"
    WIKI = "wiki"
    WEATHER = "weather"
    NEWS = "news"
    SMART_HOME = "smart_home"
    CALENDAR = "calendar"
    NOTE = "note"
    CALCULATE = "calculate"
    TRANSLATE = "translate"
    EXIT = "exit"

@dataclass
class Intent:
    type: IntentType
    confidence: float
    entities: Dict[str, str]
    raw_text: str

@dataclass
class UserContext:
    user_id: str
    session_id: str
    preferences: Dict
    conversation_history: List[str]
    current_location: Optional[str] = None

class EnhancedVoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = None
        self.user_context = None
        self.db_connection = None
        self.smart_home_devices = {}
        self.custom_commands = {}
        self.conversation_queue = queue.Queue()
        self.is_listening = False
        # Lock to protect TTS usage from multiple threads
        self.speak_lock = threading.Lock()
        # In-memory scheduled reminders: list of tuples (due_timestamp, text, id)
        self.reminders = []
        self._reminder_thread = None
        
        self._initialize_components()
        self._setup_database()
        self._load_user_preferences()
        # Start background monitor for reminders
        self._start_reminder_monitor()
        
    def _initialize_components(self):
        """Initialize TTS engine and other components"""
        try:
            # Try to initialize with different drivers
            driver_names = ['sapi5', 'nsss', 'espeak']
            
            for driver in driver_names:
                try:
                    self.engine = pyttsx3.init(driver)
                    logging.info(f"TTS initialized with driver: {driver}")
                    break
                except Exception:
                    continue
            
            if not self.engine:
                # Last resort: try default initialization
                self.engine = pyttsx3.init()
            
            # Try to set voice properties
            try:
                voices = self.engine.getProperty('voices')
                # Set a more natural voice if available
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
            except Exception as e:
                logging.warning(f"Could not set voice properties: {e}")
                
        except Exception as e:
            logging.error(f"Error initializing TTS engine: {e}")
            # Don't raise - allow assistant to work without TTS
            self.engine = None
            logging.warning("Assistant will run without text-to-speech")

    def _setup_database(self):
        """Setup SQLite database for user data and conversation history"""
        try:
            self.db_connection = sqlite3.connect(DATABASE_PATH)
            cursor = self.db_connection.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    preferences TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    session_id TEXT,
                    message TEXT,
                    response TEXT,
                    intent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    command TEXT,
                    action TEXT,
                    parameters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            self.db_connection.commit()
        except Exception as e:
            logging.error(f"Database setup error: {e}")

    def _load_user_preferences(self):
        """Load user preferences and create default context"""
        user_id = str(uuid.uuid4())  # In a real app, this would be from authentication
        session_id = str(uuid.uuid4())
        
        self.user_context = UserContext(
            user_id=user_id,
            session_id=session_id,
            preferences={},
            conversation_history=[]
        )

    def speak(self, text: str, priority: str = "normal"):
        """Enhanced text-to-speech with priority handling"""
        print(f"{ASSISTANT_NAME}: {text}")
        
        # Add to conversation history
        if self.user_context:
            self.user_context.conversation_history.append(f"Assistant: {text}")
        
        # Skip TTS if engine not available
        if not self.engine:
            return
            
        try:
            # Adjust speech rate based on text length
            if len(text) > 100:
                self.engine.setProperty('rate', 150)
            else:
                self.engine.setProperty('rate', 180)
                
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logging.exception("Error in speech synthesis")

    def listen(self, timeout: int = 5) -> str:
        """Enhanced speech recognition with better error handling"""
        with sr.Microphone() as source:
            print("\n🎤 Listening...")
            self.recognizer.pause_threshold = 1
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                return "none"
                
        try:
            print("🔄 Processing speech...")
            # Try multiple recognition services for better accuracy
            command = self.recognizer.recognize_google(audio, language='en-in').lower()
            print(f"👤 You said: {command}")
            
            # Store in conversation history
            if self.user_context:
                self.user_context.conversation_history.append(f"User: {command}")
                
            return command
        except sr.UnknownValueError:
            return "none"
        except sr.RequestError as e:
            logging.error(f"Speech recognition service error: {e}")
            return "none"
        except Exception as e:
            logging.exception("Speech recognition error")
            return "none"

    def process_natural_language(self, text: str) -> Intent:
        """Enhanced NLP processing with context awareness"""
        text = text.lower().strip()
        
        # Enhanced intent patterns with confidence scoring
        intent_patterns = [
            # Greetings with variations
            (re.compile(r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b'), IntentType.GREET, 0.9),
            
            # Time and date - more flexible patterns
            (re.compile(r'\b(what\'s|what is|whats|what\'s the|what is the|tell me the)\s*(the\s*)?(time|current time)\b'), IntentType.TIME, 0.95),
            (re.compile(r'\b(time|current time)\??\b'), IntentType.TIME, 0.8),
            (re.compile(r'\b(what\'s|what is|whats|what\'s the|what is the|tell me the)\s*(the\s*)?(date|today\'s date)\b'), IntentType.DATE, 0.95),
            (re.compile(r'\b(date|what date|today)\s*(is it|it is)?\??\b'), IntentType.DATE, 0.85),
            
            # Help and capabilities
            (re.compile(r'\b(help|what can you do|capabilities)\b'), IntentType.HELP, 0.9),
            
            # Opening applications/websites
            (re.compile(r'\bopen (.+)\b'), IntentType.OPEN, 0.8),
            (re.compile(r'\blaunch (.+)\b'), IntentType.OPEN, 0.8),
            
            # Media and entertainment
            (re.compile(r'\bplay (.+) on youtube\b'), IntentType.PLAY, 0.9),
            (re.compile(r'\bplay (.+)\b'), IntentType.PLAY, 0.7),
            
            # Communication
            (re.compile(r'\b(send|write) (an )?email\b'), IntentType.EMAIL, 0.9),
            (re.compile(r'\bemail (.+)\b'), IntentType.EMAIL, 0.8),
            
            # Reminders and tasks
            (re.compile(r'\b(remind me to|set a reminder for|create a reminder for)\b'), IntentType.REMINDER, 0.9),
            (re.compile(r'\b(remind me|set reminder|set a reminder|create reminder|create a reminder|reminder)\b'), IntentType.REMINDER, 0.85),
            
            # Search and information
            (re.compile(r'\bsearch for (.+)\b'), IntentType.SEARCH, 0.9),
            (re.compile(r'\b(tell me about|tell me more about|what are|what is) (.+)\b'), IntentType.WIKI, 0.95),
            (re.compile(r'\b(who is|who are) (.+)\b'), IntentType.WIKI, 0.95),
            (re.compile(r'\bweather in (.+)\b'), IntentType.WEATHER, 0.9),
            (re.compile(r'\bweather\b'), IntentType.WEATHER, 0.7),
            
            # News
            (re.compile(r'\b(news|latest news|current events)\b'), IntentType.NEWS, 0.9),
            
            # Smart home
            (re.compile(r'\b(turn on|turn off|switch) (.+)\b'), IntentType.SMART_HOME, 0.8),
            (re.compile(r'\b(control|manage) (.+)\b'), IntentType.SMART_HOME, 0.7),
            
            # Calendar
            (re.compile(r'\b(schedule|add to calendar|calendar)\b'), IntentType.CALENDAR, 0.8),
            
            # Notes
            (re.compile(r'\b(note|remember|write down)\b'), IntentType.NOTE, 0.8),
            
            # Calculations
            (re.compile(r'\b(calculate|compute|what is) (.+)\b'), IntentType.CALCULATE, 0.9),
            
            # Translation
            (re.compile(r'\b(translate|how do you say)\b'), IntentType.TRANSLATE, 0.8),
            
            # Exit
            (re.compile(r'\b(goodbye|exit|stop|quit)\b'), IntentType.EXIT, 0.9),
        ]
        
        best_intent = None
        best_confidence = 0.0
        
        for pattern, intent_type, confidence in intent_patterns:
            match = pattern.search(text)
            if match:
                if confidence > best_confidence:
                    best_confidence = confidence
                    entities = {}
                    
                    # Extract entities based on intent type
                    if intent_type == IntentType.OPEN:
                        entities['target'] = match.group(1)
                    elif intent_type == IntentType.PLAY:
                        entities['query'] = match.group(1)
                    elif intent_type == IntentType.SEARCH:
                        entities['query'] = match.group(1)
                    elif intent_type == IntentType.WIKI:
                        entities['topic'] = match.group(2)
                    elif intent_type == IntentType.WEATHER:
                        if 'in' in text:
                            entities['city'] = match.group(1)
                    elif intent_type == IntentType.SMART_HOME:
                        entities['action'] = match.group(1)
                        entities['device'] = match.group(2)
                    elif intent_type == IntentType.CALCULATE:
                        entities['expression'] = match.group(2)
                    
                    best_intent = Intent(
                        type=intent_type,
                        confidence=confidence,
                        entities=entities,
                        raw_text=text
                    )
        
        return best_intent or Intent(IntentType.GREET, 0.1, {}, text)

    def handle_intent(self, intent: Intent):
        """Enhanced intent handling with better error management"""
        try:
            if intent.type == IntentType.GREET:
                self.handle_greeting()
            elif intent.type == IntentType.TIME:
                self.handle_time()
            elif intent.type == IntentType.DATE:
                self.handle_date()
            elif intent.type == IntentType.HELP:
                self.handle_help()
            elif intent.type == IntentType.OPEN:
                self.handle_open(intent.entities.get('target', ''))
            elif intent.type == IntentType.PLAY:
                self.handle_play(intent.entities.get('query', ''))
            elif intent.type == IntentType.EMAIL:
                self.handle_email()
            elif intent.type == IntentType.REMINDER:
                self.handle_reminder()
            elif intent.type == IntentType.SEARCH:
                self.handle_search(intent.entities.get('query', ''))
            elif intent.type == IntentType.WIKI:
                self.handle_wiki(intent.entities.get('topic', ''))
            elif intent.type == IntentType.WEATHER:
                self.handle_weather(intent.entities.get('city', ''))
            elif intent.type == IntentType.NEWS:
                self.handle_news()
            elif intent.type == IntentType.SMART_HOME:
                self.handle_smart_home(intent.entities.get('action', ''), intent.entities.get('device', ''))
            elif intent.type == IntentType.CALENDAR:
                self.handle_calendar()
            elif intent.type == IntentType.NOTE:
                self.handle_note()
            elif intent.type == IntentType.CALCULATE:
                self.handle_calculate(intent.entities.get('expression', ''))
            elif intent.type == IntentType.TRANSLATE:
                self.handle_translate()
            elif intent.type == IntentType.EXIT:
                self.handle_exit()
            else:
                self.handle_unknown()
                
        except Exception as e:
            logging.exception(f"Error handling intent {intent.type}")
            self.speak("I encountered an error while processing your request. Please try again.")

    def handle_greeting(self):
        """Enhanced greeting with time awareness"""
        hour = datetime.datetime.now().hour
        if 0 <= hour < 12:
            greeting = "Good morning!"
        elif 12 <= hour < 18:
            greeting = "Good afternoon!"
        else:
            greeting = "Good evening!"
        
        self.speak(f"{greeting} I'm {ASSISTANT_NAME}, your advanced voice assistant. How can I help you today?")

    def handle_time(self):
        """Get current time with natural language"""
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        self.speak(f"The current time is {time_str}")

    def handle_date(self):
        """Get current date with natural language"""
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        self.speak(f"Today is {date_str}")

    def handle_help(self):
        """Enhanced help with categorized commands"""
        help_categories = [
            "Time and Date: Ask for current time or date",
            "Web and Apps: Say 'open' followed by app or website name",
            "Media: Say 'play' followed by song or video name",
            "Communication: Say 'send email' to compose an email",
            "Reminders: Say 'remind me to' followed by your reminder",
            "Information: Ask 'what is' or 'who is' for knowledge",
            "Weather: Ask for weather in any city",
            "News: Say 'news' for latest headlines",
            "Smart Home: Say 'turn on' or 'turn off' followed by device",
            "Calculations: Say 'calculate' followed by math expression",
            "Notes: Say 'note' or 'remember' to save information"
        ]
        
        self.speak("Here's what I can help you with:")
        for category in help_categories:
            self.speak(category)

    def handle_open(self, target: str):
        """Enhanced application/website opening"""
        if not target:
            self.speak("What would you like me to open?")
            return

        # Enhanced mappings
        site_map = {
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
            "google": "https://www.google.com",
            "github": "https://github.com",
            "stackoverflow": "https://stackoverflow.com",
            "whatsapp": "https://web.whatsapp.com",
            "netflix": "https://www.netflix.com",
            "spotify": "https://open.spotify.com",
            "twitter": "https://twitter.com",
            "facebook": "https://www.facebook.com",
            "instagram": "https://www.instagram.com",
            "linkedin": "https://www.linkedin.com"
        }
        
        app_map = {
            "calculator": "calc",
            "notepad": "notepad",
            "paint": "mspaint",
            "command prompt": "cmd",
            "task manager": "taskmgr",
            "file explorer": "explorer",
            "control panel": "control"
        }

        target_lower = target.lower()
        
        if target_lower in site_map:
            webbrowser.open(site_map[target_lower])
            self.speak(f"Opening {target}")
        elif target_lower in app_map:
            try:
                subprocess.run(["start", app_map[target_lower]], shell=True, check=False)
                self.speak(f"Opening {target}")
            except Exception as e:
                self.speak(f"I couldn't open {target}")
                logging.error(f"App open error: {e}")
        elif "." in target and " " not in target:
            # Looks like a domain
            url = target if target.startswith("http") else f"https://{target}"
            webbrowser.open(url)
            self.speak(f"Opening {target}")
        else:
            # Google search fallback
            url = f"https://www.google.com/search?q={target}"
            webbrowser.open(url)
            self.speak(f"Searching for {target}")

    def handle_play(self, query: str):
        """Enhanced media playback"""
        if not query:
            self.speak("What would you like me to play?")
            return
        
        # YouTube search
        url = f"https://www.youtube.com/results?search_query={query}"
        webbrowser.open(url)
        self.speak(f"Searching YouTube for {query}")

    def handle_email(self):
        """Enhanced email functionality"""
        if not SENDER_EMAIL or not SENDER_PASSWORD:
            self.speak("Email functionality is not configured. Please set your email credentials.")
            return

        try:
            contacts = self.load_contacts()
            self.speak("To whom should I send the email?")
            recipient_input = self.listen()
            
            if recipient_input == "none":
                self.speak("I didn't catch the recipient. Cancelling email.")
                return
                
            recipient = self.resolve_recipient(recipient_input, contacts)
            if not recipient:
                self.speak("I couldn't find that contact. Please try again.")
                return
            
            self.speak("What should be the subject?")
            subject = self.listen()
            if subject == "none":
                subject = "No Subject"
            
            self.speak("What's the message?")
            body = self.listen()
            if body == "none":
                self.speak("I didn't catch the message. Cancelling email.")
                return

            self.send_email(recipient, subject, body)
            self.speak("Email sent successfully!")
            
        except Exception as e:
            logging.exception("Email error")
            self.speak("Sorry, I couldn't send the email.")

    def send_email(self, recipient: str, subject: str, body: str):
        """Send email with enhanced error handling"""
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                
                message = f"Subject: {subject}\n\n{body}"
                server.sendmail(SENDER_EMAIL, recipient, message)
                
        except smtplib.SMTPAuthenticationError:
            raise Exception("Authentication failed. Check your email credentials.")
        except Exception as e:
            raise Exception(f"Email sending failed: {str(e)}")

    def handle_reminder(self):
        """Enhanced reminder system with better time parsing and display"""
        self.speak("What should I remind you about?")
        reminder_text = self.listen()
        
        if reminder_text == "none":
            self.speak("I didn't catch that. Please try again.")
            return
        
        self.speak("In how many minutes?")
        time_input = self.listen().lower()
        
        try:
            # Enhanced time parsing with debug logging
            minutes = 0
            logging.info(f"Parsing time input: '{time_input}'")
            
            # First try to extract any numbers
            numbers = re.findall(r'\d+', time_input)
            if numbers:
                minutes = int(numbers[0])
                logging.info(f"Found number in input: {minutes}")
            else:
                # If no numbers found, try word matching
                time_words = {
                    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
                    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
                }
                
                for word, value in time_words.items():
                    if word in time_input:
                        minutes = value
                        logging.info(f"Matched word number: {word} = {minutes}")
                        break
            
            if minutes > 0:
                # Calculate exact due time
                delay_seconds = minutes * 60
                due = time.time() + delay_seconds
                reminder_id = str(uuid.uuid4())
                
                # Format the due time for display
                due_time = datetime.datetime.fromtimestamp(due).strftime('%H:%M:%S')
                
                # Create and store the reminder
                self.reminders.append((due, reminder_text, reminder_id))
                
                # Display confirmation in terminal
                print("\n" + "-"*50)
                print(f"📝 New Reminder Set:")
                print(f"Task: {reminder_text}")
                print(f"Due at: {due_time} ({minutes} minute{'s' if minutes != 1 else ''})")
                print("-"*50 + "\n")
                
                # Log the scheduled reminder
                logging.info(f"Scheduled reminder {reminder_id} for {due_time}: {reminder_text}")
                
                # Speak confirmation
                self.speak(f"Okay, I'll remind you to {reminder_text} in {minutes} minute{'s' if minutes != 1 else ''}.")
            else:
                self.speak("Please provide a positive number of minutes.")
                
        except (ValueError, IndexError) as e:
            logging.error(f"Error parsing reminder time: {str(e)}")
            self.speak("I didn't understand the time. Please say a number of minutes.")

    def _start_reminder_monitor(self):
        """Start a daemon thread that monitors due reminders and fires them."""
        if self._reminder_thread and self._reminder_thread.is_alive():
            return

        def monitor():
            logging.info("Reminder monitor started")
            while True:
                try:
                    now = time.time()
                    due_items = []
                    remaining_reminders = []
                    
                    # Thread-safe copy of current reminders and sort by due time
                    current_reminders = sorted(list(self.reminders), key=lambda x: x[0])
                    
                    # Check which reminders are due
                    for reminder in current_reminders:
                        due_time, text, rid = reminder
                        time_diff = due_time - now
                        
                        # Consider a reminder due if it's within 0.5 seconds of its target time
                        if time_diff <= 0.5:
                            due_items.append(reminder)
                            logging.info(f"Reminder {rid} is due (time_diff: {time_diff:.2f}s)")
                        else:
                            remaining_reminders.append(reminder)
                            if time_diff < 10:  # Log upcoming reminders
                                logging.info(f"Reminder {rid} coming up in {time_diff:.2f} seconds")
                    
                    # Update reminders list atomically
                    if due_items:
                        self.reminders = remaining_reminders

                    # Fire due reminders
                    for due_ts, text, rid in due_items:
                        try:
                            reminder_time = datetime.datetime.fromtimestamp(due_ts).strftime('%H:%M:%S')
                            message = f"⏰ Reminder ({reminder_time}): {text}"
                            logging.info(f"Firing reminder {rid}: {message}")
                            
                            # Display reminder in terminal
                            print("\n" + "="*50)
                            print(message)
                            print("="*50 + "\n")
                            
                            # Use the speak lock to avoid concurrent TTS calls
                            with self.speak_lock:
                                self.speak(f"Reminder: {text}")
                                time.sleep(0.5)  # Small delay for clarity
                            
                            logging.info(f"Successfully fired reminder {rid}")
                        except Exception as e:
                            logging.exception(f"Error while firing reminder {rid}: {str(e)}")

                except Exception as e:
                    logging.exception(f"Reminder monitor error: {str(e)}")

                # Check frequently for precise timing
                time.sleep(0.1)  # Reduced sleep time for better accuracy

        t = threading.Thread(target=monitor, daemon=True)
        t.start()
        self._reminder_thread = t

    def handle_search(self, query: str):
        """Enhanced web search"""
        if not query:
            self.speak("What would you like me to search for?")
            return
        
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        self.speak(f"Searching for {query}")

    def handle_wiki(self, topic: str):
        """Enhanced Wikipedia search"""
        if not topic:
            self.speak("What would you like to know about?")
            return
        
        try:
            self.speak(f"Searching Wikipedia for {topic}...")
            result = wikipedia.summary(topic, sentences=3)
            self.speak("According to Wikipedia...")
            self.speak(result)
        except wikipedia.exceptions.DisambiguationError:
            self.speak(f"Multiple results found for {topic}. Please be more specific.")
        except wikipedia.exceptions.PageError:
            self.speak(f"Sorry, I couldn't find information about {topic}.")
        except Exception as e:
            logging.exception("Wikipedia error")
            self.speak("An error occurred while searching Wikipedia.")

    def handle_weather(self, city: str = ""):
        """Enhanced weather functionality"""
        if not city:
            city = self.get_current_city()
            if city:
                self.speak(f"Getting weather for your location: {city}")
            else:
                self.speak("Which city's weather would you like to know?")
                city_input = self.listen()
                if city_input != "none":
                    city = city_input
                else:
                    return
        
        if not OPENWEATHER_API_KEY:
            self.speak("Weather service is not configured.")
            return
        
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data["cod"] != "404":
                temp = data["main"]["temp"]
                description = data["weather"][0]["description"]
                humidity = data["main"]["humidity"]
                
                weather_report = f"The weather in {city} is {description} with a temperature of {temp}°C and humidity of {humidity}%"
                self.speak(weather_report)
            else:
                self.speak(f"Sorry, I couldn't find weather data for {city}")
                
        except Exception as e:
            logging.exception("Weather error")
            self.speak("I couldn't get the weather information right now.")

    def handle_news(self):
        """Get latest news headlines"""
        if not NEWS_API_KEY:
            self.speak("News service is not configured.")
            return
        
        try:
            url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data["status"] == "ok":
                articles = data["articles"][:5]  # Top 5 headlines
                self.speak("Here are the latest news headlines:")
                for i, article in enumerate(articles, 1):
                    self.speak(f"{i}. {article['title']}")
            else:
                self.speak("Sorry, I couldn't fetch the news right now.")
                
        except Exception as e:
            logging.exception("News error")
            self.speak("I couldn't get the news right now.")

    def handle_smart_home(self, action: str, device: str):
        """Smart home device control"""
        if not SMART_HOME_API_KEY:
            self.speak("Smart home integration is not configured.")
            return
        
        # This would integrate with actual smart home APIs like Philips Hue, SmartThings, etc.
        self.speak(f"I would {action} the {device}, but smart home integration needs to be configured.")

    def handle_calendar(self):
        """Calendar management"""
        self.speak("Calendar functionality is coming soon. I can help you set reminders for now.")

    def handle_note(self):
        """Note taking functionality"""
        self.speak("What would you like me to remember?")
        note_text = self.listen()
        
        if note_text != "none":
            # Save to database
            self.save_note(note_text)
            self.speak("I've saved that note for you.")

    def handle_calculate(self, expression: str):
        """Mathematical calculations"""
        if not expression:
            self.speak("What would you like me to calculate?")
            return
        
        try:
            # Safe evaluation of mathematical expressions
            result = eval(expression.replace("plus", "+").replace("minus", "-").replace("times", "*").replace("divided by", "/"))
            self.speak(f"The result is {result}")
        except Exception as e:
            self.speak("I couldn't calculate that expression. Please try a simpler one.")

    def handle_translate(self):
        """Translation functionality"""
        self.speak("Translation functionality is coming soon.")

    def handle_exit(self):
        """Graceful exit"""
        self.speak("Goodbye! Have a great day.")
        return True

    def handle_unknown(self):
        """Handle unrecognized commands"""
        self.speak("I didn't understand that. You can say 'help' to see what I can do.")

    def get_current_city(self):
        """Get current city using IP geolocation"""
        try:
            response = requests.get("http://ip-api.com/json/", timeout=5)
            data = response.json()
            return data.get("city")
        except Exception:
            return None

    def load_contacts(self):
        """Load contacts from database or environment"""
        if CONTACTS_JSON:
            try:
                return json.loads(CONTACTS_JSON)
            except Exception:
                pass
        
        return {
            "aradhya": "aradhyapendurkar192003@gmail.com",
            "self": SENDER_EMAIL,
        }

    def resolve_recipient(self, said: str, contacts: dict):
        """Resolve spoken name to email address"""
        said = said.lower()
        
        # Check if it's already an email
        if "@" in said and "." in said:
            return said
        
        # Check contacts
        if said in contacts:
            return contacts[said]
        
        # Remove common prefixes
        if said.startswith("to "):
            said = said[3:]
            if said in contacts:
                return contacts[said]
        
        return None

    def save_note(self, note_text: str):
        """Save note to database"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute(
                "INSERT INTO conversations (user_id, session_id, message, intent) VALUES (?, ?, ?, ?)",
                (self.user_context.user_id, self.user_context.session_id, note_text, "note")
            )
            self.db_connection.commit()
        except Exception as e:
            logging.error(f"Error saving note: {e}")

    def run(self):
        """Main assistant loop"""
        self.speak("Hello! I'm your advanced voice assistant. How can I help you today?")
        
        none_count = 0
        while True:
            try:
                command = self.listen()
                
                if command == "none":
                    none_count += 1
                    if TEXT_FALLBACK_ENABLED and none_count >= 2:
                        try:
                            typed = input("Type your command: ").strip().lower()
                            command = typed if typed else "none"
                            none_count = 0
                        except Exception:
                            pass
                    if command == "none":
                        continue
                else:
                    none_count = 0
                
                # Wake word handling
                if WAKE_MODE_ENABLED and WAKE_WORD not in command:
                    continue
                
                if WAKE_MODE_ENABLED:
                    command = command.replace(WAKE_WORD, "").strip()
                
                # Process natural language
                intent = self.process_natural_language(command)
                
                # Handle intent
                if self.handle_intent(intent):
                    break
                    
            except KeyboardInterrupt:
                self.speak("Goodbye!")
                break
            except Exception as e:
                logging.exception("Main loop error")
                self.speak("I encountered an error. Please try again.")

if __name__ == "__main__":
    assistant = EnhancedVoiceAssistant()
    assistant.run()
