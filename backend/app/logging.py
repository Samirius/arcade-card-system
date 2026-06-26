"""Logging configuration"""
import logging
import sys
from pathlib import Path
from app.config import settings

# Create logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
def setup_logging():
    """Set up application logging"""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)

    # File handler (all logs)
    file_handler = logging.FileHandler(LOG_DIR / "app.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(file_handler)

    # Error file handler
    error_handler = logging.FileHandler(LOG_DIR / "error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(error_handler)

    # Security logger (separate file)
    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.INFO)
    security_file_handler = logging.FileHandler(LOG_DIR / "security.log")
    security_file_handler.setFormatter(logging.Formatter(log_format, date_format))
    security_logger.addHandler(security_file_handler)

# Initialize logging on import
setup_logging()