# MCP Servers Collection

A collection of Model Context Protocol (MCP) servers for educational and family-focused AI integrations.

## Overview

This repository contains MCP servers that enable AI assistants to interact with various educational platforms and services. Each server is designed to provide secure, standardized access to different learning platforms.

## Available Servers

### 🎓 Educational Platforms

- **[Synthesis](src/synthesis/)** - Track progress on Synthesis.com math tutoring platform
- **[DuoLingo](src/duolingo/)** - Language learning progress tracking *(Coming Soon)*
- **[SimplyPiano](src/simply-piano/)** - Piano learning progress monitoring *(Coming Soon)*
- **[Outschool](src/outschool/)** - Online class management *(Coming Soon)*

### 🛠️ Shared Utilities

- **[Shared](src/shared/)** - Common utilities used across multiple MCP servers

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/BenGWeeks/mcp-servers.git
cd mcp-servers
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

### Using with Open WebUI

1. Install mcpo (MCP-to-OpenAPI proxy):
```bash
npm install -g @open-webui/mcpo
```

2. Start the MCP server:
```bash
python src/synthesis/server.py
```

3. Configure mcpo and add tools to Open WebUI as described in each server's documentation.

## Repository Structure

```
mcp-servers/
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── src/                       # MCP server implementations
│   ├── synthesis/             # Synthesis.com educational tracking
│   ├── duolingo/              # DuoLingo language learning (planned)
│   ├── simply-piano/          # SimplyPiano music learning (planned)
│   ├── outschool/             # Outschool class management (planned)
│   └── shared/                # Common utilities
├── docker/                    # Container configurations
├── docs/                      # Documentation and guides
└── .github/workflows/         # CI/CD automation
```

## Development

### Adding a New MCP Server

1. Create a new directory in `src/`
2. Follow the structure of existing servers
3. Use utilities from `src/shared/` for common functionality
4. Add documentation to `docs/`
5. Update this README

### Testing

Each server includes its own test suite. Run tests for a specific server:

```bash
python -m pytest src/synthesis/tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests:
- Create GitHub issues with detailed information
- Include server name in issue title
- Provide steps to reproduce for bugs

---

**Note**: This repository focuses on educational MCP servers that help families track learning progress across multiple platforms. Each server respects platform terms of service and prioritizes data privacy.