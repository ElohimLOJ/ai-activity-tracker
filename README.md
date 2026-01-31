# AI Activity Tracker Pro

🚀 **A comprehensive productivity analytics platform for AI-powered work.** Track, analyze, and optimize your AI tool usage with professional-grade insights and reporting.

## 🎯 Core Features

### 📋 **Enhanced Kanban Board**
- **Visual Workflow**: Todo → In Progress → Done columns with drag & drop
- **Rich Cards**: Activity details with time tracking, outcomes, and iteration counts
- **Live Timers**: Start/stop time tracking directly on cards
- **Smart Tags**: Color-coded AI tools, projects, outcomes, and time spent

### 📊 **Professional Dashboard**
- **Overview Stats**: Completion rates, total time, averages
- **Tool Performance**: Success rates and efficiency metrics for each AI tool
- **Project Analytics**: Time allocation and progress tracking
- **Failure Analysis**: Categorized insights into what doesn't work

### ⏱️ **Advanced Time Tracking**
- **Live Timers**: Click-to-start tracking with real-time display
- **Manual Entry**: Add time spent manually
- **Automatic Totals**: Cumulative time tracking across sessions
- **Time Analytics**: Average time per task, tool efficiency metrics

### 🎯 **Outcome Tracking**
- **Success Ratings**: Success / Partial / Failed outcomes
- **Detailed Notes**: What worked, what didn't
- **Iteration Counter**: Track refinement attempts
- **Failure Categories**: Technical issues, wrong tool, poor prompts, etc.

### 📤 **Export & Reporting**
- **CSV Export**: Complete data export for external analysis
- **Executive Reports**: Summary text reports with key insights
- **Calendar Integration**: Export as .ics files for Apple Calendar, Google Calendar
- **Analytics Data**: JSON APIs for custom integrations

### 🔔 **Smart Notifications**
- **Real-time Alerts**: Telegram notifications for activity changes
- **Activity Updates**: New tasks, status changes, completions
- **Toggle Control**: Enable/disable notifications
- **Rich Formatting**: Context-aware notification content

## 🛠️ Tech Stack

- **Backend**: Flask 3.0.0 with advanced REST API endpoints
- **Database**: SQLite with comprehensive analytics schema
- **Frontend**: Vanilla JavaScript with professional dashboard charts
- **UI**: Dark theme with responsive design and animated transitions
- **Analytics**: Real-time statistics and performance metrics
- **Export**: CSV, text reports, and calendar integration
- **Notifications**: Clawdbot/Telegram integration
- **Time Tracking**: Background timers with live updates

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

## 🔗 API Endpoints

### Activities
- `GET /api/activities` - Fetch all activities
- `POST /api/activities` - Create new activity with outcome tracking
- `PUT /api/activities/<id>` - Update activity
- `DELETE /api/activities/<id>` - Delete activity

### Time Tracking
- `POST /api/activities/<id>/timer/start` - Start activity timer
- `POST /api/activities/<id>/timer/stop` - Stop activity timer
- `POST /api/activities/<id>/iteration` - Increment iteration count

### Analytics & Dashboard
- `GET /api/dashboard` - Get comprehensive analytics data
- `GET /api/analytics/tools` - Get tool comparison metrics

### Export & Integration
- `GET /api/export/csv` - Download CSV data export
- `GET /api/export/report` - Download executive summary report
- `GET /api/calendar/ics` - Export as calendar (.ics) file

### Notifications
- `GET /api/notifications/status` - Check notification status
- `POST /api/notifications/toggle` - Toggle notifications on/off
- `POST /api/test-notification` - Send test notification

## 🤖 Supported AI Tools

- **Claude** (Anthropic) - with performance analytics
- **ChatGPT** (OpenAI) - success rate tracking
- **GitHub Copilot** - coding efficiency metrics  
- **Gemini** (Google) - iteration analysis
- **Midjourney** - creative outcome tracking
- **Cursor** - development workflow analytics
- **Other** - custom tool tracking

## 📈 What's New in Pro Version

### Enhanced Analytics
- **Tool Performance Dashboard**: Compare success rates, average time, and iterations across all AI tools
- **Project Time Allocation**: See where you're spending time and getting results
- **Failure Pattern Analysis**: Learn from what doesn't work
- **Outcome Trends**: Track your AI success over time

### Professional Time Tracking
- **Live Timers**: Start/stop tracking directly on kanban cards
- **Session Management**: Automatic pause/resume functionality  
- **Time Analytics**: Average time per tool, per project, per outcome
- **Cumulative Tracking**: Build up comprehensive time data

### Advanced Export Options
- **CSV Data Export**: Complete activity database for spreadsheet analysis
- **Executive Reports**: Summary insights for productivity reviews
- **Calendar Integration**: Sync with Apple Calendar, Google Calendar via .ics
- **API Access**: JSON endpoints for custom integrations

### Smart Outcome Tracking
- **Success Metrics**: Track what works and what doesn't
- **Iteration Counting**: See how many attempts tasks typically take
- **Failure Categorization**: Understand why things fail (wrong tool, poor prompt, etc.)
- **Learning Insights**: Build knowledge from outcomes

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