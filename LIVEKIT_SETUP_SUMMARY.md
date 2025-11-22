# LiveKit Integration - Implementation Summary

## What Was Implemented

The LiveKit voice integration has been successfully added to Metatron. This enables real-time voice conversations between customers and the AI sales agent.

## Files Created

1. **`metatron/agents/minimax_tts.py`** - MiniMax TTS plugin for LiveKit
2. **`metatron/agents/voice_agent.py`** - LiveKit voice agent worker
3. **`LIVEKIT_INTEGRATION.md`** - Complete setup and usage guide

## Files Modified

1. **`metatron/pyproject.toml`** - Added LiveKit dependencies
2. **`metatron/config.py`** - Added LiveKit and MiniMax settings
3. **`metatron/schemas.py`** - Added LiveKit room schemas
4. **`metatron/api/main.py`** - Added room management endpoints
5. **`metatron/cli/main.py`** - Added voice-worker and api-server commands

## New Dependencies Added

```toml
# LiveKit integration
"livekit>=0.17.0"
"livekit-agents>=0.10.0"
"livekit-plugins-openai>=0.8.0"
"livekit-plugins-silero>=0.7.0"
# HTTP client for MiniMax API
"httpx>=0.27.0"
```

## New Environment Variables Required

Add these to your `.env` file:

```bash
# OpenAI (for Whisper STT)
OPENAI_API_KEY=sk-...

# LiveKit Cloud
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=API...
LIVEKIT_API_SECRET=...

# MiniMax TTS
MINIMAX_API_KEY=...
MINIMAX_GROUP_ID=...
MINIMAX_TTS_MODEL=speech-01-turbo
MINIMAX_VOICE_ID=male-qn-qingse
```

## New CLI Commands

```bash
# Start the API server (room management)
uv run metatron api-server

# Start the voice worker (handles voice calls)
uv run metatron voice-worker
```

## New API Endpoints

### Room Management
- `POST /rooms/create` - Create a room and get access token
- `GET /rooms` - List all active rooms
- `DELETE /rooms/{room_name}` - Delete a room

### Updated Health Check
- `GET /ping` - Now includes LiveKit, OpenAI, and MiniMax status

## Architecture

```
Frontend (your separate repo)
    ↓ (calls API to create room)
API Server (metatron api-server)
    ↓ (provides room token)
Frontend connects to LiveKit
    ↓ (WebRTC audio)
LiveKit Server (Cloud/Self-hosted)
    ↓ (audio streams)
Voice Worker (metatron voice-worker)
    ↓ (processes through pipeline)
[STT] → [Closer] → [TTS] → Audio Response
```

## Quick Start

1. **Install dependencies:**
   ```bash
   cd metatron
   uv sync
   ```

2. **Configure environment:**
   - Create/update `.env` file with required API keys
   - Get LiveKit credentials from https://cloud.livekit.io/
   - Get MiniMax API key from https://platform.minimax.chat/

3. **Start the services:**
   
   Terminal 1:
   ```bash
   uv run metatron api-server
   ```
   
   Terminal 2:
   ```bash
   uv run metatron voice-worker
   ```

4. **Test the API:**
   ```bash
   curl -X POST http://localhost:5885/rooms/create \
     -H "Content-Type: application/json" \
     -d '{"participant_name": "TestUser"}'
   ```

5. **Integrate your frontend:**
   - See `LIVEKIT_INTEGRATION.md` for frontend examples
   - Use the LiveKit client SDK in your frontend repo
   - Call `/rooms/create` to get room credentials
   - Connect to LiveKit and enable microphone

## Voice Pipeline

When a customer speaks:

1. **Silero VAD** detects voice activity
2. **OpenAI Whisper** transcribes speech to text
3. **Metatron Closer** processes through:
   - Sentiment analysis
   - Response generation
   - Evaluation
   - Personality adaptation
4. **MiniMax TTS** converts response to speech
5. **LiveKit** streams audio back to customer

## Testing

1. Start both services (API server and voice worker)
2. Open browser console and paste the test code from `LIVEKIT_INTEGRATION.md`
3. Click "Start Call" and speak
4. The agent should respond with voice

## Next Steps

- [ ] Configure your frontend to use the room creation API
- [ ] Customize the voice by changing `MINIMAX_VOICE_ID`
- [ ] Adjust conversation context in `metatron/files/*.txt`
- [ ] Add authentication to protect the API endpoints
- [ ] Monitor calls using LiveKit dashboard

## Documentation

For detailed setup, configuration, troubleshooting, and frontend integration examples, see **`LIVEKIT_INTEGRATION.md`**.

## Notes

- The integration works with your existing FastAPI structure
- No separate server needed - room management is part of the main API
- Voice worker runs independently and connects to LiveKit
- Frontend is in a separate repo and uses standard LiveKit client SDK
- All Metatron pipeline logic (sentiment, generation, evaluation, adaptation) is preserved

