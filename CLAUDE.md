# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered voice agent that handles inbound restaurant phone calls via Twilio, takes orders using OpenAI LLM, and persists them to a database. Includes a React + TypeScript dashboard for viewing order history.

## Essential Commands

### Development

**Start the application (builds frontend + starts server):**
```bash
./start.sh
```

**Manual start:**
```bash
# Build frontend first
cd frontend && npm install && npm run build && cd ..

# Start backend server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Run database migrations:**
```bash
poetry run alembic upgrade head
```

**Create a new migration:**
```bash
poetry run alembic revision --autogenerate -m "description"
```

**Format code:**
```bash
poetry run black .
poetry run ruff check --fix .
```

**Frontend development server:**
```bash
cd frontend
npm run dev  # Hot reload on localhost:5173
```

**Frontend linting:**
```bash
cd frontend
npm run lint
```

### Testing
```bash
poetry run pytest
```

## Architecture

### Call Flow Overview

Incoming calls follow this orchestrated flow:

1. **Twilio webhook** → `/webhooks/voice/incoming`
2. **CallSessionManager** creates session, stores in-memory (module-level `_sessions` dict)
3. **AgentService** generates greeting with menu context injected into system prompt
4. **TwiML response** with `<Gather>` directive for speech collection
5. User speaks → Twilio transcribes → `/webhooks/voice/gather`
6. **CallSessionManager.process_user_speech()** orchestrates:
   - **AgentService** processes input with conversation state context
   - **OrderParser** extracts structured order from LLM JSON response
   - **OrderValidator** validates items against menu
   - **ConversationState** updated with order items and stage transitions
7. Loop continues until order complete
8. **Persistence services** save call and order to database
9. Call ends

### Key Components

**CallSessionManager** (`app/services/call_session/manager.py`)
- Central orchestrator for entire call lifecycle
- Manages in-memory session storage (production should use Redis)
- Coordinates between all services
- Handles order persistence

**AgentService** (`app/services/agent/agent.py`)
- LLM-powered conversation via OpenAI
- System prompt includes full menu context (`app/services/agent/prompt.py`)
- Returns JSON-structured responses for parsing
- Maintains conversation state across turns

**ConversationState** (`app/services/agent/state.py`)
- Tracks: transcript, current order items, conversation stage
- Stages: GREETING → TAKING_ORDER → CONFIRMING_ORDER → ORDER_COMPLETE
- Stage transitions in `app/services/agent/stage_transitions.py`

**MenuRepository** (`app/services/menu/repository.py`)
- Pluggable interface for menu data sources
- MVP uses `InMemoryMenuProvider` with YAML (`app/services/menu/data/menu.yaml`)
- To implement custom provider: extend `MenuProvider` base class

**OrderParser & OrderValidator** (`app/services/ordering/`)
- Two-stage validation: LLM semantic validation + strict menu validation
- Parser extracts structured order from agent's JSON response
- Validator checks items exist in menu and handles modifiers

**Persistence Services** (`app/services/persistence/`)
- `CallPersistenceService`: Manages call records and transcripts
- `OrderPersistenceService`: Manages orders and order_items tables

### Database Schema

- **calls**: call_sid, transcript, status, timestamps
- **orders**: linked to call_id, raw_text, structured_order (JSON)
- **order_items**: linked to order_id, item_name, quantity, modifiers (JSON)

### Session Storage

**Critical architectural detail**: Call sessions are stored in module-level `_sessions: Dict[str, CallSession] = {}` in `app/services/call_session/manager.py`. This is in-memory only and will not persist across:
- Server restarts
- Multiple server instances (load balancing)
- Deployments

For production multi-restaurant or distributed systems, migrate to Redis or similar.

### Frontend Architecture

Built with Vite + React + TypeScript:
- Source: `frontend/src/`
- Build output: `app/static/` (served by FastAPI)
- Auto-refreshes order history every 30 seconds
- API endpoint: `GET /api/orders/history`

## Configuration

### Environment Variables

Required in `.env`:
- `OPENAI_API_KEY` - For LLM and Whisper STT
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `DATABASE_URL` - PostgreSQL or SQLite
- `RESTAURANT_NAME` - Used in agent greeting

### Menu Configuration

Edit `app/services/menu/data/menu.yaml`:
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

To use database-backed menus: implement `MenuProvider` interface in `app/services/menu/base.py`.

### Agent Behavior Customization

Modify system prompt: `app/services/agent/prompt.py`
Adjust LLM parameters (temperature, model): `app/services/agent/agent.py`

## API Endpoints

- `GET /` - Frontend dashboard
- `GET /health` - Health check
- `GET /api/orders/history` - JSON API for order history
- `GET /api/menu` - Current menu data
- `POST /webhooks/voice/incoming` - Twilio incoming call webhook
- `POST /webhooks/voice/gather` - Twilio speech input webhook
- `POST /webhooks/voice/status` - Twilio call status webhook

## Deployment Notes

### Railway Deployment

The app is configured for Railway deployment:
- `railway.json` - Railway configuration
- `Procfile` - Process definitions
- `nixpacks.toml` - Nixpacks build configuration
- `build.sh` - Frontend build script

**Important**: On startup, `app/main.py` calls `reset_db()` which **wipes all data**. Remove this for production.

### Database Migrations on Deploy

Ensure migrations run after deployment:
```bash
railway run alembic upgrade head
```

Or add to Railway build command in `railway.json`.

## Important Implementation Details

1. **Database reset on startup**: `app/main.py` lifespan event calls `reset_db()` - removes all data every deployment. This is for demo purposes only.

2. **In-memory sessions**: Not suitable for production load balancing. Migrate to Redis for distributed deployments.

3. **Menu injection**: The entire menu is injected into the LLM system prompt every turn. For large menus (100+ items), consider semantic search or RAG.

4. **Order validation**: Two-pass system - LLM does semantic validation first, then strict parser validation against menu. Failures trigger clarification responses.

5. **Frontend static serving**: FastAPI serves pre-built frontend from `app/static/`. Must run `npm run build` before starting server or use `./start.sh`.

6. **Twilio webhook URLs**: Must be publicly accessible. Use ngrok for local development:
   ```bash
   ngrok http 8000
   ```
   Then update Twilio console with ngrok URL.
