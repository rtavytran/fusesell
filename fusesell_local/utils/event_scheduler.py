"""
Event Scheduler - Database-based event scheduling system
Creates scheduled events in database for external app to handle
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Union
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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminder_task (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    task TEXT NOT NULL,
                    cron TEXT NOT NULL,
                    cron_ts INTEGER,
                    room_id TEXT,
                    tags TEXT,
                    customextra TEXT,
                    org_id TEXT,
                    customer_id TEXT,
                    task_id TEXT,
                    import_uuid TEXT,
                    scheduled_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    error_message TEXT
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_task_status 
                ON reminder_task(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_task_org_id 
                ON reminder_task(org_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_task_task_id 
                ON reminder_task(task_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminder_task_cron 
                ON reminder_task(cron)
            """)

            cursor.execute("PRAGMA table_info(reminder_task)")
            columns = {row[1] for row in cursor.fetchall()}
            if 'cron_ts' not in columns:
                cursor.execute("ALTER TABLE reminder_task ADD COLUMN cron_ts INTEGER")
            
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

    def _format_datetime(self, value: Union[str, datetime, None]) -> str:
        """
        Normalize datetime-like values to ISO 8601 strings.

        Args:
            value: Datetime, ISO string, or None.

        Returns:
            ISO 8601 formatted string.
        """
        if isinstance(value, datetime):
            return value.replace(second=0, microsecond=0).isoformat()
        if value is None:
            return datetime.utcnow().replace(second=0, microsecond=0).isoformat()

        value_str = str(value).strip()
        if not value_str:
            return datetime.utcnow().replace(second=0, microsecond=0).isoformat()

        try:
            parsed = datetime.fromisoformat(value_str)
            return parsed.replace(second=0, microsecond=0).isoformat()
        except ValueError:
            return value_str

    def _to_unix_timestamp(self, value: Union[str, datetime, None]) -> Optional[int]:
        """
        Convert a datetime-like value to a Unix timestamp (seconds).
        """
        iso_value = self._format_datetime(value)
        try:
            parsed = datetime.fromisoformat(iso_value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())

    def _build_reminder_payload(
        self,
        base_context: Dict[str, Any],
        *,
        event_id: str,
        send_time: datetime,
        email_type: str,
        org_id: str,
        recipient_address: str,
        recipient_name: str,
        draft_id: str,
        customer_timezone: str,
        follow_up_iteration: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Construct reminder_task payload mirroring server implementation.

        Args:
            base_context: Context data supplied by caller.
            event_id: Scheduled event identifier.
            send_time: Planned send time (UTC).
            email_type: 'initial' or 'follow_up'.
            org_id: Organization identifier.
            recipient_address: Recipient email.
            recipient_name: Recipient name.
            draft_id: Draft identifier.
            customer_timezone: Customer timezone.
            follow_up_iteration: Optional follow-up iteration counter.

        Returns:
            Reminder payload dictionary or None if insufficient data.
        """
        if not base_context:
            return None

        context = dict(base_context)
        customextra_raw = context.pop('customextra', {}) or {}
        if isinstance(customextra_raw, str):
            try:
                customextra = json.loads(customextra_raw)
            except (json.JSONDecodeError, TypeError):
                customextra = {}
        elif isinstance(customextra_raw, dict):
            customextra = dict(customextra_raw)
        else:
            customextra = {}

        status = context.pop('status', 'published') or 'published'
        cron_value = context.pop('cron', None)
        scheduled_time_value = context.pop('scheduled_time', None)
        room_id = context.pop('room_id', context.pop('room', None))
        tags = context.pop('tags', None)
        task_label = context.pop('task', None)
        org_id_override = context.pop('org_id', None) or org_id
        customer_id = context.pop('customer_id', None) or customextra.get('customer_id')
        task_id = context.pop('task_id', None) or context.pop('execution_id', None) or customextra.get('task_id')
        customer_name = context.pop('customer_name', None)
        language = context.pop('language', None)
        team_id = context.pop('team_id', None)
        team_name = context.pop('team_name', None)
        staff_name = context.pop('staff_name', None)
        import_uuid = context.pop('import_uuid', None) or customextra.get('import_uuid')

        customextra.setdefault('reminder_content', 'draft_send' if email_type == 'initial' else 'follow_up')
        customextra.setdefault('org_id', org_id_override)
        customextra.setdefault('customer_id', customer_id)
        customextra.setdefault('task_id', task_id)
        customextra.setdefault('event_id', event_id)
        customextra.setdefault('email_type', email_type)
        customextra.setdefault('recipient_address', recipient_address)
        customextra.setdefault('recipient_name', recipient_name)
        customextra.setdefault('draft_id', draft_id)
        customextra.setdefault('customer_timezone', customer_timezone)
        customextra.setdefault('scheduled_time_utc', self._format_datetime(send_time))

        if team_id and 'team_id' not in customextra:
            customextra['team_id'] = team_id
        if team_name and 'team_name' not in customextra:
            customextra['team_name'] = team_name
        if language and 'language' not in customextra:
            customextra['language'] = language
        if staff_name and 'staff_name' not in customextra:
            customextra['staff_name'] = staff_name
        if customer_name and 'customer_name' not in customextra:
            customextra['customer_name'] = customer_name

        iteration = follow_up_iteration or context.pop('current_follow_up_time', None)
        if iteration is not None and 'current_follow_up_time' not in customextra:
            customextra['current_follow_up_time'] = iteration

        if not import_uuid:
            import_uuid = f"{customextra.get('org_id', '')}_{customextra.get('customer_id', '')}_{customextra.get('task_id', '')}_{event_id}"
        customextra.setdefault('import_uuid', import_uuid)

        if not tags:
            tags = ['fusesell', 'init-outreach' if email_type == 'initial' else 'follow-up']

        if not task_label:
            readable_type = "Initial Outreach" if email_type == 'initial' else "Follow-up"
            identifier = customextra.get('customer_name') or customextra.get('customer_id') or customer_id or 'customer'
            tracking_id = customextra.get('task_id') or task_id or draft_id
            task_label = f"FuseSell {readable_type} {identifier} - {tracking_id}"

        cron_value = self._format_datetime(cron_value or send_time)
        scheduled_time_str = self._format_datetime(scheduled_time_value or send_time)
        cron_ts = self._to_unix_timestamp(cron_value)

        return {
            'status': status,
            'task': task_label,
            'cron': cron_value,
            'cron_ts': cron_ts,
            'room_id': room_id,
            'tags': tags,
            'customextra': customextra,
            'org_id': customextra.get('org_id'),
            'customer_id': customextra.get('customer_id'),
            'task_id': customextra.get('task_id'),
            'import_uuid': customextra.get('import_uuid'),
            'scheduled_time': scheduled_time_str
        }

    def _insert_reminder_task(self, payload: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Insert reminder_task record into local database.

        Args:
            payload: Reminder payload produced by _build_reminder_payload.

        Returns:
            Reminder task identifier or None on failure.
        """
        if not payload:
            return None

        try:
            reminder_id = payload.get('id') or f"uuid:{str(uuid.uuid4())}"

            tags_value = payload.get('tags')
            if isinstance(tags_value, (list, tuple)):
                tags_str = json.dumps(list(tags_value))
            elif isinstance(tags_value, str):
                tags_str = tags_value
            else:
                tags_str = json.dumps([])

            customextra_value = payload.get('customextra') or {}
            if isinstance(customextra_value, dict):
                customextra_str = json.dumps(customextra_value)
            elif isinstance(customextra_value, str):
                customextra_str = customextra_value
            else:
                customextra_str = json.dumps({})

            conn = sqlite3.connect(self.main_db_path)
            cursor = conn.cursor()

            cron_ts = payload.get('cron_ts')
            if cron_ts is None:
                cron_ts = self._to_unix_timestamp(payload.get('cron'))

            cursor.execute("""
                INSERT INTO reminder_task
                (id, status, task, cron, cron_ts, room_id, tags, customextra, org_id, customer_id, task_id, import_uuid, scheduled_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reminder_id,
                payload.get('status', 'published'),
                payload.get('task') or 'FuseSell Reminder',
                self._format_datetime(payload.get('cron')),
                cron_ts,
                payload.get('room_id'),
                tags_str,
                customextra_str,
                payload.get('org_id'),
                payload.get('customer_id'),
                payload.get('task_id'),
                payload.get('import_uuid'),
                self._format_datetime(payload.get('scheduled_time'))
            ))

            conn.commit()
            conn.close()

            self.logger.debug(f"Created reminder_task record {reminder_id}")
            return reminder_id

        except Exception as exc:
            self.logger.error(f"Failed to create reminder_task record: {str(exc)}")
            return None

    def schedule_email_event(self, draft_id: str, recipient_address: str, recipient_name: str,
                           org_id: str, team_id: str = None, customer_timezone: str = None,
                           email_type: str = 'initial', send_immediately: bool = False,
                           reminder_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
            reminder_context: Optional metadata for reminder_task mirroring server behaviour

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

            reminder_task_id = None
            if reminder_context:
                reminder_payload = self._build_reminder_payload(
                    dict(reminder_context),
                    event_id=event_id,
                    send_time=send_time,
                    email_type=email_type,
                    org_id=org_id,
                    recipient_address=recipient_address,
                    recipient_name=recipient_name,
                    draft_id=draft_id,
                    customer_timezone=customer_timezone
                )
                reminder_payload.setdefault('cron_ts', self._to_unix_timestamp(reminder_payload.get('cron')))
                reminder_task_id = self._insert_reminder_task(reminder_payload)

            # Log the scheduling
            self.logger.info(f"Scheduled email event {event_id} for {send_time} (draft: {draft_id})")

            # Schedule follow-up if this is an initial email
            follow_up_event_id = None
            follow_up_reminder_id = None
            follow_up_scheduled_time = None
            if email_type == 'initial' and not send_immediately:
                follow_up_context = None
                if reminder_context:
                    follow_up_context = dict(reminder_context)
                    follow_up_extra = dict(follow_up_context.get('customextra', {}) or {})
                    follow_up_extra['reminder_content'] = 'follow_up'
                    follow_up_extra.setdefault('current_follow_up_time', 1)
                    follow_up_context['customextra'] = follow_up_extra
                    follow_up_context['tags'] = follow_up_context.get('tags') or ['fusesell', 'follow-up']

                follow_up_result = self._schedule_follow_up_event(
                    draft_id,
                    recipient_address,
                    recipient_name,
                    org_id,
                    team_id,
                    customer_timezone,
                    reminder_context=follow_up_context
                )

                if follow_up_result.get('success'):
                    follow_up_event_id = follow_up_result.get('event_id')
                    follow_up_reminder_id = follow_up_result.get('reminder_task_id')
                    follow_up_scheduled_time = follow_up_result.get('scheduled_time')
                else:
                    self.logger.warning(
                        "Follow-up scheduling failed for event %s: %s",
                        event_id,
                        follow_up_result.get('error', 'unknown error')
                    )

            return {
                'success': True,
                'event_id': event_id,
                'scheduled_time': send_time.isoformat(),
                'recipient_address': recipient_address,
                'recipient_name': recipient_name,
                'draft_id': draft_id,
                'email_type': email_type,
                'reminder_task_id': reminder_task_id,
                'follow_up_event_id': follow_up_event_id,
                'follow_up_reminder_task_id': follow_up_reminder_id,
                'follow_up_scheduled_time': follow_up_scheduled_time
            }
            
        except Exception as e:
            self.logger.error(f"Failed to schedule email event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _schedule_follow_up_event(self, original_draft_id: str, recipient_address: str, 
                                recipient_name: str, org_id: str, team_id: str = None,
                                customer_timezone: str = None,
                                reminder_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Schedule follow-up email event after initial email.

        Args:
            original_draft_id: ID of the original draft
            recipient_address: Email address of recipient
            recipient_name: Name of recipient
            org_id: Organization ID
            team_id: Team ID (optional)
            customer_timezone: Customer's timezone (optional)
            reminder_context: Optional metadata for reminder_task rows

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
            
            reminder_task_id = None
            if reminder_context:
                reminder_payload = self._build_reminder_payload(
                    dict(reminder_context),
                    event_id=followup_event_id,
                    send_time=follow_up_time,
                    email_type='follow_up',
                    org_id=org_id,
                    recipient_address=recipient_address,
                    recipient_name=recipient_name,
                    draft_id=original_draft_id,
                    customer_timezone=event_data['customer_timezone']
                )
                reminder_payload.setdefault('cron_ts', self._to_unix_timestamp(reminder_payload.get('cron')))
                reminder_task_id = self._insert_reminder_task(reminder_payload)
            
            self.logger.info(f"Scheduled follow-up event {followup_event_id} for {follow_up_time}")
            
            return {
                'success': True,
                'event_id': followup_event_id,
                'scheduled_time': follow_up_time.isoformat(),
                'reminder_task_id': reminder_task_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to schedule follow-up event: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'reminder_task_id': None
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
