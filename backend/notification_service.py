import asyncio
import logging
from pathlib import Path
from typing import Optional, Literal
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to notifier.exe
NOTIFIER_PATH = Path(__file__).parent / "notifier.exe"

NotificationType = Literal["default", "alarm", "timer", "reminder"]

class NotificationService:
    """
    Service to handle notifications using notifier.exe CLI tool
    """
    
    @staticmethod
    async def send_notification(
        type_: NotificationType ,
        title: str, 
        message: str, 
        notification_id: Optional[str] = None
    ) -> bool:
        """
        Send a notification using notifier.exe
        
        Args:
            type_: Type of notification (default, alarm, timer, reminder)
            title: Notification title
            message: Notification message
            notification_id: Optional ID for alarm notifications (required for alarms)
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            # Build command
            cmd = [
                str(NOTIFIER_PATH),
                type_,
                title.capitalize(),
                message.capitalize()
            ]
            
            # Add ID for alarm type
            if type_ == "alarm":
                if not notification_id:
                    logger.error("Notification ID is required for alarm type")
                    return False
                cmd.append(notification_id)
            elif notification_id:
                # Add ID for other types if provided (e.g., timer)
                cmd.append(notification_id)
            
            logger.info(f"Sending notification: {cmd}")
            
            # Run notifier.exe
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=Path(__file__).parent
            )
            
            if result.returncode == 0:
                logger.info(f"Notification sent successfully: {title}")
                if result.stdout:
                    logger.debug(f"Notifier output: {result.stdout}")
                return True
            else:
                logger.error(f"Failed to send notification: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    @staticmethod
    async def send_alarm(title: str, message: str, alarm_id: str) -> bool:
        """
        Send an alarm notification with snooze/dismiss options
        
        Args:
            title: Alarm title
            message: Alarm message
            alarm_id: Unique alarm ID
            
        Returns:
            bool: True if alarm was sent successfully
        """
        return await NotificationService.send_notification("alarm", title, message, alarm_id)

    @staticmethod
    async def send_timer(title: str, message: str, timer_id: Optional[str] = None) -> bool:
        """
        Send a timer notification
        
        Args:
            title: Timer title
            message: Timer message
            timer_id: Optional timer ID
            
        Returns:
            bool: True if timer notification was sent successfully
        """
        return await NotificationService.send_notification("timer", title, message, timer_id)

    @staticmethod
    async def send_reminder(title: str, message: str) -> bool:
        """
        Send a reminder notification
        
        Args:
            title: Reminder title
            message: Reminder message
            
        Returns:
            bool: True if reminder was sent successfully
        """
        return await NotificationService.send_notification("reminder", title, message)

    @staticmethod
    async def send_default(title: str, message: str) -> bool:
        """
        Send a default notification
        
        Args:
            title: Notification title
            message: Notification message
            
        Returns:
            bool: True if notification was sent successfully
        """
        return await NotificationService.send_notification("default", title, message)


# Convenience functions for backward compatibility
async def send_notification_cli(
    type_: NotificationType,
    title: str,
    message: str,
    notification_id: Optional[str] = None
) -> bool:
    """
    Send notification using CLI tool
    """
    return await NotificationService.send_notification(type_, title, message, notification_id)

# Replace the old send_notification function
async def send_notification(title: str, message: str | dict, type_: str = "info"):
    """
    Updated send_notification to use notifier.exe instead of SSE
    Maps old notification types to new CLI types
    """
    # Convert message dict to string if needed
    if isinstance(message, dict):
        if "message" in message:
            message_text = message["message"]
        else:
            message_text = str(message)
    else:
        message_text = message
    
    # Map old types to new types
    notification_type: NotificationType
    if type_ in ["alarm", "timer", "reminder"]:
        notification_type = type_  # type: ignore
    else:
        notification_type = "default"
    
    # Extract ID if it's in the message dict
    notification_id = None
    if isinstance(message, dict) and "id" in message:
        notification_id = message["id"]
    
    return await NotificationService.send_notification(
        notification_type, title, message_text, notification_id
    )