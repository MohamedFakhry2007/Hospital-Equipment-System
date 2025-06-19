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
                    try:
                        await EmailService.process_reminders()
                        logger.debug("Finished processing reminders.")
                    except Exception as e:
                        logger.error(f"Error during process_reminders call in scheduler loop: {str(e)}", exc_info=True)
                else:
                    logger.info("Email notifications are DISABLED in settings. Skipping reminder processing.")

                logger.info(f"Scheduler sleeping for {interval_minutes} minutes ({interval_seconds} seconds).")
                await asyncio.sleep(interval_seconds)
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

                        due_date_obj = datetime.strptime(ppm_due_date_str, '%d/%m/%Y')
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
                    due_date_obj = datetime.strptime(due_date_str, '%d/%m/%Y')
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
        upcoming.sort(key=lambda x: datetime.strptime(x[4], '%d/%m/%Y'))
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
    async def process_reminders():
        """Process and send reminders for upcoming maintenance."""
        from app.services.data_service import DataService # Keep import here for clarity within this static method
        logger.info("Starting process_reminders.")

        settings = {}
        try:
            # Load application settings
            settings = DataService.load_settings()
            logger.debug(f"Loaded settings in process_reminders: {settings}")
        except Exception as e:
            logger.error(f"Error loading settings in process_reminders: {str(e)}. Aborting reminder processing for this cycle.", exc_info=True)
            return # Stop processing if settings can't be loaded

        email_enabled = settings.get("email_notifications_enabled", False) # Default to False if key is missing or settings are malformed

        if not email_enabled:
            logger.info("Email notifications are disabled in settings (checked within process_reminders). Skipping actual reminder sending.")
            logger.info("Finished process_reminders (email disabled).")
            return

        logger.info("Email notifications are ENABLED in settings (checked within process_reminders). Proceeding to gather data.")
        try:
            # Load PPM data
            logger.debug("Loading PPM data for reminders.")
            ppm_data = DataService.load_data('ppm')
            logger.debug(f"Loaded {len(ppm_data)} PPM entries.")

            # Load OCM data
            ocm_data = DataService.load_data('ocm')

            # Get upcoming maintenance for PPM
            logger.debug("Getting upcoming PPM maintenance tasks.")
            upcoming_ppm = await EmailService.get_upcoming_maintenance(ppm_data, data_type='ppm')
            logger.debug(f"Found {len(upcoming_ppm)} upcoming PPM tasks.")

            # Get upcoming maintenance for OCM
            logger.debug("Getting upcoming OCM maintenance tasks.")
            upcoming_ocm = await EmailService.get_upcoming_maintenance(ocm_data, data_type='ocm')
            logger.debug(f"Found {len(upcoming_ocm)} upcoming OCM tasks.")

            # Combine upcoming maintenance tasks
            upcoming = upcoming_ppm + upcoming_ocm
            logger.debug(f"Total upcoming tasks combined: {len(upcoming)}.")

            # Sort the combined list by date (index 4 is due_date_str)
            if upcoming:
                upcoming.sort(key=lambda x: datetime.strptime(x[4], '%d/%m/%Y'))
                logger.debug("Sorted upcoming tasks by due date.")

            # Send reminder if there are upcoming maintenance tasks
            if upcoming:
                logger.info(f"Found {len(upcoming)} tasks. Attempting to send reminder email.")
                await EmailService.send_reminder_email(upcoming)
            else:
                logger.info("No upcoming maintenance tasks found to send email for.")

            logger.info("Finished process_reminders (email enabled path).")

        except Exception as e:
            logger.error(f"Error during reminder data processing or email sending in process_reminders: {str(e)}", exc_info=True)
        logger.info("Finished process_reminders.")
