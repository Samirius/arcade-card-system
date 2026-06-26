"""Audit logging utilities"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditLog, AuditAction


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


def log_action(
    db: Session,
    user_id: str,
    action: str,
    details: str = None,
    resource_type: str = None,
    resource_id: str = None
) -> None:
    """
    Log audit entry to database.

    Args:
        db: Database session
        user_id: ID of user who performed action
        action: Action performed (LOGIN, LOGOUT, CARD_CREATE, etc.)
        details: Action details
        resource_type: Type of resource affected
        resource_id: ID of resource affected
    """
    try:
        # Map action to AuditAction enum
        action_map = {
            'LOGIN': AuditAction.LOGIN,
            'LOGOUT': AuditAction.LOGOUT,
            'CARD_CREATE': AuditAction.CREATE,
            'CARD_UPDATE': AuditAction.UPDATE,
            'CARD_ACTIVATE': AuditAction.UPDATE,
            'CARD_DEACTIVATE': AuditAction.UPDATE,
            'CARD_ADD_CREDIT': AuditAction.CREATE,
            'CARD_CHARGE': AuditAction.CREATE,
            'TRANSACTION_CREATE': AuditAction.CREATE,
            'CONFIG_CHANGE': AuditAction.CONFIG_CHANGE,
        }

        audit_action = action_map.get(action, AuditAction.UPDATE)

        # Create audit log
        audit_log = AuditLog(
            user_id=user_id,
            action=audit_action,
            resource_type=resource_type or 'system',
            resource_id=resource_id,
            ip_address=None,  # Will be set from request if available
            user_agent=None,
            old_values=None,
            new_values={'details': details} if details else None,
            success=True,
            error_message=None
        )

        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log to database: {e}")
        # Don't raise - we don't want to break the application due to logging failures


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
        from app.models.audit import AuditLog, AuditAction

        # Map action string to AuditAction enum
        action_map = {
            'LOGIN': AuditAction.LOGIN,
            'LOGOUT': AuditAction.LOGOUT,
            'CREATE': AuditAction.CREATE,
            'READ': AuditAction.READ,
            'UPDATE': AuditAction.UPDATE,
            'DELETE': AuditAction.DELETE,
            'TRANSACTION': AuditAction.TRANSACTION,
            'REFUND': AuditAction.REFUND,
            'CONFIG_CHANGE': AuditAction.CONFIG_CHANGE,
            'FAILED_LOGIN': AuditAction.FAILED_LOGIN,
        }

        audit_action = action_map.get(action, AuditAction.OTHER if hasattr(AuditAction, 'OTHER') else AuditAction.UPDATE)

        # Create audit log
        audit_log = AuditLog(
            user_id=user_id,
            action=audit_action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            old_values=old_values,
            new_values=new_values,
            success=success,
            error_message=error_message
        )

        db.add(audit_log)
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
        from app.models.audit import AuditLog

        query = db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if action:
            query = query.filter(AuditLog.action == action)

        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

        return [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action.value if hasattr(log.action, 'value') else str(log.action),
                "resource_type": log.resource_type,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "ip_address": log.ip_address,
                "success": log.success,
                "error_message": log.error_message,
                "created_at": log.created_at,
                "old_values": log.old_values,
                "new_values": log.new_values
            }
            for log in logs
        ]

    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        return []