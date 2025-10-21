"""
Logging configuration for FuseSell Local
"""

import logging
import sys
from typing import Optional
from pathlib import Path
from datetime import datetime


# Global flag to prevent multiple logging setups
_logging_configured = False

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    verbose: bool = False,
    force_reconfigure: bool = False
) -> logging.Logger:
    """
    Set up logging configuration for FuseSell.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        verbose: Enable verbose logging
        force_reconfigure: Force reconfiguration even if already configured
        
    Returns:
        Configured logger instance
    """
    global _logging_configured
    
    # Check if logging is already configured
    if _logging_configured and not force_reconfigure:
        logger = logging.getLogger("fusesell")
        logger.debug("Logging already configured, skipping setup")
        return logger
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    if verbose:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)
    
    # Get FuseSell logger
    logger = logging.getLogger("fusesell")
    logger.info(f"Logging initialized at {level} level")
    
    if log_file:
        logger.info(f"Logging to file: {log_file}")
    
    # Mark logging as configured
    _logging_configured = True
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific component.
    
    Args:
        name: Logger name (will be prefixed with 'fusesell.')
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"fusesell.{name}")


class LoggerMixin:
    """
    Mixin class to add logging capabilities to other classes.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        class_name = self.__class__.__name__.lower()
        return get_logger(class_name)


def log_execution_start(execution_id: str, config: dict) -> None:
    """
    Log the start of a FuseSell execution.
    
    Args:
        execution_id: Unique execution identifier
        config: Execution configuration
    """
    logger = get_logger("execution")
    logger.info(f"Starting execution {execution_id}")
    logger.info(f"Organization: {config.get('org_name')} ({config.get('org_id')})")
    logger.info(f"Customer: {config.get('customer_website')}")
    logger.info(f"Language: {config.get('language', 'english')}")


def log_execution_complete(execution_id: str, status: str, duration: float) -> None:
    """
    Log the completion of a FuseSell execution.
    
    Args:
        execution_id: Unique execution identifier
        status: Execution status (completed, failed, etc.)
        duration: Execution duration in seconds
    """
    logger = get_logger("execution")
    logger.info(f"Execution {execution_id} {status} in {duration:.2f} seconds")


def log_stage_start(stage_name: str, execution_id: str) -> None:
    """
    Log the start of a pipeline stage.
    
    Args:
        stage_name: Name of the stage
        execution_id: Execution identifier
    """
    logger = get_logger("stage")
    logger.info(f"Starting {stage_name} stage for execution {execution_id}")


def log_stage_complete(stage_name: str, execution_id: str, status: str, duration: float) -> None:
    """
    Log the completion of a pipeline stage.
    
    Args:
        stage_name: Name of the stage
        execution_id: Execution identifier
        status: Stage status
        duration: Stage duration in seconds
    """
    logger = get_logger("stage")
    logger.info(f"Stage {stage_name} {status} for execution {execution_id} in {duration:.2f} seconds")


def log_api_call(service: str, endpoint: str, status_code: int, duration: float) -> None:
    """
    Log API call details.
    
    Args:
        service: Service name (e.g., 'openai', 'serper')
        endpoint: API endpoint
        status_code: HTTP status code
        duration: Call duration in seconds
    """
    logger = get_logger("api")
    logger.debug(f"{service} API call to {endpoint}: {status_code} in {duration:.3f}s")


def log_error(component: str, error: Exception, context: Optional[dict] = None) -> None:
    """
    Log error with context information.
    
    Args:
        component: Component where error occurred
        error: Exception instance
        context: Optional context information
    """
    logger = get_logger("error")
    logger.error(f"Error in {component}: {str(error)}")
    
    if context:
        logger.error(f"Context: {context}")
    
    logger.debug("Exception details:", exc_info=True)