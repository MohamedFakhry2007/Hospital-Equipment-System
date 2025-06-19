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
        """The actual asynchronous scheduler loop."""
        if EmailService._scheduler_running:
            logger.info("Scheduler loop already running in this process.")
            return

        # Acquire lock before checking and setting _scheduler_running
        with EmailService._scheduler_lock:
            if EmailService._scheduler_running:
                logger.info("Scheduler loop already running in this process (checked after lock).")
                return
            EmailService._scheduler_running = True
            logger.info("Email reminder scheduler async loop started in process ID: %s.", os.getpid())
            logger.warning("If running multiple application instances (e.g., Gunicorn workers), ensure this scheduler is enabled in only ONE instance to avoid duplicate emails.")
        
        try:
            # Removed the while True loop to run reminders only once
            try:
                await EmailService.process_reminders()
            except Exception as e: # Catch specific errors if possible, e.g. related to email sending
                logger.error(f"Error processing reminders: {str(e)}")
        finally:
            # Ensure the flag is reset after the single execution
            with EmailService._scheduler_lock:
                EmailService._scheduler_running = False
            logger.info("Email reminder processing finished.")

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
                    "To":   [ { "Email": Config.EMAIL_RECEIVER, "Name": "Recipient" } ],
                    "Subject": subject,
                    "HTMLPart": html_content,
                    "CustomID": "ReminderEmail"
                    }
                ]
            }

            logger.debug(f"Sending email from: {Config.EMAIL_SENDER} to: {Config.EMAIL_RECEIVER} with data: {json.dumps(data)}")
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
        from app.services.data_service import DataService

        try:
            # Load PPM data
            ppm_data = DataService.load_data('ppm')

            # Load OCM data
            ocm_data = DataService.load_data('ocm')

            # Get upcoming maintenance for PPM
            upcoming_ppm = await EmailService.get_upcoming_maintenance(ppm_data, data_type='ppm')

            # Get upcoming maintenance for OCM
            upcoming_ocm = await EmailService.get_upcoming_maintenance(ocm_data, data_type='ocm')

            # Combine upcoming maintenance tasks
            upcoming = upcoming_ppm + upcoming_ocm

            # Sort the combined list by date (index 4 is due_date_str)
            upcoming.sort(key=lambda x: datetime.strptime(x[4], '%d/%m/%Y'))

            # Send reminder if there are upcoming maintenance tasks
            if upcoming:
                await EmailService.send_reminder_email(upcoming)
            else:
                logger.info("No upcoming maintenance tasks found")

        except Exception as e:
            logger.error(f"Error processing reminders: {str(e)}")
