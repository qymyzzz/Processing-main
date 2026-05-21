# Ticket Management Bot

An intelligent Telegram bot for support ticket management and classification using AI (Google Gemini) and rule-based systems. Automate your support workflow with real-time ticket creation, AI-powered categorization, and comprehensive reporting.

## Description

This bot streamlines support team operations by automatically:
- **Classifying** incoming support requests into categories (Operational Work, Incidents, Integrations) using both AI and pattern matching
- **Creating & Managing** support tickets with real-time tracking, assignment, and status management
- **Storing** message history and ticket data reliably in AWS S3 with automatic backup
- **Generating** Excel reports and analytics for ticket data analysis
- **Scheduling** reminders for unresolved tickets to ensure timely resolution
- **Monitoring** system health and providing diagnostics

The bot bridges Telegram, Google Gemini AI, and AWS, providing a seamless experience for support teams of any size.

## Badges

![Python](https://img.shields.io/badge/Python-3.13+-blue?style=flat-square&logo=python)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)
![Telegram](https://img.shields.io/badge/Telegram-Bot-0088cc?style=flat-square&logo=telegram)
![AWS](https://img.shields.io/badge/AWS-S3-FF9900?style=flat-square&logo=amazon-aws)
![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?style=flat-square&logo=docker)

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd processing\ 5
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run
python main.py
```

## Features

### Intelligent Classification
- **AI-powered**: Google Gemini API for context-aware ticket categorization
- **Rule-based Fallback**: Fast pattern matching for reliable classification when AI is unavailable
- **Three Categories**:
  - ⚙️ Operational Work
  - 🔥 Incidents  
  - 🔗 Integrations

### Ticket Lifecycle Management
- Create tickets from Telegram messages with automatic assignment
- Track ticket status (open/resolved) in real-time
- Assign tickets to team members
- View personal and team ticket queues
- Close resolved tickets with confirmation

### Reporting & Analytics
- Generate Excel reports with detailed ticket summaries
- Query ticket history by date range
- Export ticket data for external analysis
- View metrics and statistics on ticket resolution

### Data Management
- AWS S3 integration for reliable message and ticket storage
- Automatic backup and archival of old records
- Metadata persistence with JSON storage
- Data recovery capabilities

### Team Collaboration
- Group ticket notifications
- On-duty assignment tracking
- Team member alerts for assigned tickets
- Shared ticket queue visibility

### System Reliability
- Built-in health checks and monitoring
- Comprehensive logging and diagnostics
- Graceful shutdown with data persistence
- Error recovery mechanisms

## Tech Stack

- **Python 3.13**
- **Telegram Bot API** (`python-telegram-bot`)
- **Google Genai** (AI classification)
- **AWS S3** (data storage)
- **pandas** (data processing)
- **openpyxl** (Excel generation)
- **APScheduler** (task scheduling)
- **Docker** (containerization)

## Installation

### Prerequisites
- Python 3.13+
- Docker (optional, for containerized deployment)
- AWS S3 credentials
- Google Gemini API key
- Telegram Bot token

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd processing\ 5
   ```

2. **Create a virtual environment**
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Update `.env` with:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   GEMINI_API_KEY=your_gemini_api_key
   AWS_ACCESS_KEY_ID=your_aws_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret
   AWS_REGION=your_region
   S3_BUCKET=your_bucket_name
   ```

## Usage

### Run Locally
```bash
python main.py
```

### Run with Docker
```bash
docker build -t ticket-bot .
docker run -d --env-file .env ticket-bot
```

### Available Commands
- `/start` - Initialize and get help
- `/mytickets` - View your assigned tickets
- `/tickets` - View all tickets
- `/report` - Generate ticket report
- `/duty` - Check on-duty assignments
- `/close` - Close a ticket

## Project Structure

```
├── main.py                   # Bot entry point
├── classifier.py             # AI & rule-based classification
├── categories.py             # Ticket categories
├── ticket_store.py           # Ticket storage & management
├── message_history.py        # Message history management
├── commands/                 # Telegram command handlers
│   ├── start.py
│   ├── mytickets.py
│   ├── tickets.py
│   ├── report.py
│   ├── close.py
│   ├── duty.py
│   └── claim.py
├── health_check.py           # System health monitoring
├── logging_config.py         # Logging setup
├── reminder.py               # Reminder scheduling
├── utils.py                  # Utility functions
├── sanitize.py               # Input sanitization
├── rules.py                  # Classification rules
├── tests/                    # Test suite
└── Dockerfile                # Container configuration
```

## Testing

Run tests with:
```bash
bash run_tests.sh
```

Or with pytest directly:
```bash
pytest tests/
```

Test coverage includes:
- Ticket management operations
- Classification (AI and rule-based)
- Utility functions
- Data sanitization
- Health checks

## Configuration

### Environment Variables
- `TELEGRAM_BOT_TOKEN` - Telegram Bot API token
- `GEMINI_API_KEY` - Google Gemini API key
- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `AWS_REGION` - AWS region
- `S3_BUCKET` - S3 bucket name for storage

### Logging
Configure logging levels in `logging_config.py`. Default level is INFO.

## API Integration

### Google Gemini
- Used for intelligent ticket classification
- Fallback to rule-based classification if API unavailable

### AWS S3
- Stores message history
- Stores ticket metadata
- Automatic cleanup of old records

### Telegram
- Interactive bot commands
- Real-time messaging
- Group notifications

## Deployment

### Docker
```bash
docker build -t ticket-bot:latest .
docker run --env-file .env ticket-bot:latest
```

### Health Check Endpoint
The bot exposes a health check endpoint on port 8443. Monitor this for deployment health.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `bash run_tests.sh`
4. Submit a pull request

## Troubleshooting

### Connection Issues
- Verify AWS credentials in `.env`
- Check Telegram token validity
- Ensure S3 bucket is accessible

### Classification Issues
- Check Gemini API quota and rate limits
- Review classification rules in `rules.py`
- Check logs for detailed error messages

### Data Loss
- Tickets and messages are backed up in S3
- Recovery via `s3_load_tickets()` and `s3_load_messages()`

## Roadmap

### v1.0 (Current)
- ✅ Core ticket management system
- ✅ AI and rule-based classification
- ✅ S3 storage integration
- ✅ Excel report generation
- ✅ Basic reminder system

### v1.1 (Planned)
- [ ] Custom classification rules per team
- [ ] Advanced reporting with charts
- [ ] Ticket priority levels
- [ ] SLA tracking
- [ ] Multi-language support

### v1.2 (Proposed)
- [ ] Slack integration
- [ ] Email notifications
- [ ] Advanced analytics dashboard
- [ ] Automated ticket routing
- [ ] Integration webhooks

### v2.0 (Future Vision)
- [ ] Web dashboard for ticket management
- [ ] Machine learning model training
- [ ] Custom workflow automation
- [ ] Mobile app
- [ ] Multi-channel support (Teams, Discord, etc.)

## Contributing

We welcome contributions from the community! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes with clear, descriptive commits
4. **Write or update** tests for your changes
5. **Run** the full test suite: `bash run_tests.sh`
6. **Submit** a pull request with a detailed description

### Development Guidelines
- Follow PEP 8 style guidelines
- Add docstrings to all functions
- Include tests for new features
- Update README if adding new commands/features
- Keep commits focused and atomic

### Reporting Issues
- Check existing issues before creating a new one
- Include Python version, OS, and relevant logs
- Provide steps to reproduce the issue
- Include expected vs actual behavior

## Authors and Acknowledgment

**Created by**: qymyzzz  
**Repository**: [processingkz/Processing-main](https://github.com/qymyzzz/Processing-main)

### Contributors
- Telegram bot API community
- Google Genai developers
- boto3/AWS SDK team

### Special Thanks
- The open-source Python community
- All contributors and issue reporters

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, and feature requests:
- 📝 Open an [issue on GitHub](https://github.com/qymyzzz/Processing-main/issues)
- 💬 Discuss ideas in [Pull Requests](https://github.com/qymyzzz/Processing-main/pulls)
- 📧 Contact the maintainers

## Project Status

**Status**: 🟢 **Active Development**

This project is actively maintained and in production use. Regular updates and improvements are being made based on user feedback and operational needs.

---

**Last Updated**: May 2026  
**Python Version**: 3.13+  
**Current Version**: 1.0
