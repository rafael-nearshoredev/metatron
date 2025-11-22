# Quick Start Guide

## ✅ Your Project is Now Ready!

The structure has been fixed and all imports are working.

## Current Status

✅ Project structure corrected (pyproject.toml moved to root)
✅ All imports fixed (using metatron. prefix)
✅ CLI commands working
✅ LiveKit configured
✅ ElevenLabs TTS configured (using built-in plugin)
✅ OpenAI Whisper STT configured
✅ Voice agent updated to livekit-agents 1.3.3 API
✅ Outbound calling enabled

## Running the System

### 1. Set Your ElevenLabs API Key

Edit `.env` and add your ElevenLabs API key:

```bash
ELEVENLABS_API_KEY=your_key_here
```

Get it from: https://elevenlabs.io/

### 2. Start the Services

**Terminal 1 - API Server:**
```bash
uv run metatron api-server
```

**Terminal 2 - Voice Worker:**
```bash
uv run metatron voice-worker
```

### 3. Test the System

**Option A: WebRTC Call (Browser)**

Call this from your frontend:
```javascript
const response = await fetch('http://localhost:5885/rooms/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ participant_name: 'Customer' })
});

const { room_name, token, url } = await response.json();
// Connect with LiveKit client SDK...
```

**Option B: Outbound Phone Call**

```bash
uv run python test.py
```

Or with curl:
```bash
curl -X POST http://localhost:5885/calls/outbound \
  -H "Content-Type': 'application/json" \
  -d '{"phone_number": "+573118718353"}'
```

## Available Commands

### CLI Commands

```bash
# Start API server
uv run metatron api-server

# Start voice worker
uv run metatron voice-worker

# Run other commands
uv run metatron ping
uv run metatron chat
uv run metatron sentiment "texto a analizar"
uv run metatron adapt "texto a adaptar"
```

### API Endpoints

Once the API server is running (http://localhost:5885):

**Context Management:**
- `GET /ping` - Health check
- `GET /context/{type}` - Get context content
- `PUT /context/{type}` - Update context

**LiveKit Rooms:**
- `POST /rooms/create` - Create room for WebRTC call
- `GET /rooms` - List active rooms
- `DELETE /rooms/{name}` - Delete room
- `POST /rooms/{room_name}/agent` - Insert agent into room

**Outbound Calls:**
- `POST /calls/outbound` - Make outbound phone call

**API Docs:**
- http://localhost:5885/docs - Swagger UI
- http://localhost:5885/redoc - ReDoc

## Environment Variables Reference

Your `.env` file should have:

```bash
# OpenAI (for Whisper STT)
OPENAI_API_KEY=sk-...

# Groq (for LLM)
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b

# LiveKit
LIVEKIT_URL=wss://metatron-jwaryzej.livekit.cloud
LIVEKIT_API_KEY=API...
LIVEKIT_API_SECRET=...
LIVEKIT_SIP_TRUNK_ID=ST_...  # For outbound calls

# ElevenLabs TTS  
ELEVENLABS_API_KEY=...  # ⚠️ ADD THIS
ELEVENLABS_MODEL=eleven_turbo_v2_5
ELEVENLABS_DEFAULT_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Server
HOST=0.0.0.0
PORT=5885
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Testing Workflow

### Test 1: Health Check
```bash
curl http://localhost:5885/ping
```

Expected response:
```json
{
  "message": "pong",
  "status": "ok",
  "environment": "development",
  "livekit_configured": true,
  "openai_configured": true,
  "elevenlabs_configured": true
}
```

### Test 2: Create WebRTC Room
```bash
curl -X POST http://localhost:5885/rooms/create \
  -H "Content-Type: application/json" \
  -d '{"participant_name": "TestUser"}'
```

### Test 3: Make Outbound Call
```bash
uv run python test.py
```

## Troubleshooting

### "ElevenLabs API key not configured"
Add `ELEVENLABS_API_KEY` to your `.env` file

### "LiveKit not configured"
Verify all LIVEKIT_* vars are set in `.env`

### "Cannot connect to API server"
Make sure Terminal 1 is running the API server

### Voice agent doesn't join
Make sure Terminal 2 is running the voice worker

## Next Steps

1. ✅ Add ELEVENLABS_API_KEY to .env
2. ✅ Start both services
3. ✅ Run test.py to make a call
4. ✅ Answer your phone and talk to the agent!

The system is ready to use! 🚀

