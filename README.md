# AI Ops Desk

> **AI-powered operations desk for shared inbox automation**

Automates Gmail + Google Calendar scheduling and FAQ support for UK B2B agencies and service businesses.

## Overview

AI Ops Desk is a multi-agent AI system that handles routine inbox operations:
- **Scheduling**: Automatically proposes meeting times based on calendar availability
- **Support**: Answers FAQ questions using knowledge base retrieval
- **Quality Assurance**: Guardrails decide whether to auto-send, draft, or escalate responses

## Architecture

Built on a **centralized orchestrator pattern** with specialized agents:

1. **Ingestion Agent**: Fetches and normalizes incoming messages
2. **Triage Agent**: Classifies intent (scheduling, support, billing, etc.) and priority
3. **Worker Agents**:
   - `admin_scheduling_agent`: Finds available slots and drafts scheduling replies
   - `support_faq_agent`: Searches knowledge base and drafts support answers
4. **QA Guardrail Agent**: Risk-scores responses and decides: `AUTO_SEND`, `DRAFT_ONLY`, or `ESCALATE`

All agents share a single `WorkflowPayload` that carries message context, classification, actions, and tenant configuration through the pipeline.

## Project Structure

```
ai-ops-desk/
├── schemas.py           # Data models (WorkflowPayload, Intent, QADecision, etc.)
├── agents.py            # All 5 agent functions
├── orchestrator.py      # FastAPI service coordinating agent execution
├── connectors/
│   ├── gmail.py         # Gmail API integration (fetch threads, send replies)
│   └── calendar.py      # Google Calendar API (find slots, create events)
├── tests/
│   └── test_orchestration.py  # Unit and E2E tests
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Setup

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Gmail & Google Calendar API credentials
- OpenAI or Anthropic API key (for LLM triage and drafting)

### 2. Installation

```bash
git clone https://github.com/labgadget015-dotcom/ai-ops-desk.git
cd ai-ops-desk
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/ai_ops_desk

# Google APIs
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REFRESH_TOKEN=your-refresh-token

# LLM Provider
OPENAI_API_KEY=sk-...
# OR
# ANTHROPIC_API_KEY=sk-ant-...

# Tenant Configuration
DEFAULT_TIMEZONE=Europe/London
WORKING_HOURS_START=9
WORKING_HOURS_END=17
```

### 4. Database Setup

```bash
alembic upgrade head
```

## Usage

### Run the Orchestrator Service

```bash
uvicorn orchestrator:app --reload --port 8000
```

### API Endpoints

**POST** `/workflows/incoming-message`

Submit a new email for processing:

```json
{
  "tenant_id": "agency-001",
  "source": {
    "channel": "gmail",
    "thread_id": "1234abcd",
    "message_id": "msg-5678"
  },
  "contact": {
    "email": "client@example.com",
    "name": "Jane Doe"
  },
  "message": {
    "subject": "Meeting request",
    "body_text": "Can we schedule a call next week?",
    "received_at": "2025-01-15T10:30:00Z",
    "message_id": "msg-5678",
    "thread_id": "1234abcd"
  },
  "tenant_config": {
    "tenant_id": "agency-001",
    "auto_send_enabled": false,
    "escalation_threshold": 0.7
  }
}
```

Response:

```json
{
  "workflow_id": "wf-uuid-1234",
  "decision": "draft_only",
  "status": "ok"
}
```

**GET** `/workflows/{workflow_id}`

Retrieve workflow state for debugging and audit.

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Adding New Agents

1. Define agent function in `agents.py` following the signature:
   ```python
   def my_agent(payload: WorkflowPayload) -> AgentOutput:
       ...
   ```
2. Wire it into the orchestrator chain in `orchestrator.py`
3. Add unit tests in `tests/test_orchestration.py`

### Connector Implementation

The `connectors/` directory contains placeholder functions. Implement:
- `gmail.py`: `fetch_gmail_thread()`, `send_reply()`
- `calendar.py`: `find_calendar_slots()`, `create_event()`

Refer to Google API documentation for authentication and usage.

## Roadmap

- [ ] Implement full Gmail & Calendar connectors
- [ ] Add LLM provider integrations (OpenAI, Anthropic)
- [ ] Build knowledge base search (vector DB)
- [ ] Create admin dashboard for workflow monitoring
- [ ] Add multi-tenant isolation and role-based access
- [ ] Support for Outlook/Exchange calendars
- [ ] Slack integration for notifications

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Contact

For questions or support, open an issue on GitHub.
