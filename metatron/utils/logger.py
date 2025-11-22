"""
Logger configuration for metatron.
"""

import logging

# ---------------------------
# CONFIGURAR LOGGING GLOBAL
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="🟦 [%(levelname)s] %(message)s"
)

# Create and export the logger
logger = logging.getLogger("metatron")

__all__ = ["logger"]