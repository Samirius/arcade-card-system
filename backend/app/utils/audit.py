"""Audit logging utilities"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditLog


# Setup file logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create file handler
file_handler = logging.FileHandler('audit.log')
file_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(file_handler)


def log_audit(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """
    Log audit entry to both file and database.

    Args:
        db: Database session
        action: Action performed (LOGIN, LOGOUT, CREATE, READ, UPDATE, DELETE, etc.)
        resource_type: Type of resource affected
        resource_id: ID of resource affected
        user_id: ID of user who performed action
        ip_address: IP address of request
        user_agent: User agent string
        old_values: Previous values (for UPDATE actions)
        new_values: New values
        success: Whether action was successful
        error_message: Error message if action failed
    """
    # Log to file
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'user_id': user_id,
        'ip_address': ip_address,
        'success': success,
        'error_message': error_message
    }

    if old_values:
        log_entry['old_values'] = old_values

    if new_values:
        log_entry['new_values'] = new_values

    logger.info(f"AUDIT: {log_entry}")

    # Log to database
    try:
        # Import here to avoid circular dependency
        from sqlalchemy import text

        query = text("""
            INSERT INTO audit_logs (
                user_id, action, resource_type, resource_id,
                ip_address, user_agent, old_values, new_values,
                success, error_message
            ) VALUES (
                :user_id, :action, :resource_type, :resource_id,
                :ip_address, :user_agent, :old_values, :new_values,
                :success, :error_message
            )
        """)

        db.execute(query, {
            'user_id': user_id,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'old_values': old_values,
            'new_values': new_values,
            'success': success,
            'error_message': error_message
        })
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")
        # Don't raise - we don't want to break the application due to logging failures


def get_audit_logs(
    db: Session,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
) -> list:
    """
    Get audit logs with optional filters.

    Args:
        db: Database session
        user_id: Filter by user ID
        action: Filter by action type
        limit: Maximum number of logs to return

    Returns:
        List of audit log entries
    """
    try:
        from sqlalchemy import text

        query = text("""
            SELECT
                id, user_id, action, resource_type, resource_id,
                ip_address, user_agent, old_values, new_values,
                success, error_message, created_at
            FROM audit_logs
            WHERE 1=1
        """)

        params = {}

        if user_id:
            query = text(str(query) + " AND user_id = :user_id")
            params['user_id'] = user_id

        if action:
            query = text(str(query) + " AND action = :action")
            params['action'] = action

        query = text(str(query) + " ORDER BY created_at DESC LIMIT :limit")
        params['limit'] = limit

        result = db.execute(query, params)
        return [dict(row) for row in result]

    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        return []