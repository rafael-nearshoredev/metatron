"""
Simple script to run the Metatron API server.
Run this from the metatron/metatron directory with: uv run python run.py
"""
import uvicorn
from metatron.main import app
from metatron.config import settings

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )