# Advanced Voice Assistant

A sophisticated voice assistant with natural language processing capabilities, smart home integration, security features, and a modern web interface.

## 🚀 Features

### Core Capabilities
- **Advanced Speech Recognition**: Multiple recognition engines with fallback support
- **Natural Language Processing**: Context-aware intent recognition and entity extraction
- **Text-to-Speech**: Configurable voice settings and multiple language support
- **Wake Word Detection**: Optional wake word activation for hands-free operation

### Smart Features
- **Email Integration**: Send emails hands-free with contact management
- **Weather Updates**: Real-time weather information for any city
- **Web Search**: Intelligent web search with result summarization
- **Wikipedia Integration**: Knowledge base queries with disambiguation
- **Reminder System**: Set and manage reminders with threading
- **News Updates**: Latest news headlines and current events
- **Smart Home Control**: Integration with Philips Hue, SmartThings, Home Assistant, and Alexa

### Security & Privacy
- **Data Encryption**: End-to-end encryption for sensitive data
- **Privacy Controls**: Configurable data retention and sharing settings
- **Session Management**: Secure user sessions with timeout
- **Access Logging**: Comprehensive audit trail for security
- **Anonymization**: Automatic PII detection and anonymization

### Customization
- **Custom Commands**: Create personalized voice commands
- **API Integrations**: Connect with external services via webhooks
- **Voice Customization**: Adjustable speech rate, volume, and voice selection
- **UI Themes**: Customizable interface themes and preferences
- **User Preferences**: Personalized settings and configurations

### Error Handling & UX
- **Graceful Degradation**: Fallback responses when services are unavailable
- **Retry Mechanisms**: Automatic retry with exponential backoff
- **User Feedback**: Satisfaction tracking and improvement suggestions
- **Performance Monitoring**: Response time and success rate tracking
- **Error Pattern Analysis**: Learning from common errors

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Microphone and speakers
- Internet connection for API services

### Quick Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd Voice_Assistant
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp env_example.txt .env
# Edit .env with your API keys and settings
```

4. **Run the assistant**
```bash
# Command line version
python enhanced_voice_assistant.py

# Web interface version
cd web_interface
python app.py
```

### Detailed Setup

#### 1. Environment Configuration

Create a `.env` file with the following variables:

```env
# Assistant Settings
ASSISTANT_NAME=YourAssistant
WAKE_WORD=hey assistant
WAKE_MODE_ENABLED=true
TEXT_FALLBACK_ENABLED=true

# Email Configuration
SENDER_EMAIL=your-email@gmail.com
SENDER_APP_PASSWORD=your-app-password

# API Keys
OPENWEATHER_API_KEY=your-openweather-api-key
NEWS_API_KEY=your-news-api-key
SMART_HOME_API_KEY=your-smart-home-api-key

# Security
MASTER_PASSWORD=your-master-password
ENCRYPTION_KEY=your-encryption-key
```

#### 2. API Keys Setup

**OpenWeatherMap API** (for weather):
1. Go to [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Get your API key
4. Add it to your `.env` file

**News API** (for news):
1. Go to [NewsAPI](https://newsapi.org/)
2. Sign up for a free account
3. Get your API key
4. Add it to your `.env` file

**Email Setup** (for email functionality):
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password
3. Use your email and app password in the `.env` file

#### 3. Smart Home Integration

**Philips Hue**:
1. Find your Hue bridge IP address
2. Press the bridge button and run the discovery
3. Configure in the smart home settings

**SmartThings**:
1. Create a SmartThings developer account
2. Generate a personal access token
3. Add the token to your configuration

**Home Assistant**:
1. Enable the REST API in Home Assistant
2. Generate a long-lived access token
3. Configure the base URL and token

## 🎯 Usage

### Command Line Interface

```bash
python enhanced_voice_assistant.py
```

### Web Interface

```bash
cd web_interface
python app.py
```

Then open your browser to `http://localhost:5000`

### Voice Commands

#### Basic Commands
- "Hello" / "Hi" - Greet the assistant
- "What's the time?" - Get current time
- "What's the date?" - Get current date
- "Help" - List available commands

#### Information Commands
- "Search for [query]" - Web search
- "What is [topic]?" - Wikipedia lookup
- "Weather in [city]" - Weather information
- "News" - Latest headlines

#### Communication
- "Send email" - Compose and send email
- "Remind me to [task]" - Set reminders

#### Smart Home
- "Turn on [device]" - Control smart devices
- "Turn off [device]" - Control smart devices
- "Dim [light]" - Adjust lighting

#### Custom Commands
- Create your own voice commands through the web interface
- Set up API integrations
- Configure personalized responses

## 🔧 Configuration

### Voice Settings

```python
# Adjust speech rate (words per minute)
engine.setProperty('rate', 150)

# Adjust volume (0.0 to 1.0)
engine.setProperty('volume', 0.8)

# Change voice
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)  # Select different voice
```

### Privacy Settings

Access privacy settings through the web interface or programmatically:

```python
from security_features import SecurityManager

security_manager = SecurityManager()
privacy_settings = {
    'voice_data_retention_days': 30,
    'conversation_logging': True,
    'data_encryption': True,
    'anonymous_analytics': True,
    'third_party_sharing': False
}
security_manager.set_privacy_settings(user_id, privacy_settings)
```

### Custom Commands

Create custom commands through the web interface or programmatically:

```python
from customization_features import CustomizationManager

customization_manager = CustomizationManager()

# Create a text response command
command_id = customization_manager.create_custom_command(
    user_id="user123",
    trigger_phrase="tell me a joke",
    action_type="text_response",
    action_data={"response": "Why don't scientists trust atoms? Because they make up everything!"},
    description="Tells a joke"
)

# Create an API call command
command_id = customization_manager.create_custom_command(
    user_id="user123",
    trigger_phrase="check my calendar",
    action_type="api_call",
    action_data={
        "url": "https://api.calendar.com/events",
        "method": "GET",
        "headers": {"Authorization": "Bearer your-token"}
    },
    description="Checks calendar events"
)
```

## 🏗️ Architecture

### Core Components

1. **Enhanced Voice Assistant** (`enhanced_voice_assistant.py`)
   - Main assistant class with NLP processing
   - Intent recognition and entity extraction
   - Command handling and response generation

2. **Web Interface** (`web_interface/`)
   - Flask-based web application
   - Real-time voice interaction
   - Settings and customization interface

3. **Smart Home Integration** (`smart_home_integration.py`)
   - Multi-platform smart home support
   - Device discovery and control
   - Protocol abstraction layer

4. **Security Features** (`security_features.py`)
   - Data encryption and secure storage
   - Privacy controls and data retention
   - Session management and access logging

5. **Customization System** (`customization_features.py`)
   - Custom command creation
   - API integration framework
   - User preference management

6. **Error Handling** (`error_handling.py`)
   - Comprehensive error tracking
   - Retry mechanisms and fallbacks
   - User experience monitoring

### Database Schema

The assistant uses SQLite for data storage with the following main tables:

- `users` - User accounts and preferences
- `conversations` - Chat history and context
- `custom_commands` - User-defined commands
- `custom_integrations` - API integrations
- `error_logs` - Error tracking and analysis
- `user_feedback` - User satisfaction data
- `privacy_settings` - Privacy and data retention settings

## 🔒 Security Considerations

### Data Protection
- All sensitive data is encrypted before storage
- User sessions are managed securely
- Privacy settings allow users to control data sharing

### API Security
- API keys are stored securely in environment variables
- Rate limiting prevents abuse
- Input validation prevents injection attacks

### Privacy Features
- Automatic PII detection and anonymization
- Configurable data retention periods
- User control over data sharing and analytics

## 🚀 Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp env_example.txt .env
# Edit .env with your settings

# Run the assistant
python enhanced_voice_assistant.py
```

### Production Deployment

#### Using Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "web_interface/app.py"]
```

#### Using Cloud Services
- Deploy to Heroku, AWS, or Google Cloud
- Set environment variables in your deployment platform
- Configure database for production use
- Set up SSL certificates for HTTPS

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**Speech Recognition Not Working**
- Check microphone permissions
- Ensure good audio quality
- Try different recognition engines

**API Errors**
- Verify API keys are correct
- Check internet connection
- Review API rate limits

**Database Errors**
- Ensure SQLite is properly installed
- Check file permissions
- Verify database schema

**Smart Home Integration**
- Verify device connectivity
- Check API credentials
- Ensure devices are discoverable

### Getting Help

1. Check the troubleshooting section
2. Review error logs in `assistant.log`
3. Check database for error patterns
4. Submit an issue with detailed information

## 🔮 Future Enhancements

- Machine learning for better intent recognition
- Multi-language support
- Advanced smart home protocols
- Cloud synchronization
- Mobile app integration
- Voice cloning capabilities
- Advanced analytics and insights

## 📊 Performance Monitoring

The assistant includes built-in performance monitoring:

- Response time tracking
- Success rate analysis
- Error pattern recognition
- User satisfaction scoring
- Resource usage monitoring

Access these metrics through the web interface or programmatically via the UX manager.

---

**Built with ❤️ for the future of voice interaction**
