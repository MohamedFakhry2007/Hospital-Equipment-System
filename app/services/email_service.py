"""
Email service for sending maintenance reminders.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import os
import json
import threading

from app.config import Config
from mailjet_rest import Client


logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""
    
    logger.debug("Initializing EmailService")
    _scheduler_running = False
    _scheduler_lock = threading.Lock()

    @staticmethod
    async def run_scheduler_async_loop():
        """The actual asynchronous scheduler loop that runs periodically."""
        # Import DataService here to avoid circular import issues at module level
        from app.services.data_service import DataService

        if EmailService._scheduler_running:
            logger.info("Scheduler loop already running in this process.")
            return

        with EmailService._scheduler_lock:
            if EmailService._scheduler_running:
                logger.info("Scheduler loop already running (checked after lock).")
                return
            EmailService._scheduler_running = True
            logger.info("Email reminder scheduler async loop started in process ID: %s.", os.getpid())
            logger.warning("If running multiple application instances (e.g., Gunicorn workers), ensure this scheduler is enabled in only ONE instance to avoid duplicate emails.")

        try:
            # Add an initial delay before the first run
            initial_delay_seconds = 30  # e.g., 30 seconds
            logger.info(f"Scheduler starting. Initial delay of {initial_delay_seconds} seconds before first run.")
            await asyncio.sleep(initial_delay_seconds)

            while True:
                logger.debug("Scheduler loop iteration started.")
                settings = {}
                try:
                    settings = DataService.load_settings()
                    logger.debug(f"Loaded settings: {settings}")
                except Exception as e:
                    logger.error(f"Error loading settings in scheduler loop: {str(e)}. Will use defaults and retry.", exc_info=True)
                    # Use defaults to allow the loop to continue and retry loading settings next time
                    settings = {
                        "email_notifications_enabled": False, # Default to false if settings can't be loaded
                        "email_reminder_interval_minutes": 60 # Default interval
                    }

                email_enabled = settings.get("email_notifications_enabled", False) # Default to False if key is missing
                interval_minutes = settings.get("email_reminder_interval_minutes", 60) # Default to 60 if key is missing

                if not isinstance(interval_minutes, int) or interval_minutes <= 0:
                    logger.warning(f"Invalid email_reminder_interval_minutes: {interval_minutes}. Defaulting to 60 minutes.")
                    interval_minutes = 60

                interval_seconds = interval_minutes * 60

                if email_enabled:
                    logger.info("Email notifications are ENABLED in settings. Processing reminders.")
                    
                    # Check if it's time to send emails (configurable daily time)
                    current_time = datetime.now()
                    target_hour = settings.get("email_send_time_hour", 7)  # Default to 7 AM if not configured
                    
                    # Calculate next scheduled time
                    if current_time.hour >= target_hour:
                        # If it's already past the target hour today, schedule for tomorrow
                        next_run = current_time.replace(hour=target_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
                    else:
                        # If it's before the target hour today, schedule for today
                        next_run = current_time.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                    
                    # Check if we should send emails now (within 5 minutes of target time)
                    time_until_next = (next_run - current_time).total_seconds()
                    
                    if time_until_next <= 300:  # Within 5 minutes (300 seconds) of target time
                        logger.info(f"It's time to send daily emails! Current time: {current_time.strftime('%H:%M:%S')}, Target: {target_hour:02d}:00")
                        try:
                            await EmailService.process_reminders()
                            logger.info(f"Finished processing daily reminders at scheduled time ({target_hour:02d}:00).")
                        except Exception as e:
                            logger.error(f"Error during process_reminders call in scheduler loop: {str(e)}", exc_info=True)
                        
                        # Sleep until next day's target time
                        sleep_seconds = max(time_until_next + 86400, 3600)  # At least 1 hour, or until next day
                        logger.info(f"Daily emails sent. Sleeping until next {target_hour:02d}:00 ({sleep_seconds/3600:.1f} hours).")
                    else:
                        # Not time yet, sleep until closer to target time
                        sleep_seconds = min(time_until_next - 60, 3600)  # Check again 1 minute before target time, or in 1 hour max
                        logger.info(f"Next email scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')}. Sleeping for {sleep_seconds/60:.1f} minutes.")
                else:
                    logger.info("Email notifications are DISABLED in settings. Skipping reminder processing.")
                    sleep_seconds = 3600  # Check settings again in 1 hour

                await asyncio.sleep(sleep_seconds)
                logger.debug("Scheduler awake after sleep.")

        except asyncio.CancelledError:
            logger.info("Scheduler loop was cancelled.")
        except Exception as e:
            logger.error(f"Unhandled error in scheduler loop: {str(e)}", exc_info=True)
            # This part of the code might not be reached if the loop itself is the source of an unhandled exception.
            # Consider how to restart or gracefully handle such a scenario if needed.
        finally:
            with EmailService._scheduler_lock:
                EmailService._scheduler_running = False
            logger.info("Email reminder scheduler async loop has stopped.")

    @staticmethod
    def parse_date_flexible(date_str: str) -> datetime:
        """Parse date string in multiple formats.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            datetime object
            
        Raises:
            ValueError: If date cannot be parsed in any supported format
        """
        formats_to_try = [
            '%Y-%m-%d',  # HTML5 date format (2025-06-01)
            '%d/%m/%Y',  # DD/MM/YYYY format (01/06/2025)
            '%m/%d/%Y'   # MM/DD/YYYY format (06/01/2025)
        ]
        
        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse date '{date_str}' in any supported format")

    @staticmethod
    async def get_upcoming_maintenance(data: List[Dict[str, Any]], data_type: str, days_ahead: int = None) -> List[Tuple[str, str, str, str, str, str]]:
        """Get upcoming maintenance within specified days for OCM or PPM data.
        
        Args:
            data: List of OCM or PPM entries.
            data_type: String indicating the type of data ('ocm' or 'ppm').
            days_ahead: Days ahead to check (default: from config).
            
        Returns:
            List of upcoming maintenance as (type, department, serial, description, due_date_str, engineer).
        """
        if days_ahead is None:
            days_ahead = Config.REMINDER_DAYS
            
        now = datetime.now()
        upcoming = []
        
        for entry in data:
            try:
                due_date_str = None
                engineer = None
                description = None
                department = entry.get('Department', 'N/A')
                serial = entry.get('Serial', entry.get('SERIAL', 'N/A')) # OCM uses 'Serial', PPM uses 'SERIAL'

                if data_type == 'ocm':
                    due_date_str = entry.get('Next_Maintenance')
                    engineer = entry.get('Engineer', 'N/A')
                    description = 'Next Maintenance'
                    if not due_date_str:
                        logger.warning(f"OCM entry {serial} missing 'Next_Maintenance' date.")
                        continue

                elif data_type == 'ppm':
                    # PPM data has multiple potential dates per entry
                    for q_key in ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']:
                        q_data = entry.get(q_key, {})
                        if not q_data or not q_data.get('quarter_date'):
                            continue

                        ppm_due_date_str = q_data['quarter_date']
                        ppm_engineer = q_data.get('engineer', 'N/A')
                        ppm_description = q_key.replace('PPM_Q_', 'Quarter ')

                        due_date_obj = EmailService.parse_date_flexible(ppm_due_date_str)
                        days_until = (due_date_obj - now).days

                        if 0 <= days_until <= days_ahead:
                            upcoming.append((
                                'PPM',
                                department,
                                serial,
                                ppm_description,
                                ppm_due_date_str,
                                ppm_engineer
                            ))
                    continue # Continue to next entry after processing all quarters for PPM

                else:
                    logger.error(f"Unknown data_type: {data_type} for entry {serial}")
                    continue

                # Common date processing for OCM (PPM dates are handled within its loop)
                if data_type == 'ocm': # This block is now only for OCM
                    due_date_obj = EmailService.parse_date_flexible(due_date_str)
                    days_until = (due_date_obj - now).days
                    
                    if 0 <= days_until <= days_ahead:
                        upcoming.append((
                            'OCM',
                            department,
                            serial,
                            description,
                            due_date_str,
                            engineer
                        ))

            except ValueError as e:
                logger.error(f"Error parsing date for {serial} (type: {data_type}): {str(e)}. Date string was: '{due_date_str}'.")
            except KeyError as e:
                logger.error(f"Missing key for {serial} (type: {data_type}): {str(e)}")
        
        # Sort by date - index 4 is due_date_str
        upcoming.sort(key=lambda x: EmailService.parse_date_flexible(x[4]))
        return upcoming

    @staticmethod
    async def get_upcoming_maintenance_by_days(data: List[Dict[str, Any]], data_type: str, min_days: int, max_days: int) -> List[Tuple[str, str, str, str, str, str, int]]:
        """Get upcoming maintenance within a specific day range for OCM or PPM data.
        
        Args:
            data: List of OCM or PPM entries.
            data_type: String indicating the type of data ('ocm' or 'ppm').
            min_days: Minimum days until maintenance (inclusive).
            max_days: Maximum days until maintenance (inclusive).
            
        Returns:
            List of upcoming maintenance as (type, department, serial, description, due_date_str, engineer, days_until).
        """
        now = datetime.now()
        upcoming = []
        
        for entry in data:
            try:
                due_date_str = None
                engineer = None
                description = None
                department = entry.get('Department', 'N/A')
                serial = entry.get('Serial', entry.get('SERIAL', 'N/A'))

                if data_type == 'ocm':
                    due_date_str = entry.get('Next_Maintenance')
                    engineer = entry.get('Engineer', 'N/A')
                    description = 'Next Maintenance'
                    if not due_date_str:
                        logger.warning(f"OCM entry {serial} missing 'Next_Maintenance' date.")
                        continue

                elif data_type == 'ppm':
                    # PPM data has multiple potential dates per entry
                    for q_key in ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']:
                        q_data = entry.get(q_key, {})
                        if not q_data or not q_data.get('quarter_date'):
                            continue

                        ppm_due_date_str = q_data['quarter_date']
                        ppm_engineer = q_data.get('engineer', 'N/A')
                        ppm_description = q_key.replace('PPM_Q_', 'Quarter ')

                        due_date_obj = EmailService.parse_date_flexible(ppm_due_date_str)
                        days_until = (due_date_obj - now).days

                        if min_days <= days_until <= max_days:
                            upcoming.append((
                                'PPM',
                                department,
                                serial,
                                ppm_description,
                                ppm_due_date_str,
                                ppm_engineer,
                                days_until
                            ))
                    continue

                else:
                    logger.error(f"Unknown data_type: {data_type} for entry {serial}")
                    continue

                # Common date processing for OCM
                if data_type == 'ocm':
                    due_date_obj = EmailService.parse_date_flexible(due_date_str)
                    days_until = (due_date_obj - now).days
                    
                    if min_days <= days_until <= max_days:
                        upcoming.append((
                            'OCM',
                            department,
                            serial,
                            description,
                            due_date_str,
                            engineer,
                            days_until
                        ))

            except ValueError as e:
                logger.error(f"Error parsing date for {serial} (type: {data_type}): {str(e)}. Date string was: '{due_date_str}'.")
            except KeyError as e:
                logger.error(f"Missing key for {serial} (type: {data_type}): {str(e)}")
        
        # Sort by days until due (ascending)
        upcoming.sort(key=lambda x: x[6])  # index 6 is days_until
        return upcoming

    @staticmethod
    async def send_reminder_email(upcoming: List[Tuple[str, str, str, str, str, str]]) -> bool:
        """Send reminder email for upcoming maintenance.
        
        Args:
            upcoming: List of upcoming maintenance as (type, department, serial, description, due_date_str, engineer).
            
        Returns:
            True if email was sent successfully, False otherwise.
        """
        if not upcoming:
            logger.info("No upcoming maintenance to send reminders for")
            return True
            
        try:
            # Import DataService here to avoid circular import issues at module level
            # and ensure it's available in this static method's scope.
            from app.services.data_service import DataService
            settings = DataService.load_settings()
            recipient_email_override = settings.get("recipient_email", "").strip()

            target_email_receiver = recipient_email_override if recipient_email_override else Config.EMAIL_RECEIVER

            if not target_email_receiver:
                logger.error("Email recipient is not configured. Cannot send email. Check settings (recipient_email) or .env (EMAIL_RECEIVER).")
                return False

            api_key = Config.MAILJET_API_KEY
            api_secret = Config.MAILJET_SECRET_KEY
            mailjet = Client(auth=(api_key, api_secret), version='v3.1')
            
            # Email content
            subject = f"Hospital Equipment Maintenance Reminder - {len(upcoming)} upcoming tasks"
            
            # Create HTML content
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 10px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>Upcoming Equipment Maintenance</h2>
                    <p>The following equipment requires maintenance in the next {Config.REMINDER_DAYS} days:</p>
                </div>
                <table>
                    <tr>
                        <th>Type</th>
                        <th>Department</th>
                        <th>Serial Number</th>
                        <th>Description</th>
                        <th>Due Date</th>
                        <th>Engineer</th>
                    </tr>
            """
            
            for task_type, department, serial, description, due_date_str, engineer in upcoming:
                html_content += f"""
                    <tr>
                        <td>{task_type}</td>
                        <td>{department}</td>
                        <td>{serial}</td>
                        <td>{description}</td>
                        <td>{due_date_str}</td>
                        <td>{engineer}</td>
                    </tr>
                """
                
            html_content += """
                </table>
                <p>Please ensure these maintenance tasks are completed on time.</p>
                <p>This is an automated reminder from the Hospital Equipment Maintenance System.</p>
            </body>
            </html>
            """
            
            data = {
                "SandboxMode": False,  # ⚠️ Add here
                "Messages": [
                    {
                    "From": { "Email": Config.EMAIL_SENDER, "Name": "Hospital Equipment Maintenance System" },
                    "To":   [ { "Email": target_email_receiver, "Name": "Recipient" } ],
                    "Subject": subject,
                    "HTMLPart": html_content,
                    "CustomID": "ReminderEmail"
                    }
                ]
            }

            logger.debug(f"Sending email from: {Config.EMAIL_SENDER} to: {target_email_receiver} with data: {json.dumps(data)}")
            result = mailjet.send.create(data=data)
            logger.debug(f"Mailjet API response: {result.status_code}, {result.json()}")

            if result.status_code == 200:
                logger.info(f"Reminder email sent for {len(upcoming)} upcoming maintenance tasks")
                return True
            else:
                logger.error(f"Failed to send reminder email: {result.status_code}, {result.json()}")
                return False
            
        except Exception as e:
            logger.exception(f"Failed to send reminder email: {str(e)}")
            return False

    @staticmethod
    def send_immediate_email(recipients: List[str], subject: str, html_content: str) -> bool:
        """Send an immediate email (for test emails or one-off notifications).
        
        Args:
            recipients: List of email addresses to send to
            subject: Email subject
            html_content: HTML content of the email
            
        Returns:
            True if email was sent successfully, False otherwise.
        """
        try:
            api_key = Config.MAILJET_API_KEY
            api_secret = Config.MAILJET_SECRET_KEY
            
            if not api_key or not api_secret:
                logger.error("Mailjet API credentials not configured. Cannot send email.")
                return False
            
            mailjet = Client(auth=(api_key, api_secret), version='v3.1')
            
            # Prepare recipients list
            to_list = [{"Email": email.strip(), "Name": "Recipient"} for email in recipients if email.strip()]
            
            if not to_list:
                logger.error("No valid recipients provided.")
                return False
            
            data = {
                "SandboxMode": False,
                "Messages": [
                    {
                        "From": {"Email": Config.EMAIL_SENDER, "Name": "Hospital Equipment Maintenance System"},
                        "To": to_list,
                        "Subject": subject,
                        "HTMLPart": html_content,
                        "CustomID": "ImmediateEmail"
                    }
                ]
            }
            
            logger.debug(f"Sending immediate email from: {Config.EMAIL_SENDER} to: {recipients}")
            result = mailjet.send.create(data=data)
            logger.debug(f"Mailjet API response: {result.status_code}, {result.json()}")
            
            if result.status_code == 200:
                logger.info(f"Immediate email sent successfully to {recipients}")
                return True
            else:
                logger.error(f"Failed to send immediate email: {result.status_code}, {result.json()}")
                return False
                
        except Exception as e:
            logger.exception(f"Failed to send immediate email: {str(e)}")
            return False
    
    @staticmethod
    async def send_threshold_reminder_email(upcoming: List[Tuple[str, str, str, str, str, str, int]], threshold_days: int, priority_level: str) -> bool:
        """Send reminder email for a specific time threshold.
        
        Args:
            upcoming: List of upcoming maintenance as (type, department, serial, description, due_date_str, engineer, days_until).
            threshold_days: Number of days threshold for this email.
            priority_level: Priority level (URGENT, HIGH, MEDIUM, LOW).
            
        Returns:
            True if email was sent successfully, False otherwise.
        """
        if not upcoming:
            logger.info(f"No upcoming maintenance found for {threshold_days} day threshold")
            return True
            
        try:
            from app.services.data_service import DataService
            settings = DataService.load_settings()
            recipient_email_override = settings.get("recipient_email", "").strip()
            cc_emails = settings.get("cc_emails", "").strip()

            target_email_receiver = recipient_email_override if recipient_email_override else Config.EMAIL_RECEIVER

            if not target_email_receiver:
                logger.error("Email recipient is not configured. Cannot send email.")
                return False

            api_key = Config.MAILJET_API_KEY
            api_secret = Config.MAILJET_SECRET_KEY
            mailjet = Client(auth=(api_key, api_secret), version='v3.1')
            
            # Determine email styling based on priority
            priority_colors = {
                'URGENT': {'bg': '#dc3545', 'text': 'white', 'icon': '🚨'},  # Red
                'HIGH': {'bg': '#fd7e14', 'text': 'white', 'icon': '⚠️'},    # Orange  
                'MEDIUM': {'bg': '#ffc107', 'text': 'black', 'icon': '⏰'},   # Yellow
                'LOW': {'bg': '#28a745', 'text': 'white', 'icon': '📅'}       # Green
            }
            
            color_config = priority_colors.get(priority_level, priority_colors['MEDIUM'])
            
            # Create subject based on threshold
            if threshold_days == 1:
                subject_text = f"URGENT: {len(upcoming)} Equipment Due for Maintenance TODAY!"
                time_description = "TODAY (within 24 hours)"
            elif threshold_days <= 7:
                subject_text = f"HIGH PRIORITY: {len(upcoming)} Equipment Due Within {threshold_days} Days"
                time_description = f"within {threshold_days} days"
            elif threshold_days <= 15:
                subject_text = f"MEDIUM PRIORITY: {len(upcoming)} Equipment Due Within {threshold_days} Days"
                time_description = f"within {threshold_days} days"
            else:
                subject_text = f"NOTICE: {len(upcoming)} Equipment Due Within {threshold_days} Days"
                time_description = f"within {threshold_days} days"
            
            # Create HTML content with enhanced styling
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 800px; margin: 0 auto; background-color: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }}
                    .header {{ background-color: {color_config['bg']}; color: {color_config['text']}; padding: 20px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 24px; }}
                    .header p {{ margin: 10px 0 0 0; font-size: 16px; opacity: 0.9; }}
                    .content {{ padding: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px 8px; text-align: left; }}
                    th {{ background-color: #f8f9fa; font-weight: bold; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    tr:hover {{ background-color: #e8f4fd; }}
                    .priority-badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
                    .urgent {{ background-color: #dc3545; color: white; }}
                    .high {{ background-color: #fd7e14; color: white; }}
                    .medium {{ background-color: #ffc107; color: black; }}
                    .low {{ background-color: #28a745; color: white; }}
                    .days-column {{ font-weight: bold; text-align: center; }}
                    .footer {{ padding: 20px; background-color: #f8f9fa; text-align: center; color: #6c757d; }}
                    .summary {{ background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{color_config['icon']} Equipment Maintenance Alert</h1>
                        <p>{len(upcoming)} equipment items require maintenance {time_description}</p>
                        <span class="priority-badge {priority_level.lower()}">{priority_level} PRIORITY</span>
                    </div>
                    <div class="content">
                        <div class="summary">
                            <strong>Summary:</strong> The following equipment requires maintenance attention {time_description}. 
                            Please review and schedule maintenance accordingly to ensure optimal equipment performance and safety.
                        </div>
                        <table>
                            <thead>
                                <tr>
                                    <th>Type</th>
                                    <th>Department</th>
                                    <th>Serial Number</th>
                                    <th>Description</th>
                                    <th>Due Date</th>
                                    <th>Days Until Due</th>
                                    <th>Engineer</th>
                                </tr>
                            </thead>
                            <tbody>
            """
            
            # Add equipment rows
            for task_type, department, serial, description, due_date_str, engineer, days_until in upcoming:
                # Color code days until due
                if days_until <= 1:
                    days_class = "urgent"
                elif days_until <= 7:
                    days_class = "high"
                elif days_until <= 15:
                    days_class = "medium"
                else:
                    days_class = "low"
                    
                html_content += f"""
                    <tr>
                        <td><strong>{task_type}</strong></td>
                        <td>{department}</td>
                        <td><strong>{serial}</strong></td>
                        <td>{description}</td>
                        <td>{due_date_str}</td>
                        <td class="days-column"><span class="priority-badge {days_class}">{days_until} day{'s' if days_until != 1 else ''}</span></td>
                        <td>{engineer}</td>
                    </tr>
                """
                
            html_content += f"""
                            </tbody>
                        </table>
                    </div>
                    <div class="footer">
                        <p><strong>Action Required:</strong> Please ensure these maintenance tasks are completed on time.</p>
                        <p>This is an automated reminder from the Hospital Equipment Maintenance System.</p>
                        <p><small>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Prepare recipient list
            to_list = [{"Email": target_email_receiver, "Name": "Maintenance Manager"}]
            
            # Add CC recipients if specified
            if cc_emails:
                cc_list = [{"Email": email.strip(), "Name": "CC Recipient"} for email in cc_emails.split(',') if email.strip()]
            else:
                cc_list = []
            
            data = {
                "SandboxMode": False,
                "Messages": [
                    {
                        "From": {"Email": Config.EMAIL_SENDER, "Name": "Hospital Equipment Maintenance System"},
                        "To": to_list,
                        "Cc": cc_list,
                        "Subject": subject_text,
                        "HTMLPart": html_content,
                        "CustomID": f"ThresholdReminder_{threshold_days}Days"
                    }
                ]
            }

            logger.debug(f"Sending {threshold_days}-day threshold email from: {Config.EMAIL_SENDER} to: {target_email_receiver}")
            result = mailjet.send.create(data=data)
            logger.debug(f"Mailjet API response: {result.status_code}, {result.json()}")

            if result.status_code == 200:
                logger.info(f"Successfully sent {threshold_days}-day threshold reminder email for {len(upcoming)} maintenance tasks")
                
                # Log to audit system
                try:
                    from app.services.audit_service import AuditService
                    AuditService.log_event(
                        event_type=AuditService.EVENT_TYPES['REMINDER_SENT'],
                        performed_by="System",
                        description=f"Email reminder sent for {len(upcoming)} equipment maintenance tasks ({threshold_days}-day threshold, {priority_level} priority)",
                        status=AuditService.STATUS_SUCCESS,
                        details={
                            "threshold_days": threshold_days,
                            "priority_level": priority_level,
                            "equipment_count": len(upcoming),
                            "recipient": target_email_receiver,
                            "email_type": "threshold_reminder"
                        }
                    )
                except Exception as audit_error:
                    logger.warning(f"Failed to log reminder email to audit system: {audit_error}")
                
                return True
            else:
                logger.error(f"Failed to send {threshold_days}-day threshold reminder email: {result.status_code}, {result.json()}")
                
                # Log failure to audit system
                try:
                    from app.services.audit_service import AuditService
                    AuditService.log_event(
                        event_type=AuditService.EVENT_TYPES['REMINDER_SENT'],
                        performed_by="System",
                        description=f"Failed to send email reminder for {len(upcoming)} equipment maintenance tasks ({threshold_days}-day threshold)",
                        status=AuditService.STATUS_FAILED,
                        details={
                            "threshold_days": threshold_days,
                            "priority_level": priority_level,
                            "equipment_count": len(upcoming),
                            "error_code": result.status_code,
                            "error_response": result.json()
                        }
                    )
                except Exception as audit_error:
                    logger.warning(f"Failed to log failed reminder email to audit system: {audit_error}")
                
                return False
            
        except Exception as e:
            logger.exception(f"Failed to send {threshold_days}-day threshold reminder email: {str(e)}")
            return False

    @staticmethod
    async def process_reminders():
        """Process and send reminders for upcoming maintenance with multiple thresholds."""
        from app.services.data_service import DataService
        logger.info("Starting enhanced process_reminders with multiple thresholds.")

        settings = {}
        try:
            settings = DataService.load_settings()
            logger.debug(f"Loaded settings in process_reminders: {settings}")
        except Exception as e:
            logger.error(f"Error loading settings in process_reminders: {str(e)}. Aborting reminder processing for this cycle.", exc_info=True)
            return

        email_enabled = settings.get("email_notifications_enabled", False)

        if not email_enabled:
            logger.info("Email notifications are disabled in settings. Skipping reminder sending.")
            return

        logger.info("Email notifications are ENABLED. Processing reminders with multiple thresholds.")
        
        try:
            # Load data
            logger.debug("Loading PPM and OCM data for reminders.")
            ppm_data = DataService.load_data('ppm')
            ocm_data = DataService.load_data('ocm')
            logger.debug(f"Loaded {len(ppm_data)} PPM entries and {len(ocm_data)} OCM entries.")

            # Define threshold configurations
            # Each threshold: (min_days, max_days, priority_level, threshold_name)
            thresholds = [
                (0, 1, 'URGENT', '1 Day'),           # Due today or tomorrow
                (2, 7, 'HIGH', '7 Days'),            # Due within 2-7 days  
                (8, 15, 'MEDIUM', '15 Days'),        # Due within 8-15 days
                (16, 30, 'LOW', '30 Days'),          # Due within 16-30 days
            ]

            emails_sent = 0
            total_tasks_found = 0

            for min_days, max_days, priority_level, threshold_name in thresholds:
                logger.debug(f"Processing {threshold_name} threshold ({min_days}-{max_days} days)...")
                
                # Get upcoming maintenance for this threshold
                upcoming_ppm = await EmailService.get_upcoming_maintenance_by_days(ppm_data, 'ppm', min_days, max_days)
                upcoming_ocm = await EmailService.get_upcoming_maintenance_by_days(ocm_data, 'ocm', min_days, max_days)
                
                # Combine and sort
                upcoming_combined = upcoming_ppm + upcoming_ocm
                upcoming_combined.sort(key=lambda x: x[6])  # Sort by days_until
                
                logger.info(f"Found {len(upcoming_combined)} tasks for {threshold_name} threshold")
                total_tasks_found += len(upcoming_combined)
                
                if upcoming_combined:
                    # Send email for this threshold
                    success = await EmailService.send_threshold_reminder_email(
                        upcoming_combined, 
                        max_days,  # Use max_days as the threshold for display purposes
                        priority_level
                    )
                    if success:
                        emails_sent += 1
                        logger.info(f"Successfully sent {threshold_name} threshold reminder email")
                    else:
                        logger.error(f"Failed to send {threshold_name} threshold reminder email")
                else:
                    logger.debug(f"No tasks found for {threshold_name} threshold - no email sent")

            logger.info(f"Enhanced reminder processing completed. Sent {emails_sent} emails for {total_tasks_found} total maintenance tasks.")

        except Exception as e:
            logger.error(f"Error during enhanced reminder processing: {str(e)}", exc_info=True)

        logger.info("Finished enhanced process_reminders.")
