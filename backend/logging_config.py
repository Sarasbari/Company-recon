"""
Centralized structured logging configuration using Loguru.
Import `logger` from this module across the backend.
"""

import sys
from loguru import logger

# Remove default handler to avoid duplicate output
logger.remove()

# Structured console handler with color coding
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)
