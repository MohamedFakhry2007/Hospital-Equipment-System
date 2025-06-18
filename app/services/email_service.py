"""
Email service for sending maintenance reminders.
"""
import asyncio
import logging
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import List, Dict, Any, Tuple

from app.config import Config


logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications."""
    
    logger.debug("Initializing EmailService")
    
    async def get_upcoming_maintenance(
        self, # Add self
        ppm_data: List[Dict[str, Any]],
        ocm_data: List[Dict[str, Any]],
        days_ahead: int = None
    ) -> Dict[str, list]:
        """Get upcoming PPM and OCM maintenance within specified days.
        
        Args:
            ppm_data: List of PPM entries.
            ocm_data: List of OCM entries.
            days_ahead: Days ahead to check (default: from config).
            
        Returns:
            A dictionary with "ppm_tasks" and "ocm_tasks" lists.
            PPM tasks: (equipment, SERIAL, quarter, date, engineer)
            OCM tasks: (equipment_name, serial_number, next_maintenance_date, engineer, department)
        """
        if days_ahead is None:
            days_ahead = Config.REMINDER_DAYS
            
        now = datetime.now()
        results = {"ppm_tasks": [], "ocm_tasks": []}
        
        # Process PPM data
        if ppm_data:
            for entry in ppm_data:
                if entry.get('PPM', '').lower() != 'yes':
                    continue
                    
                for q in ['PPM_Q_I', 'PPM_Q_II', 'PPM_Q_III', 'PPM_Q_IV']:
                    q_data = entry.get(q, {})
                    if not q_data or not q_data.get('date'):
                        continue

                    try:
                        due_date = datetime.strptime(q_data['date'], '%d/%m/%Y')
                        days_until = (due_date - now).days

                        if 0 <= days_until <= days_ahead:
                            results["ppm_tasks"].append((
                                entry['EQUIPMENT'],
                                entry['SERIAL'],
                                q.replace('PPM_Q_', 'Quarter '),
                                q_data['date'],
                                q_data['engineer']
                            ))
                    except (ValueError, KeyError) as e:
                        logger.error(f"Error parsing PPM date for {entry.get('SERIAL', 'unknown')}, quarter {q}: {str(e)}")

        # Process OCM data
        if ocm_data:
            for entry in ocm_data:
                try:
                    next_maintenance_str = entry.get('Next_Maintenance')
                    if not next_maintenance_str:
                        continue

                    due_date = datetime.strptime(next_maintenance_str, '%d/%m/%Y')
                    days_until = (due_date - now).days
                    
                    if 0 <= days_until <= days_ahead:
                        results["ocm_tasks"].append((
                            entry['Name'],
                            entry['Serial'],
                            next_maintenance_str,
                            entry['Engineer'],
                            entry.get('Department', 'N/A')
                        ))
                except ValueError as e:
                    logger.error(f"Error parsing OCM date for {entry.get('Serial', 'unknown')}: {str(e)}. Date string: '{next_maintenance_str}'")
                except KeyError as e:
                    logger.error(f"Missing key for OCM entry {entry.get('Serial', 'unknown')}: {str(e)}")

        # Sort results
        try:
            results["ppm_tasks"].sort(key=lambda x: datetime.strptime(x[3], '%d/%m/%Y'))
        except ValueError as e:
            logger.error(f"Error sorting PPM tasks: {str(e)}")

        try:
            results["ocm_tasks"].sort(key=lambda x: datetime.strptime(x[2], '%d/%m/%Y'))
        except ValueError as e:
            logger.error(f"Error sorting OCM tasks: {str(e)}")

        return results

    def _send_email_sync(self, subject: str, html_content: str, sender: str, receiver: str) -> bool:
        """Synchronously sends an email.

        Args:
            subject: Email subject.
            html_content: Email HTML content.
            sender: Email sender address.
            receiver: Email receiver address.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        try:
            msg = EmailMessage()
            msg.set_content("Please view this email with an HTML-compatible email client.")
            msg.add_alternative(html_content, subtype='html')

            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = receiver

            # Send email
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Error in _send_email_sync: {str(e)}")
            return False

    async def send_reminder_email(self, upcoming_tasks: Dict[str, list]) -> bool:
        """Send reminder email for upcoming maintenance.
        
        Args:
            upcoming_tasks: Dictionary with "ppm_tasks" and "ocm_tasks".
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        ppm_tasks = upcoming_tasks.get("ppm_tasks", [])
        ocm_tasks = upcoming_tasks.get("ocm_tasks", [])

        if not ppm_tasks and not ocm_tasks:
            logger.info("No upcoming maintenance to send reminders for")
            return True
            
        total_tasks = len(ppm_tasks) + len(ocm_tasks)

        # Email content
        subject = f"Hospital Equipment Maintenance Reminder - {total_tasks} upcoming tasks"

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
        """

        if ppm_tasks:
            html_content += """
            <h3>PPM Tasks</h3>
            <table>
                <tr>
                    <th>Equipment</th>
                    <th>Serial Number</th>
                    <th>Quarter</th>
                    <th>Due Date</th>
                    <th>Engineer</th>
                </tr>
            """
            for equipment, serial, quarter, date, engineer in ppm_tasks:
                html_content += f"""
                    <tr>
                        <td>{equipment}</td>
                        <td>{serial}</td>
                        <td>{quarter}</td>
                        <td>{date}</td>
                        <td>{engineer}</td>
                    </tr>
                """
            html_content += "</table>"

        if ocm_tasks:
            html_content += """
            <h3>OCM Tasks</h3>
            <table>
                <tr>
                    <th>Equipment Name</th>
                    <th>Serial Number</th>
                    <th>Next Maintenance Date</th>
                    <th>Engineer</th>
                    <th>Department</th>
                </tr>
            """
            for name, serial, next_date, engineer, department in ocm_tasks:
                html_content += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{serial}</td>
                        <td>{next_date}</td>
                        <td>{engineer}</td>
                        <td>{department}</td>
                    </tr>
                """
            html_content += "</table>"
            
        html_content += """
            <p>Please ensure these maintenance tasks are completed on time.</p>
            <p>This is an automated reminder from the Hospital Equipment Maintenance System.</p>
        </body>
        </html>
        """

        try:
            loop = asyncio.get_event_loop()
            email_sent = await loop.run_in_executor(
                None,
                self._send_email_sync,
                subject,
                html_content,
                Config.EMAIL_SENDER,
                Config.EMAIL_RECEIVER
            )
            
            if email_sent:
                logger.info(f"Reminder email sent for {total_tasks} upcoming maintenance tasks")
            else:
                logger.error(f"Failed to send reminder email for {total_tasks} tasks (handled by _send_email_sync)")
            return email_sent
            
        except Exception as e:
            logger.error(f"Failed to send reminder email: {str(e)}")
            return False
    
    async def process_reminders(self):
        """Process and send reminders for upcoming maintenance."""
        from app.services.data_service import DataService
        
        try:
            # Load PPM and OCM data
            ppm_data = DataService.load_data('ppm')
            ocm_data = DataService.load_data('ocm') # Assuming DataService can load OCM data
            
            # Get upcoming maintenance
            upcoming_tasks = await self.get_upcoming_maintenance(ppm_data, ocm_data)
            
            # Send reminder if there are upcoming maintenance tasks
            if upcoming_tasks.get("ppm_tasks") or upcoming_tasks.get("ocm_tasks"):
                await self.send_reminder_email(upcoming_tasks)
            else:
                logger.info("No upcoming maintenance tasks found for PPM or OCM")
                
        except Exception as e:
            logger.error(f"Error processing reminders: {str(e)}")
            
    async def run_scheduler(self):
        """Run scheduler for periodic reminder sending."""
        if not Config.SCHEDULER_ENABLED:
            logger.info("Reminder scheduler is disabled")
            return
            
        logger.info(f"Starting reminder scheduler (interval: {Config.SCHEDULER_INTERVAL} hours)")
        
        while True:
            await self.process_reminders()
            await asyncio.sleep(Config.SCHEDULER_INTERVAL * 3600)  # Convert hours to seconds
