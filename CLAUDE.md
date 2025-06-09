# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This repository contains a collection of Model Context Protocol (MCP) servers focused on educational platforms and family learning management. The architecture follows the official MCP servers pattern with educational-specific enhancements.

### Core Architecture Components

**MCP Base Classes**: All servers inherit from `MCPBaseServer` in `src/shared/mcp_base.py`, which provides standardized MCP protocol handling, tool registration, and error management.

**Multi-Modal Data Collection**: Educational platforms lack APIs, so servers use hybrid approaches:
- Email monitoring for authentication codes and progress notifications
- Web automation via Playwright for dashboard scraping
- SQLite databases for persistent progress tracking and analytics

**Container Orchestration**: Each MCP server runs in its own container with shared dependencies (ProtonMail Bridge for secure email access) managed via Docker Compose.

### Synthesis Tracker Architecture

The flagship server (`src/synthesis/`) demonstrates the full architecture pattern:

1. **Email Integration Layer** (`shared/email_utils.py`): Monitors ProtonMail via Bridge for both login codes and daily progress emails from Synthesis.com
2. **Web Automation Layer** (`synthesis/synthesis_client.py`): Playwright-based browser automation for dashboard data extraction when email parsing isn't sufficient
3. **Data Persistence Layer** (`shared/storage_utils.py`): SQLite database with session tracking, streak calculations, and progress analytics
4. **MCP Protocol Layer** (`synthesis/server.py`): 6 standardized tools for AI assistant integration

## Development Commands

### Local Development
```bash
# Install dependencies and setup
pip install -r requirements.txt
playwright install chromium

# Set up environment
cp .env.example .env
# Edit .env with ProtonMail credentials and Synthesis account details

# Run MCP server directly
export PYTHONPATH="$(pwd)/src"
python src/synthesis/server.py

# Run with debug logging
DEBUG=true LOG_LEVEL=DEBUG python src/synthesis/server.py
```

### Testing
```bash
# Run all tests
export PYTHONPATH="$(pwd)/src"
python -m pytest src/ -v

# Run specific server tests
python -m pytest src/synthesis/tests/ -v

# Test Docker build
docker build -f docker/Dockerfile.synthesis -t synthesis-test .
```

### Docker Development
```bash
# Start full stack (ProtonMail Bridge + MCP server)
cd docker
docker-compose up -d

# View logs
docker-compose logs -f synthesis-tracker

# Initialize ProtonMail Bridge (first time)
docker run --rm -it -v protonmail:/root shenxn/protonmail-bridge init

# Rebuild and restart specific service
docker-compose build synthesis-tracker
docker-compose restart synthesis-tracker
```

### Code Quality
```bash
# Format code
black src/
isort src/

# Lint code
flake8 src/
```

## Key Design Patterns

### Email-First Data Collection
Educational platforms rarely provide APIs. The architecture prioritizes email monitoring as the primary data source since platforms reliably send progress emails. Web scraping serves as backup/supplemental data collection.

### Environment-Driven Configuration
All servers use `config.py` modules that read from environment variables. This enables the same codebase to work in development (direct Python), Docker containers, and production deployments without code changes.

### Shared Utility Design
Common functionality (email parsing, database operations, notifications) lives in `src/shared/` to be reused across multiple educational platform integrations. New MCP servers should extend these utilities rather than reinventing them.

### MCP Tool Granularity
Each server provides 4-6 focused tools rather than one monolithic interface. This allows AI assistants to be more precise in their data requests and enables better caching/optimization.

## Integration Points

### Open WebUI Integration
MCP servers integrate with Open WebUI via the `mcpo` (MCP-to-OpenAPI) proxy. Configuration lives in `mcpo-config.json`. The proxy converts MCP protocol calls to REST API endpoints that Open WebUI can consume.

### ProtonMail Bridge Dependency
All servers requiring email access depend on the ProtonMail Bridge container for secure IMAP/SMTP access. The Bridge provides localhost endpoints that bypass ProtonMail's encryption requirements while maintaining security.

### Database Sharing Strategy
Each server maintains its own SQLite database, but shared utilities in `storage_utils.py` provide consistent schemas and cross-server analytics capabilities. Future servers can query data from other servers for comprehensive family learning insights.

## Adding New Educational Platform Servers

1. Create directory in `src/[platform-name]/`
2. Implement `server.py` inheriting from `MCPBaseServer`
3. Add platform-specific client class for data collection
4. Use shared utilities for email, database, and notifications
5. Add Docker configuration in `docker/Dockerfile.[platform-name]`
6. Update `docker-compose.yml` with new service
7. Add comprehensive documentation in `docs/[platform-name].md`

The architecture is designed to make adding new educational platforms straightforward while maintaining consistency and reusability across all MCP servers.