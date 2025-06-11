# Synthesis MCP Server

A simplified Model Context Protocol (MCP) server for tracking study progress on Synthesis.com through email monitoring, designed for AI assistant integration with Open WebUI.

## Overview

The Synthesis MCP server provides AI assistants with direct access to Synthesis.com study progress by monitoring email notifications. This architecture returns human-readable responses that AI assistants can easily interpret, without requiring complex parsing or database management.

## Architecture

The server provides a lightweight, email-focused approach:

1. **Direct Email Access**: Connects to ProtonMail Bridge or IMAP servers to fetch emails on-demand
2. **Human-Readable Responses**: Returns formatted text that AI assistants can immediately understand
3. **No Background Processing**: Fetches emails only when requested (typically 0.3s response time)
4. **No Database**: Stateless operation - emails are the source of truth
5. **Flexible Parameters**: AI can request specific time ranges and email counts

### Performance Design

- **Email fetching**: On-demand via IMAP (average 0.3 seconds)
- **Response format**: Human-readable text with email content
- **Parameter flexibility**: Configurable days/limit per request
- **Maximum safety**: 50 email limit to prevent large responses

## Available Tools

The server provides 5 MCP tools optimized for AI assistant interaction:

### 1. `get_study_progress`
Get Synthesis.com study session emails showing time spent and activities.

**Parameters:**
- `limit`: Number of emails to return (1-50, default: 10)
- `since_days`: Days to look back (default: 7)

**Frequency**: Session emails arrive 2-4 times per week after each study session.

**Returns:**
```
Found 3 email(s) from the last 7 days:

**Email 1:**
Subject: Nineveh's Synthesis Session: Stellar Skip Counting Success!
From: Synthesis Tutor <no-reply@tutor.synthesis.com>
Date: Tue, 10 Jun 2025 13:43:51 +0000
Preview: I had a productive session with Nineveh during our Cosmic Quest lesson. Nineveh successfully navigated number patterns by skip counting...

==================================================

**Email 2:**
Subject: Nineveh's Synthesis Session: Math Mastery and Memory Magic!
From: Synthesis Tutor <no-reply@tutor.synthesis.com>
Date: Mon, 09 Jun 2025 15:45:00 +0000
Preview: Nineveh impressed by earning both the Treasure Seeker and Rising Star achievements, showcasing speed and accuracy with addition facts...

==================================================
```

### 2. `get_login_codes`
Get Synthesis login verification emails containing 4-digit codes.

**Parameters:**
- `limit`: Number of emails to return (1-50, default: 1)
- `since_days`: Days to look back (default: 1)

**Frequency**: Sent on-demand when logging in. Codes expire after 2 hours.

**Returns:**
```
Found 1 email(s) from the last 1 days:

**Email 1:**
Subject: Login for Synthesis Tutor
From: Synthesis Tutor <no-reply@tutor.synthesis.com>
Date: Tue, 10 Jun 2025 22:12:41 +0000
Preview: Here's your log in verification code: 5045...
**LOGIN CODE: 1234**

==================================================
```

### 3. `get_subscription_status`
Get Synthesis payment and subscription emails.

**Parameters:**
- `limit`: Number of emails to return (1-50, default: 3)
- `since_days`: Days to look back (default: 35)

**Frequency**: Monthly for subscriptions or when payments are processed.

**Returns:**
```
Found 1 email(s) from the last 35 days:

**Email 1:**
Subject: Payment Confirmation for Synthesis Tutor
From: Synthesis <billing@synthesis.com>
Date: Tue, 01 Jun 2025 10:30:00 +0000
Preview: Your payment of $35.00 has been processed successfully for your Tutor Monthly subscription...

==================================================
```

### 4. `get_synthesis_newsletter`
Get 'This Week at Synthesis' newsletters with upcoming activities.

**Parameters:**
- `limit`: Number of emails to return (1-50, default: 2)
- `since_days`: Days to look back (default: 14)

**Frequency**: Weekly on Mondays with educational content and upcoming activities.

**Returns:**
```
Found 1 email(s) from the last 14 days:

**Email 1:**
Subject: This Week at Synthesis: Cosmic Math Adventures!
From: Synthesis Team <newsletter@synthesis.com>
Date: Mon, 08 Jun 2025 09:00:00 +0000
Preview: This week we're featuring space-themed math lessons including skip counting through the cosmos...

==================================================
```

### 5. `get_any_email`
Search for any email by subject or sender.

**Parameters:**
- `subject_contains`: Text to search for in subject (optional)
- `from_contains`: Text to search for in sender (optional)
- `limit`: Number of emails to return (1-50, default: 5)
- `since_days`: Days to look back (default: 30)

**Use Cases**: Finding CEO updates, special announcements, or specific communications.

**Returns:**
```
Found 2 email(s) from the last 30 days:

**Email 1:**
Subject: Important Update from Synthesis CEO
From: CEO Team <ceo@synthesis.com>
Date: Fri, 07 Jun 2025 16:00:00 +0000
Preview: We're excited to announce new features coming to the platform...

==================================================
```

## Repository Contents

This repository includes everything needed to run the Synthesis MCP server:

- **`synthesis-server.py`**: The main MCP server (200 lines, email-only)
- **`docker-compose.yml`**: **Scripted setup** - MCP server + MCPO proxy (for Open WebUI)
- **`docker-compose.mcp-only.yml`**: **Scripted setup** - MCP server only (for direct integration)
- **`Dockerfile`**: Container build configuration
- **`requirements.txt`**: Python dependencies
- **`mcpo-config.json`**: MCPO configuration (used by both Docker and manual setup)
- **`.env.example`**: Environment template with email settings
- **`README.md`**: Complete setup and usage documentation

## Setup

### Prerequisites

1. **ProtonMail Bridge** (recommended) or **Direct IMAP Access**
2. **Email Forwarding**: Set up forwarding from Synthesis emails to your account
3. **Synthesis.com Account**: Active account with email notifications enabled

### Environment Variables

1. **Copy the example configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your email configuration:**
   ```bash
   # ProtonMail Bridge (Recommended)
   EMAIL_SERVER=protonmail-bridge
   EMAIL_PORT=143
   EMAIL_USERNAME=your-email@proton.me
   EMAIL_PASSWORD=your-bridge-password
   EMAIL_USE_SSL=false

   # Or Direct IMAP (Gmail example)
   EMAIL_SERVER=imap.gmail.com
   EMAIL_PORT=993
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_USE_SSL=true

   # Study Goals
   STUDY_GOAL_MINUTES=300  # 5 hours per week
   MINIMUM_STUDY_MINUTES=20
   ```

### Email Provider Setup

#### ProtonMail Bridge (Recommended)
- **Security**: End-to-end encryption maintained
- **Setup**: Install ProtonMail Bridge application
- **Configuration**: Use bridge-generated password
- **Port**: 143 (no SSL with bridge)

#### Direct IMAP Providers
- **Gmail**: Enable 2FA and create an [app-specific password](https://myaccount.google.com/apppasswords)
- **Outlook**: Use `outlook.office365.com:993` and generate an app password
- **Other providers**: Most support IMAP on port 993 with SSL

### Installation

#### Option 1: Docker with MCPO (Recommended for Open WebUI)

1. **Start the complete stack:**
   ```bash
   docker-compose up synthesis-mcpo -d
   ```

2. **The MCPO proxy provides REST API endpoints:**
   - `http://localhost:8002/get_study_progress`
   - `http://localhost:8002/get_login_codes`
   - `http://localhost:8002/get_subscription_status`
   - `http://localhost:8002/get_synthesis_newsletter`
   - `http://localhost:8002/get_any_email`

#### Option 2: Local Development

1. **Install dependencies:**
   ```bash
   pip install asyncio imaplib email
   ```

2. **Run the server:**
   ```bash
   python synthesis-server.py
   ```

### Integration with Open WebUI

#### What is MCPO?

MCPO (MCP-to-OpenAPI proxy) is a tool that converts Model Context Protocol (MCP) servers into REST API endpoints that Open WebUI can consume. It acts as a bridge between:

- **MCP Protocol**: Uses stdio (JSON-RPC over stdin/stdout) 
- **REST API**: HTTP endpoints that Open WebUI expects

**MCPO Features:**
- Converts MCP tools to OpenAPI REST endpoints
- Handles authentication with API keys
- Provides automatic OpenAPI documentation
- Manages CORS for web integration

#### Option A: Using Docker (Recommended)

Choose one of two Docker configurations:

**A1. MCP Server + MCPO Proxy (for Open WebUI integration):**
```bash
cp .env.example .env
# Edit .env with your email settings
docker-compose up -d
```

**A2. MCP Server Only (for direct MCP integration):**
```bash
cp .env.example .env
# Edit .env with your email settings
docker-compose -f docker-compose.mcp-only.yml up -d
```

**For Open WebUI integration (A1):**
- Go to Admin Panel → Settings → Tools
- Add endpoint: `http://localhost:8002`
- Set API key: `synthesis-mcpo-key-2024` *(safe for localhost)*
- Import Synthesis tools

#### Option B: Manual MCPO Setup

If you want to run MCPO manually:

1. **Install MCPO:**
   ```bash
   npm install -g @open-webui/mcpo
   ```

2. **Configure environment variables:**
   ```bash
   export EMAIL_SERVER=your-email-server
   export EMAIL_USERNAME=your-email
   export EMAIL_PASSWORD=your-password
   # ... other environment variables
   ```

3. **Start MCPO with included config:**
   ```bash
   mcpo --config mcpo-config.json --port 8002 --api-key synthesis-mcpo-key-2024
   ```

   The included `mcpo-config.json` reads environment variables from your shell.

#### Testing the Integration

```bash
curl -X POST "http://localhost:8002/get_study_progress" \
  -H "Authorization: Bearer synthesis-mcpo-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"limit": 3, "since_days": 7}'
```

## What is Synthesis.com?

[Synthesis](https://synthesis.com) is an AI-powered online learning platform that provides:

- **Collaborative Games**: Team-based learning experiences for children ages 8-14
- **AI Tutoring**: Personalized 1-on-1 sessions with AI tutors
- **Skill Development**: Focus on problem-solving, communication, and critical thinking
- **Progress Tracking**: Detailed analytics and achievement systems
- **Parent Visibility**: Email notifications and dashboard insights

The platform combines traditional educational content with modern gamification and AI assistance to create engaging learning experiences.

## Email Forwarding Setup

To monitor your child's progress, set up email forwarding:

1. **In Synthesis.com settings:**
   - Enable all email notifications
   - Set notification frequency to "After each session"

2. **Forward to your monitoring email:**
   - Use Outlook rules, Gmail filters, or provider forwarding
   - Forward all emails from `*@synthesis.com` to your monitored account

3. **Verify forwarding:**
   - Complete a Synthesis session
   - Check that session emails arrive in your monitored account

## Troubleshooting

### Common Issues

1. **No emails found:**
   - Verify email forwarding is working
   - Check IMAP server settings and credentials
   - Test with longer time ranges (`since_days: 30`)

2. **Authentication errors:**
   - Use app-specific passwords for Gmail/Outlook
   - For ProtonMail Bridge, use bridge-generated password
   - Verify server and port settings

3. **Login codes not extracted:**
   - Check email content manually
   - Login codes are automatically extracted from email body
   - Ensure emails contain the standard Synthesis format

### Debug Mode

Enable detailed logging:
```bash
DEBUG=true python synthesis-server.py
```

### Test Email Connection

```bash
# Test IMAP connection directly
curl -X POST "http://localhost:8002/get_any_email" \
  -H "Authorization: Bearer synthesis-mcpo-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"subject_contains": "synthesis", "limit": 5, "since_days": 30}'
```

## Architecture Benefits

### Why Simplified?

1. **AI-Friendly**: Returns human-readable text that AI assistants can immediately interpret
2. **Fast Performance**: 0.3s average response time for email fetching
3. **Stateless**: No database to maintain or sync
4. **Flexible**: AI can request exactly what it needs
5. **Reliable**: Emails are the authoritative source of truth

### Comparison to Complex Systems

| Feature | Simplified | Background Processing |
|---------|------------|---------------------|
| Response Time | 0.3s | Instant (cached) |
| Setup Complexity | Low | High |
| Data Freshness | Always current | May be stale |
| Resource Usage | Low | High (background jobs) |
| Maintenance | Minimal | Database management |
| AI Integration | Natural text | JSON parsing |

## Security Considerations

- **Email credentials**: Stored in environment variables only
- **ProtonMail encryption**: End-to-end encryption maintained with Bridge
- **No data persistence**: No local storage of sensitive information
- **IMAP isolation**: Connections are temporary and per-request
- **API authentication**: Bearer token required for MCPO endpoints

## Development

### Adding New Email Types

1. **Update email search patterns** in `synthesis-server.py`
2. **Add new tool** with appropriate subject filters
3. **Update descriptions** with frequency information
4. **Test with real email data**

### Code Structure

```
synthesis-server.py          # Main MCP server (200 lines)
├── SimpleEmailMonitor       # IMAP connection and search
├── SimpleSynthesisMCPServer # MCP protocol handling
└── Tool implementations     # 5 email-fetching tools
```

## License

MIT License - see root LICENSE file for details.

---

## Support

For issues with the Synthesis MCP server:
1. Check email forwarding and IMAP connectivity
2. Review troubleshooting section above
3. Test with direct curl commands
4. Create GitHub issue with log output (remove credentials)
