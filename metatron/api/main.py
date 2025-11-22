"""
FastAPI route definitions.
"""

from __future__ import annotations

import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
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
            "minimax_configured": bool(settings.minimax_api_key),
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
        
        # Create LiveKit API client
        lk_api = livekit_api.LiveKitAPI(
            settings.livekit_url,
            settings.livekit_api_key,
            settings.livekit_api_secret,
        )
        
        # Create or get room
        room_info = await lk_api.room.create_room(
            livekit_api.CreateRoomRequest(
                name=room_name,
                empty_timeout=300,  # 5 minutes
                max_participants=2,  # 1 customer + 1 agent
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
        
        rooms = await lk_api.room.list_rooms(livekit_api.ListRoomsRequest())
        
        return ListRoomsResponse(
            rooms=[
                RoomInfo(
                    name=room.name,
                    num_participants=room.num_participants,
                    creation_time=room.creation_time,
                )
                for room in rooms
            ]
        )
    except Exception as e:
        logger.error(f"Error listing rooms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list rooms: {str(e)}")


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