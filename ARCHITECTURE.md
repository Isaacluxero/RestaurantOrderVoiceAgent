# Architecture Overview

## System Components

### 1. Call Flow

```
Incoming Call (Twilio)
    ↓
/webhooks/voice/incoming
    ↓
CallSessionManager.create_session()
    ↓
AgentService.get_greeting()
    ↓
TwiML Response (with Gather)
    ↓
User Speaks
    ↓
/webhooks/voice/gather
    ↓
CallSessionManager.process_user_speech()
    ↓
AgentService.process_user_input()
    ↓
OrderParser.parse_agent_action()
    ↓
OrderValidator.validate_item()
    ↓
Update ConversationState
    ↓
Generate TwiML Response
    ↓
[Loop until order complete]
    ↓
Persist Order
    ↓
End Call
```

### 2. Service Layer

#### CallSessionManager
- Orchestrates the entire call flow
- Manages conversation state
- Coordinates between all services
- Handles order persistence

#### AgentService
- LLM-powered conversation handling
- Maintains conversation context
- Generates natural responses
- Determines user intent

#### MenuRepository
- Provides menu data to agent
- Validates menu items
- Pluggable interface for different menu sources

#### OrderParser & OrderValidator
- Parses agent actions into structured orders
- Validates items against menu
- Handles modifiers and quantities

#### Speech Services (STT/TTS)
- STT: Transcribes audio (using OpenAI Whisper via Twilio)
- TTS: Generates TwiML for speech output

#### Persistence Services
- CallPersistenceService: Manages call records
- OrderPersistenceService: Manages orders and order items

### 3. Database Schema

```
calls
├── id (PK)
├── call_sid (unique)
├── started_at
├── ended_at
├── status
└── transcript

orders
├── id (PK)
├── call_id (FK -> calls.id)
├── status
├── raw_text
├── structured_order (JSON)
└── created_at

order_items
├── id (PK)
├── order_id (FK -> orders.id)
├── item_name
├── quantity
└── modifiers (JSON)
```

### 4. Key Design Decisions

#### Pluggable Menu System
- `MenuProvider` interface allows swapping menu sources
- MVP uses `InMemoryMenuProvider` with YAML
- Future: Database-backed, POS-integrated, per-restaurant menus

#### Conversation State Management
- In-memory for MVP (single restaurant)
- State includes transcript, current order, stage
- Future: Redis for distributed systems

#### LLM Agent Design
- System prompt includes menu context
- JSON-structured responses for parsing
- State injected every turn for context

#### Order Validation
- Two-stage: LLM validates semantically, parser validates against menu
- Graceful error handling with clarification requests

### 5. Extension Points

#### Custom Menu Provider
```python
class CustomMenuProvider(MenuProvider):
    async def get_menu(self) -> Menu:
        # Your implementation
        pass
```

#### Custom Agent Behavior
- Modify `app/services/agent/prompt.py` for different agent personalities
- Adjust temperature and model in `AgentService`

#### Additional Persistence
- Add new tables in `app/db/models.py`
- Create corresponding persistence services

### 6. Environment Variables

Required:
- `OPENAI_API_KEY` - For LLM and speech services
- `TWILIO_ACCOUNT_SID` - Twilio account
- `TWILIO_AUTH_TOKEN` - Twilio authentication
- `TWILIO_PHONE_NUMBER` - Twilio phone number
- `DATABASE_URL` - Database connection string
- `RESTAURANT_NAME` - Restaurant name for agent

Optional:
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)

### 7. API Endpoints

All endpoints are under `/webhooks/voice/`:

- `POST /incoming` - Handles incoming calls
- `POST /gather` - Handles speech input
- `POST /status` - Handles call status updates

### 8. Future Enhancements

- Multi-restaurant support (session storage in Redis)
- POS system integration
- Admin dashboard for menu management
- Call analytics and reporting
- SMS order confirmation
- Human handoff capability
- Payment processing
- Delivery tracking

