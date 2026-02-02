# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered voice agent that handles inbound restaurant phone calls via Twilio, takes orders using OpenAI LLM, and persists them to a database. Includes a password-protected React + TypeScript dashboard for viewing order history, metrics, and managing the menu.

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
- **Password-protected**: All dashboard routes require authentication
- **Three main tabs**: Metrics, Order History, Menu Editor
- Auto-refreshes order history every 30 seconds
- Session-based authentication with HTTP-only cookies

### Authentication System

**Backend** (`app/api/auth.py`):
- Session-based auth with in-memory session storage (use Redis in production)
- Sessions expire after 24 hours
- HTTP-only cookies for security
- `require_auth()` dependency protects dashboard and API routes

**Protected Routes**:
- Dashboard (`/`) - Requires login
- All `/api/orders/*` endpoints
- All `/api/menu/*` endpoints (except GET for agent access)

**Unprotected Routes**:
- `/api/auth/login`, `/api/auth/logout`, `/api/auth/session`
- `/health` - Health check
- `/webhooks/*` - Twilio webhooks (must be publicly accessible)

**Session Storage**: Module-level `_sessions` dict in `app/api/auth.py`. For production with multiple instances, migrate to Redis.

## Configuration

### Environment Variables

Required in `.env`:
- `OPENAI_API_KEY` - For LLM and Whisper STT
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- `DATABASE_URL` - PostgreSQL or SQLite
- `RESTAURANT_NAME` - Used in agent greeting

**Optional Configuration** (defaults provided):
- `DASHBOARD_PASSWORD` - Password for dashboard access (default: `admin123`)
- `SESSION_SECRET_KEY` - Secret key for session signing (default: insecure, change for production)
- `TAX_RATE` - Sales tax rate as decimal (default: `0.0925` = 9.25%)

**Example .env**:
```env
DASHBOARD_PASSWORD=my-secure-password
SESSION_SECRET_KEY=$(openssl rand -hex 32)  # Generate random secret
TAX_RATE=0.0925  # 9.25% sales tax
```

### Menu Configuration

**Two ways to manage the menu:**

1. **UI Editor (Recommended)**: Login to dashboard → Menu tab → Add/Edit/Delete items
   - Changes persist immediately to `menu.yaml`
   - No server restart needed
   - Categories auto-update based on items

2. **Manual YAML editing**: Edit `app/services/menu/data/menu.yaml`:
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

**Menu Management API** (`app/api/menu.py`):
- `POST /api/menu/items` - Create new item
- `PUT /api/menu/items/{item_name}` - Update item
- `DELETE /api/menu/items/{item_name}` - Delete item
- All operations save to YAML immediately via `InMemoryMenuProvider._save_menu()`

**Custom Menu Provider**: Implement `MenuProvider` interface in `app/services/menu/base.py` for database-backed menus.

### Agent Behavior Customization

Modify system prompt: `app/services/agent/prompt.py`
Adjust LLM parameters (temperature, model): `app/services/agent/agent.py`

## API Endpoints

### Public Endpoints
- `GET /health` - Health check
- `POST /api/auth/login` - Login with password
- `POST /api/auth/logout` - Logout and clear session
- `GET /api/auth/session` - Check current session status
- `POST /webhooks/voice/incoming` - Twilio incoming call webhook
- `POST /webhooks/voice/gather` - Twilio speech input webhook
- `POST /webhooks/voice/status` - Twilio call status webhook

### Protected Endpoints (Require Authentication)
- `GET /` - Frontend dashboard
- `GET /login` - Login page (redirects if already authenticated)
- `GET /api/orders/history` - JSON API for order history
- `GET /api/menu` - Current menu data
- `POST /api/menu/items` - Create menu item
- `PUT /api/menu/items/{item_name}` - Update menu item
- `DELETE /api/menu/items/{item_name}` - Delete menu item

## Deployment Notes

### Railway Deployment

The app is configured for Railway deployment:
- `railway.json` - Railway configuration
- `Procfile` - Process definitions
- `nixpacks.toml` - Nixpacks build configuration
- `build.sh` - Frontend build script

### Database Migrations on Deploy

Ensure migrations run after deployment:
```bash
railway run alembic upgrade head
```

Or add to Railway build command in `railway.json`.

## Important Implementation Details

1. **Authentication sessions**: Stored in-memory (`app/api/auth.py`). For production with multiple server instances, migrate to Redis. Sessions expire after 24 hours.

2. **In-memory call sessions**: Not suitable for production load balancing. Migrate to Redis for distributed deployments.

3. **Menu injection**: The entire menu is injected into the LLM system prompt every turn. For large menus (100+ items), consider semantic search or RAG.

4. **Order validation**: Two-pass system - LLM does semantic validation first, then strict parser validation against menu. Failures trigger clarification responses.

5. **Frontend static serving**: FastAPI serves pre-built frontend from `app/static/`. Must run `npm run build` before starting server or use `./start.sh`.

6. **Menu persistence**: Changes made via UI editor save immediately to `menu.yaml`. The agent picks up changes on next call (no restart needed due to dynamic loading).

7. **Twilio webhook URLs**: Must be publicly accessible. Use ngrok for local development:
   ```bash
   ngrok http 8000
   ```
   Then update Twilio console with ngrok URL.

## Dashboard Usage

### First Time Setup

1. **Build frontend**: `cd frontend && npm install && npm run build && cd ..`
2. **Set password**: Add `DASHBOARD_PASSWORD=your-password` to `.env`
3. **Start server**: `./start.sh` or `poetry run uvicorn app.main:app --reload`
4. **Access dashboard**: Visit `http://localhost:8000`
5. **Login**: Enter your password (default: `admin123`)

### Menu Management

**Via UI (Recommended)**:
1. Login to dashboard
2. Click "Menu" tab
3. Click "+ Add New Item" to create items
4. Click "✏️ Edit" on any item to modify
5. Click "🗑️ Delete" to remove items
6. Changes save immediately and persist to `menu.yaml`

**Item Fields**:
- **Name** (required): Item identifier (e.g., "cheeseburger")
- **Description**: Shown to customers in future features
- **Price** (required): Item price in dollars
- **Category** (required): Group items (e.g., "burgers", "sides", "drinks")
- **Options**: Modifiers/customizations (e.g., "no onions", "extra cheese", "large")

**Tips**:
- Categories are created automatically when you add items
- Options are suggested to customers during ordering
- Keep item names lowercase and simple for better LLM recognition
- Delete unused categories by removing all items in that category
