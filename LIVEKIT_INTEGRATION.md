# LiveKit Voice Integration for Metatron

This guide explains how to set up and use the LiveKit voice integration for real-time voice conversations with the Metatron sales agent.

## Overview

The LiveKit integration enables real-time voice calls between customers and the Metatron AI sales agent. The system uses:

- **LiveKit Cloud/Self-hosted**: Real-time communication infrastructure
- **OpenAI Whisper**: Speech-to-Text (STT) for transcribing customer speech
- **MiniMax**: Text-to-Speech (TTS) for agent voice responses
- **Groq**: LLM processing for the Closer pipeline
- **Metatron Closer**: Sales conversation logic and pipeline

## Architecture

```
┌─────────────────────┐
│  Frontend Client    │
│  (your repo)        │
└──────────┬──────────┘
           │ WebRTC
           ▼
┌─────────────────────┐
│  LiveKit Server     │
│  (Cloud/Self-host)  │
└──────────┬──────────┘
           │ Audio Streams
           ▼
┌─────────────────────┐
│ Metatron Voice      │
│ Agent (Worker)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│         Voice Processing Pipeline           │
├─────────────────────────────────────────────┤
│ STT (Whisper) → Closer Pipeline → TTS      │
│                                             │
│ Customer Speech → Text → AI Analysis →     │
│ Response Generation → Voice Output          │
└─────────────────────────────────────────────┘
```

## Prerequisites

### 1. LiveKit Server

You need access to a LiveKit server. Choose one:

#### Option A: LiveKit Cloud (Recommended for getting started)

1. Sign up at [LiveKit Cloud](https://cloud.livekit.io/)
2. Create a new project
3. Note your credentials:
   - `LIVEKIT_URL` (e.g., `wss://your-project.livekit.cloud`)
   - `LIVEKIT_API_KEY` (e.g., `APIxxxxx`)
   - `LIVEKIT_API_SECRET`

#### Option B: Self-Hosted LiveKit

1. Install LiveKit server:
   ```bash
   # macOS
   brew install livekit
   
   # Linux
   curl -sSL https://get.livekit.io | bash
   
   # Docker
   docker run -d -p 7880:7880 -p 7881:7881 -p 7882:7882/udp \
     livekit/livekit-server --dev
   ```

2. For development, use:
   - `LIVEKIT_URL=ws://localhost:7880`
   - `LIVEKIT_API_KEY=devkey`
   - `LIVEKIT_API_SECRET=secret`

### 2. API Keys

You'll need API keys for:

- **OpenAI** (for Whisper STT): Get from [OpenAI Platform](https://platform.openai.com/)
- **MiniMax** (for TTS): Get from [MiniMax Platform](https://platform.minimax.chat/)
- **Groq** (already configured for LLM): Get from [Groq Console](https://console.groq.com/)

## Installation

### 1. Install Dependencies

```bash
# From the metatron directory
uv sync
```

This will install all required packages including:
- `livekit>=0.17.0`
- `livekit-agents>=0.10.0`
- `livekit-plugins-openai>=0.8.0`
- `livekit-plugins-silero>=0.7.0`
- `httpx>=0.27.0`

### 2. Configure Environment Variables

Create or update your `.env` file in the `metatron/` directory:

```bash
# Groq (already configured)
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b

# OpenAI (for Whisper STT)
OPENAI_API_KEY=sk-...

# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=API...
LIVEKIT_API_SECRET=...

# MiniMax TTS Configuration
MINIMAX_API_KEY=...
MINIMAX_GROUP_ID=...
MINIMAX_TTS_MODEL=speech-01-turbo
MINIMAX_VOICE_ID=male-qn-qingse

# Server Configuration (optional)
HOST=0.0.0.0
PORT=5885
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Available MiniMax Voice IDs

Choose a voice that fits your sales agent persona:

**Spanish Voices:**
- `male-qn-qingse` - Male, clear and professional
- `female-shaonv` - Female, warm and friendly
- `male-qn-jingying` - Male, energetic
- `female-yujie` - Female, mature and confident

For more voices, check the [MiniMax documentation](https://platform.minimax.chat/document/guides/voice-overview).

## Running the System

The system consists of two components that run independently:

### 1. Start the API Server (for room management)

The API server handles room creation and provides access tokens to clients:

```bash
# Option 1: Using CLI command
uv run metatron api-server

# Option 2: Direct Python execution
uv run python -m metatron.main

# Option 3: Using uvicorn directly
uv run uvicorn metatron.main:app --host 0.0.0.0 --port 5885
```

The server will start at `http://localhost:5885` with:
- API docs: http://localhost:5885/docs
- Health check: http://localhost:5885/ping

### 2. Start the Voice Worker (processes voice calls)

The voice worker connects to LiveKit and handles voice conversations:

```bash
uv run metatron voice-worker
```

You should see:
```
🎙️  METATRON VOICE WORKER
================================================================================

✓ LiveKit URL: wss://your-project.livekit.cloud
✓ OpenAI API: Configured
✓ MiniMax API: Configured
✓ Groq API: Configured

Waiting for connections...
```

**Keep both terminals running** for the full system to work.

## API Endpoints

### Health Check

```bash
GET /ping
```

Response:
```json
{
  "message": "pong",
  "status": "ok",
  "environment": "development",
  "livekit_configured": true,
  "openai_configured": true,
  "minimax_configured": true
}
```

### Create Room and Get Token

```bash
POST /rooms/create
Content-Type: application/json

{
  "participant_name": "Juan Pérez",
  "room_name": "optional-room-name",
  "metadata": {"customer_id": "12345"}
}
```

Response:
```json
{
  "room_name": "sales-abc123",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "url": "wss://your-project.livekit.cloud"
}
```

### List Active Rooms

```bash
GET /rooms
```

Response:
```json
{
  "rooms": [
    {
      "name": "sales-abc123",
      "num_participants": 2,
      "creation_time": 1700000000
    }
  ]
}
```

### Delete Room

```bash
DELETE /rooms/{room_name}
```

## Frontend Integration

Your frontend (in the separate repo) needs to:

1. **Call the API to create a room**
2. **Connect to LiveKit using the provided token**
3. **Enable microphone for the user**

### Example Frontend Code (React/TypeScript)

```typescript
import { Room, RoomEvent, Track } from 'livekit-client';

async function startVoiceCall(participantName: string) {
  // 1. Create room and get token from Metatron API
  const response = await fetch('http://localhost:5885/rooms/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      participant_name: participantName 
    })
  });
  
  const { room_name, token, url } = await response.json();
  
  // 2. Connect to LiveKit room
  const room = new Room();
  
  // 3. Set up event handlers
  room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
    if (track.kind === Track.Kind.Audio) {
      // Attach agent's audio to play it
      const audioElement = track.attach();
      document.body.appendChild(audioElement);
    }
  });
  
  room.on(RoomEvent.Disconnected, () => {
    console.log('Disconnected from room');
  });
  
  // 4. Connect to the room
  await room.connect(url, token);
  
  // 5. Enable user's microphone
  await room.localParticipant.setMicrophoneEnabled(true);
  
  console.log('Connected to voice call!');
  
  return room;
}

// Usage
const room = await startVoiceCall('Cliente');

// To disconnect later
await room.disconnect();
```

### Example Frontend Code (Vanilla JavaScript)

```html
<!DOCTYPE html>
<html>
<head>
  <title>Metatron Voice Call</title>
  <script src="https://unpkg.com/livekit-client/dist/livekit-client.umd.min.js"></script>
</head>
<body>
  <button id="startCall">Iniciar Llamada</button>
  <button id="endCall" disabled>Terminar Llamada</button>
  <div id="status">Desconectado</div>

  <script>
    const API_URL = 'http://localhost:5885';
    let room = null;
    
    document.getElementById('startCall').addEventListener('click', async () => {
      try {
        // Create room
        const response = await fetch(`${API_URL}/rooms/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ participant_name: 'Cliente' })
        });
        
        const data = await response.json();
        
        // Connect to LiveKit
        room = new LivekitClient.Room();
        
        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track) => {
          if (track.kind === LivekitClient.Track.Kind.Audio) {
            const audio = track.attach();
            document.body.appendChild(audio);
          }
        });
        
        await room.connect(data.url, data.token);
        await room.localParticipant.setMicrophoneEnabled(true);
        
        document.getElementById('status').textContent = '🟢 Conectado';
        document.getElementById('startCall').disabled = true;
        document.getElementById('endCall').disabled = false;
        
      } catch (error) {
        console.error('Error:', error);
        document.getElementById('status').textContent = '❌ Error: ' + error.message;
      }
    });
    
    document.getElementById('endCall').addEventListener('click', async () => {
      if (room) {
        await room.disconnect();
        document.getElementById('status').textContent = 'Desconectado';
        document.getElementById('startCall').disabled = false;
        document.getElementById('endCall').disabled = true;
      }
    });
  </script>
</body>
</html>
```

## Testing

### 1. Test the API

```bash
# Test health check
curl http://localhost:5885/ping

# Create a test room
curl -X POST http://localhost:5885/rooms/create \
  -H "Content-Type: application/json" \
  -d '{"participant_name": "TestUser"}'

# List rooms
curl http://localhost:5885/rooms
```

### 2. Test Voice Connection

With both the API server and voice worker running:

1. Open your frontend application
2. Click "Start Call" or equivalent
3. Speak into your microphone
4. The agent should respond with voice

Check the voice worker terminal for logs showing:
- Participant joined
- Audio processing
- Response generation

## Conversation Flow

When a customer speaks:

1. **Voice Activity Detection (VAD)**: Silero VAD detects when the customer is speaking
2. **Speech-to-Text**: OpenAI Whisper transcribes the audio to text
3. **Sentiment Analysis**: Metatron analyzes the customer's sentiment and intent
4. **Response Generation**: Multiple response options are generated
5. **Evaluation**: Best response is selected based on sales strategy
6. **Personality Adaptation**: Response is adapted to match the salesman's voice
7. **Text-to-Speech**: MiniMax converts the text to natural speech
8. **Audio Playback**: Speech is sent back to the customer via LiveKit

## Troubleshooting

### Voice Worker Errors

**"OPENAI_API_KEY not configured"**
- Add `OPENAI_API_KEY=sk-...` to your `.env` file

**"MINIMAX_API_KEY not configured"**
- Add `MINIMAX_API_KEY=...` and `MINIMAX_GROUP_ID=...` to your `.env` file

**"LiveKit not configured"**
- Ensure `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` are set

### Connection Issues

**Agent doesn't join the room**
- Check that the voice worker is running
- Verify LiveKit credentials are correct
- Check voice worker logs for errors

**No audio from agent**
- Check browser console for errors
- Ensure audio element is properly attached
- Verify MiniMax API is working (check voice worker logs)

**Audio cutting out**
- Check network connectivity
- Increase `empty_timeout` in room creation
- Check LiveKit server resources

### API Errors

**503 Service Unavailable**
- LiveKit SDK may not be installed: `uv sync`
- LiveKit credentials not configured

**500 Internal Server Error**
- Check API server logs for details
- Verify all services are running
- Check database connection if applicable

## Production Deployment

### Environment Variables

For production, ensure:

```bash
ENVIRONMENT=production
DEBUG=false
RELOAD=false
LOG_LEVEL=warning

# Use production LiveKit URL
LIVEKIT_URL=wss://your-production.livekit.cloud

# Secure your endpoints
# Add authentication/authorization
```

### Docker Deployment

The provided `docker-compose.yml` already includes LiveKit environment variables:

```yaml
services:
  metatron:
    environment:
      LIVEKIT_URL: ${LIVEKIT_URL}
      LIVEKIT_API_KEY: ${LIVEKIT_API_KEY}
      LIVEKIT_API_SECRET: ${LIVEKIT_API_SECRET}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      MINIMAX_API_KEY: ${MINIMAX_API_KEY}
      MINIMAX_GROUP_ID: ${MINIMAX_GROUP_ID}
```

### Running with Docker

```bash
# Build and start services
docker-compose up -d

# Start voice worker separately (not in docker-compose by default)
uv run metatron voice-worker
```

### Security Considerations

1. **Never expose API keys** in client-side code
2. **Implement authentication** for the `/rooms/create` endpoint
3. **Rate limit** room creation to prevent abuse
4. **Validate participant identities** before creating tokens
5. **Use HTTPS/WSS** in production
6. **Set proper CORS** origins in `metatron/main.py`

## Monitoring and Logs

### Voice Worker Logs

The voice worker logs important events:
- Participant connections/disconnections
- Audio processing steps
- Errors in the pipeline

### API Server Logs

Check FastAPI logs for:
- Room creation requests
- Token generation
- API errors

### LiveKit Dashboard

If using LiveKit Cloud, use the dashboard to monitor:
- Active rooms
- Participant count
- Audio quality metrics
- Bandwidth usage

## Advanced Configuration

### Custom Voice Settings

Adjust MiniMax TTS parameters in `.env`:

```bash
MINIMAX_TTS_MODEL=speech-01        # Higher quality, slower
MINIMAX_TTS_MODEL=speech-01-turbo  # Faster, good quality

MINIMAX_VOICE_ID=male-qn-qingse    # Professional male
MINIMAX_VOICE_ID=female-shaonv      # Warm female
```

### Conversation Stages

The Closer automatically tracks conversation stages:
- `inicio` - Initial greeting
- `negociacion` - Negotiation phase
- `cierre` - Closing phase

The agent adapts its strategy based on the current stage.

### Custom Context

Modify the context files in `metatron/files/`:
- `salesman_context.txt` - Agent personality and style
- `product_context.txt` - Product information
- `lead_context.txt` - Lead qualification criteria
- `close_context.txt` - Closing strategies

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify all environment variables are set
3. Ensure all services are running
4. Review the [LiveKit documentation](https://docs.livekit.io/)

## Next Steps

- [ ] Implement authentication for room creation
- [ ] Add conversation analytics
- [ ] Implement call recording
- [ ] Add support for multiple languages
- [ ] Create admin dashboard for monitoring calls

