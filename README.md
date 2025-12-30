# AI Voice Agent for Restaurant Order Taking

An AI-powered voice agent that answers phone calls, takes orders, and persists them to a database.

## Features

- Inbound call handling via Twilio
- Speech-to-text and text-to-speech
- LLM-powered conversation agent
- Pluggable menu system
- Order parsing and validation
- Database persistence
- React + TypeScript frontend dashboard for viewing order history

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
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

**Quick Start (Builds frontend and starts server):**
```bash
./start.sh
```

**Manual Start:**
```bash
# First, build the frontend
cd frontend
npm install
npm run build
cd ..

# Then start the server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

After starting, visit `http://localhost:8000` to view the order history dashboard.

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

## Frontend

The application includes a React + TypeScript frontend dashboard for viewing order history. The frontend:

- Displays all calls with their orders
- Shows call transcripts, status, and timestamps
- Lists order items with quantities and modifiers
- Auto-refreshes every 30 seconds
- Modern, responsive design

The frontend is built using Vite and served statically by the FastAPI backend.

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

- `GET /` - Frontend dashboard (order history)
- `GET /health` - Health check
- `GET /api/orders/history` - Get all calls with orders (JSON API)
- `POST /webhooks/voice/incoming` - Twilio webhook for incoming calls
- `POST /webhooks/voice/gather` - Twilio webhook for speech input
- `POST /webhooks/voice/status` - Twilio webhook for call status updates

## Database Schema

- **calls**: Call metadata and transcripts
- **orders**: Order records linked to calls
- **order_items**: Individual items in each order

## Deployment

### Railway Deployment

1. **Install Railway CLI** (optional):
   ```bash
   npm install -g @railway/cli
   ```

2. **Create a Railway account** at [railway.app](https://railway.app)

3. **Connect your repository**:
   - Go to Railway dashboard
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

4. **Add Environment Variables** in Railway dashboard:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
   - `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token
   - `TWILIO_PHONE_NUMBER` - Your Twilio phone number (e.g., +19789972543)
   - `DATABASE_URL` - PostgreSQL connection string (Railway will auto-generate if you add a PostgreSQL service)
   - `RESTAURANT_NAME` - Name of your restaurant

5. **Add PostgreSQL Database** (recommended):
   - In Railway project, click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set the `DATABASE_URL` environment variable

6. **Deploy**:
   - Railway will automatically detect the Python app and deploy
   - The app will be available at the provided Railway URL

7. **Run Database Migrations**:
   After first deployment, run migrations via Railway CLI:
   ```bash
   railway run alembic upgrade head
   ```
   
   Or add a migration script that runs automatically on deploy by adding to `railway.json`:
   ```json
   "buildCommand": "pip install -r requirements.txt && cd frontend && npm install && npm run build && alembic upgrade head"
   ```

8. **Verify Deployment**:
   - Check the Railway logs for any errors
   - Visit your Railway URL to see the frontend
   - Test the `/health` endpoint

8. **Update Twilio Webhooks**:
   - In Twilio Console, update webhook URLs to your Railway domain:
     - **A CALL COMES IN**: `https://your-app.railway.app/webhooks/voice/incoming`
     - **CALL STATUS CHANGES**: `https://your-app.railway.app/webhooks/voice/status`

**Note**: Railway will automatically handle:
- Installing Python dependencies (from `requirements.txt`)
- Building the frontend (if you add a build command)
- Setting the PORT environment variable
- SSL/HTTPS certificates

For automatic frontend builds, you can add a build script or use Railway's build hooks.

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

