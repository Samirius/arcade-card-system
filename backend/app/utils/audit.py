"""Audit logging system"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import Base, get_db

# Set up audit logger
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# File handler for audit logs
audit_handler = logging.FileHandler("logs/audit.log")
audit_handler.setLevel(logging.INFO)
audit_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s'
)
audit_handler.setFormatter(audit_formatter)
audit_logger.addHandler(audit_handler)

class AuditLog(Base):
    """Audit log model for database"""
    __tablename__ = "audit_logs"

    id = int
    user_id = Optional[str]
    action = str
    resource_type = Optional[str]
    resource_id = Optional[str]
    ip_address = Optional[str]
    user_agent = Optional[str]
    old_values = Optional[Dict[str, Any]]
    new_values = Optional[Dict[str, Any]]
    success = bool
    error_message = Optional[str]
    created_at = datetime

def log_audit_event(
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """
    Log an audit event.

    Args:
        user_id: ID of the user performing the action
        action: Action being performed
        resource_type: Type of resource (e.g., 'card', 'transaction')
        resource_id: ID of the resource
        ip_address: IP address of the request
        user_agent: User agent string
        old_values: Old values (for updates)
        new_values: New values
        success: Whether the action was successful
        error_message: Error message if action failed
    """
    # Log to file
    log_message = f"User: {user_id} | Action: {action} | Resource: {resource_type}:{resource_id} | Success: {success}"

    if not success and error_message:
        log_message += f" | Error: {error_message}"

    audit_logger.info(log_message)

    # Log to database (if session available)
    try:
        # Get database session
        from app.database import SessionLocal
        db = SessionLocal()

        # Create audit log record
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            old_values=old_values,
            new_values=new_values,
            success=success,
            error_message=error_message,
            created_at=datetime.utcnow()
        )

        db.add(audit_log)
        db.commit()
        db.close()

    except Exception as e:
        # Don't fail the application if audit logging fails
        audit_logger.error(f"Failed to log to database: {e}")

def audit_decorator(action: str, resource_type: Optional[str] = None):
    """
    Decorator for automatically logging function calls.

    Args:
        action: Action being performed
        resource_type: Type of resource
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id') or getattr(args[0], 'current_user_id', None)
            resource_id = kwargs.get('id') or kwargs.get('resource_id')

            try:
                result = func(*args, **kwargs)

                # Log successful action
                log_audit_event(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=True
                )

                return result

            except Exception as e:
                # Log failed action
                log_audit_event(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=False,
                    error_message=str(e)
                )
                raise

        return wrapper
    return decorator