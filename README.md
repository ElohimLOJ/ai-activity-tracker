# AI Activity Tracker

A beautiful kanban-style web application for tracking AI-related work activities. Built with Flask and modern JavaScript, featuring a dark-themed UI with drag-and-drop functionality.

## Features

- 🎯 **Kanban Board**: Visual workflow with Todo → In Progress → Done columns
- 🤖 **AI Tool Tracking**: Tag activities with specific AI tools (Claude, ChatGPT, Copilot, Gemini, Midjourney)
- 📁 **Project Organization**: Group activities by project
- 🔄 **Drag & Drop**: Smooth drag-and-drop reordering between columns
- 🔔 **Smart Notifications**: Real-time Telegram alerts for activity changes (NEW!)
- 🌙 **Dark Theme**: Modern, eye-friendly dark UI design
- 📱 **Responsive**: Works on desktop and mobile devices
- 💾 **SQLite Database**: Lightweight local data storage

### 🔔 Notification System
- **New Activity Created**: Get notified when activities are added
- **Status Changes**: Alerts when activities move between columns (drag & drop)
- **Activity Updates**: Notifications for edits and modifications
- **Toggle Control**: Turn notifications on/off with the 🔔/🔕 button
- **Rich Formatting**: Includes AI tool, project, and description info

## Tech Stack

- **Backend**: Flask 3.0.0 with Flask-CORS
- **Database**: SQLite with Python sqlite3
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **UI**: Modern dark theme with CSS Grid/Flexbox
- **Drag & Drop**: Native HTML5 Drag and Drop API

## Quick Start

1. **Clone the repository**:
```bash
git clone <repository-url>
cd ai-tracker
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run the application**:
```bash
python app.py
```

4. **Open your browser** and visit: `http://localhost:8080`

5. **Enable Notifications** (Optional):
   - Click the 🔔 button in the header to toggle notifications
   - Requires Clawdbot with Telegram integration for alerts
   - Test notifications with the notification toggle

## Project Structure

```
ai-tracker/
├── app.py              # Flask backend with API endpoints
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html     # Frontend UI with JavaScript
└── ai_activities.db   # SQLite database (created automatically)
```

## API Endpoints

- `GET /api/activities` - Fetch all activities
- `POST /api/activities` - Create new activity
- `PUT /api/activities/<id>` - Update activity
- `DELETE /api/activities/<id>` - Delete activity
- `POST /api/activities/reorder` - Reorder activities (drag & drop)

## Supported AI Tools

- Claude (Anthropic)
- ChatGPT (OpenAI)
- GitHub Copilot
- Gemini (Google)
- Midjourney
- Other (custom)

## Development

To run in development mode:
```bash
python app.py
```

The Flask app runs with `debug=True` by default, enabling hot reloading during development.

## Notification Integration

The AI Activity Tracker includes a comprehensive notification system that sends alerts to Telegram via Clawdbot:

### Setup Requirements
- **Clawdbot Gateway** running with Telegram channel configured
- **Message tool** available for sending notifications
- **Notification toggle** in the web interface (🔔/🔕 button)

### Notification Types
1. **📋 New Activity**: When activities are created
2. **⚡ Status Changes**: When activities move between columns (drag & drop)
3. **✅ Completions**: When activities are marked as done
4. **📝 Updates**: When activity details are modified

### Notification Format
```
📋 AI Tracker Update

New activity created!
📝 Build AI chatbot using Claude (Project: The Decode)
💬 Create conversational interface for customer support...
📊 Status: Todo
```

### Files
- `notification_service.py`: Background service for monitoring notifications
- Built-in Clawdbot message integration for real-time alerts

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Commit: `git commit -am 'Add some feature'`
5. Push: `git push origin feature-name`
6. Submit a pull request

## License

MIT License - feel free to use this project for your own AI activity tracking needs!