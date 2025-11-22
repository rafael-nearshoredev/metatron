"""
FastAPI route definitions.
"""

from __future__ import annotations

import asyncio
import secrets
import subprocess
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from ..config import settings
from ..schemas import (
    UpdateContextRequest,
    UpdateContextResponse,
    GetContextResponse,
    ContextType,
    CreateRoomRequest,
    RoomResponse,
    RoomInfo,
    ListRoomsResponse,
    InsertAgentRequest,
    InsertAgentResponse,
    MakeCallRequest,
    MakeCallResponse,
)
# from ..services import ContextService  # TODO: Implement services
from ..utils.file_reader import (
    get_salesman_context,
    get_lead_context,
    get_product_context,
    get_close_context,
    set_salesman_context,
    set_lead_context,
    set_product_context,
    set_close_context,
)
from ..utils.logger import logger

# Import LiveKit only if configured
try:
    from livekit import api as livekit_api
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False
    logger.warning("LiveKit SDK not installed. Room management endpoints will not be available.")

router = APIRouter()


@router.get("/ping", tags=["Utils"])
async def ping() -> JSONResponse:
    """
    Simple health-check endpoint.
    """
    return JSONResponse(
        status_code=200,
        content={
            "message": "pong",
            "status": "ok",
            "environment": settings.environment,
            "livekit_configured": bool(settings.livekit_url and settings.livekit_api_key),
            "openai_configured": bool(settings.openai_api_key),
            "elevenlabs_configured": bool(settings.elevenlabs_api_key),
        },
    )



@router.get(
    "/context/{context_type}",
    response_model=GetContextResponse,
    summary="Get context content",
    description="Retrieve the current content of a context file",
    tags=["Context"],
    responses={
        200: {"description": "Context retrieved successfully"},
        404: {"description": "Context file not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_context(context_type: ContextType) -> GetContextResponse:
    """
    Get the content of a specific context file.
    
    Args:
        context_type: Type of context to retrieve (salesman, lead, product, close)
    
    Returns:
        GetContextResponse with the context content
    """
    try:
        context_getters = {
            "salesman": get_salesman_context,
            "lead": get_lead_context,
            "product": get_product_context,
            "close": get_close_context,
        }
        
        content = context_getters[context_type]()
        
        return GetContextResponse(
            context_type=context_type,
            content=content,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading context: {str(e)}")


@router.put(
    "/context/{context_type}",
    response_model=UpdateContextResponse,
    summary="Update context content",
    description="Update the content of a context file with plain text",
    tags=["Context"],
    responses={
        200: {"description": "Context updated successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal Server Error"},
    },
)
async def update_context(
    context_type: ContextType,
    request: UpdateContextRequest,
) -> UpdateContextResponse:
    """
    Update a context file with new plain text content.
    
    Args:
        context_type: Type of context to update (salesman, lead, product, close)
        request: Request body containing the new content
    
    Returns:
        UpdateContextResponse with success status and message
    """
    try:
        context_setters = {
            "salesman": set_salesman_context,
            "lead": set_lead_context,
            "product": set_product_context,
            "close": set_close_context,
        }
        
        context_setters[context_type](request.content)
        
        return UpdateContextResponse(
            success=True,
            context_type=context_type,
            message=f"Context '{context_type}' updated successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating context: {str(e)}",
        )


# LiveKit Room Management Endpoints

@router.post(
    "/rooms/create",
    response_model=RoomResponse,
    summary="Create LiveKit room",
    description="Create a new LiveKit room and generate an access token for the participant",
    tags=["LiveKit"],
    responses={
        200: {"description": "Room created successfully"},
        500: {"description": "Internal Server Error"},
        503: {"description": "LiveKit not configured"},
    },
)
async def create_room(request: CreateRoomRequest) -> RoomResponse:
    """
    Create a new LiveKit room and generate an access token.
    
    Your frontend should call this endpoint to:
    1. Create a new room
    2. Get an access token
    3. Connect to LiveKit using the token
    
    Args:
        request: CreateRoomRequest with optional room_name and participant info
    
    Returns:
        RoomResponse with room details and access token
    """
    if not LIVEKIT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="LiveKit SDK not installed. Install with: pip install livekit livekit-api"
        )
    
    if not settings.livekit_url or not settings.livekit_api_key or not settings.livekit_api_secret:
        raise HTTPException(
            status_code=503,
            detail="LiveKit not configured. Please set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET"
        )
    
    try:
        # Generate unique room name if not provided
        room_name = request.room_name or f"sales-{secrets.token_hex(6)}"
        
        logger.info(f"Creating LiveKit room: {room_name} for participant: {request.participant_name}")
        
        # Prepare room metadata with voice_id if provided
        room_metadata = {}
        if request.voice_id:
            room_metadata["voice_id"] = request.voice_id
            logger.info(f"Room will use custom voice_id: {request.voice_id}")
        
        # Merge with any additional metadata from request
        if request.metadata:
            room_metadata.update(request.metadata)
        
        # Create LiveKit API client
        lk_api = livekit_api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret,
        )
        
        try:
            # Create or get room with metadata
            import json
            room_info = await lk_api.room.create_room(
                livekit_api.CreateRoomRequest(
                    name=room_name,
                    empty_timeout=300,  # 5 minutes
                    max_participants=2,  # 1 customer + 1 agent
                    metadata=json.dumps(room_metadata) if room_metadata else "",
                )
            )
            
            logger.info(f"Room created/retrieved: {room_name}")
            
            # Generate access token for participant
            token = livekit_api.AccessToken(
                settings.livekit_api_key,
                settings.livekit_api_secret
            )
            token.with_identity(request.participant_name)
            token.with_name(request.participant_name)
            token.with_grants(
                livekit_api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            
            if request.metadata:
                token.with_metadata(str(request.metadata))
            
            jwt_token = token.to_jwt()
            
            logger.info(f"Generated access token for {request.participant_name} in room {room_name}")
            
            return RoomResponse(
                room_name=room_name,
                token=jwt_token,
                url=settings.livekit_url
            )
        finally:
            await lk_api.aclose()
        
    except Exception as e:
        logger.error(f"Error creating room: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create room: {str(e)}")


@router.get(
    "/rooms",
    response_model=ListRoomsResponse,
    summary="List active rooms",
    description="Get a list of all active LiveKit rooms",
    tags=["LiveKit"],
    responses={
        200: {"description": "Rooms retrieved successfully"},
        500: {"description": "Internal Server Error"},
        503: {"description": "LiveKit not configured"},
    },
)
async def list_rooms() -> ListRoomsResponse:
    """
    List all active LiveKit rooms.
    
    Returns:
        ListRoomsResponse with information about all active rooms
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
    
    try:
        lk_api = livekit_api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret,
        )
        
        try:
            rooms_response = await lk_api.room.list_rooms(livekit_api.ListRoomsRequest())
            
            return ListRoomsResponse(
                rooms=[
                    RoomInfo(
                        name=room.name,
                        num_participants=room.num_participants,
                        creation_time=room.creation_time,
                    )
                    for room in rooms_response.rooms
                ]
            )
        finally:
            await lk_api.aclose()
    except Exception as e:
        logger.error(f"Error listing rooms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list rooms: {str(e)}")


@router.post(
    "/rooms/{room_name}/agent",
    response_model=InsertAgentResponse,
    summary="Insert voice agent into room",
    description="Insert the Metatron voice agent into an existing LiveKit room",
    tags=["LiveKit"],
    responses={
        200: {"description": "Agent inserted successfully"},
        404: {"description": "Room not found"},
        500: {"description": "Internal Server Error"},
        503: {"description": "LiveKit not configured"},
    },
)
async def insert_agent(
    room_name: str,
    background_tasks: BackgroundTasks
) -> InsertAgentResponse:
    """
    Insert the Metatron voice agent into a LiveKit room.
    
    This endpoint will:
    1. Verify the room exists
    2. Start the voice agent in the background
    3. The agent will join the room and begin processing conversations
    
    Args:
        room_name: Name of the room to join
        background_tasks: FastAPI background tasks for async agent startup
    
    Returns:
        InsertAgentResponse with success status
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
    
    try:
        # Verify room exists
        lk_api = livekit_api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret,
        )
        
        try:
            rooms_response = await lk_api.room.list_rooms(livekit_api.ListRoomsRequest())
            room_exists = any(room.name == room_name for room in rooms_response.rooms)
            
            if not room_exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Room '{room_name}' not found"
                )
        finally:
            await lk_api.aclose()
        
        logger.info(f"Request to insert voice agent into room: {room_name}")
        
        async def start_agent_process():
            """Background task to start the voice agent as a subprocess"""
            try:
                # Get the path to the metatron package
                metatron_path = Path(__file__).parent.parent
                
                # Start the voice agent as a subprocess
                logger.info(f"Starting voice agent worker for room: {room_name}")
                
                # Use uv run to execute the voice agent
                process = subprocess.Popen(
                    ["uv", "run", "python", "-m", "metatron.agents.voice_agent"],
                    cwd=metatron_path.parent,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                logger.info(f"Voice agent worker started with PID: {process.pid}")
                
                # Wait a bit to check if it started successfully
                await asyncio.sleep(2)
                
                if process.poll() is not None:
                    # Process already terminated
                    stdout, stderr = process.communicate()
                    logger.error(f"Voice agent failed to start: {stderr}")
                else:
                    logger.info(f"Voice agent worker running successfully for room: {room_name}")
                    
            except Exception as e:
                logger.error(f"Error starting voice agent process: {e}", exc_info=True)
        
        # Start the agent in the background
        background_tasks.add_task(start_agent_process)
        
        return InsertAgentResponse(
            success=True,
            room_name=room_name,
            message=f"Voice agent worker is starting for room '{room_name}'. The agent will join automatically."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inserting agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to insert agent: {str(e)}"
        )


@router.delete(
    "/rooms/{room_name}",
    summary="Delete a room",
    description="Delete a LiveKit room by name",
    tags=["LiveKit"],
    responses={
        200: {"description": "Room deleted successfully"},
        500: {"description": "Internal Server Error"},
        503: {"description": "LiveKit not configured"},
    },
)
async def delete_room(room_name: str):
    """
    Delete a LiveKit room.
    
    Args:
        room_name: Name of the room to delete
        
    Returns:
        Success message
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
    
    try:
        lk_api = livekit_api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret,
        )
        
        await lk_api.room.delete_room(livekit_api.DeleteRoomRequest(room=room_name))
        
        logger.info(f"Room deleted: {room_name}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Room '{room_name}' deleted successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"Error deleting room: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete room: {str(e)}")


@router.post(
    "/calls/outbound",
    response_model=MakeCallResponse,
    summary="Make outbound call",
    description="Initiate an outbound phone call to a number using SIP trunk",
    tags=["LiveKit"],
    responses={
        200: {"description": "Call initiated successfully"},
        400: {"description": "Invalid phone number or request"},
        500: {"description": "Internal Server Error"},
        503: {"description": "LiveKit or SIP trunk not configured"},
    },
)
async def make_outbound_call(request: MakeCallRequest) -> MakeCallResponse:
    """
    Initiate an outbound phone call.
    
    The voice agent will automatically join the call when the recipient answers.
    
    Args:
        request: MakeCallRequest with phone_number and optional metadata
    
    Returns:
        MakeCallResponse with call details
    
    Example:
        POST /calls/outbound
        {
            "phone_number": "+1234567890",
            "metadata": {"campaign": "sales_q4"}
        }
    """
    if not LIVEKIT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="LiveKit SDK not installed. Install with: pip install livekit livekit-api"
        )
    
    if not settings.livekit_url or not settings.livekit_api_key or not settings.livekit_api_secret:
        raise HTTPException(
            status_code=503,
            detail="LiveKit not configured. Please set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET"
        )
    
    if not settings.livekit_sip_trunk_id:
        raise HTTPException(
            status_code=503,
            detail="LiveKit SIP trunk not configured. Set LIVEKIT_SIP_TRUNK_ID in .env file"
        )
    
    # Validate phone number format (basic E.164 check)
    phone = request.phone_number.strip()
    if not phone.startswith('+') or not phone[1:].isdigit() or len(phone) < 10:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number. Must be in E.164 format (e.g., +1234567890)"
        )
    
    try:
        # Generate unique room name if not provided
        room_name = request.room_name or f"call-{secrets.token_hex(6)}"
        
        logger.info(f"Initiating outbound call to {phone} in room {room_name}")
        
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
        
        # Prepare metadata
        import json
        metadata_str = json.dumps(request.metadata or {})
        
        # Create SIP participant (initiates the call)
        sip_request = livekit_api.CreateSIPParticipantRequest(
            sip_trunk_id=settings.livekit_sip_trunk_id,
            sip_call_to=phone,
            room_name=room_name,
            participant_identity=f"phone-{phone.replace('+', '')}",
            participant_name=f"Call to {phone}",
            participant_metadata=metadata_str,
            dtmf="",  # No DTMF to send initially
            play_ringtone=True,  # Play ringtone while connecting
            hide_phone_number=False,  # Show caller ID
        )
        
        sip_participant = await lk_api.sip.create_sip_participant(sip_request)
        
        logger.info(f"✅ Outbound call initiated: {sip_participant.participant_id} to {phone}")
        
        return MakeCallResponse(
            call_id=sip_participant.participant_id,
            room_name=room_name,
            phone_number=phone,
            status="initiated"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making outbound call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")