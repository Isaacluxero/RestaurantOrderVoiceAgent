# AI Voice Agent for Restaurant Order Taking

An AI-powered voice agent that answers phone calls, takes orders, and persists them to a database.

## Features

- Inbound call handling via Twilio
- Speech-to-text and text-to-speech
- LLM-powered conversation agent
- Pluggable menu system
- Order parsing and validation
- Database persistence

## Setup

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- PostgreSQL (or SQLite for MVP)
- OpenAI API key
- Twilio account with a phone number

### Installation

1. Install dependencies:
```bash
poetry install
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Configure your `.env` file with:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
   - `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token
   - `TWILIO_PHONE_NUMBER` - Your Twilio phone number (e.g., +1234567890)
   - `DATABASE_URL` - Database connection string
     - PostgreSQL: `postgresql://user:password@localhost:5432/voice_agent_db`
     - SQLite: `sqlite:///./voice_agent.db`
   - `RESTAURANT_NAME` - Name of your restaurant

4. Run database migrations:
```bash
poetry run alembic upgrade head
```

5. Start the server:
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Twilio Configuration

1. In your Twilio Console, go to Phone Numbers → Manage → Active Numbers
2. Select your phone number
3. Under "Voice & Fax", set the webhook URL to:
   - **A CALL COMES IN**: `https://your-domain.com/webhooks/voice/incoming`
   - **CALL STATUS CHANGES**: `https://your-domain.com/webhooks/voice/status`
4. Set HTTP method to `POST`

**For local development**, use a tool like [ngrok](https://ngrok.com/) to expose your local server:
```bash
ngrok http 8000
```
Then use the ngrok URL in your Twilio webhook configuration.

## Configuration

### Menu Configuration

The menu can be configured by editing `app/services/menu/data/menu.yaml`. The menu uses a simple YAML format:

```yaml
items:
  - name: cheeseburger
    description: Classic cheeseburger
    price: 8.99
    category: burgers
    options:
      - no onions
      - extra cheese
```

To use a custom menu provider (e.g., database-backed), implement the `MenuProvider` interface in `app/services/menu/base.py`.

## Architecture

The system is designed with a modular architecture:

- **Call Session Manager**: Orchestrates the conversation flow
- **Agent Service**: LLM-powered conversation handling
- **Menu Service**: Pluggable menu system
- **Order Parser/Validator**: Validates orders against menu
- **Persistence Layer**: Database operations for calls and orders
- **Speech Services**: STT/TTS integration

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /webhooks/voice/incoming` - Twilio webhook for incoming calls
- `POST /webhooks/voice/gather` - Twilio webhook for speech input
- `POST /webhooks/voice/status` - Twilio webhook for call status updates

## Database Schema

- **calls**: Call metadata and transcripts
- **orders**: Order records linked to calls
- **order_items**: Individual items in each order

## Development

Run tests (when implemented):
```bash
poetry run pytest
```

Format code:
```bash
poetry run black .
poetry run ruff check --fix .
```

