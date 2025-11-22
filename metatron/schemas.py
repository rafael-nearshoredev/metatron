"""
Pydantic schemas for API requests and responses.
"""

from __future__ import annotations

from typing import Literal

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