"""
FastAPI route definitions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ..config import settings
from ..schemas import (
    UpdateContextRequest,
    UpdateContextResponse,
    GetContextResponse,
    ContextType,
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
            "livekit_configured": bool(settings.livekit_project_id),
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