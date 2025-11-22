"""
Pydantic schemas for API requests and responses.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# Token schemas (existing)
class CreateTokenRequest(BaseModel):
    """Request schema for creating a room token."""
    room_name: str = Field(..., description="Name of the room")
    participant_name: str = Field(..., description="Name of the participant")


class CreateTokenResponse(BaseModel):
    """Response schema for token creation."""
    token: str = Field(..., description="JWT token for room access")


# Context update schemas
ContextType = Literal["salesman", "lead", "product", "close"]


class UpdateContextRequest(BaseModel):
    """Request schema for updating a context file."""
    content: str = Field(..., description="Plain text content to write to the context file")


class UpdateContextResponse(BaseModel):
    """Response schema for context update."""
    success: bool = Field(..., description="Whether the update was successful")
    context_type: ContextType = Field(..., description="Type of context that was updated")
    message: str = Field(..., description="Success or error message")


class GetContextResponse(BaseModel):
    """Response schema for getting context content."""
    context_type: ContextType = Field(..., description="Type of context")
    content: str = Field(..., description="Plain text content of the context file")


# LiveKit room schemas
class CreateRoomRequest(BaseModel):
    """Request schema for creating a LiveKit room."""
    room_name: Optional[str] = Field(default=None, description="Name of the room (auto-generated if not provided)")
    participant_name: str = Field(default="Guest", description="Name of the participant")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata for the room")
    voice_id: Optional[str] = Field(default=None, description="ElevenLabs voice ID for voice cloning")


class RoomResponse(BaseModel):
    """Response schema for LiveKit room creation."""
    room_name: str = Field(..., description="Name of the created room")
    token: str = Field(..., description="JWT token for joining the room")
    url: str = Field(..., description="LiveKit server URL")


class RoomInfo(BaseModel):
    """Information about a LiveKit room."""
    name: str = Field(..., description="Room name")
    num_participants: int = Field(..., description="Number of participants in the room")
    creation_time: int = Field(..., description="Room creation timestamp")


class ListRoomsResponse(BaseModel):
    """Response schema for listing rooms."""
    rooms: list[RoomInfo] = Field(..., description="List of active rooms")


# Outbound call schemas
class MakeCallRequest(BaseModel):
    """Request schema for making an outbound call."""
    phone_number: str = Field(..., description="Phone number to call in E.164 format (e.g., +1234567890)")
    room_name: Optional[str] = Field(default=None, description="Optional room name (auto-generated if not provided)")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata for the call")


class MakeCallResponse(BaseModel):
    """Response schema for outbound call initiation."""
    call_id: str = Field(..., description="Unique identifier for the call (participant ID)")
    room_name: str = Field(..., description="LiveKit room name where the call is happening")
    phone_number: str = Field(..., description="Phone number being called")
    status: str = Field(..., description="Call status (e.g., 'initiated', 'ringing')")


class InsertAgentRequest(BaseModel):
    """Request schema for inserting an agent into a room."""
    room_name: str = Field(..., description="Name of the room to join")


class InsertAgentResponse(BaseModel):
    """Response schema for agent insertion."""
    success: bool = Field(..., description="Whether the agent was successfully inserted")
    room_name: str = Field(..., description="Name of the room")
    message: str = Field(..., description="Status message")