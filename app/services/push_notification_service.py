"""
Push Notification service for sending summarized maintenance reminders.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
import os
import threading

# Assuming EmailService is in the same directory or adjust import path
from app.services.email_service import EmailService
from app.config import Config # For REMINDER_DAYS if not passed explicitly

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service for sending push notifications."""

    logger.debug("Initializing PushNotificationService")
    _scheduler_running = False
    _scheduler_lock = threading.Lock()

    @staticmethod
    async def run_scheduler_async_loop():
        """The actual asynchronous scheduler loop that runs periodically."""
        from app.services.data_service import DataService # Avoid circular import

        if PushNotificationService._scheduler_running:
            logger.info("Push Notification Scheduler loop already running in this process.")
            return

        with PushNotificationService._scheduler_lock:
            if PushNotificationService._scheduler_running:
                logger.info("Push Notification Scheduler loop already running (checked after lock).")
                return
            PushNotificationService._scheduler_running = True
            logger.info("Push Notification reminder scheduler async loop started in process ID: %s.", os.getpid())
            logger.warning("If running multiple application instances (e.g., Gunicorn workers), ensure this scheduler is enabled in only ONE instance if push logic isn't idempotent or if it involves external state not designed for concurrency.")


        try:
            initial_delay_seconds = 45  # Slightly different from email service for staggered starts
            logger.info(f"Push Notification Scheduler starting. Initial delay of {initial_delay_seconds} seconds before first run.")
            await asyncio.sleep(initial_delay_seconds)

            while True:
                logger.debug("Push Notification Scheduler loop iteration started.")
                settings = {}
                try:
                    settings = DataService.load_settings()
                    logger.debug(f"Loaded settings for Push Notification Service: {settings}")
                except Exception as e:
                    logger.error(f"Error loading settings in Push Notification scheduler loop: {str(e)}. Will use defaults and retry.", exc_info=True)
                    settings = {
                        "push_notifications_enabled": False,
                        "push_notification_interval_minutes": 60
                    }

                push_enabled = settings.get("push_notifications_enabled", False)
                interval_minutes = settings.get("push_notification_interval_minutes", 60)

                if not isinstance(interval_minutes, int) or interval_minutes <= 0:
                    logger.warning(f"Invalid push_notification_interval_minutes: {interval_minutes}. Defaulting to 60 minutes.")
                    interval_minutes = 60

                interval_seconds = interval_minutes * 60

                if push_enabled:
                    logger.info("Push notifications are ENABLED in settings. Processing push notifications.")
                    try:
                        await PushNotificationService.process_push_notifications()
                        logger.debug("Finished processing push notifications.")
                    except Exception as e:
                        logger.error(f"Error during process_push_notifications call in scheduler loop: {str(e)}", exc_info=True)
                else:
                    logger.info("Push notifications are DISABLED in settings. Skipping push notification processing.")

                logger.info(f"Push Notification Scheduler sleeping for {interval_minutes} minutes ({interval_seconds} seconds).")
                await asyncio.sleep(interval_seconds)
                logger.debug("Push Notification Scheduler awake after sleep.")

        except asyncio.CancelledError:
            logger.info("Push Notification Scheduler loop was cancelled.")
        except Exception as e:
            logger.error(f"Unhandled error in Push Notification scheduler loop: {str(e)}", exc_info=True)
        finally:
            with PushNotificationService._scheduler_lock:
                PushNotificationService._scheduler_running = False
            logger.info("Push Notification reminder scheduler async loop has stopped.")

    @staticmethod
    def summarize_upcoming_maintenance(upcoming: List[Tuple[str, str, str, str, str, str]]) -> str:
        """
        Summarizes upcoming maintenance tasks for a concise push notification.
        Example: "3 PPM tasks and 2 OCM tasks due soon."
        """
        if not upcoming:
            return "No upcoming maintenance tasks."

        ppm_count = sum(1 for task in upcoming if task[0] == 'PPM')
        ocm_count = sum(1 for task in upcoming if task[0] == 'OCM')

        summary_parts = []
        if ppm_count > 0:
            summary_parts.append(f"{ppm_count} PPM task{'s' if ppm_count > 1 else ''}")
        if ocm_count > 0:
            summary_parts.append(f"{ocm_count} OCM task{'s' if ocm_count > 1 else ''}")

        if not summary_parts: # Should not happen if upcoming is not empty, but good practice
            return "Upcoming maintenance tasks found (unable to categorize)."

        return " and ".join(summary_parts) + " due soon."


    @staticmethod
    async def send_push_notification(summary_message: str):
        """
        Sends the push notification.
        For now, this will just log the message.
        Actual implementation would involve Web Push API or a similar service.
        """
        if summary_message == "No upcoming maintenance tasks.":
            logger.info(f"Push Notification: {summary_message}")
        else:
            # In a real scenario, this is where you'd interact with a push service
            # (e.g., send a message to a VAPID endpoint for web push).
            logger.info(f"SENDING PUSH NOTIFICATION (Simulated): {summary_message}")
            # Placeholder for actual push sending logic
            # E.g., await some_web_push_library.send(subscription_info, summary_message)
        return True # Assuming success for now

    @staticmethod
    async def process_push_notifications():
        """Process and send summarized push notifications for upcoming maintenance."""
        from app.services.data_service import DataService # Avoid circular import

        logger.info("Starting process_push_notifications.")
        settings = DataService.load_settings() # Reload settings to ensure fresh check

        if not settings.get("push_notifications_enabled", False):
            logger.info("Push notifications are disabled (checked within process_push_notifications). Skipping.")
            return

        try:
            ppm_data = DataService.load_data('ppm')
            ocm_data = DataService.load_data('ocm')

            # Use EmailService's method to get upcoming tasks.
            # Config.REMINDER_DAYS will be used by default by get_upcoming_maintenance
            upcoming_ppm = await EmailService.get_upcoming_maintenance(ppm_data, data_type='ppm')
            upcoming_ocm = await EmailService.get_upcoming_maintenance(ocm_data, data_type='ocm')

            upcoming_all = upcoming_ppm + upcoming_ocm
            if upcoming_all:
                # Sort by date if needed, though summary doesn't strictly require it
                upcoming_all.sort(key=lambda x: datetime.strptime(x[4], '%d/%m/%Y'))

            summary = PushNotificationService.summarize_upcoming_maintenance(upcoming_all)
            await PushNotificationService.send_push_notification(summary)

            logger.info("Finished process_push_notifications.")

        except Exception as e:
            logger.error(f"Error during push notification data processing or sending: {str(e)}", exc_info=True)
        logger.info("Finished process_push_notifications (after try-except).")
