import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Literal
from config import scheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytimeparse import parse as parse_time_duration

import logging
from agno.tools import Toolkit


logging.basicConfig(level=logging.INFO)
alarm_logger = logging.getLogger("alarms")

alarm_logger.info("Alarm system initialized.")



class AlarmTools(Toolkit):
    """
    Toolkit for managing alarms, timers, and reminders.
    """
    
    def __init__(self, **kwargs):
        # Instance storage for active items
        self.active_alarms: Dict[str, Dict[str, Any]] = {}
        self.active_timers: Dict[str, Dict[str, Any]] = {}
        self.active_reminders: Dict[str, Dict[str, Any]] = {}
        
        global _alarm_tools_instance
        if _alarm_tools_instance is None:
            _alarm_tools_instance = self

        super().__init__(
            name="alarm_tools",
            tools=[
                self.create_alarm,
                self.create_timer,
                self.create_reminder,
                self.list_active,
                self.delete_alarm_timer_reminder
            ],
            **kwargs
        )

    async def alarm_callback(self, alarm_id: str):
        """Callback when alarm triggers"""
        if alarm_id in self.active_alarms:
            alarm_data = self.active_alarms[alarm_id]
            alarm_logger.info(f"Alarm triggered: {alarm_data['name']}")
            
            # Send notification using notifier.exe
            from notification_service import NotificationService
            await NotificationService.send_alarm(
                alarm_data["name"],
                alarm_data.get("message", "Alarm!"),
                alarm_id
            )
            
            # Remove one-time alarms
            if not alarm_data.get("recurring"):
                del self.active_alarms[alarm_id]

    async def timer_callback(self, timer_id: str):
        """Callback when timer completes"""
        if timer_id in self.active_timers:
            timer_data = self.active_timers[timer_id]
            alarm_logger.info(f"Timer completed: {timer_data['name']}")
            
            # Send notification using notifier.exe
            from notification_service import NotificationService
            await NotificationService.send_timer(
                timer_data["name"],
                timer_data.get("message", "Timer completed!"),
                timer_id
            )
            
            # Remove completed timer
            del self.active_timers[timer_id]

    async def reminder_callback(self, reminder_id: str):
        """Callback when reminder triggers"""
        if reminder_id in self.active_reminders:
            reminder_data = self.active_reminders[reminder_id]
            alarm_logger.info(f"Reminder triggered: {reminder_data['name']}")
            
            # Send notification using notifier.exe
            from notification_service import NotificationService
            await NotificationService.send_reminder(
                reminder_data["name"],
                reminder_data["message"]
            )
            
            # Remove one-time reminders
            if not reminder_data.get("recurring"):
                del self.active_reminders[reminder_id]

    def create_alarm(self, name: str, time_str: str, message: str = "", recurring: str = "") -> str:
        """
        Create an alarm that will trigger at a specific time.

        Args:
            name (str): Name/description of the alarm.
            time_str (str): Time for alarm in format HH:MM, YYYY-MM-DD HH:MM, or relative time like "in 2 hours".
            message (str, optional): Optional message for the alarm.
            recurring (str, optional): Recurrence pattern (e.g., "daily", "weekly", "weekly on Mon,Wed,Fri").
        """
        alarm_id = f"alarm_{uuid.uuid4().hex[:8]}"
        
        try:
            now = datetime.now()
            
            # Try to parse as relative time first (e.g., "in 2 hours", "30 minutes")
            duration_seconds = parse_time_duration(time_str)
            if duration_seconds is not None:
                alarm_time = now + timedelta(seconds=duration_seconds)
            elif ":" in time_str and len(time_str) <= 5:
                # Format: HH:MM - schedule for today or tomorrow
                time_parts = time_str.split(":")
                hour, minute = int(time_parts[0]), int(time_parts[1])
                alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed today, schedule for tomorrow
                if alarm_time <= now:
                    alarm_time += timedelta(days=1)
            else:
                # Full datetime string
                alarm_time = datetime.fromisoformat(time_str)
            
            # Store alarm data
            self.active_alarms[alarm_id] = {
                "id": alarm_id,
                "name": name,
                "message": message,
                "time": alarm_time.isoformat(),
                "recurring": recurring,
                "created_at": now.isoformat()
            }
            
            # Schedule the alarm
            if recurring:
                if recurring == "daily":
                    trigger = CronTrigger(hour=alarm_time.hour, minute=alarm_time.minute)
                elif recurring.startswith("weekly"):
                    # Handle "weekly" and "weekly on Mon,Wed,Fri"
                    parts = recurring.split(" on ")
                    if len(parts) > 1:
                        days_of_week = parts[1]
                        trigger = CronTrigger(day_of_week=days_of_week, hour=alarm_time.hour, minute=alarm_time.minute)
                    else:
                        trigger = CronTrigger(day_of_week=alarm_time.weekday(), hour=alarm_time.hour, minute=alarm_time.minute)
                else:
                    # Fallback for simple recurring patterns if needed
                    trigger = DateTrigger(run_date=alarm_time)
            else:
                trigger = DateTrigger(run_date=alarm_time)
            
            scheduler.add_job(
                _alarm_job,
                trigger=trigger,
                args=[alarm_id],
                id=alarm_id
            )
            
            alarm_logger.info(f"Created alarm: {name} at {alarm_time}")
            return f"Alarm '{name}' set for {alarm_time.strftime('%Y-%m-%d %H:%M')}"
            
        except Exception as e:
            alarm_logger.error(f"Error creating alarm: {e}")
            return f"Failed to create alarm: {str(e)}"

    def create_timer(self, duration_str: str, name: str = "Timer", message: str = "") -> str:
        """
        Create a timer that will trigger after a specific duration.

        Args:
            name (str): Name/description of the timer.
            duration_str (str): Duration like "30 minutes", "2h30m", "1.5 hours", etc.
            message (str, optional): Optional message when timer completes.
        """
        timer_id = f"timer_{uuid.uuid4().hex[:8]}"
        
        try:
            # Parse duration using pytimeparse
            duration_seconds = parse_time_duration(duration_str)
            if duration_seconds is None:
                return f"Failed to parse duration: {duration_str}"
            
            now = datetime.now()
            end_time = now + timedelta(seconds=duration_seconds)
            
            # Store timer data
            self.active_timers[timer_id] = {
                "id": timer_id,
                "name": name,
                "message": message,
                "duration_str": duration_str,
                "duration_seconds": duration_seconds,
                "start_time": now.isoformat(),
                "end_time": end_time.isoformat()
            }
            
            # Schedule the timer
            scheduler.add_job(
                _timer_job,
                trigger=DateTrigger(run_date=end_time),
                args=[timer_id],
                id=timer_id
            )
            
            alarm_logger.info(f"Created timer: {name} for {duration_str}")
            return f"Timer '{name}' set for {duration_str}"
            
        except Exception as e:
            alarm_logger.error(f"Error creating timer: {e}")
            return f"Failed to create timer: {str(e)}"

    def create_reminder(self, name: str, message: str, time_str: str = "",  recurring: str = "") -> str:
        """
        Create a reminder that will trigger at a specific time with a message.

        Args:
            name (str): Name/description of the reminder.
            message (str): Reminder message.
            time_str (str): Time for reminder in format HH:MM, YYYY-MM-DD HH:MM, or relative time like "in 1 hour". Can be empty for interval reminders.
            recurring (str, optional): Recurrence pattern (daily, weekly, hourly, or interval like "every 10 minutes"). 
        """
        reminder_id = f"reminder_{uuid.uuid4().hex[:8]}"
        
        try:
            now = datetime.now()
            
            # Handle recurring reminders with intervals
            if recurring.startswith("every "):
                # Parse "every X minutes/hours/days"
                interval_part = recurring.replace("every ", "")
                duration_seconds = parse_time_duration(interval_part)
                if duration_seconds is None:
                    return f"Failed to parse interval: {recurring}"
                
                # Store reminder data
                self.active_reminders[reminder_id] = {
                    "id": reminder_id,
                    "name": name,
                    "message": message,
                    "recurring": recurring,
                    "interval_seconds": duration_seconds,
                    "created_at": now.isoformat()
                }
                
                # Schedule with IntervalTrigger
                scheduler.add_job(
                    _reminder_job,
                    trigger=IntervalTrigger(seconds=int(duration_seconds)),
                    args=[reminder_id],
                    id=reminder_id
                )
                
                alarm_logger.info(f"Created recurring reminder: {name} {recurring}")
                return f"Recurring reminder '{name}' set for {recurring}"
            
            # Try to parse as relative time first (e.g., "in 1 hour", "30 minutes")
            parseable_time_str = time_str.lower().replace("in ", "")
            duration_seconds = parse_time_duration(parseable_time_str)
            if duration_seconds is not None:
                reminder_time = now + timedelta(seconds=duration_seconds)
            elif ":" in time_str and len(time_str) <= 5:
                # Format: HH:MM
                time_parts = time_str.split(":")
                hour, minute = int(time_parts[0]), int(time_parts[1])
                reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if reminder_time <= now:
                    reminder_time += timedelta(days=1)
            elif time_str: # Ensure time_str is not empty before trying to parse
                # Full datetime string
                reminder_time = datetime.fromisoformat(time_str)
            else:
                return "Failed to create reminder: time_str is empty and no valid recurring interval was provided."
            
            # Store reminder data
            self.active_reminders[reminder_id] = {
                "id": reminder_id,
                "name": name,
                "message": message,
                "time": reminder_time.isoformat(),
                "recurring": recurring,
                "created_at": now.isoformat()
            }
            
            # Schedule the reminder
            if recurring == "daily":
                trigger = CronTrigger(hour=reminder_time.hour, minute=reminder_time.minute)
            elif recurring == "weekly":
                trigger = CronTrigger(day_of_week=reminder_time.weekday(), 
                                    hour=reminder_time.hour, minute=reminder_time.minute)
            elif recurring == "hourly":
                trigger = CronTrigger(minute=reminder_time.minute)
            else:
                trigger = DateTrigger(run_date=reminder_time)
            
            scheduler.add_job(
                _reminder_job,
                trigger=trigger,
                args=[reminder_id],
                id=reminder_id
            )
            
            alarm_logger.info(f"Created reminder: {name} at {reminder_time}")
            return f"Reminder '{name}' set for {reminder_time.strftime('%Y-%m-%d %H:%M')}"
            
        except Exception as e:
            alarm_logger.error(f"Error creating reminder: {e}")
            return f"Failed to create reminder: {str(e)}"

    def list_active(self, item_type: Literal['alarms', 'timers', 'reminders']) -> str:
        """
        List all active alarms, timers, or reminders.

        Args:
            item_type (str): One of 'alarms', 'timers', or 'reminders'.
        """
        if item_type == "alarms":
            items = self.active_alarms
            if not items:
                return "No active alarms"
            item_list = [
                f"- {data['name']} at {data['time']}"
                for data in items.values()
            ]
            return "Active alarms:\n" + "\n".join(item_list)
        elif item_type == "timers":
            items = self.active_timers
            if not items:
                return "No active timers"
            item_list = [
                f"- {data['name']} ({data['duration_str']})"
                for data in items.values()
            ]
            return "Active timers:\n" + "\n".join(item_list)
        elif item_type == "reminders":
            items = self.active_reminders
            if not items:
                return "No active reminders"
            item_list = []
            for data in items.values():
                if "time" in data:
                    item_list.append(f"- {data['name']} at {data['time']}")
                else:
                    item_list.append(f"- {data['name']} ({data.get('recurring', 'recurring')})")
            return "Active reminders:\n" + "\n".join(item_list)
        else:
            return "Invalid type. Use 'alarms', 'timers', or 'reminders'."

    def delete_alarm_timer_reminder(self, name_or_id: str) -> str:
        """
        Delete an alarm, timer, or reminder by name or ID.

        Args:
            name_or_id (str): Name or ID of the alarm/timer/reminder to delete.
        """
        try:
            deleted_items = []
            
            # Check alarms
            for alarm_id, alarm_data in list(self.active_alarms.items()):
                if alarm_id == name_or_id or alarm_data["name"].lower() == name_or_id.lower():
                    # Remove from scheduler
                    try:
                        scheduler.remove_job(alarm_id)
                    except Exception:
                        pass  # Job might not exist in scheduler
                    
                    # Remove from active alarms
                    del self.active_alarms[alarm_id]
                    deleted_items.append(f"alarm '{alarm_data['name']}'")
                    break
            
            # Check timers
            for timer_id, timer_data in list(self.active_timers.items()):
                if timer_id == name_or_id or timer_data["name"].lower() == name_or_id.lower():
                    # Remove from scheduler
                    try:
                        scheduler.remove_job(timer_id)
                    except Exception:
                        pass  # Job might not exist in scheduler
                    
                    # Remove from active timers
                    del self.active_timers[timer_id]
                    deleted_items.append(f"timer '{timer_data['name']}'")
                    break
            
            # Check reminders
            for reminder_id, reminder_data in list(self.active_reminders.items()):
                if reminder_id == name_or_id or reminder_data["name"].lower() == name_or_id.lower():
                    # Remove from scheduler
                    try:
                        scheduler.remove_job(reminder_id)
                    except Exception:
                        pass  # Job might not exist in scheduler
                    
                    # Remove from active reminders
                    del self.active_reminders[reminder_id]
                    deleted_items.append(f"reminder '{reminder_data['name']}'")
                    break
            
            if deleted_items:
                alarm_logger.info(f"Deleted: {', '.join(deleted_items)}")
                return f"Successfully deleted: {', '.join(deleted_items)}"
            else:
                return f"No alarm, timer, or reminder found with name/ID: {name_or_id}"
                
        except Exception as e:
            alarm_logger.error(f"Error deleting item: {e}")
            return f"Failed to delete item: {str(e)}"


# Add module-level wrapper callbacks so APScheduler can pickle them
async def _alarm_job(alarm_id: str):
    inst = get_alarm_tools_instance()
    await inst.alarm_callback(alarm_id)

async def _timer_job(timer_id: str):
    inst = get_alarm_tools_instance()
    await inst.timer_callback(timer_id)

async def _reminder_job(reminder_id: str):
    inst = get_alarm_tools_instance()
    await inst.reminder_callback(reminder_id)

# Global function to handle alarm snoozing from notification actions
async def handle_alarm_snooze(alarm_id: str, snooze_minutes: int = 5) -> str:
    """
    Handle alarm snooze action by rescheduling the alarm
    
    Args:
        alarm_id: ID of the alarm to snooze
        snooze_minutes: Number of minutes to snooze (default: 5)
        
    Returns:
        str: Result message
    """
    try:
        # Find the alarm tools instance (we need to access the active_alarms dict)
        # Since this is a global function, we need to get the instance from somewhere
        # For now, we'll access it through the scheduler jobs
        
        # Get all alarm tool instances from active jobs
        for job in scheduler.get_jobs():
            if job.id.startswith("alarm_") and job.id == alarm_id:
                # Calculate new snooze time
                snooze_time = datetime.now() + timedelta(minutes=snooze_minutes)
                
                # Remove the current job
                scheduler.remove_job(alarm_id)
                
                # Get alarm data from job args or reconstruct
                alarm_logger.info(f"Snoozing alarm {alarm_id} for {snooze_minutes} minutes until {snooze_time}")
                
                # Reschedule the alarm
                scheduler.add_job(
                    snooze_alarm_callback,
                    trigger=DateTrigger(run_date=snooze_time),
                    args=[alarm_id, snooze_minutes],
                    id=f"snooze_{alarm_id}_{int(datetime.now().timestamp())}"
                )
                
                return f"Alarm snoozed for {snooze_minutes} minutes until {snooze_time.strftime('%H:%M')}"
        
        alarm_logger.warning(f"Alarm {alarm_id} not found for snoozing")
        return f"Alarm {alarm_id} not found"
        
    except Exception as e:
        alarm_logger.error(f"Error snoozing alarm {alarm_id}: {e}")
        return f"Failed to snooze alarm: {str(e)}"


async def snooze_alarm_callback(original_alarm_id: str, snooze_count: int = 1):
    """
    Callback for snoozed alarms
    
    Args:
        original_alarm_id: Original alarm ID
        snooze_count: Number of times this alarm has been snoozed
    """
    try:
        from notification_service import NotificationService
        
        # Send the alarm notification again
        title = f"Snoozed Alarm (#{snooze_count})"
        message = "Your snoozed alarm is now going off again"
        
        alarm_logger.info(f"Snoozed alarm {original_alarm_id} triggered (snooze #{snooze_count})")
        
        # Send notification with the original alarm ID so it can be snoozed again
        await NotificationService.send_alarm(title, message, original_alarm_id)
        
    except Exception as e:
        alarm_logger.error(f"Error in snooze callback for {original_alarm_id}: {e}")


# Create a global instance for accessing alarm data
_alarm_tools_instance = None

def get_alarm_tools_instance():
    """Get or create global alarm tools instance"""
    global _alarm_tools_instance
    if _alarm_tools_instance is None:
        _alarm_tools_instance = AlarmTools()
    return _alarm_tools_instance

