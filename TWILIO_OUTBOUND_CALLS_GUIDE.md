# Twilio + LiveKit Outbound Calls Guide

Complete guide for enabling your Metatron API to make outbound phone calls using Twilio and LiveKit.

## Prerequisites

✅ You have:
- Twilio account with credits
- LiveKit Cloud account (or self-hosted)
- Metatron API already running

## Architecture

```
Your API → LiveKit SIP Service → Twilio SIP Trunk → Phone Call
```

## Step 1: Configure Twilio SIP Trunk

### 1.1 Get Your Twilio Number

You should already have a phone number. Find it at:
- Twilio Console → Phone Numbers → Manage → Active Numbers
- Note the number (e.g., `+15551234567`)

### 1.2 Create Elastic SIP Trunk

1. Go to **Twilio Console** → **Elastic SIP Trunking** → **Trunks**
2. Click **Create new SIP Trunk**
3. Name it: `livekit-outbound`
4. Click **Create**

### 1.3 Configure Trunk Settings

In your new trunk:

**Termination:**
1. Go to **Termination** tab
2. Click **Add new Termination SIP URI**
3. Enter LiveKit's SIP URI (get from LiveKit dashboard)
4. Priority: `10`
5. Weight: `10`
6. Save

**Origination:**
1. Go to **Origination** tab
2. You can skip this for outbound-only calls

**Numbers:**
1. Go to **Numbers** tab
2. Click **Add Existing Number**
3. Select your phone number
4. Click **Add Selected**

### 1.4 Get Credentials

Note these from your trunk:
- **SIP Trunk Domain**: Usually `youraccount.pstn.twilio.com`
- **Account SID**: Found in Twilio Console dashboard
- **Auth Token**: Found in Twilio Console dashboard

## Step 2: Configure LiveKit SIP

### 2.1 Get LiveKit SIP Access

**If using LiveKit Cloud:**
- SIP is available on Pro plan or higher
- Contact LiveKit sales if you need to upgrade

**If self-hosting:**
- You'll need to deploy the LiveKit SIP service separately
- See: https://github.com/livekit/sip

### 2.2 Create Outbound SIP Trunk in LiveKit

Using LiveKit API (add this to your setup script):

```python
# setup_livekit_sip.py
import asyncio
from livekit import api

async def setup_sip_trunk():
    # Initialize LiveKit API
    lk_api = api.LiveKitAPI(
        url="https://your-project.livekit.cloud",  # Your LiveKit URL
        api_key="YOUR_LIVEKIT_API_KEY",
        api_secret="YOUR_LIVEKIT_API_SECRET"
    )
    
    # Create outbound SIP trunk
    trunk_request = api.CreateSIPOutboundTrunkRequest(
        trunk=api.SIPOutboundTrunkInfo(
            name="twilio-outbound",
            address="youraccount.pstn.twilio.com",  # Your Twilio SIP domain
            numbers=["+15551234567"],  # Your Twilio number
            auth_username="YOUR_TWILIO_ACCOUNT_SID",
            auth_password="YOUR_TWILIO_AUTH_TOKEN",
            transport=api.SIPTransport.SIP_TRANSPORT_TCP
        )
    )
    
    trunk = await lk_api.sip.create_sip_outbound_trunk(trunk_request)
    print(f"✅ Created SIP trunk: {trunk.sip_trunk_id}")
    print(f"   Name: {trunk.name}")
    print(f"   Numbers: {trunk.numbers}")
    
    return trunk.sip_trunk_id

if __name__ == "__main__":
    trunk_id = asyncio.run(setup_sip_trunk())
    print(f"\n📋 Save this trunk ID: {trunk_id}")
    print("   Add it to your .env as: LIVEKIT_SIP_TRUNK_ID")
```

Run it:
```bash
uv run python setup_livekit_sip.py
```

Save the trunk ID that gets printed.

## Step 3: Update Metatron Configuration

### 3.1 Add Environment Variables

Add to `metatron/.env`:

```bash
# Existing configs...

# Twilio (for reference)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+15551234567

# LiveKit SIP
LIVEKIT_SIP_TRUNK_ID=ST_xxxxx  # From Step 2.2
```

### 3.2 Update Config Schema

Add to `metatron/config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # LiveKit SIP
    livekit_sip_trunk_id: Optional[str] = Field(default=None, alias="LIVEKIT_SIP_TRUNK_ID")
```

## Step 4: Add Outbound Call Schema

Add to `metatron/schemas.py`:

```python
class MakeCallRequest(BaseModel):
    """Request to make an outbound call."""
    phone_number: str = Field(..., description="Phone number to call (E.164 format: +1234567890)")
    room_name: Optional[str] = Field(default=None, description="Room name (auto-generated if not provided)")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata for the call")


class MakeCallResponse(BaseModel):
    """Response from making an outbound call."""
    call_id: str = Field(..., description="Unique identifier for the call")
    room_name: str = Field(..., description="LiveKit room name")
    phone_number: str = Field(..., description="Phone number being called")
    status: str = Field(..., description="Call status")
```

## Step 5: Add Outbound Call Endpoint

Add to `metatron/api/main.py`:

```python
@router.post(
    "/calls/outbound",
    response_model=MakeCallResponse,
    summary="Make outbound call",
    description="Initiate an outbound call to a phone number",
    tags=["LiveKit"],
)
async def make_outbound_call(request: MakeCallRequest) -> MakeCallResponse:
    """
    Initiate an outbound phone call.
    
    The voice agent will automatically join the call when it connects.
    """
    if not LIVEKIT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="LiveKit SDK not installed"
        )
    
    if not settings.livekit_url or not settings.livekit_api_key or not settings.livekit_api_secret:
        raise HTTPException(
            status_code=503,
            detail="LiveKit not configured"
        )
    
    if not settings.livekit_sip_trunk_id:
        raise HTTPException(
            status_code=503,
            detail="LiveKit SIP trunk not configured. Set LIVEKIT_SIP_TRUNK_ID in .env"
        )
    
    try:
        # Generate unique room name if not provided
        room_name = request.room_name or f"call-{secrets.token_hex(6)}"
        
        logger.info(f"Initiating outbound call to {request.phone_number} in room {room_name}")
        
        # Create LiveKit API client
        lk_api = livekit_api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret,
        )
        
        # Create room first
        await lk_api.room.create_room(
            livekit_api.CreateRoomRequest(
                name=room_name,
                empty_timeout=600,  # 10 minutes
                max_participants=2,  # Phone participant + Agent
            )
        )
        
        logger.info(f"Created room: {room_name}")
        
        # Create SIP participant (initiates the call)
        sip_request = livekit_api.CreateSIPParticipantRequest(
            sip_trunk_id=settings.livekit_sip_trunk_id,
            sip_call_to=request.phone_number,
            room_name=room_name,
            participant_identity=f"phone-{request.phone_number.replace('+', '')}",
            participant_name=f"Call to {request.phone_number}",
            participant_metadata=json.dumps(request.metadata or {}),
            dtmf="",  # No DTMF to send initially
            play_ringtone=True,  # Play ringtone while connecting
            hide_phone_number=False,  # Show caller ID
        )
        
        sip_participant = await lk_api.sip.create_sip_participant(sip_request)
        
        logger.info(f"✅ Outbound call initiated: {sip_participant.participant_id}")
        
        return MakeCallResponse(
            call_id=sip_participant.participant_id,
            room_name=room_name,
            phone_number=request.phone_number,
            status="initiated"
        )
        
    except Exception as e:
        logger.error(f"Error making outbound call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")
```

## Step 6: Update Voice Agent for Outbound Calls

The voice agent already handles participants joining, but you may want to customize the greeting for outbound calls.

Update `metatron/agents/voice_agent.py`:

```python
async def entrypoint(self, ctx: JobContext):
    """Entry point - handles both inbound and outbound calls."""
    logger.info(f"Voice agent joining room: {ctx.room.name}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    participant = await ctx.wait_for_participant()
    
    # Check if this is an outbound call (phone participant joined first)
    is_outbound = "phone-" in participant.identity or "call-" in ctx.room.name
    
    logger.info(f"Participant joined: {participant.identity} (outbound: {is_outbound})")
    
    # ... rest of setup code ...
    
    # Different greeting for outbound vs inbound
    if is_outbound:
        greeting = "Hola, le llamo de parte de nuestra empresa. ¿Tiene un momento para hablar?"
    else:
        greeting = "Hola, gracias por llamar. Soy tu asesor de ventas. ¿En qué puedo ayudarte hoy?"
    
    await assistant.say(greeting, allow_interruptions=True)
```

## Step 7: Test the Integration

### 7.1 Start Services

**Terminal 1 - API Server:**
```bash
uv run metatron api-server
```

**Terminal 2 - Voice Worker:**
```bash
uv run metatron voice-worker
```

### 7.2 Make a Test Call

```bash
curl -X POST http://localhost:5885/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "metadata": {"campaign": "test"}
  }'
```

Expected response:
```json
{
  "call_id": "PA_xxxxx",
  "room_name": "call-abc123",
  "phone_number": "+1234567890",
  "status": "initiated"
}
```

### 7.3 Monitor the Call

Check the voice worker terminal for:
```
Voice agent joining room: call-abc123
Participant joined: phone-1234567890 (outbound: True)
MiniMax TTS: Synthesizing text...
```

## Usage Examples

### Python Client

```python
import httpx

async def make_sales_call(phone_number: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:5885/calls/outbound",
            json={
                "phone_number": phone_number,
                "metadata": {
                    "campaign": "Q4_sales",
                    "lead_id": "12345"
                }
            }
        )
        return response.json()

# Usage
result = await make_sales_call("+15551234567")
print(f"Call initiated: {result['call_id']}")
```

### JavaScript/TypeScript

```typescript
async function makeSalesCall(phoneNumber: string) {
  const response = await fetch('http://localhost:5885/calls/outbound', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone_number: phoneNumber,
      metadata: { campaign: 'Q4_sales' }
    })
  });
  
  return await response.json();
}

// Usage
const result = await makeSalesCall('+15551234567');
console.log(`Call initiated: ${result.call_id}`);
```

## Cost Breakdown

### Per Call Costs (5-minute call):
- **Twilio**: ~$0.013 per minute = $0.065
- **OpenAI Whisper**: ~$0.006 per minute = $0.030
- **MiniMax TTS**: ~$0.002 per minute = $0.010
- **Groq LLM**: Negligible (fast inference)
- **Total**: ~$0.105 per 5-minute call

### Monthly Costs:
- **Twilio Number**: $1/month
- **LiveKit Cloud Pro**: $50/month (for SIP)
- **100 calls/month (5 min avg)**: ~$10.50

**Total**: ~$61.50/month base + per-call costs

## Troubleshooting

### "SIP trunk not found"
- Verify `LIVEKIT_SIP_TRUNK_ID` is set correctly
- Check trunk was created successfully in Step 2.2

### "Call fails immediately"
- Check Twilio account has credits
- Verify phone number is in E.164 format (+1234567890)
- Check Twilio SIP trunk configuration

### "Voice agent doesn't join"
- Ensure voice worker is running
- Check voice worker logs for errors
- Verify room was created successfully

### "No audio"
- Check MiniMax API key is valid
- Verify OpenAI API key is configured
- Check voice worker logs for TTS errors

## Advanced: Webhook for Call Status

To track call status (answered, busy, no-answer):

1. Add webhook endpoint to your API:

```python
@router.post("/webhooks/livekit/call-status")
async def call_status_webhook(request: Request):
    """Receive call status updates from LiveKit."""
    payload = await request.json()
    
    event = payload.get("event")
    room_name = payload.get("room", {}).get("name")
    participant = payload.get("participant", {})
    
    logger.info(f"Call status update: {event} in {room_name}")
    
    if event == "participant_joined":
        logger.info(f"Call answered: {participant.get('identity')}")
    elif event == "participant_disconnected":
        logger.info(f"Call ended: {participant.get('identity')}")
    
    return {"status": "ok"}
```

2. Configure webhook in LiveKit dashboard:
   - URL: `https://your-domain.com/webhooks/livekit/call-status`
   - Events: `participant_joined`, `participant_disconnected`

## Next Steps

- [ ] Add call recording
- [ ] Implement call queuing for multiple simultaneous calls
- [ ] Add call analytics/reporting
- [ ] Integrate with CRM to log calls
- [ ] Add DTMF support for IVR menus
- [ ] Implement call transfer functionality

## Security Considerations

1. **Validate phone numbers** before calling (prevent toll fraud)
2. **Rate limit** the outbound call endpoint
3. **Authenticate** API requests (add JWT/API key)
4. **Restrict** which numbers can be called (whitelist/blacklist)
5. **Monitor** call costs and set alerts
6. **Log** all calls for compliance

## Compliance

Ensure you comply with:
- **TCPA** (US): Get consent before calling
- **GDPR** (EU): Handle call data properly
- **Local regulations**: Check your jurisdiction's requirements
- **Do Not Call** lists: Maintain and respect them

## Summary

You now have:
✅ Twilio SIP trunk configured
✅ LiveKit SIP integration set up
✅ API endpoint to make outbound calls
✅ Voice agent that handles outbound calls
✅ Complete testing workflow

To make a call, simply:
```bash
POST /calls/outbound
{
  "phone_number": "+1234567890"
}
```

The system will:
1. Create a LiveKit room
2. Initiate call via Twilio
3. Voice agent joins when call connects
4. Conversation flows through your Closer pipeline
5. Natural voice interaction via MiniMax TTS

