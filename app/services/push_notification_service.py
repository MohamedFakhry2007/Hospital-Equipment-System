"""
Push Notification service for sending summarized maintenance reminders.
"""
import asyncio
import logging
import json # For constructing the push payload
from datetime import datetime
from typing import List, Dict, Any, Tuple
import os
import threading

from pywebpush import webpush, WebPushException

from app.services.email_service import EmailService
from app.config import Config
from app.services.data_service import DataService # Added for loading subscriptions

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service for sending push notifications."""

    logger.info("PushNotificationService class loading.")
    _scheduler_running = False
    _scheduler_lock = threading.Lock()

    @staticmethod
    async def run_scheduler_async_loop():
        """The actual asynchronous scheduler loop that runs periodically."""
        logger.info("Attempting to start Push Notification Scheduler async loop.")
        from app.services.data_service import DataService # Avoid circular import

        if PushNotificationService._scheduler_running:
            logger.info("Push Notification Scheduler loop is already marked as running in this process.")
            return

        with PushNotificationService._scheduler_lock:
            if PushNotificationService._scheduler_running:
                logger.info("Push Notification Scheduler loop already running (checked after acquiring lock).")
                return
            PushNotificationService._scheduler_running = True
            logger.info("Push Notification reminder scheduler async loop initiated in process ID: %s.", os.getpid())
            logger.warning("If running multiple application instances (e.g., Gunicorn workers), ensure this scheduler is enabled in only ONE instance if push logic isn't idempotent or if it involves external state not designed for concurrency.")


        try:
            initial_delay_seconds = 45  # Slightly different from email service for staggered starts
            logger.info(f"Push Notification Scheduler: Initial delay of {initial_delay_seconds} seconds before first run.")
            await asyncio.sleep(initial_delay_seconds)
            logger.info("Push Notification Scheduler: Initial delay complete. Starting main loop.")

            while True:
                logger.debug("Push Notification Scheduler: Loop iteration started.")
                settings = {}
                try:
                    logger.debug("Push Notification Scheduler: Loading settings...")
                    settings = DataService.load_settings()
                    logger.info(f"Push Notification Scheduler: Loaded settings: {settings}")
                except Exception as e:
                    logger.error(f"Push Notification Scheduler: Error loading settings: {str(e)}. Using defaults.", exc_info=True)
                    settings = {
                        "push_notifications_enabled": False,
                        "push_notification_interval_minutes": 60 # Default interval
                    }

                push_enabled = settings.get("push_notifications_enabled", False)
                logger.debug(f"Push Notification Scheduler: Push notifications enabled: {push_enabled}")
                interval_minutes = settings.get("push_notification_interval_minutes", 60)
                logger.debug(f"Push Notification Scheduler: Interval (minutes): {interval_minutes}")

                if not isinstance(interval_minutes, int) or interval_minutes <= 0:
                    logger.warning(f"Push Notification Scheduler: Invalid push_notification_interval_minutes: {interval_minutes}. Defaulting to 60 minutes.")
                    interval_minutes = 60

                interval_seconds = interval_minutes * 60
                logger.debug(f"Push Notification Scheduler: Interval (seconds): {interval_seconds}")

                if push_enabled:
                    logger.info("Push Notification Scheduler: Push notifications are ENABLED. Processing...")
                    try:
                        await PushNotificationService.process_push_notifications()
                        logger.info("Push Notification Scheduler: Finished processing push notifications for this iteration.")
                    except Exception as e:
                        logger.error(f"Push Notification Scheduler: Error during process_push_notifications: {str(e)}", exc_info=True)
                else:
                    logger.info("Push Notification Scheduler: Push notifications are DISABLED. Skipping processing.")

                logger.info(f"Push Notification Scheduler: Sleeping for {interval_minutes} minutes ({interval_seconds} seconds).")
                await asyncio.sleep(interval_seconds)
                logger.debug("Push Notification Scheduler: Woke up after sleep.")

        except asyncio.CancelledError:
            logger.info("Push Notification Scheduler: Loop was cancelled.")
        except Exception as e:
            logger.error(f"Push Notification Scheduler: Unhandled error in scheduler loop: {str(e)}", exc_info=True)
        finally:
            with PushNotificationService._scheduler_lock:
                PushNotificationService._scheduler_running = False
            logger.info("Push Notification Scheduler: Async loop has stopped.")

    @staticmethod
    def summarize_upcoming_maintenance(upcoming: List[Tuple[str, str, str, str, str, str]]) -> str:
        """
        Summarizes upcoming maintenance tasks for a concise push notification.
        Example: "3 PPM tasks and 2 OCM tasks due soon."
        """
        logger.debug(f"Summarizing upcoming maintenance. Tasks received: {len(upcoming)}")
        if not upcoming:
            logger.debug("No upcoming tasks to summarize.")
            return "No upcoming maintenance tasks."

        ppm_count = sum(1 for task in upcoming if task[0] == 'PPM')
        ocm_count = sum(1 for task in upcoming if task[0] == 'OCM')
        logger.debug(f"PPM count: {ppm_count}, OCM count: {ocm_count}")

        summary_parts = []
        if ppm_count > 0:
            summary_parts.append(f"{ppm_count} PPM task{'s' if ppm_count > 1 else ''}")
        if ocm_count > 0:
            summary_parts.append(f"{ocm_count} OCM task{'s' if ocm_count > 1 else ''}")

        if not summary_parts:
            logger.warning("Upcoming tasks present but could not categorize into PPM/OCM for summary.")
            return "Upcoming maintenance tasks found (unable to categorize)."

        summary = " and ".join(summary_parts) + " due soon."
        logger.debug(f"Generated summary: {summary}")
        return summary


    @staticmethod
    async def send_push_notification(summary_message: str):
        """
        Sends the push notification to all subscribed clients.
        """
        logger.info(f"Attempting to send push notification with summary: '{summary_message}'")

        if not Config.VAPID_PRIVATE_KEY or not Config.VAPID_SUBJECT:
            logger.error("VAPID_PRIVATE_KEY or VAPID_SUBJECT not configured. Cannot send push notifications.")
            return False
        logger.debug("VAPID configuration seems present.")

        logger.debug("Loading push subscriptions...")
        subscriptions = DataService.load_push_subscriptions()
        if not subscriptions:
            logger.info("No push subscriptions found. Nothing to send.")
            return True # No error, just no one to send to
        logger.info(f"Found {len(subscriptions)} push subscription(s).")

        if summary_message == "No upcoming maintenance tasks.":
            logger.info("Summary indicates no upcoming tasks. Push notification will not be sent.")
            # Optionally, you might still send a "no tasks" notification if desired
            # For now, we only send if there are tasks.
            return True

        logger.info(f"Preparing to send push notification: '{summary_message}' to {len(subscriptions)} subscription(s).")

        push_payload = {
            "title": "Equipment Maintenance Reminder",
            "body": summary_message,
            # "icon": "/static/img/notification_icon.png", # Optional: path to an icon
            # "data": {"url": "/"} # Optional: URL to open when notification is clicked
        }
        payload_json_str = json.dumps(push_payload)
        logger.debug(f"Push payload (JSON): {payload_json_str}")

        success_count = 0
        failure_count = 0
        subscriptions_to_remove = []

        for sub_info in subscriptions:
            endpoint_short = sub_info.get('endpoint', 'N/A')[:70] # For concise logging
            logger.debug(f"Processing subscription with endpoint starting: {endpoint_short}...")
            try:
                logger.info(f"Sending push notification to: {endpoint_short}...")
                webpush(
                    subscription_info=sub_info,
                    data=payload_json_str,
                    vapid_private_key=Config.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": Config.VAPID_SUBJECT}
                )
                logger.info(f"Successfully sent push notification to: {endpoint_short}.")
                success_count += 1
            except WebPushException as ex:
                logger.error(f"WebPushException while sending to {endpoint_short}: {ex}")
                if ex.response:
                    logger.error(f"Push server response status: {ex.response.status_code}, body: {ex.response.text}")
                    if ex.response.status_code in [404, 410]: # Gone or Not Found
                        logger.warning(f"Subscription {endpoint_short} is invalid (status {ex.response.status_code}). Marking for removal.")
                        subscriptions_to_remove.append(sub_info.get("endpoint"))
                else:
                    logger.error(f"WebPushException for {endpoint_short} did not have a response object.")
                failure_count += 1
            except Exception as e:
                logger.error(f"Unexpected error sending push notification to {endpoint_short}: {e}", exc_info=True)
                failure_count += 1

        if subscriptions_to_remove:
            logger.info(f"Attempting to remove {len(subscriptions_to_remove)} invalid/expired subscriptions.")
            removed_count = 0
            for endpoint_to_remove in subscriptions_to_remove:
                try:
                    DataService.remove_push_subscription(endpoint_to_remove)
                    logger.info(f"Successfully removed subscription: {endpoint_to_remove[:70]}...")
                    removed_count +=1
                except Exception as e:
                    logger.error(f"Failed to remove subscription {endpoint_to_remove[:70]}...: {e}", exc_info=True)
            logger.info(f"Finished removing subscriptions. Successfully removed: {removed_count}/{len(subscriptions_to_remove)}.")


        logger.info(f"Push notification sending attempt complete. Successes: {success_count}, Failures: {failure_count}.")
        # Return True if there were any successes, or if there were no failures and some subscriptions were targeted (even if 0 successes due to "no tasks")
        return success_count > 0 or (success_count == 0 and failure_count == 0 and len(subscriptions) > 0)


    @staticmethod
    async def process_push_notifications():
        """Process and send summarized push notifications for upcoming maintenance."""
        logger.info("Starting process_push_notifications method.")
        # DataService is already imported at the class level if needed, or can be imported here
        # from app.services.data_service import DataService

        logger.debug("Reloading settings within process_push_notifications...")
        settings = DataService.load_settings()
        logger.debug(f"Settings loaded in process_push_notifications: {settings}")

        if not settings.get("push_notifications_enabled", False):
            logger.info("Push notifications are disabled (checked within process_push_notifications). Skipping further processing.")
            return
        logger.info("Push notifications are enabled. Proceeding with data loading and processing.")

        try:
            logger.debug("Loading PPM data...")
            ppm_data = DataService.load_data('ppm')
            logger.debug(f"Loaded {len(ppm_data)} PPM entries.")

            logger.debug("Loading OCM data...")
            ocm_data = DataService.load_data('ocm')
            logger.debug(f"Loaded {len(ocm_data)} OCM entries.")

            logger.debug("Getting upcoming PPM maintenance tasks...")
            # Use EmailService's method to get upcoming tasks.
            # Config.REMINDER_DAYS will be used by default by get_upcoming_maintenance
            upcoming_ppm = await EmailService.get_upcoming_maintenance(ppm_data, data_type='ppm')
            logger.debug(f"Found {len(upcoming_ppm)} upcoming PPM tasks.")

            logger.debug("Getting upcoming OCM maintenance tasks...")
            upcoming_ocm = await EmailService.get_upcoming_maintenance(ocm_data, data_type='ocm')
            logger.debug(f"Found {len(upcoming_ocm)} upcoming OCM tasks.")

            upcoming_all = upcoming_ppm + upcoming_ocm
            logger.info(f"Total upcoming maintenance tasks (PPM & OCM): {len(upcoming_all)}")

            if upcoming_all:
                logger.debug("Sorting all upcoming tasks by date...")
                # Sort by date if needed, though summary doesn't strictly require it
                upcoming_all.sort(key=lambda x: EmailService.parse_date_flexible(x[4]))
                logger.debug("Tasks sorted.")

            logger.debug("Summarizing all upcoming tasks...")
            summary = PushNotificationService.summarize_upcoming_maintenance(upcoming_all)
            logger.info(f"Generated summary for push notification: '{summary}'")

            logger.debug("Sending push notification with the generated summary...")
            await PushNotificationService.send_push_notification(summary)
            logger.info("Push notification sending process initiated from process_push_notifications.")

        except Exception as e:
            logger.error(f"Error during push notification data processing or sending: {str(e)}", exc_info=True)

        logger.info("Finished process_push_notifications method.")
