"""
Event Scheduler - Database-based event scheduling system
Creates scheduled events in database for external app to handle
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pytz
import json
import sqlite3
import uuid
from pathlib import Path


class EventScheduler:
    """
    Database-based event scheduling system.
    Creates scheduled events that external apps can process.
    """

    def __init__(self, data_dir: str = "./fusesell_data"):
        """
        Initialize the event scheduler.

        Args:
            data_dir: Directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        
        # Database path
        self.main_db_path = self.data_dir / "fusesell.db"
        
        # Initialize scheduled events database
        self._initialize_scheduled_events_db()
        
        # Initialize scheduling rules database
        self._initialize_scheduling_rules_db()

    def _initialize_scheduled_events_db(self):
        """Initialize database table for scheduled events."""
        try:
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_events (
                    id TEXT PRIMARY KEY,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    scheduled_time TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    org_id TEXT NOT NULL,
                    team_id TEXT,
                    draft_id TEXT,
                    recipient_address TEXT NOT NULL,
                    recipient_name TEXT,
                    customer_timezone TEXT,
                    event_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    error_message TEXT
                )
            """)
            
            # Create index for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scheduled_events_time_status 
                ON scheduled_events(scheduled_time, status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_scheduled_events_org_team 
                ON scheduled_events(org_id, team_id)
            """)
            
            conn.commit()
            conn.close()
            
            self.logger.info("Scheduled events database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize scheduled events DB: {str(e)}")
            raise

    def _initialize_scheduling_rules_db(self):
        """Initialize database table for scheduling rules."""
        try:
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduling_rules (
                    id TEXT PRIMARY KEY,
                    org_id TEXT NOT NULL,
                    team_id TEXT,
                    rule_name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    business_hours_start TEXT DEFAULT '08:00',
                    business_hours_end TEXT DEFAULT '20:00',
                    default_delay_hours INTEGER DEFAULT 2,
                    timezone TEXT DEFAULT 'Asia/Bangkok',
                    follow_up_delay_hours INTEGER DEFAULT 120,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(org_id, team_id, rule_name)
                )
            """)
            
            # Create default rule if none exists
            cursor.execute("""
                INSERT OR IGNORE INTO scheduling_rules 
                (id, org_id, team_id, rule_name, business_hours_start, business_hours_end, 
                 default_delay_hours, timezone, follow_up_delay_hours)
                VALUES (?, 'default', 'default', 'default_rule', '08:00', '20:00', 2, 'Asia/Bangkok', 120)
            """, (f"uuid:{str(uuid.uuid4())}",))
            
            conn.commit()
            conn.close()
            
            self.logger.info("Scheduling rules database initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize scheduling rules DB: {str(e)}")
            raise

    def schedule_email_event(self, draft_id: str, recipient_address: str, recipient_name: str,
                           org_id: str, team_id: str = None, customer_timezone: str = None,
                           email_type: str = 'initial', send_immediately: bool = False) -> Dict[str, Any]:
        """
        Schedule an email event in the database for external app to handle.

        Args:
            draft_id: ID of the email draft to send
            recipient_address: Email address of recipient
            recipient_name: Name of recipient
            org_id: Organization ID
            team_id: Team ID (optional)
            customer_timezone: Customer's timezone (optional)
            email_type: Type of email ('initial' or 'follow_up')
            send_immediately: If True, schedule for immediate sending

        Returns:
            Event creation result with event ID and scheduled time
        """
        try:
            # Get scheduling rule for the team
            rule = self._get_scheduling_rule(org_id, team_id)
            
            # Determine customer timezone
            if not customer_timezone:
                customer_timezone = rule.get('timezone', 'Asia/Bangkok')
            
            # Calculate optimal send time
            if send_immediately:
                send_time = datetime.utcnow()
            else:
                send_time = self._calculate_send_time(rule, customer_timezone)
            
            # Create event ID
            event_id = f"uuid:{str(uuid.uuid4())}"
            event_type = "email"
            related_draft_id = draft_id
            
            # Prepare event data
            event_data = {
                'draft_id': draft_id,
                'email_type': email_type,
                'org_id': org_id,
                'team_id': team_id,
                'customer_timezone': customer_timezone,
                'send_immediately': send_immediately
            }
            
            # Insert scheduled event into database
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scheduled_events 
                (id, event_id, event_type, scheduled_time, org_id, team_id, draft_id,
                 recipient_address, recipient_name, customer_timezone, event_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"uuid:{str(uuid.uuid4())}", event_id, 'email_send', send_time, org_id, team_id, draft_id,
                recipient_address, recipient_name, customer_timezone, json.dumps(event_data)
            ))
            
            conn.commit()
            conn.close()
            
            # Log the scheduling
            self.logger.info(f"Scheduled email event {event_id} for {send_time} (draft: {draft_id})")
            
            # Schedule follow-up if this is an initial email
            follow_up_event_id = None
            if email_type == 'initial' and not send_immediately:
                follow_up_result = self._schedule_follow_up_event(
                    draft_id, recipient_address, recipient_name, org_id, team_id, customer_timezone
                )
                follow_up_event_id = follow_up_result.get('event_id')
            
            return {
                'success': True,
                'event_id': event_id,
                'scheduled_time': send_time.isoformat(),
                'recipient_address': recipient_address,
                'recipient_name': recipient_name,
                'draft_id': draft_id,
                'email_type': email_type,
                'follow_up_event_id': follow_up_event_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to schedule email event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _schedule_follow_up_event(self, original_draft_id: str, recipient_address: str, 
                                recipient_name: str, org_id: str, team_id: str = None,
                                customer_timezone: str = None) -> Dict[str, Any]:
        """
        Schedule follow-up email event after initial email.

        Args:
            original_draft_id: ID of the original draft
            recipient_address: Email address of recipient
            recipient_name: Name of recipient
            org_id: Organization ID
            team_id: Team ID (optional)
            customer_timezone: Customer's timezone (optional)

        Returns:
            Follow-up event creation result
        """
        try:
            # Get scheduling rule
            rule = self._get_scheduling_rule(org_id, team_id)
            
            # Calculate follow-up time (default: 5 days after initial send)
            follow_up_delay = rule.get('follow_up_delay_hours', 120)  # 120 hours = 5 days
            follow_up_time = datetime.utcnow() + timedelta(hours=follow_up_delay)
            
            # Create follow-up event ID
            followup_event_id = f"uuid:{str(uuid.uuid4())}"
            followup_event_type = "followup"
            related_original_draft_id = original_draft_id
            
            # Prepare event data
            event_data = {
                'original_draft_id': original_draft_id,
                'email_type': 'follow_up',
                'org_id': org_id,
                'team_id': team_id,
                'customer_timezone': customer_timezone or rule.get('timezone', 'Asia/Bangkok')
            }
            
            # Insert follow-up event into database
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scheduled_events 
                (id, event_id, event_type, scheduled_time, org_id, team_id, draft_id,
                 recipient_address, recipient_name, customer_timezone, event_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"uuid:{str(uuid.uuid4())}", followup_event_id, 'email_follow_up', follow_up_time, org_id, team_id, 
                original_draft_id, recipient_address, recipient_name, 
                customer_timezone, json.dumps(event_data)
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Scheduled follow-up event {followup_event_id} for {follow_up_time}")
            
            return {
                'success': True,
                'event_id': followup_event_id,
                'scheduled_time': follow_up_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to schedule follow-up event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_scheduling_rule(self, org_id: str, team_id: str = None) -> Dict[str, Any]:
        """
        Get scheduling rule for organization/team.

        Args:
            org_id: Organization ID
            team_id: Team ID (optional)

        Returns:
            Scheduling rule dictionary
        """
        try:
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            
            # Try to get team-specific settings from team_settings table first
            if team_id:
                cursor.execute("""
                    SELECT gs_team_schedule_time
                    FROM team_settings 
                    WHERE team_id = ?
                """, (team_id,))
                
                row = cursor.fetchone()
                if row and row[0]:
                    try:
                        schedule_settings = json.loads(row[0])
                        if schedule_settings:
                            self.logger.debug(f"Using team settings for scheduling: {team_id}")
                            conn.close()
                            # Convert team settings to scheduling rule format
                            return {
                                'business_hours_start': schedule_settings.get('business_hours_start', '08:00'),
                                'business_hours_end': schedule_settings.get('business_hours_end', '20:00'),
                                'default_delay_hours': schedule_settings.get('default_delay_hours', 2),
                                'timezone': schedule_settings.get('timezone', 'Asia/Bangkok'),
                                'follow_up_delay_hours': schedule_settings.get('follow_up_delay_hours', 120),
                                'avoid_weekends': schedule_settings.get('avoid_weekends', True)
                            }
                    except (json.JSONDecodeError, TypeError) as e:
                        self.logger.warning(f"Failed to parse team schedule settings: {e}")
                
                # Fall back to scheduling_rules table for team-specific rule
                cursor.execute("""
                    SELECT business_hours_start, business_hours_end, default_delay_hours,
                           timezone, follow_up_delay_hours
                    FROM scheduling_rules 
                    WHERE org_id = ? AND team_id = ? AND is_active = 1
                    ORDER BY updated_at DESC LIMIT 1
                """, (org_id, team_id))
                
                row = cursor.fetchone()
                if row:
                    conn.close()
                    return {
                        'business_hours_start': row[0],
                        'business_hours_end': row[1],
                        'default_delay_hours': row[2],
                        'timezone': row[3],
                        'follow_up_delay_hours': row[4]
                    }
            
            # Fall back to org-specific rule
            cursor.execute("""
                SELECT business_hours_start, business_hours_end, default_delay_hours,
                       timezone, follow_up_delay_hours
                FROM scheduling_rules 
                WHERE org_id = ? AND is_active = 1
                ORDER BY updated_at DESC LIMIT 1
            """, (org_id,))
            
            row = cursor.fetchone()
            if row:
                conn.close()
                return {
                    'business_hours_start': row[0],
                    'business_hours_end': row[1],
                    'default_delay_hours': row[2],
                    'timezone': row[3],
                    'follow_up_delay_hours': row[4]
                }
            
            # Fall back to default rule
            cursor.execute("""
                SELECT business_hours_start, business_hours_end, default_delay_hours,
                       timezone, follow_up_delay_hours
                FROM scheduling_rules 
                WHERE org_id = 'default' AND is_active = 1
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'business_hours_start': row[0],
                    'business_hours_end': row[1],
                    'default_delay_hours': row[2],
                    'timezone': row[3],
                    'follow_up_delay_hours': row[4]
                }
            
            # Ultimate fallback
            return {
                'business_hours_start': '08:00',
                'business_hours_end': '20:00',
                'default_delay_hours': 2,
                'timezone': 'Asia/Bangkok',
                'follow_up_delay_hours': 120
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get scheduling rule: {str(e)}")
            # Return default rule
            return {
                'business_hours_start': '08:00',
                'business_hours_end': '20:00',
                'default_delay_hours': 2,
                'timezone': 'Asia/Bangkok',
                'follow_up_delay_hours': 120
            }

    def _calculate_send_time(self, rule: Dict[str, Any], customer_timezone: str) -> datetime:
        """
        Calculate optimal send time based on scheduling rule and customer timezone.

        Args:
            rule: Scheduling rule dictionary
            customer_timezone: Customer's timezone

        Returns:
            Optimal send time in UTC
        """
        try:
            # Validate timezone
            try:
                customer_tz = pytz.timezone(customer_timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                self.logger.warning(f"Unknown timezone '{customer_timezone}', using default")
                customer_tz = pytz.timezone(rule.get('timezone', 'Asia/Bangkok'))
                customer_timezone = rule.get('timezone', 'Asia/Bangkok')
            
            # Get current time in customer timezone
            now_customer = datetime.now(customer_tz)
            
            # Parse business hours
            start_hour, start_minute = map(int, rule['business_hours_start'].split(':'))
            end_hour, end_minute = map(int, rule['business_hours_end'].split(':'))
            
            # Calculate proposed send time (now + delay)
            delay_hours = rule['default_delay_hours']
            proposed_time = now_customer + timedelta(hours=delay_hours)
            
            # Check if proposed time is within business hours
            business_start = proposed_time.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            business_end = proposed_time.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            
            # Skip weekends (Saturday=5, Sunday=6)
            while proposed_time.weekday() >= 5:
                proposed_time += timedelta(days=1)
                business_start = proposed_time.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                business_end = proposed_time.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            
            if business_start <= proposed_time <= business_end:
                # Within business hours, use proposed time
                send_time_customer = proposed_time
            else:
                # Outside business hours, schedule for next business day at start time
                if proposed_time < business_start:
                    # Too early, schedule for today's business start
                    send_time_customer = business_start
                else:
                    # Too late, schedule for tomorrow's business start
                    next_day = proposed_time + timedelta(days=1)
                    # Skip weekends
                    while next_day.weekday() >= 5:
                        next_day += timedelta(days=1)
                    send_time_customer = next_day.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            
            # Convert to UTC for storage
            send_time_utc = send_time_customer.astimezone(pytz.UTC)
            
            self.logger.info(f"Calculated send time: {send_time_customer} ({customer_timezone}) -> {send_time_utc} (UTC)")
            
            return send_time_utc.replace(tzinfo=None)  # Store as naive datetime in UTC
            
        except Exception as e:
            self.logger.error(f"Failed to calculate send time: {str(e)}")
            # Fallback: 2 hours from now
            return datetime.utcnow() + timedelta(hours=2)

    def get_scheduled_events(self, org_id: str = None, status: str = None) -> List[Dict[str, Any]]:
        """
        Get list of scheduled events.

        Args:
            org_id: Filter by organization ID (optional)
            status: Filter by status (optional)

        Returns:
            List of scheduled events
        """
        try:
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM scheduled_events WHERE 1=1"
            params = []
            
            if org_id:
                query += " AND org_id = ?"
                params.append(org_id)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY scheduled_time ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            conn.close()
            
            # Convert to list of dictionaries
            events = []
            for row in rows:
                event = dict(zip(columns, row))
                # Parse event_data JSON
                if event['event_data']:
                    try:
                        event['event_data'] = json.loads(event['event_data'])
                    except json.JSONDecodeError:
                        pass
                events.append(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to get scheduled events: {str(e)}")
            return []

    def cancel_scheduled_event(self, event_id: str) -> bool:
        """
        Cancel a scheduled event by marking it as cancelled.

        Args:
            event_id: ID of the event to cancel

        Returns:
            True if cancelled successfully
        """
        try:
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE scheduled_events 
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE event_id = ?
            """, (event_id,))
            
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            
            if rows_affected > 0:
                self.logger.info(f"Cancelled scheduled event: {event_id}")
                return True
            else:
                self.logger.warning(f"Event not found for cancellation: {event_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to cancel event {event_id}: {str(e)}")
            return False

    def create_scheduling_rule(self, org_id: str, team_id: str = None, rule_name: str = 'default',
                             business_hours_start: str = '08:00', business_hours_end: str = '20:00',
                             default_delay_hours: int = 2, timezone: str = 'Asia/Bangkok',
                             follow_up_delay_hours: int = 120) -> bool:
        """
        Create or update a scheduling rule.

        Args:
            org_id: Organization ID
            team_id: Team ID (optional)
            rule_name: Name of the rule
            business_hours_start: Business hours start time (HH:MM)
            business_hours_end: Business hours end time (HH:MM)
            default_delay_hours: Default delay in hours
            timezone: Timezone for the rule
            follow_up_delay_hours: Follow-up delay in hours

        Returns:
            True if created/updated successfully
        """
        try:
            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO scheduling_rules 
                (id, org_id, team_id, rule_name, business_hours_start, business_hours_end,
                 default_delay_hours, timezone, follow_up_delay_hours, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (f"uuid:{str(uuid.uuid4())}", org_id, team_id, rule_name, business_hours_start, business_hours_end,
                  default_delay_hours, timezone, follow_up_delay_hours))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created/updated scheduling rule for {org_id}/{team_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create scheduling rule: {str(e)}")
            return False