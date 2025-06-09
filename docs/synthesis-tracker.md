# Synthesis Tracker MCP Server

MCP server for tracking educational progress on Synthesis.com tutoring platform.

## Overview

The Synthesis Tracker enables AI assistants to monitor and track study progress on Synthesis.com, providing insights into daily study habits, progress streaks, and learning achievements. Since Synthesis.com doesn't provide a public API, this server uses email monitoring and web automation to gather progress data.

## Features

### 📧 Email Integration
- Monitors ProtonMail for Synthesis login codes
- Parses daily progress emails automatically
- Extracts study time and lesson completion data

### 🤖 Web Automation
- Automated login using Playwright
- Dashboard data scraping for detailed progress
- Screenshot capture for debugging

### 📊 Progress Tracking
- Daily study session recording
- Weekly progress summaries
- Streak calculation and monitoring
- Achievement notifications

## MCP Tools

The server provides 6 MCP tools for AI assistant integration:

### `check_synthesis_login`
Check if user has logged into Synthesis.com today.
- **Parameters**: None
- **Returns**: Login status, study minutes, streak info

### `get_study_progress`
Get detailed study progress for a specific date.
- **Parameters**: `date` (optional, defaults to today)
- **Returns**: Comprehensive progress data

### `get_weekly_summary`
Get weekly study statistics and recommendations.
- **Parameters**: None
- **Returns**: Week summary, goal progress, recommendations

### `send_study_reminder`
Send a study reminder if user hasn't studied today.
- **Parameters**: `custom_message` (optional)
- **Returns**: Reminder status and message

### `get_current_streak`
Get current study streak and recent activity.
- **Parameters**: None
- **Returns**: Streak count and recent study history

### `force_update_progress`
Force update progress by logging into Synthesis.com.
- **Parameters**: None
- **Returns**: Latest progress data from platform

## Setup

### Prerequisites

1. **ProtonMail Paid Account** with Bridge access
2. **Email Forwarding** from Synthesis.com to ProtonMail
3. **Docker** and Docker Compose (for containerized deployment)

### Email Configuration

1. **Setup ProtonMail Bridge**:
   ```bash
   docker run --rm -it -v protonmail:/root shenxn/protonmail-bridge init
   # Follow prompts to add your account
   ```

2. **Configure Email Forwarding**:
   - Set up rule to forward Synthesis emails to your ProtonMail
   - Ensure both login codes and progress emails are forwarded

### Environment Variables

Create `.env` file with your credentials:

```env
# ProtonMail Bridge Settings
EMAIL_SERVER=protonmail-bridge
EMAIL_PORT=143
EMAIL_USERNAME=claude.weeks@proton.me
EMAIL_PASSWORD=your-bridge-password
EMAIL_USE_SSL=false

# Synthesis.com Account
SYNTHESIS_EMAIL=student@example.com
SYNTHESIS_URL=https://synthesis.com

# Database Settings
DATABASE_PATH=/app/data/synthesis.db

# Notification Settings
NOTIFICATION_ENABLED=true
NOTIFICATION_TIMES=09:00,15:00,19:00

# Browser Automation
HEADLESS_BROWSER=true
BROWSER_TIMEOUT=30

# Study Goals
MINIMUM_STUDY_MINUTES=15
STUDY_GOAL_MINUTES=30
```

### Docker Deployment

1. **Start services**:
   ```bash
   cd docker
   docker-compose up -d
   ```

2. **Check logs**:
   ```bash
   docker-compose logs -f synthesis-tracker
   ```

### Open WebUI Integration

1. **Install mcpo**:
   ```bash
   npm install -g @open-webui/mcpo
   ```

2. **Create mcpo config**:
   ```json
   {
     "mcpServers": {
       "synthesis-tracker": {
         "command": "python",
         "args": ["src/synthesis/server.py"],
         "env": {
           "PYTHONPATH": "/app"
         }
       }
     }
   }
   ```

3. **Add tools to Open WebUI**:
   - Go to Settings → Tools
   - Add MCP server endpoints
   - Configure with Whiskers agent

## Usage Examples

### Daily Progress Check
```
"Whiskers, did my daughter study today?"
→ Uses check_synthesis_login tool
→ Returns: "Yes, she completed 25 minutes and worked on fractions!"
```

### Weekly Summary
```
"Show me this week's math progress"
→ Uses get_weekly_summary tool  
→ Returns detailed stats and recommendations
```

### Proactive Reminders
```
Whiskers automatically checks if no study activity
→ Uses send_study_reminder tool
→ Sends encouraging message to study
```

## Data Storage

### SQLite Database
- **Location**: Configurable via `DATABASE_PATH`
- **Tables**: 
  - `study_sessions` - Daily progress records
  - `notifications` - Reminder history
  - `user_settings` - Configuration data

### Data Fields
- Daily login status and time
- Study duration in minutes  
- Lessons completed
- Streak calculations
- Progress trends

## Troubleshooting

### Common Issues

1. **Email Connection Fails**:
   - Verify ProtonMail Bridge is running
   - Check Bridge credentials are correct
   - Ensure IMAP port (143) is accessible

2. **Web Automation Fails**:
   - Check if Synthesis changed their login flow
   - Verify login codes are being forwarded correctly
   - Try non-headless mode for debugging

3. **No Progress Data**:
   - Confirm email forwarding is working
   - Check if Synthesis sends progress emails
   - Verify database permissions

### Debug Mode

Enable detailed logging:
```bash
DEBUG=true LOG_LEVEL=DEBUG python src/synthesis/server.py
```

### Health Checks

Test server health:
```bash
curl http://localhost:8000/health
```

## Security Considerations

- **Email credentials** stored securely in environment variables
- **ProtonMail Bridge** provides encrypted email access
- **Database encryption** for sensitive progress data
- **Container isolation** in production deployments

## Future Enhancements

- **Real-time notifications** via WebSocket
- **Progress analytics** with charts and insights
- **Parent dashboard** integration
- **Multi-child support** for families
- **Achievement badges** and gamification

## Support

For issues specific to Synthesis Tracker:
1. Check this documentation first
2. Review Docker logs for errors
3. Test email connectivity manually
4. Create GitHub issue with detailed information