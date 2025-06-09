# Synthesis MCP Server

A Model Context Protocol (MCP) server for tracking study progress on Synthesis.com, designed for family learning management and AI assistant integration.

## Overview

The Synthesis MCP server provides AI assistants (like Whiskers in Open WebUI) with instant access to Synthesis.com study progress through automated background data collection. It monitors both email notifications and web dashboard data to provide comprehensive learning analytics.

## Architecture

The Synthesis MCP server provides AI assistants with fast, cached access to Synthesis.com study progress through automated background data collection:

1. **Background Scheduler**: Automated data collection every 5-30 minutes
2. **Email Monitoring**: Processes login codes and progress notifications automatically  
3. **Web Automation**: Playwright scrapes dashboard data on schedule, not on-demand
4. **Data Persistence**: SQLite database stores progress history and analytics
5. **Instant MCP Responses**: All tools return cached data for sub-second response times

### Performance Design

- **Email checks**: Every 5 minutes for real-time updates
- **Web scraping**: Every 30 minutes for comprehensive data
- **Health checks**: Daily at 8 AM and 8 PM
- **MCP tool responses**: Instant (cached data only)
- **Force update**: Triggers immediate background collection

## Available Tools

The server provides 6 MCP tools for AI assistant integration:

### 1. `check_synthesis_login`
Check if the user has logged into Synthesis.com today.

**Returns:**
```json
{
  "logged_in_today": true,
  "study_minutes": 45,
  "has_studied": true,
  "last_check": "2024-01-15T14:30:00",
  "streak": 7
}
```

### 2. `get_study_progress`
Get detailed study progress for today or a specific date.

**Parameters:**
- `date` (optional): Date to check (YYYY-MM-DD format)

**Returns:**
```json
{
  "date": "2024-01-15",
  "logged_in": true,
  "login_time": "14:00:00",
  "study_minutes": 45,
  "lessons_completed": ["Blasting Through Numbers in the Cosmos!", "Math Mastery and Memory Magic!"],
  "last_activity": "15:30:00",
  "streak_days": 7,
  "total_points": 1250
}
```

### 3. `get_weekly_summary`
Get weekly study summary and statistics.

**Returns:**
```json
{
  "week_summary": {
    "total_minutes": 315,
    "days_logged_in": 5,
    "avg_minutes": 63
  },
  "current_streak": 7,
  "weekly_goal_minutes": 350,
  "goal_progress_percent": 90.0,
  "average_session": 63.0,
  "recommendations": "Amazing! You're on a 7-day streak! Keep it going!"
}
```

### 4. `send_study_reminder`
Create a study reminder notification if the user hasn't studied today.

**Parameters:**
- `custom_message` (optional): Custom reminder text

**Returns:**
```json
{
  "reminder_sent": true,
  "message": "Good morning! Time for some Synthesis math practice! 🧮",
  "current_streak": 6,
  "todays_reminder_count": 1
}
```

### 5. `get_current_streak`
Get the current study streak in days with recent activity.

**Returns:**
```json
{
  "current_streak": 7,
  "recent_activity": [
    {
      "date": "2024-01-15",
      "studied": true,
      "minutes": 45
    }
  ]
}
```

### 6. `force_update_progress`
Trigger immediate background data collection and return updated progress.

**Returns:**
```json
{
  "success": true,
  "message": "Data collection completed successfully",
  "data": {
    "study_minutes": 45,
    "lessons_completed": 2,
    "last_activity": "15:30:00",
    "streak_days": 7,
    "data_sources": {
      "email_processed": true,
      "web_scraped": true
    }
  }
}
```

### 7. `get_synthesis_newsletter`
Get the latest Synthesis newsletter to see upcoming activities and events.

**Returns:**
```json
{
  "newsletter_available": true,
  "newsletter": {
    "subject": "This Week at Synthesis",
    "date": "2024-01-14",
    "preview": "This week we're featuring...",
    "full_content": "Full newsletter content..."
  },
  "total_newsletters": 3,
  "message": "Latest Synthesis newsletter content available for AI context"
}
```

### 8. `get_subscription_status`
Get Synthesis subscription status and recent payment history.

**Returns:**
```json
{
  "subscription_active": "active",
  "latest_payment": {
    "date": "2024-01-22",
    "amount": 35.0,
    "plan_type": "Tutor Monthly",
    "days_ago": 8
  },
  "payment_history": {
    "total_payments": 6,
    "total_spent": 210.0,
    "average_payment": 35.0,
    "recent_payments": [
      {
        "date": "2024-01-22",
        "amount": 35.0,
        "plan_type": "Tutor Monthly"
      }
    ]
  },
  "message": "Found 6 payments in the last 90 days"
}
```

## Setup

### Prerequisites

1. **Email Account**: Set up email forwarding from Synthesis.com to your email account (Gmail, Outlook, etc.)
2. **IMAP Access**: Ensure your email provider supports IMAP access
3. **Synthesis.com Account**: Active account with email notifications enabled

### Environment Variables

1. **Copy the example configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual credentials:**
   ```bash
   # Email Configuration (Gmail example)
   EMAIL_SERVER=imap.gmail.com
   EMAIL_PORT=993
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_USE_SSL=true

   # Synthesis.com Account
   SYNTHESIS_EMAIL=your-synthesis-email@domain.com

   # Database
   DATABASE_PATH=./data/synthesis.db

   # Browser Settings
   HEADLESS_BROWSER=true

   # Study Goals
   STUDY_GOAL_MINUTES=50
   MINIMUM_STUDY_MINUTES=20
   ```

3. **Email Provider Setup:**
   - **Gmail**: Enable 2FA and create an [app-specific password](https://myaccount.google.com/apppasswords)
   - **Outlook**: Use `outlook.office365.com:993` and generate an app password
   - **Other providers**: Most support IMAP on port 993 with SSL

**Note**: The `.env` file is automatically ignored by Git to keep your credentials secure.

### Installation

#### Option 1: Docker (Recommended)

1. **Start Synthesis server:**
   ```bash
   cd docker
   docker-compose up synthesis -d
   ```

#### Option 2: Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Run the server:**
   ```bash
   export PYTHONPATH="$(pwd)/src"
   python src/synthesis/server.py
   ```

### Integration with Open WebUI

1. **Install mcpo (MCP-to-OpenAPI proxy):**
   ```bash
   npm install -g @open-webui/mcpo
   ```

2. **Configure mcpo:**
   ```json
   {
     "servers": [
       {
         "name": "synthesis",
         "command": "python",
         "args": ["/path/to/mcp-servers/src/synthesis/server.py"],
         "env": {},
         "timeout": 30000
       }
     ]
   }
   ```

3. **Start mcpo:**
   ```bash
   mcpo --config mcpo-config.json
   ```

4. **Add tools to Open WebUI:**
   - Go to Admin Panel → Settings → Tools
   - Add mcpo endpoint: `http://localhost:3000`
   - Import Synthesis tools

## Data Sources

The server collects data from multiple sources for comprehensive tracking:

### Email Monitoring
- **Login codes**: 6-digit codes sent by Synthesis for authentication
- **Progress emails**: Daily/weekly progress reports from Synthesis
- **Study reminders**: Automated from Synthesis platform

### Web Dashboard Scraping
- **Session data**: Login times, study duration, logout times
- **Lesson progress**: Completed lessons, current topics, skill levels
- **Performance metrics**: Points earned, streak tracking, achievement badges
- **Calendar data**: Study schedule, missed sessions, consistency metrics

### Data Processing
- **Email parsing**: Extracts study time, lesson completion from notification emails
- **Web scraping**: Comprehensive dashboard data collection via Playwright
- **Data merging**: Combines email and web sources for complete picture
- **Validation**: Cross-references multiple sources for accuracy

## Troubleshooting

### Common Issues

1. **No login codes received:**
   - Verify email forwarding is set up correctly in Synthesis.com
   - Check email server connection and IMAP settings
   - Ensure email credentials are correct (use app passwords for Gmail)

2. **Web scraping fails:**
   - Check if Synthesis.com changed their login flow
   - Verify Playwright browser installation
   - Check network connectivity

3. **Database errors:**
   - Ensure write permissions for database directory
   - Check disk space availability
   - Verify SQLite installation

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
DEBUG=true LOG_LEVEL=DEBUG python src/synthesis/server.py
```

### Health Checks

The server includes built-in health monitoring:

- **Email connectivity**: Tests IMAP connection every morning
- **Database integrity**: Validates data consistency daily
- **Background processes**: Monitors scheduler health
- **Data freshness**: Alerts if data becomes stale

## Development

### Testing

```bash
# Run all tests
export PYTHONPATH="$(pwd)/src"
python -m pytest src/synthesis/tests/ -v

# Test specific functionality
python -m pytest src/synthesis/tests/test_server.py -v

# Test Docker build
docker build -f docker/Dockerfile.synthesis -t synthesis-test .
```

### Code Quality

```bash
# Format code
black src/synthesis/
isort src/synthesis/

# Lint code
flake8 src/synthesis/
```

## Security Considerations

- **Email credentials**: Stored in environment variables, never in code
- **Browser automation**: Runs in headless mode by default
- **Data storage**: Local SQLite database, no cloud transmission
- **Network isolation**: Docker containers use isolated networks
- **App passwords**: Use app-specific passwords for enhanced email security

## License

MIT License - see root LICENSE file for details.

---

## Support

For issues specific to the Synthesis MCP server:
1. Check the troubleshooting section above
2. Review logs for error messages
3. Create GitHub issue with detailed reproduction steps
4. Include relevant log snippets (remove sensitive data)