"""
Audit Service for logging all system actions and events.
"""
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import Config

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing audit logs."""
    
    AUDIT_LOG_PATH = os.path.join(Config.DATA_DIR, "audit_log.json")
    
    # Event type constants
    EVENT_TYPES = {
        'REMINDER_SENT': 'Reminder Sent',
        'SETTING_CHANGED': 'Setting Changed',
        'EQUIPMENT_ADDED': 'Equipment Added',
        'EQUIPMENT_UPDATED': 'Equipment Updated',
        'EQUIPMENT_DELETED': 'Equipment Deleted',
        'BULK_IMPORT': 'Bulk Import',
        'BULK_DELETE': 'Bulk Delete',
        'DATA_EXPORT': 'Data Export',
        'PUSH_NOTIFICATION': 'Push Notification',
        'EMAIL_NOTIFICATION': 'Email Notification',
        'TEST_EMAIL': 'Test Email',
        'TEST_PUSH': 'Test Push',
        'TRAINING_ADDED': 'Training Added',
        'TRAINING_UPDATED': 'Training Updated',
        'TRAINING_DELETED': 'Training Deleted',
        'BACKUP_CREATED': 'Backup Created',
        'BACKUP_DELETED': 'Backup Deleted',
        'BACKUP_RESTORED': 'Backup Restored',
        'SYSTEM_STARTUP': 'System Startup',
        'SYSTEM_ERROR': 'System Error',
        'USER_ACTION': 'User Action'
    }
    
    # Status constants
    STATUS_SUCCESS = 'Success'
    STATUS_FAILED = 'Failed'
    STATUS_WARNING = 'Warning'
    STATUS_INFO = 'Info'
    
    @staticmethod
    def _ensure_audit_file_exists():
        """Ensure the audit log file exists."""
        try:
            if not os.path.exists(AuditService.AUDIT_LOG_PATH):
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(AuditService.AUDIT_LOG_PATH), exist_ok=True)
                
                # Create initial audit log with sample entries
                initial_logs = AuditService._create_sample_logs()
                AuditService._save_logs(initial_logs)
                logger.info(f"Created audit log file at {AuditService.AUDIT_LOG_PATH}")
        except Exception as e:
            logger.error(f"Error ensuring audit file exists: {e}")
    
    @staticmethod
    def _create_sample_logs() -> List[Dict[str, Any]]:
        """Create sample audit log entries for demonstration."""
        sample_logs = [
            {
                "id": 1,
                "timestamp": "2025-06-22 10:15:30",
                "event_type": "System Startup",
                "performed_by": "System",
                "description": "Hospital Equipment Management System started successfully",
                "status": "Success",
                "details": {
                    "version": "1.0.0",
                    "modules": ["PPM", "OCM", "Training", "Notifications"]
                }
            },
            {
                "id": 2,
                "timestamp": "2025-06-22 10:30:45",
                "event_type": "Equipment Added",
                "performed_by": "Admin User",
                "description": "New PPM equipment added: Ventilator (Serial: VNT-2025-001)",
                "status": "Success",
                "details": {
                    "equipment_type": "PPM",
                    "serial": "VNT-2025-001",
                    "department": "ICU"
                }
            },
            {
                "id": 3,
                "timestamp": "2025-06-22 11:45:12",
                "event_type": "Reminder Sent",
                "performed_by": "System",
                "description": "Email reminder sent for 15 equipment maintenance tasks (7-day threshold)",
                "status": "Success",
                "details": {
                    "threshold": "7 days",
                    "equipment_count": 15,
                    "recipient": "maintenance@hospital.com"
                }
            },
            {
                "id": 4,
                "timestamp": "2025-06-22 14:20:18",
                "event_type": "Bulk Import",
                "performed_by": "Maintenance Manager",
                "description": "Bulk import of 25 OCM equipment records from CSV file",
                "status": "Success",
                "details": {
                    "file_type": "CSV",
                    "records_imported": 25,
                    "records_failed": 0,
                    "equipment_type": "OCM"
                }
            },
            {
                "id": 5,
                "timestamp": "2025-06-22 15:10:33",
                "event_type": "Setting Changed",
                "performed_by": "Admin User",
                "description": "Push notification interval changed from 60 to 5 minutes",
                "status": "Success",
                "details": {
                    "setting": "push_notification_interval_minutes",
                    "old_value": 60,
                    "new_value": 5
                }
            }
        ]
        return sample_logs
    
    @staticmethod
    def _load_logs() -> List[Dict[str, Any]]:
        """Load audit logs from JSON file."""
        try:
            AuditService._ensure_audit_file_exists()
            
            with open(AuditService.AUDIT_LOG_PATH, 'r', encoding='utf-8') as file:
                logs = json.load(file)
                logger.debug(f"Loaded {len(logs)} audit log entries")
                return logs
        except FileNotFoundError:
            logger.warning(f"Audit log file not found: {AuditService.AUDIT_LOG_PATH}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing audit log JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading audit logs: {e}")
            return []
    
    @staticmethod
    def _save_logs(logs: List[Dict[str, Any]]):
        """Save audit logs to JSON file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(AuditService.AUDIT_LOG_PATH), exist_ok=True)
            
            with open(AuditService.AUDIT_LOG_PATH, 'w', encoding='utf-8') as file:
                json.dump(logs, file, indent=2, ensure_ascii=False)
                logger.debug(f"Saved {len(logs)} audit log entries")
        except Exception as e:
            logger.error(f"Error saving audit logs: {e}")
            raise
    
    @staticmethod
    def _get_next_id() -> int:
        """Get the next available ID for a new log entry."""
        logs = AuditService._load_logs()
        if not logs:
            return 1
        return max(log.get('id', 0) for log in logs) + 1
    
    @staticmethod
    def log_event(
        event_type: str,
        performed_by: str,
        description: str,
        status: str = STATUS_SUCCESS,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a new audit event.
        
        Args:
            event_type: Type of event (use EVENT_TYPES constants)
            performed_by: User or system that performed the action
            description: Human-readable description of the action
            status: Status of the action (Success, Failed, Warning, Info)
            details: Additional details as a dictionary
            
        Returns:
            bool: True if logged successfully, False otherwise
        """
        try:
            logs = AuditService._load_logs()
            
            new_log = {
                "id": AuditService._get_next_id(),
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "event_type": event_type,
                "performed_by": performed_by,
                "description": description,
                "status": status,
                "details": details or {}
            }
            
            logs.append(new_log)
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(logs) > 1000:
                logs = logs[-1000:]
                logger.info("Trimmed audit log to last 1000 entries")
            
            AuditService._save_logs(logs)
            logger.info(f"Audit event logged: {event_type} by {performed_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False
    
    @staticmethod
    def get_all_logs() -> List[Dict[str, Any]]:
        """Get all audit logs, sorted by timestamp (newest first)."""
        logs = AuditService._load_logs()
        # Sort by timestamp descending (newest first)
        return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    @staticmethod
    def get_logs_by_type(event_type: str) -> List[Dict[str, Any]]:
        """Get audit logs filtered by event type."""
        logs = AuditService.get_all_logs()
        return [log for log in logs if log.get('event_type') == event_type]
    
    @staticmethod
    def get_logs_by_user(performed_by: str) -> List[Dict[str, Any]]:
        """Get audit logs filtered by user."""
        logs = AuditService.get_all_logs()
        return [log for log in logs if log.get('performed_by') == performed_by]
    
    @staticmethod
    def get_logs_by_date_range(start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get audit logs filtered by date range (YYYY-MM-DD format)."""
        logs = AuditService.get_all_logs()
        filtered_logs = []
        
        for log in logs:
            log_date = log.get('timestamp', '').split(' ')[0]  # Extract date part
            if start_date <= log_date <= end_date:
                filtered_logs.append(log)
        
        return filtered_logs
    
    @staticmethod
    def search_logs(query: str) -> List[Dict[str, Any]]:
        """Search audit logs by description, event type, or user."""
        logs = AuditService.get_all_logs()
        query_lower = query.lower()
        
        filtered_logs = []
        for log in logs:
            if (query_lower in log.get('description', '').lower() or
                query_lower in log.get('event_type', '').lower() or
                query_lower in log.get('performed_by', '').lower()):
                filtered_logs.append(log)
        
        return filtered_logs
    
    @staticmethod
    def get_event_types() -> List[str]:
        """Get all available event types."""
        return list(AuditService.EVENT_TYPES.values())
    
    @staticmethod
    def get_unique_users() -> List[str]:
        """Get list of unique users from audit logs."""
        logs = AuditService._load_logs()
        users = set()
        for log in logs:
            user = log.get('performed_by', '')
            if user:
                users.add(user)
        return sorted(list(users))
    
    @staticmethod
    def export_to_csv() -> str:
        """Export audit logs to CSV format."""
        logs = AuditService.get_all_logs()
        
        # CSV header
        csv_content = "ID,Timestamp,Event Type,Performed By,Description,Status,Details\n"
        
        # CSV rows
        for log in logs:
            details_str = json.dumps(log.get('details', {})).replace('"', '""')
            description = log.get('description', '').replace('"', '""')
            csv_content += f"{log.get('id', '')},{log.get('timestamp', '')},{log.get('event_type', '')},{log.get('performed_by', '')},\"{description}\",{log.get('status', '')},\"{details_str}\"\n"
        
        return csv_content
    
    @staticmethod
    def clear_logs() -> bool:
        """Clear all audit logs (admin only)."""
        try:
            AuditService._save_logs([])
            logger.warning("All audit logs cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear audit logs: {e}")
            return False


# Convenience functions for common audit events
def log_equipment_action(action: str, equipment_type: str, serial: str, user: str, status: str = AuditService.STATUS_SUCCESS):
    """Log equipment-related actions."""
    AuditService.log_event(
        event_type=f"Equipment {action.title()}",
        performed_by=user,
        description=f"{action.title()} {equipment_type} equipment: {serial}",
        status=status,
        details={"equipment_type": equipment_type, "serial": serial, "action": action}
    )

def log_reminder_sent(threshold: str, count: int, recipient: str, status: str = AuditService.STATUS_SUCCESS):
    """Log reminder email/notification sent."""
    AuditService.log_event(
        event_type=AuditService.EVENT_TYPES['REMINDER_SENT'],
        performed_by="System",
        description=f"Reminder sent for {count} equipment maintenance tasks ({threshold} threshold)",
        status=status,
        details={"threshold": threshold, "equipment_count": count, "recipient": recipient}
    )

def log_setting_change(setting_name: str, old_value: Any, new_value: Any, user: str):
    """Log setting changes."""
    AuditService.log_event(
        event_type=AuditService.EVENT_TYPES['SETTING_CHANGED'],
        performed_by=user,
        description=f"Setting '{setting_name}' changed from '{old_value}' to '{new_value}'",
        status=AuditService.STATUS_SUCCESS,
        details={"setting": setting_name, "old_value": old_value, "new_value": new_value}
    )

def log_bulk_operation(operation: str, count: int, user: str, details: Dict[str, Any] = None):
    """Log bulk operations like import/export/delete."""
    AuditService.log_event(
        event_type=f"Bulk {operation.title()}",
        performed_by=user,
        description=f"Bulk {operation} of {count} records",
        status=AuditService.STATUS_SUCCESS,
        details=details or {"operation": operation, "record_count": count}
    ) 