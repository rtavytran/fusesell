"""
Local Data Manager for FuseSell Local Implementation
Handles SQLite database operations and local file management
"""

import sqlite3
import json
import os
import uuid
from typing import Dict, Any, List, Optional, Sequence, Union
from datetime import datetime
import logging
from pathlib import Path


class LocalDataManager:
    """
    Manages local data storage using SQLite database and JSON files.
    Provides interface for storing execution results, customer data, and configurations.
    """
    
    # Class-level tracking to prevent multiple initializations
    _initialized_databases = set()
    _initialization_lock = False
    _product_json_fields = [
        'target_users',
        'key_features',
        'unique_selling_points',
        'pain_points_solved',
        'competitive_advantages',
        'pricing',
        'pricing_rules',
        'sales_metrics',
        'customer_feedback',
        'keywords',
        'related_products',
        'seasonal_demand',
        'market_insights',
        'case_studies',
        'testimonials',
        'success_metrics',
        'product_variants',
        'technical_specifications',
        'compatibility',
        'support_info',
        'regulatory_compliance',
        'localization',
        'shipping_info'
    ]

    def __init__(self, data_dir: str = "./fusesell_data"):
        """
        Initialize data manager with specified data directory.

        Args:
            data_dir: Directory path for storing local data
        """
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "fusesell.db"
        self.config_dir = self.data_dir / "config"
        self.drafts_dir = self.data_dir / "drafts"
        self.logs_dir = self.data_dir / "logs"

        self.logger = logging.getLogger("fusesell.data_manager")

        # Create directories if they don't exist
        self._create_directories()

        # Initialize database with optimization check
        self._init_database_optimized()

    def _create_directories(self) -> None:
        """Create necessary directories for data storage."""
        for directory in [self.data_dir, self.config_dir, self.drafts_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def _init_database_optimized(self) -> None:
        """
        Initialize database with optimization to avoid redundant initialization.
        Only performs full initialization if database doesn't exist or is incomplete.
        Uses a class-level lock to prevent concurrent initialization.
        """
        try:
            db_path_str = str(self.db_path)
            
            # Check if this database has already been initialized in this process
            if db_path_str in LocalDataManager._initialized_databases:
                self.logger.debug("Database already initialized in this process, skipping initialization")
                return
            
            # Use class-level lock to prevent concurrent initialization
            if LocalDataManager._initialization_lock:
                self.logger.debug("Database initialization in progress by another instance, skipping")
                return
            
            LocalDataManager._initialization_lock = True
            
            try:
                # Double-check after acquiring lock
                if db_path_str in LocalDataManager._initialized_databases:
                    self.logger.debug("Database already initialized by another instance, skipping initialization")
                    return
                
                # Check if database exists and has basic tables
                if self.db_path.exists():
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        
                        # Check if key tables exist (use tables that actually exist in our schema)
                        cursor.execute("""
                            SELECT name FROM sqlite_master 
                            WHERE type='table' AND name IN ('stage_results', 'customers', 'llm_worker_task')
                        """)
                        existing_tables = [row[0] for row in cursor.fetchall()]
                        
                        self.logger.debug(f"Database exists, found tables: {existing_tables}")
                        
                        if len(existing_tables) >= 3:
                            self._migrate_email_drafts_table(cursor)
                            self.logger.info("Database already initialized, skipping full initialization")
                            LocalDataManager._initialized_databases.add(db_path_str)
                            return
                
                # Perform full initialization
                self.logger.info("Performing database initialization")
                self._init_database()
                LocalDataManager._initialized_databases.add(db_path_str)
                
            finally:
                LocalDataManager._initialization_lock = False
            
        except Exception as e:
            LocalDataManager._initialization_lock = False
            self.logger.warning(f"Database optimization check failed, performing full initialization: {str(e)}")
            self._init_database()
            LocalDataManager._initialized_databases.add(db_path_str)

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create executions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS executions (
                        execution_id TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        org_name TEXT,
                        customer_website TEXT,
                        customer_name TEXT,
                        status TEXT NOT NULL,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        config_json TEXT,
                        results_json TEXT
                    )
                """)

                # Create stage_results table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS stage_results (
                        id TEXT PRIMARY KEY,
                        execution_id TEXT NOT NULL,
                        stage_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        input_data TEXT,
                        output_data TEXT,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        error_message TEXT,
                        FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
                    )
                """)

                # Create customers table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS customers (
                        customer_id TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        company_name TEXT,
                        website TEXT,
                        industry TEXT,
                        contact_name TEXT,
                        contact_email TEXT,
                        contact_phone TEXT,
                        address TEXT,
                        profile_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create lead_scores table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS lead_scores (
                        id TEXT PRIMARY KEY,
                        execution_id TEXT NOT NULL,
                        customer_id TEXT,
                        product_id TEXT,
                        score REAL,
                        criteria_breakdown TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
                    )
                """)

                # Create email_drafts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS email_drafts (
                        draft_id TEXT PRIMARY KEY,
                        execution_id TEXT NOT NULL,
                        customer_id TEXT,
                        subject TEXT,
                        content TEXT,
                        draft_type TEXT,
                        version INTEGER DEFAULT 1,
                        status TEXT DEFAULT 'draft',
                        metadata TEXT,
                        priority_order INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
                    )
                """)

                # Create llm_worker_task table (server-compatible)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS llm_worker_task (
                        task_id TEXT PRIMARY KEY,
                        plan_id TEXT NOT NULL,
                        org_id TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'running',
                        current_runtime_index INTEGER DEFAULT 0,
                        messages JSON,
                        request_body JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (plan_id) REFERENCES llm_worker_plan(id)
                    )
                """)

                # Simply drop and recreate llm_worker_operation table to ensure correct schema
                cursor.execute("DROP TABLE IF EXISTS llm_worker_operation")
                self.logger.info(
                    "Creating llm_worker_operation table with server-compatible schema - FIXED VERSION")

                # Create llm_worker_operation table (server-compatible)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS llm_worker_operation (
                        operation_id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        executor_name TEXT NOT NULL,
                        runtime_index INTEGER NOT NULL DEFAULT 0,
                        chain_index INTEGER NOT NULL DEFAULT 0,
                        execution_status TEXT NOT NULL DEFAULT 'running',
                        input_data JSON,
                        output_data JSON,
                        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES llm_worker_task(task_id)
                    )
                """)

                # Create teams table (equivalent to llm_worker_plan_team)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS teams (
                        team_id TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        org_name TEXT,
                        plan_id TEXT NOT NULL,
                        plan_name TEXT,
                        project_code TEXT,
                        name TEXT NOT NULL,
                        description TEXT,
                        avatar TEXT,
                        completed_settings INTEGER DEFAULT 0,
                        total_settings INTEGER DEFAULT 0,
                        completed_settings_list TEXT,
                        missing_settings_list TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create team_settings table (equivalent to gs_team_settings)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS team_settings (
                        id TEXT PRIMARY KEY,
                        team_id TEXT NOT NULL,
                        org_id TEXT NOT NULL,
                        plan_id TEXT NOT NULL,
                        plan_name TEXT,
                        project_code TEXT,
                        team_name TEXT,
                        gs_team_organization TEXT,
                        gs_team_rep TEXT,
                        gs_team_product TEXT,
                        gs_team_schedule_time TEXT,
                        gs_team_initial_outreach TEXT,
                        gs_team_follow_up TEXT,
                        gs_team_auto_interaction TEXT,
                        gs_team_followup_schedule_time TEXT,
                        gs_team_birthday_email TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (team_id) REFERENCES teams(team_id)
                    )
                """)
                
                # Check if we need to migrate old column names
                try:
                    cursor.execute("PRAGMA table_info(team_settings)")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    # Check if we have old column names and need to migrate
                    old_columns = ['organization_settings', 'sales_rep_settings', 'product_settings']
                    
                    if any(col in columns for col in old_columns):
                        self.logger.info("Migrating team_settings table to new column names")
                        
                        # Create new table with correct column names
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS team_settings_new (
                                id TEXT PRIMARY KEY,
                                team_id TEXT NOT NULL,
                                org_id TEXT NOT NULL,
                                plan_id TEXT NOT NULL,
                                plan_name TEXT,
                                project_code TEXT,
                                team_name TEXT,
                                gs_team_organization TEXT,
                                gs_team_rep TEXT,
                                gs_team_product TEXT,
                                gs_team_schedule_time TEXT,
                                gs_team_initial_outreach TEXT,
                                gs_team_follow_up TEXT,
                                gs_team_auto_interaction TEXT,
                                gs_team_followup_schedule_time TEXT,
                                gs_team_birthday_email TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY (team_id) REFERENCES teams(team_id)
                            )
                        """)
                        
                        # Copy data from old table to new table
                        cursor.execute("""
                            INSERT OR IGNORE INTO team_settings_new 
                            (id, team_id, org_id, plan_id, plan_name, project_code, team_name,
                             gs_team_organization, gs_team_rep, gs_team_product, gs_team_schedule_time,
                             gs_team_initial_outreach, gs_team_follow_up, gs_team_auto_interaction,
                             gs_team_followup_schedule_time, gs_team_birthday_email, created_at, updated_at)
                            SELECT 
                                id, team_id, org_id, plan_id, plan_name, project_code, team_name,
                                organization_settings, sales_rep_settings, product_settings, schedule_time_settings,
                                initial_outreach_settings, follow_up_settings, auto_interaction_settings,
                                followup_schedule_settings, birthday_email_settings, created_at, updated_at
                            FROM team_settings
                        """)
                        
                        # Drop old table and rename new one
                        cursor.execute("DROP TABLE team_settings")
                        cursor.execute("ALTER TABLE team_settings_new RENAME TO team_settings")
                        
                        self.logger.info("Team settings table migration completed")
                except Exception as e:
                    self.logger.debug(f"Migration check/execution failed (may be normal): {str(e)}")

                # Ensure teams table has status column for enabling/disabling teams
                try:
                    cursor.execute("PRAGMA table_info(teams)")
                    team_columns = [row[1] for row in cursor.fetchall()]

                    if "status" not in team_columns:
                        self.logger.info("Adding status column to teams table")
                        cursor.execute(
                            "ALTER TABLE teams ADD COLUMN status TEXT DEFAULT 'active'"
                        )
                except Exception as e:
                    self.logger.debug(
                        f"Teams status column migration skipped/failed (may be normal): {str(e)}"
                    )

                # Create products table (equivalent to sell_products)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS products (
                        product_id TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        org_name TEXT,
                        project_code TEXT,
                        product_name TEXT NOT NULL,
                        short_description TEXT,
                        long_description TEXT,
                        category TEXT,
                        subcategory TEXT,
                        target_users TEXT,
                        key_features TEXT,
                        unique_selling_points TEXT,
                        pain_points_solved TEXT,
                        competitive_advantages TEXT,
                        pricing TEXT,
                        pricing_rules TEXT,
                        product_website TEXT,
                        demo_available BOOLEAN DEFAULT FALSE,
                        trial_available BOOLEAN DEFAULT FALSE,
                        sales_contact_email TEXT,
                        image_url TEXT,
                        sales_metrics TEXT,
                        customer_feedback TEXT,
                        keywords TEXT,
                        related_products TEXT,
                        seasonal_demand TEXT,
                        market_insights TEXT,
                        case_studies TEXT,
                        testimonials TEXT,
                        success_metrics TEXT,
                        product_variants TEXT,
                        availability TEXT,
                        technical_specifications TEXT,
                        compatibility TEXT,
                        support_info TEXT,
                        regulatory_compliance TEXT,
                        localization TEXT,
                        installation_requirements TEXT,
                        user_manual_url TEXT,
                        return_policy TEXT,
                        shipping_info TEXT,
                        schema_version TEXT DEFAULT '1.3',
                        status TEXT DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create gs_customer_llmtask table (server-compatible)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS gs_customer_llmtask (
                        id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        customer_id TEXT NOT NULL,
                        customer_name TEXT NOT NULL,
                        customer_phone TEXT,
                        customer_address TEXT,
                        customer_email TEXT,
                        customer_industry TEXT,
                        customer_taxcode TEXT,
                        customer_website TEXT,
                        contact_name TEXT,
                        org_id TEXT NOT NULL,
                        org_name TEXT,
                        project_code TEXT,
                        crm_dob DATE,
                        image_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (task_id) REFERENCES llm_worker_task(task_id),
                        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                    )
                """)

                # Create prompts table (equivalent to gs_plan_team_prompt)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS prompts (
                        id TEXT PRIMARY KEY,
                        execution_id TEXT,
                        org_id TEXT NOT NULL,
                        plan_id TEXT,
                        team_id TEXT,
                        project_code TEXT,
                        input_stage TEXT NOT NULL,
                        prompt TEXT NOT NULL,
                        fewshots BOOLEAN DEFAULT FALSE,
                        instance_id TEXT,
                        submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        retrieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create scheduler_rules table (equivalent to gs_scheduler)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scheduler_rules (
                        id TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        org_name TEXT,
                        plan_id TEXT,
                        plan_name TEXT,
                        team_id TEXT,
                        team_name TEXT,
                        project_code TEXT,
                        input_stage TEXT NOT NULL,
                        input_stage_label TEXT,
                        language TEXT,
                        rule_config TEXT,
                        is_autorun_time_rule BOOLEAN DEFAULT FALSE,
                        status_code INTEGER,
                        message TEXT,
                        md_code TEXT,
                        username TEXT,
                        fullname TEXT,
                        instance_id TEXT,
                        submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create reminder_task table (equivalent to Directus reminder_task)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reminder_task (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        task TEXT NOT NULL,
                        cron TEXT NOT NULL,
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

                # Create extracted_files table (equivalent to gs_plan_setting_extracted_file)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS extracted_files (
                        id TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        plan_id TEXT,
                        team_id TEXT,
                        project_code TEXT,
                        import_uuid TEXT,
                        file_url TEXT,
                        project_url TEXT,
                        extracted_data TEXT,
                        username TEXT,
                        fullname TEXT,
                        instance_id TEXT,
                        submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        retrieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create llm_worker_plan table (server schema)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS llm_worker_plan (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        org_id TEXT,
                        status TEXT,
                        executors TEXT,
                        settings TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date_created TIMESTAMP,
                        date_updated TIMESTAMP,
                        user_created TEXT,
                        user_updated TEXT,
                        sort INTEGER
                    )
                """)

                # Create gs_company_criteria table (server schema)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS gs_company_criteria (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        definition TEXT,
                        weight REAL,
                        guidelines TEXT,
                        scoring_factors TEXT,
                        org_id TEXT,
                        status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date_created TIMESTAMP,
                        date_updated TIMESTAMP,
                        user_created TEXT,
                        user_updated TEXT,
                        sort INTEGER
                    )
                """)

                # Create indexes for better performance
                # Check if executions is a table before creating index (it might be a view)
                cursor.execute(
                    "SELECT type FROM sqlite_master WHERE name='executions'")
                executions_type = cursor.fetchone()
                if executions_type and executions_type[0] == 'table':
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_executions_org_id ON executions(org_id)")

                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_stage_results_execution_id ON stage_results(execution_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_customers_org_id ON customers(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_lead_scores_execution_id ON lead_scores(execution_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_email_drafts_execution_id ON email_drafts(execution_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_task_org_id ON llm_worker_task(org_id)")
                # Server-compatible indexes for performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_task_org_id ON llm_worker_task(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_task_plan_id ON llm_worker_task(plan_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_task_status ON llm_worker_task(status)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_operation_task_id ON llm_worker_operation(task_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_operation_task_runtime ON llm_worker_operation(task_id, runtime_index)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_operation_executor_status ON llm_worker_operation(executor_name, execution_status)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_operation_created_date ON llm_worker_operation(date_created)")

                # Existing indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_teams_org_id ON teams(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_team_settings_team_id ON team_settings(team_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_products_org_id ON products(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_gs_customer_llmtask_task_id ON gs_customer_llmtask(task_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_prompts_org_id ON prompts(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_scheduler_rules_org_id ON scheduler_rules(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reminder_task_status ON reminder_task(status)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reminder_task_org_id ON reminder_task(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reminder_task_task_id ON reminder_task(task_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reminder_task_cron ON reminder_task(cron)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_extracted_files_org_id ON extracted_files(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_llm_worker_plan_org_id ON llm_worker_plan(org_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_gs_company_criteria_org_id ON gs_company_criteria(org_id)")

                # Create compatibility views for backward compatibility
                cursor.execute("""
                    CREATE VIEW IF NOT EXISTS executions_view AS
                    SELECT 
                        task_id as execution_id,
                        org_id,
                        '' as org_name,
                        '' as customer_website,
                        '' as customer_name,
                        status,
                        created_at as started_at,
                        updated_at as completed_at,
                        request_body as config_json,
                        '{}' as results_json
                    FROM llm_worker_task
                """)

                cursor.execute("""
                    CREATE VIEW IF NOT EXISTS stage_results_view AS
                    SELECT 
                        operation_id as id,
                        task_id as execution_id,
                        executor_name as stage_name,
                        execution_status as status,
                        input_data,
                        output_data,
                        date_created as started_at,
                        date_updated as completed_at,
                        CASE WHEN execution_status = 'failed' 
                             THEN json_extract(output_data, '$.error') 
                             ELSE NULL END as error_message
                    FROM llm_worker_operation
                """)

                # Ensure email_drafts table has latest columns
                self._migrate_email_drafts_table(cursor)

                conn.commit()

                # Initialize default data for new tables
                self._initialize_default_data()

                self.logger.info("Database initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def _migrate_email_drafts_table(self, cursor: sqlite3.Cursor) -> None:
        """
        Ensure email_drafts table has expected columns for metadata and priority.

        Args:
            cursor: Active database cursor
        """
        try:
            cursor.execute("PRAGMA table_info(email_drafts)")
            columns = {row[1] for row in cursor.fetchall()}

            if "status" not in columns:
                cursor.execute("ALTER TABLE email_drafts ADD COLUMN status TEXT DEFAULT 'draft'")
            if "metadata" not in columns:
                cursor.execute("ALTER TABLE email_drafts ADD COLUMN metadata TEXT")
            if "priority_order" not in columns:
                cursor.execute("ALTER TABLE email_drafts ADD COLUMN priority_order INTEGER DEFAULT 0")
            if "updated_at" not in columns:
                try:
                    cursor.execute("ALTER TABLE email_drafts ADD COLUMN updated_at TIMESTAMP")
                    cursor.execute(
                        "UPDATE email_drafts SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
                    )
                except Exception as exc:
                    self.logger.debug(f"Updated_at column add skipped: {exc}")

            try:
                cursor.execute(
                    """
                    WITH ordered AS (
                        SELECT draft_id,
                               ROW_NUMBER() OVER (PARTITION BY execution_id ORDER BY created_at, draft_id) AS rn
                        FROM email_drafts
                        WHERE IFNULL(priority_order, 0) <= 0
                    )
                    UPDATE email_drafts
                    SET priority_order = (
                        SELECT rn FROM ordered WHERE ordered.draft_id = email_drafts.draft_id
                    )
                    WHERE draft_id IN (SELECT draft_id FROM ordered)
                    """
                )
            except Exception as exc:
                self.logger.debug(f"Priority backfill skipped: {exc}")

            try:
                cursor.connection.commit()
            except Exception:
                pass
        except Exception as exc:
            self.logger.warning(f"Email drafts table migration skipped/failed: {exc}")

    def save_execution(
        self,
        execution_id: str,
        org_id: str,
        config: Dict[str, Any],
        org_name: Optional[str] = None,
        customer_website: Optional[str] = None,
        customer_name: Optional[str] = None
    ) -> None:
        """
        Save execution record to database.

        Args:
            execution_id: Unique execution identifier
            org_id: Organization ID
            config: Execution configuration
            org_name: Organization name
            customer_website: Customer website URL
            customer_name: Customer company name
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO executions 
                    (execution_id, org_id, org_name, customer_website, customer_name, status, config_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_id, org_id, org_name, customer_website,
                    customer_name, 'running', json.dumps(config)
                ))
                conn.commit()
                self.logger.debug(f"Saved execution record: {execution_id}")

        except Exception as e:
            self.logger.error(f"Failed to save execution: {str(e)}")
            raise

    def update_execution_status(
        self,
        execution_id: str,
        status: str,
        results: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update execution status and results.

        Args:
            execution_id: Execution identifier
            status: New status (running, completed, failed)
            results: Optional execution results
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if results:
                    cursor.execute("""
                        UPDATE executions 
                        SET status = ?, completed_at = CURRENT_TIMESTAMP, results_json = ?
                        WHERE execution_id = ?
                    """, (status, json.dumps(results), execution_id))
                else:
                    cursor.execute("""
                        UPDATE executions 
                        SET status = ?, completed_at = CURRENT_TIMESTAMP
                        WHERE execution_id = ?
                    """, (status, execution_id))

                conn.commit()
                self.logger.debug(
                    f"Updated execution status: {execution_id} -> {status}")

        except Exception as e:
            self.logger.error(f"Failed to update execution status: {str(e)}")
            raise

    def save_stage_result(
        self,
        execution_id: str,
        stage_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Save stage execution result.

        Args:
            execution_id: Execution identifier
            stage_name: Name of the stage
            input_data: Stage input data
            output_data: Stage output data
            status: Stage execution status
            error_message: Optional error message
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO stage_results 
                    (id, execution_id, stage_name, status, input_data, output_data, completed_at, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """, (
                    f"uuid:{str(uuid.uuid4())}", execution_id, stage_name, status,
                    json.dumps(input_data), json.dumps(
                        output_data), error_message
                ))
                conn.commit()
                self.logger.debug(
                    f"Saved stage result: {execution_id}/{stage_name}")

        except Exception as e:
            self.logger.error(f"Failed to save stage result: {str(e)}")
            raise

    def save_customer(self, customer_data: Dict[str, Any]) -> str:
        """
        Save or update customer information.

        Args:
            customer_data: Customer information dictionary

        Returns:
            Customer ID
        """
        try:
            customer_id = customer_data.get(
                'customer_id') or self._generate_customer_id()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if customer exists
                cursor.execute(
                    "SELECT customer_id FROM customers WHERE customer_id = ?", (customer_id,))
                exists = cursor.fetchone()

                if exists:
                    # Update existing customer
                    cursor.execute("""
                        UPDATE customers 
                        SET company_name = ?, website = ?, industry = ?, contact_name = ?,
                            contact_email = ?, contact_phone = ?, address = ?, 
                            profile_data = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE customer_id = ?
                    """, (
                        customer_data.get('company_name'),
                        customer_data.get('website'),
                        customer_data.get('industry'),
                        customer_data.get('contact_name'),
                        customer_data.get('contact_email'),
                        customer_data.get('contact_phone'),
                        customer_data.get('address'),
                        json.dumps(customer_data),
                        customer_id
                    ))
                else:
                    # Insert new customer
                    cursor.execute("""
                        INSERT INTO customers 
                        (customer_id, org_id, company_name, website, industry, contact_name,
                         contact_email, contact_phone, address, profile_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        customer_id,
                        customer_data.get('org_id'),
                        customer_data.get('company_name'),
                        customer_data.get('website'),
                        customer_data.get('industry'),
                        customer_data.get('contact_name'),
                        customer_data.get('contact_email'),
                        customer_data.get('contact_phone'),
                        customer_data.get('address'),
                        json.dumps(customer_data)
                    ))

                conn.commit()
                self.logger.debug(f"Saved customer: {customer_id}")
                return customer_id

        except Exception as e:
            self.logger.error(f"Failed to save customer: {str(e)}")
            raise

    def save_customer_task(self, customer_task_data: Dict[str, Any]) -> str:
        """
        Save customer task data to gs_customer_llmtask table (server-compatible).

        Args:
            customer_task_data: Customer task information dictionary

        Returns:
            Record ID
        """
        try:
            record_id = f"{customer_task_data.get('task_id')}_{customer_task_data.get('customer_id')}"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert or replace customer task data
                cursor.execute("""
                    INSERT OR REPLACE INTO gs_customer_llmtask 
                    (id, task_id, customer_id, customer_name, customer_phone, customer_address,
                     customer_email, customer_industry, customer_taxcode, customer_website,
                     contact_name, org_id, org_name, project_code, crm_dob, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    customer_task_data.get('task_id'),
                    customer_task_data.get('customer_id'),
                    customer_task_data.get('customer_name'),
                    customer_task_data.get('customer_phone'),
                    customer_task_data.get('customer_address'),
                    customer_task_data.get('customer_email'),
                    customer_task_data.get('customer_industry'),
                    customer_task_data.get('customer_taxcode'),
                    customer_task_data.get('customer_website'),
                    customer_task_data.get('contact_name'),
                    customer_task_data.get('org_id'),
                    customer_task_data.get('org_name'),
                    customer_task_data.get('project_code'),
                    customer_task_data.get('crm_dob'),
                    customer_task_data.get('image_url')
                ))

                conn.commit()
                self.logger.debug(f"Saved customer task: {record_id}")
                return record_id

        except Exception as e:
            self.logger.error(f"Failed to save customer task data: {str(e)}")
            raise

    def save_lead_score(
        self,
        execution_id: str,
        customer_id: str,
        product_id: str,
        score: float,
        criteria_breakdown: Dict[str, Any]
    ) -> None:
        """
        Save lead scoring result.

        Args:
            execution_id: Execution identifier
            customer_id: Customer identifier
            product_id: Product identifier
            score: Lead score (0-100)
            criteria_breakdown: Detailed scoring breakdown
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO lead_scores 
                    (id, execution_id, customer_id, product_id, score, criteria_breakdown)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"uuid:{str(uuid.uuid4())}", execution_id, customer_id, product_id, score,
                    json.dumps(criteria_breakdown)
                ))
                conn.commit()
                self.logger.debug(
                    f"Saved lead score: {customer_id}/{product_id} = {score}")

        except Exception as e:
            self.logger.error(f"Failed to save lead score: {str(e)}")
            raise

    def save_email_draft(
        self,
        draft_id: Union[str, Dict[str, Any]],
        execution_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        draft_type: str = "initial_outreach",
        version: int = 1,
        status: str = "draft",
        metadata: Optional[Union[Dict[str, Any], str]] = None,
        priority_order: int = 0
    ) -> None:
        """
        Save email draft. Accepts either explicit parameters or a draft data dictionary.

        Args:
            draft_id: Draft identifier or draft dictionary with keys
            execution_id: Execution identifier
            customer_id: Customer identifier
            subject: Email subject
            content: Email content
            draft_type: Type of draft (initial_outreach, follow_up)
            version: Draft version number
            status: Draft status
            metadata: Additional metadata (dict or JSON string)
            priority_order: Numeric priority for scheduling/selection
        """
        try:
            if isinstance(draft_id, dict):
                data = draft_id
                draft_id = data.get("draft_id")
                execution_id = data.get("execution_id")
                customer_id = data.get("customer_id")
                subject = data.get("subject")
                content = data.get("content")
                draft_type = data.get("draft_type", draft_type)
                version = data.get("version", version)
                status = data.get("status", status)
                metadata = data.get("metadata")
                priority_order = data.get("priority_order", priority_order)

            metadata_json = metadata
            if isinstance(metadata, dict):
                metadata_json = json.dumps(metadata)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO email_drafts 
                    (draft_id, execution_id, customer_id, subject, content, draft_type, version, status, metadata, priority_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        draft_id,
                        execution_id,
                        customer_id,
                        subject,
                        content,
                        draft_type,
                        version,
                        status,
                        metadata_json,
                        priority_order or 0,
                    ),
                )
                conn.commit()
                self.logger.debug(f"Saved email draft: {draft_id}")

        except Exception as e:
            self.logger.error(f"Failed to save email draft: {str(e)}")
            raise

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution record by ID.

        Args:
            execution_id: Execution identifier

        Returns:
            Execution record dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM executions WHERE execution_id = ?", (execution_id,))
                row = cursor.fetchone()

                if row:
                    result = dict(row)
                    if result['config_json']:
                        result['config'] = json.loads(result['config_json'])
                    if result['results_json']:
                        result['results'] = json.loads(result['results_json'])
                    return result
                return None

        except Exception as e:
            self.logger.error(f"Failed to get execution: {str(e)}")
            raise

    def get_stage_results(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        Get all stage results for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            List of stage result dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM stage_results 
                    WHERE execution_id = ? 
                    ORDER BY started_at
                """, (execution_id,))

                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result['input_data']:
                        result['input_data'] = json.loads(result['input_data'])
                    if result['output_data']:
                        result['output_data'] = json.loads(
                            result['output_data'])
                    results.append(result)

                return results

        except Exception as e:
            self.logger.error(f"Failed to get stage results: {str(e)}")
            raise

    def load_prompts(self) -> Dict[str, Any]:
        """
        Load prompt templates from configuration.
        Priority: custom prompts (data_dir/config/prompts.json) > default prompts (package)

        Returns:
            Dictionary of prompt templates
        """
        try:
            # Load default prompts from package
            default_prompts = self._load_default_prompts()

            # Load custom prompts from user's data directory
            custom_prompts_file = self.config_dir / "prompts.json"
            custom_prompts = {}
            if custom_prompts_file.exists():
                with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                    custom_prompts = json.load(f)
                    self.logger.debug(f"Loaded custom prompts from {custom_prompts_file}")

            # Merge prompts - custom overrides default
            merged_prompts = default_prompts.copy()
            for stage_name, stage_prompts in custom_prompts.items():
                if stage_name in merged_prompts:
                    merged_prompts[stage_name].update(stage_prompts)
                else:
                    merged_prompts[stage_name] = stage_prompts

            return merged_prompts
        except Exception as e:
            self.logger.error(f"Failed to load prompts: {str(e)}")
            return {}

    def _load_default_prompts(self) -> Dict[str, Any]:
        """
        Load default system prompts from package.

        Returns:
            Dictionary of default prompt templates
        """
        return self._load_default_config('default_prompts.json')

    def load_scoring_criteria(self) -> Dict[str, Any]:
        """
        Load scoring criteria configuration.
        Priority: custom criteria (data_dir/config/scoring_criteria.json) > default criteria (package)

        Returns:
            Dictionary of scoring criteria
        """
        try:
            # Load default criteria from package
            default_criteria = self._load_default_config('default_scoring_criteria.json')

            # Load custom criteria from user's data directory
            custom_criteria_file = self.config_dir / "scoring_criteria.json"
            if custom_criteria_file.exists():
                with open(custom_criteria_file, 'r', encoding='utf-8') as f:
                    custom_criteria = json.load(f)
                    # Merge custom with default (custom overrides)
                    merged = default_criteria.copy()
                    merged.update(custom_criteria)
                    return merged

            return default_criteria
        except Exception as e:
            self.logger.error(f"Failed to load scoring criteria: {str(e)}")
            return {}

    def load_email_templates(self) -> Dict[str, Any]:
        """
        Load email templates configuration.
        Priority: custom templates (data_dir/config/email_templates.json) > default templates (package)

        Returns:
            Dictionary of email templates
        """
        try:
            # Load default templates from package
            default_templates = self._load_default_config('default_email_templates.json')

            # Load custom templates from user's data directory
            custom_templates_file = self.config_dir / "email_templates.json"
            if custom_templates_file.exists():
                with open(custom_templates_file, 'r', encoding='utf-8') as f:
                    custom_templates = json.load(f)
                    # Merge custom with default (custom overrides)
                    merged = default_templates.copy()
                    merged.update(custom_templates)
                    return merged

            return default_templates
        except Exception as e:
            self.logger.error(f"Failed to load email templates: {str(e)}")
            return {}

    def _load_default_config(self, filename: str) -> Dict[str, Any]:
        """
        Load default configuration file from package.

        Args:
            filename: Name of the config file (e.g., 'default_prompts.json')

        Returns:
            Dictionary of configuration data
        """
        try:
            import importlib.resources as pkg_resources
            from pathlib import Path

            # Try to load from package resources
            try:
                # Python 3.9+
                with pkg_resources.files('fusesell_local.config').joinpath(filename).open('r', encoding='utf-8') as f:
                    return json.load(f)
            except AttributeError:
                # Python 3.8 fallback
                with pkg_resources.open_text('fusesell_local.config', filename, encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load default config {filename} from package: {str(e)}")
            # Fallback: try to load from installed location
            try:
                import fusesell_local
                package_dir = Path(fusesell_local.__file__).parent
                default_config_file = package_dir / "config" / filename
                if default_config_file.exists():
                    with open(default_config_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except Exception as fallback_error:
                self.logger.warning(f"Fallback load also failed for {filename}: {str(fallback_error)}")

            return {}

    def generate_custom_prompt(
        self,
        stage_name: str,
        prompt_key: str,
        user_request: str,
        llm_client: Any = None,
        required_fields: Optional[List[str]] = None
    ) -> str:
        """
        Generate a custom prompt based on user's natural language request.

        Args:
            stage_name: The stage name (e.g., 'initial_outreach', 'follow_up')
            prompt_key: The prompt key (e.g., 'email_generation')
            user_request: User's natural language customization request
            llm_client: LLM client instance for generating the prompt
            required_fields: List of required fields that must always exist in the prompt

        Returns:
            Generated custom prompt string
        """
        if not llm_client:
            raise ValueError("LLM client is required for custom prompt generation")

        # Load default prompt as base
        default_prompts = self._load_default_prompts()
        default_prompt = default_prompts.get(stage_name, {}).get(prompt_key, "")

        if not default_prompt:
            self.logger.warning(f"No default prompt found for {stage_name}.{prompt_key}")
            default_prompt = ""

        # Build required fields context
        required_fields_str = ""
        if required_fields:
            required_fields_str = f"\n\nRequired fields that MUST be present in the prompt: {', '.join(required_fields)}"

        # Generate custom prompt using LLM
        system_prompt = f"""You are an expert at creating email generation prompts for sales automation systems.
Your task is to modify the default system prompt based on the user's customization request.

IMPORTANT RULES:
1. Preserve all placeholder variables (##variable_name##) from the original prompt
2. Maintain the JSON output structure requirements
3. Keep essential instructions about email formatting and validation
4. Incorporate the user's customization request naturally{required_fields_str}
5. Return ONLY the modified prompt text, no explanations or markdown formatting
6. The output should be a complete, standalone prompt that can be used directly"""

        user_prompt = f"""Default System Prompt:
{default_prompt}

User's Customization Request:
{user_request}

Generate the modified prompt that incorporates the user's request while maintaining all critical elements."""

        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )

            return response.strip()

        except Exception as e:
            self.logger.error(f"Failed to generate custom prompt: {str(e)}")
            raise

    def save_custom_prompt(
        self,
        stage_name: str,
        prompt_key: str,
        custom_prompt: str
    ) -> None:
        """
        Save custom prompt to user's data directory.

        Args:
            stage_name: The stage name (e.g., 'initial_outreach', 'follow_up')
            prompt_key: The prompt key (e.g., 'email_generation')
            custom_prompt: The custom prompt to save
        """
        try:
            custom_prompts_file = self.config_dir / "prompts.json"

            # Load existing custom prompts
            existing_prompts = {}
            if custom_prompts_file.exists():
                with open(custom_prompts_file, 'r', encoding='utf-8') as f:
                    existing_prompts = json.load(f)

            # Update with new custom prompt
            if stage_name not in existing_prompts:
                existing_prompts[stage_name] = {}
            existing_prompts[stage_name][prompt_key] = custom_prompt

            # Save back to file
            with open(custom_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(existing_prompts, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Saved custom prompt for {stage_name}.{prompt_key}")

        except Exception as e:
            self.logger.error(f"Failed to save custom prompt: {str(e)}")
            raise

    def process_initial_outreach_customization(
        self,
        initial_outreach_config: Dict[str, Any],
        llm_client: Any = None
    ) -> Dict[str, Any]:
        """
        Process initial_outreach configuration and generate custom prompts if requested.

        Args:
            initial_outreach_config: Initial outreach configuration with optional customization_request
            llm_client: LLM client for generating custom prompts

        Returns:
            Processed initial_outreach configuration
        """
        if not initial_outreach_config:
            return {}

        # Required fields that should always exist
        required_fields = ['tone']

        # Extract customization request if present
        customization_request = initial_outreach_config.get('customization_request')

        if customization_request and llm_client:
            try:
                # Generate custom prompt for initial_outreach stage
                custom_prompt = self.generate_custom_prompt(
                    stage_name='initial_outreach',
                    prompt_key='email_generation',
                    user_request=customization_request,
                    llm_client=llm_client,
                    required_fields=required_fields
                )

                # Save the custom prompt
                self.save_custom_prompt(
                    stage_name='initial_outreach',
                    prompt_key='email_generation',
                    custom_prompt=custom_prompt
                )

                self.logger.info("Generated and saved custom prompt for initial_outreach")

            except Exception as e:
                self.logger.error(f"Failed to process customization request: {str(e)}")
                # Don't fail the entire save operation, just log the error

        # Build the processed configuration (keep all fields except customization_request)
        processed_config = {}
        for key, value in initial_outreach_config.items():
            if key != 'customization_request':
                processed_config[key] = value

        # Ensure tone field exists
        if 'tone' not in processed_config:
            processed_config['tone'] = 'Professional'

        return processed_config

    def _generate_customer_id(self) -> str:
        """Generate unique customer ID."""
        import uuid
        return f"uuid:{str(uuid.uuid4())}"

    def _normalize_status_value(self, status: Optional[Union[str, bool]]) -> Optional[str]:
        """
        Normalize activation status values.

        Args:
            status: Status value provided by the caller

        Returns:
            Normalized status ("active"/"inactive") or None if not provided
        """
        if status is None:
            return None

        if isinstance(status, bool):
            return 'active' if status else 'inactive'

        normalized = str(status).strip().lower()
        if not normalized:
            return None

        if normalized not in {'active', 'inactive'}:
            raise ValueError("Status must be 'active' or 'inactive'")

        return normalized

    # ===== TEAM MANAGEMENT METHODS =====

    def save_team(
        self,
        team_id: str,
        org_id: str,
        org_name: str,
        plan_id: str,
        name: str,
        description: str = None,
        plan_name: str = None,
        project_code: str = None,
        avatar: str = None,
        status: Optional[Union[str, bool]] = None
    ) -> str:
        """
        Save or update team information.

        Args:
            team_id: Team identifier
            org_id: Organization identifier
            org_name: Organization name
            plan_id: Plan identifier
            name: Team name
            description: Team description
            plan_name: Plan name
            project_code: Project code
            avatar: Avatar URL

        Returns:
            Team ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT status FROM teams WHERE team_id = ?", (team_id,))
                existing_row = cursor.fetchone()
                normalized_status = self._normalize_status_value(status)
                status_value = normalized_status or (
                    existing_row[0] if existing_row and len(existing_row) > 0 else None
                ) or 'active'

                if existing_row:
                    # Update existing team
                    cursor.execute("""
                        UPDATE teams SET
                            org_name = ?, plan_name = ?, project_code = ?, name = ?, description = ?,
                            avatar = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE team_id = ?
                    """, (org_name, plan_name, project_code, name, description, avatar, status_value, team_id))
                else:
                    # Insert new team
                    cursor.execute("""
                        INSERT INTO teams 
                        (team_id, org_id, org_name, plan_id, plan_name, project_code, name, description, avatar, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (team_id, org_id, org_name, plan_id, plan_name, project_code, name, description, avatar, status_value))

                conn.commit()
                self.logger.debug(f"Saved team: {team_id}")
                return team_id

        except Exception as e:
            self.logger.error(f"Error saving team {team_id}: {str(e)}")
            raise

    def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Get team by ID.

        Args:
            team_id: Team identifier

        Returns:
            Team data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,))
                row = cursor.fetchone()

                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None

        except Exception as e:
            self.logger.error(f"Error getting team {team_id}: {str(e)}")
            raise

    def list_teams(self, org_id: str, status: Optional[str] = "active") -> List[Dict[str, Any]]:
        """
        List all teams for an organization.

        Args:
            org_id: Organization identifier

        Returns:
            List of team data
        """
        try:
            # Normalize status
            normalized_status: Optional[str] = status
            if isinstance(normalized_status, str):
                normalized_status = normalized_status.strip().lower()
            if normalized_status not in {'active', 'inactive', 'all'}:
                normalized_status = 'active'

            where_clauses = ["org_id = ?"]
            params: List[Any] = [org_id]

            if normalized_status != 'all':
                where_clauses.append("status = ?")
                params.append(normalized_status)

            query = "SELECT * FROM teams WHERE " + " AND ".join(where_clauses)
            query += " ORDER BY created_at DESC"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            self.logger.error(f"Error listing teams for org {org_id}: {str(e)}")
            raise

    def update_team(
        self,
        team_id: str,
        name: str = None,
        description: str = None,
        plan_name: str = None,
        project_code: str = None,
        avatar: str = None,
        status: Optional[Union[str, bool]] = None
    ) -> bool:
        """
        Update team information.

        Args:
            team_id: Team identifier
            name: New team name
            description: New team description
            plan_name: New plan name
            project_code: New project code
            avatar: New avatar URL

        Returns:
            True if updated successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Build update query dynamically
                updates = []
                params = []

                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                if plan_name is not None:
                    updates.append("plan_name = ?")
                    params.append(plan_name)
                if project_code is not None:
                    updates.append("project_code = ?")
                    params.append(project_code)
                if avatar is not None:
                    updates.append("avatar = ?")
                    params.append(avatar)
                if status is not None:
                    normalized_status = self._normalize_status_value(status)
                    if normalized_status is not None:
                        updates.append("status = ?")
                        params.append(normalized_status)

                if not updates:
                    return True  # Nothing to update

                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(team_id)

                query = f"UPDATE teams SET {', '.join(updates)} WHERE team_id = ?"
                cursor.execute(query, params)

                conn.commit()
                self.logger.debug(f"Updated team: {team_id}")
                return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"Error updating team {team_id}: {str(e)}")
            raise

    def update_team_status(
        self,
        team_id: str,
        status: Union[str, bool]
    ) -> bool:
        """
        Update the activation status for a team.

        Args:
            team_id: Team identifier
            status: Target status ("active" or "inactive")

        Returns:
            True if a record was updated
        """
        normalized_status = self._normalize_status_value(status)
        if normalized_status is None:
            raise ValueError("Status is required when updating team status")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE teams
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE team_id = ?
                    """,
                    (normalized_status, team_id)
                )
                conn.commit()
                if cursor.rowcount:
                    self.logger.debug(f"Updated team status: {team_id} -> {normalized_status}")
                return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"Error updating team status {team_id}: {str(e)}")
            raise

    # ===== TEAM SETTINGS MANAGEMENT METHODS =====

    def save_team_settings(
        self,
        team_id: str,
        org_id: str,
        plan_id: str,
        team_name: str,
        gs_team_organization: Optional[Dict[str, Any]] = None,
        gs_team_rep: Optional[List[Dict[str, Any]]] = None,
        gs_team_product: Optional[List[Dict[str, Any]]] = None,
        gs_team_schedule_time: Optional[Dict[str, Any]] = None,
        gs_team_initial_outreach: Optional[Dict[str, Any]] = None,
        gs_team_follow_up: Optional[Dict[str, Any]] = None,
        gs_team_auto_interaction: Optional[Dict[str, Any]] = None,
        gs_team_followup_schedule_time: Optional[Dict[str, Any]] = None,
        gs_team_birthday_email: Optional[Dict[str, Any]] = None,
        llm_client: Any = None
    ) -> None:
        """
        Save or update team settings.

        Args:
            team_id: Team identifier
            org_id: Organization identifier
            plan_id: Plan identifier
            team_name: Team name
            gs_team_organization: Organization configuration
            gs_team_rep: Sales representative settings
            gs_team_product: Product configuration
            gs_team_schedule_time: Scheduling configuration
            gs_team_initial_outreach: Initial outreach configuration
            gs_team_follow_up: Follow-up configuration
            gs_team_auto_interaction: Auto interaction rules (can include customization_request)
            gs_team_followup_schedule_time: Follow-up scheduling rules
            gs_team_birthday_email: Birthday email configuration
            llm_client: Optional LLM client for custom prompt generation
        """
        try:
            settings_id = f"{team_id}_{org_id}"

            # Process initial_outreach customization if present
            processed_initial_outreach = gs_team_initial_outreach
            if gs_team_initial_outreach and isinstance(gs_team_initial_outreach, dict):
                if gs_team_initial_outreach.get('customization_request'):
                    try:
                        processed_initial_outreach = self.process_initial_outreach_customization(
                            gs_team_initial_outreach,
                            llm_client=llm_client
                        )
                        self.logger.info("Processed initial_outreach customization request")
                    except Exception as e:
                        self.logger.warning(f"Failed to process initial_outreach customization: {str(e)}")
                        # Continue with original config if processing fails
                        processed_initial_outreach = gs_team_initial_outreach

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if settings exist
                cursor.execute(
                    "SELECT id FROM team_settings WHERE team_id = ?", (team_id,))
                exists = cursor.fetchone()

                if exists:
                    # Update existing settings
                    cursor.execute("""
                        UPDATE team_settings 
                        SET org_id = ?, plan_id = ?, team_name = ?,
                            gs_team_organization = ?, gs_team_rep = ?, gs_team_product = ?,
                            gs_team_schedule_time = ?, gs_team_initial_outreach = ?, gs_team_follow_up = ?,
                            gs_team_auto_interaction = ?, gs_team_followup_schedule_time = ?, gs_team_birthday_email = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE team_id = ?
                    """, (
                        org_id, plan_id, team_name,
                        json.dumps(
                            gs_team_organization) if gs_team_organization else None,
                        json.dumps(
                            gs_team_rep) if gs_team_rep else None,
                        json.dumps(
                            gs_team_product) if gs_team_product else None,
                        json.dumps(
                            gs_team_schedule_time) if gs_team_schedule_time else None,
                        json.dumps(
                            processed_initial_outreach) if processed_initial_outreach else None,
                        json.dumps(
                            gs_team_follow_up) if gs_team_follow_up else None,
                        json.dumps(
                            gs_team_auto_interaction) if gs_team_auto_interaction else None,
                        json.dumps(
                            gs_team_followup_schedule_time) if gs_team_followup_schedule_time else None,
                        json.dumps(
                            gs_team_birthday_email) if gs_team_birthday_email else None,
                        team_id
                    ))
                else:
                    # Insert new settings
                    cursor.execute("""
                        INSERT INTO team_settings 
                        (id, team_id, org_id, plan_id, team_name, gs_team_organization, gs_team_rep,
                         gs_team_product, gs_team_schedule_time, gs_team_initial_outreach, gs_team_follow_up,
                         gs_team_auto_interaction, gs_team_followup_schedule_time, gs_team_birthday_email)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        settings_id, team_id, org_id, plan_id, team_name,
                        json.dumps(
                            gs_team_organization) if gs_team_organization else None,
                        json.dumps(
                            gs_team_rep) if gs_team_rep else None,
                        json.dumps(
                            gs_team_product) if gs_team_product else None,
                        json.dumps(
                            gs_team_schedule_time) if gs_team_schedule_time else None,
                        json.dumps(
                            processed_initial_outreach) if processed_initial_outreach else None,
                        json.dumps(
                            gs_team_follow_up) if gs_team_follow_up else None,
                        json.dumps(
                            gs_team_auto_interaction) if gs_team_auto_interaction else None,
                        json.dumps(
                            gs_team_followup_schedule_time) if gs_team_followup_schedule_time else None,
                        json.dumps(
                            gs_team_birthday_email) if gs_team_birthday_email else None
                    ))

                conn.commit()
                self.logger.debug(f"Saved team settings: {team_id}")

        except Exception as e:
            self.logger.error(f"Failed to save team settings: {str(e)}")
            raise

    def get_team_settings(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Get team settings by team ID.

        Args:
            team_id: Team identifier

        Returns:
            Team settings dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM team_settings WHERE team_id = ?", (team_id,))
                row = cursor.fetchone()

                if row:
                    result = dict(row)
                    # Parse JSON fields
                    json_fields = [
                        'gs_team_organization', 'gs_team_rep', 'gs_team_product',
                        'gs_team_schedule_time', 'gs_team_initial_outreach', 'gs_team_follow_up',
                        'gs_team_auto_interaction', 'gs_team_followup_schedule_time', 'gs_team_birthday_email'
                    ]

                    for field in json_fields:
                        if result[field]:
                            try:
                                result[field] = json.loads(result[field])
                            except json.JSONDecodeError:
                                result[field] = None

                    return result
                return None

        except Exception as e:
            self.logger.error(f"Failed to get team settings: {str(e)}")
            raise

    def build_team_settings_snapshot(
        self,
        team_id: str,
        sections: Optional[Sequence[str]] = None
    ) -> Dict[str, Any]:
        """
        Build a response payload containing team settings in the expected RealTimeX format.

        Args:
            team_id: Team identifier
            sections: Optional sequence of section names to include. Accepts either
                full keys (e.g. ``gs_team_product``) or shorthand without the prefix.

        Returns:
            Dictionary shaped as ``{"data": [{...}]}``. When no settings exist,
            returns ``{"data": []}``.
        """
        settings = self.get_team_settings(team_id)
        if not settings:
            return {"data": []}

        available_fields = [
            'gs_team_organization',
            'gs_team_rep',
            'gs_team_product',
            'gs_team_schedule_time',
            'gs_team_initial_outreach',
            'gs_team_follow_up',
            'gs_team_auto_interaction',
            'gs_team_followup_schedule_time',
            'gs_team_birthday_email',
        ]

        if sections:
            normalized = set()
            for item in sections:
                if not item:
                    continue
                item = item.strip()
                if not item:
                    continue
                if item.startswith("gs_team_"):
                    normalized.add(item)
                else:
                    normalized.add(f"gs_team_{item}")
            fields_to_include = [field for field in available_fields if field in normalized]
        else:
            fields_to_include = available_fields

        list_like_fields = {
            'gs_team_organization',
            'gs_team_rep',
            'gs_team_product',
            'gs_team_auto_interaction',
        }
        list_field_defaults = {
            'gs_team_organization': {
                'org_name': None,
                'address': None,
                'website': None,
                'industry': None,
                'description': None,
                'logo': None,
                'primary_email': None,
                'primary_phone': None,
                'primary_color': None,
                'is_active': False,
                'avg_rating': None,
                'total_sales': None,
                'total_products': None,
                'date_joined': None,
                'last_active': None,
                'social_media_links': [],
            },
            'gs_team_rep': {
                'name': None,
                'email': None,
                'phone': None,
                'position': None,
                'website': None,
                'logo': None,
                'username': None,
                'is_primary': False,
                'primary_color': None,
                'primary_phone': None,
            },
            'gs_team_product': {
                'product_id': None,
                'product_name': None,
                'image_url': None,
                'enabled': True,
                'priority': None,
            },
            'gs_team_auto_interaction': {
                'from_email': '',
                'from_name': '',
                'from_number': '',
                'tool_type': 'Email',
                'email_cc': '',
                'email_bcc': '',
            },
        }
        alias_fields = {
            'gs_team_organization': {
                'name': 'org_name',
                'brand_palette': 'primary_color',
            },
        }

        snapshot: Dict[str, Any] = {}
        for field in fields_to_include:
            value = settings.get(field)
            if value is None:
                continue

            if field in list_like_fields:
                if isinstance(value, list):
                    normalized_items = []
                    defaults = list_field_defaults.get(field, {})
                    aliases = alias_fields.get(field, {})
                    for item in value:
                        if not isinstance(item, dict):
                            continue
                        normalized = {}
                        for key, default_val in defaults.items():
                            if key == 'social_media_links':
                                current = item.get(key)
                                normalized[key] = current if isinstance(current, list) else []
                            else:
                                normalized[key] = item.get(key, default_val)
                        for legacy_key, target_key in aliases.items():
                            if normalized.get(target_key) in (None, '', []):
                                if legacy_key in item:
                                    normalized[target_key] = item[legacy_key]
                        # include any additional keys that might exist
                        normalized_items.append(normalized)
                    snapshot[field] = normalized_items
                elif value:
                    defaults = list_field_defaults.get(field, {})
                    aliases = alias_fields.get(field, {})
                    normalized = {key: value.get(key, default_val) for key, default_val in defaults.items()}
                    for legacy_key, target_key in aliases.items():
                        if normalized.get(target_key) in (None, '', []):
                            if legacy_key in value:
                                normalized[target_key] = value[legacy_key]
                    snapshot[field] = [normalized]
                else:
                    snapshot[field] = []
            else:
                snapshot[field] = value

        if not snapshot:
            return {"data": []}

        return {"data": [snapshot]}

    def _deserialize_product_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert a product row into a dictionary with JSON fields parsed.

        Args:
            row: SQLite row containing product data

        Returns:
            Dictionary representation of the row with JSON fields decoded
        """
        product = dict(row)

        for field in self._product_json_fields:
            value = product.get(field)
            if value:
                try:
                    product[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    product[field] = None

        return product

    def save_product(self, product_data: Dict[str, Any]) -> str:
        """
        Save or update product information.

        Args:
            product_data: Product information dictionary

        Returns:
            Product ID
        """
        try:
            product_id = product_data.get('product_id') or product_data.get(
                'id') or self._generate_product_id()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT status FROM products WHERE product_id = ?", (product_id,))
                existing_row = cursor.fetchone()
                existing_status = existing_row[0] if existing_row else None
                normalized_status = self._normalize_status_value(product_data.get('status'))
                status_value = normalized_status or existing_status or 'active'

                if existing_row:
                    # Update existing product
                    cursor.execute("""
                        UPDATE products 
                        SET org_id = ?, org_name = ?, project_code = ?, product_name = ?,
                            short_description = ?, long_description = ?, category = ?, subcategory = ?,
                            target_users = ?, key_features = ?, unique_selling_points = ?, pain_points_solved = ?,
                            competitive_advantages = ?, pricing = ?, pricing_rules = ?, product_website = ?,
                            demo_available = ?, trial_available = ?, sales_contact_email = ?, image_url = ?,
                            sales_metrics = ?, customer_feedback = ?, keywords = ?, related_products = ?,
                            seasonal_demand = ?, market_insights = ?, case_studies = ?, testimonials = ?,
                            success_metrics = ?, product_variants = ?, availability = ?, technical_specifications = ?,
                            compatibility = ?, support_info = ?, regulatory_compliance = ?, localization = ?,
                            installation_requirements = ?, user_manual_url = ?, return_policy = ?, shipping_info = ?,
                            status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE product_id = ?
                    """, (
                        product_data.get('org_id'), product_data.get(
                            'org_name'), product_data.get('project_code'),
                        product_data.get('productName'), product_data.get(
                            'shortDescription'), product_data.get('longDescription'),
                        product_data.get('category'), product_data.get(
                            'subcategory'),
                        json.dumps(product_data.get('targetUsers')) if product_data.get(
                            'targetUsers') else None,
                        json.dumps(product_data.get('keyFeatures')) if product_data.get(
                            'keyFeatures') else None,
                        json.dumps(product_data.get('uniqueSellingPoints')) if product_data.get(
                            'uniqueSellingPoints') else None,
                        json.dumps(product_data.get('painPointsSolved')) if product_data.get(
                            'painPointsSolved') else None,
                        json.dumps(product_data.get('competitiveAdvantages')) if product_data.get(
                            'competitiveAdvantages') else None,
                        json.dumps(product_data.get('pricing')) if product_data.get(
                            'pricing') else None,
                        json.dumps(product_data.get('pricingRules')) if product_data.get(
                            'pricingRules') else None,
                        product_data.get('productWebsite'), product_data.get(
                            'demoAvailable', False),
                        product_data.get('trialAvailable', False), product_data.get(
                            'salesContactEmail'),
                        product_data.get('imageUrl'),
                        json.dumps(product_data.get('salesMetrics')) if product_data.get(
                            'salesMetrics') else None,
                        json.dumps(product_data.get('customerFeedback')) if product_data.get(
                            'customerFeedback') else None,
                        json.dumps(product_data.get('keywords')) if product_data.get(
                            'keywords') else None,
                        json.dumps(product_data.get('relatedProducts')) if product_data.get(
                            'relatedProducts') else None,
                        json.dumps(product_data.get('seasonalDemand')) if product_data.get(
                            'seasonalDemand') else None,
                        json.dumps(product_data.get('marketInsights')) if product_data.get(
                            'marketInsights') else None,
                        json.dumps(product_data.get('caseStudies')) if product_data.get(
                            'caseStudies') else None,
                        json.dumps(product_data.get('testimonials')) if product_data.get(
                            'testimonials') else None,
                        json.dumps(product_data.get('successMetrics')) if product_data.get(
                            'successMetrics') else None,
                        json.dumps(product_data.get('productVariants')) if product_data.get(
                            'productVariants') else None,
                        product_data.get('availability'),
                        json.dumps(product_data.get('technicalSpecifications')) if product_data.get(
                            'technicalSpecifications') else None,
                        json.dumps(product_data.get('compatibility')) if product_data.get(
                            'compatibility') else None,
                        json.dumps(product_data.get('supportInfo')) if product_data.get(
                            'supportInfo') else None,
                        json.dumps(product_data.get('regulatoryCompliance')) if product_data.get(
                            'regulatoryCompliance') else None,
                        json.dumps(product_data.get('localization')) if product_data.get(
                            'localization') else None,
                        product_data.get('installationRequirements'), product_data.get(
                            'userManualUrl'),
                        product_data.get('returnPolicy'),
                        json.dumps(product_data.get('shippingInfo')) if product_data.get(
                            'shippingInfo') else None,
                        status_value,
                        product_id
                    ))
                else:
                    # Insert new product
                    cursor.execute("""
                        INSERT INTO products 
                        (product_id, org_id, org_name, project_code, product_name, short_description, long_description,
                         category, subcategory, target_users, key_features, unique_selling_points, pain_points_solved,
                         competitive_advantages, pricing, pricing_rules, product_website, demo_available, trial_available,
                         sales_contact_email, image_url, sales_metrics, customer_feedback, keywords, related_products,
                         seasonal_demand, market_insights, case_studies, testimonials, success_metrics, product_variants,
                         availability, technical_specifications, compatibility, support_info, regulatory_compliance,
                         localization, installation_requirements, user_manual_url, return_policy, shipping_info, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        product_id, product_data.get('org_id'), product_data.get(
                            'org_name'), product_data.get('project_code'),
                        product_data.get('productName'), product_data.get(
                            'shortDescription'), product_data.get('longDescription'),
                        product_data.get('category'), product_data.get(
                            'subcategory'),
                        json.dumps(product_data.get('targetUsers')) if product_data.get(
                            'targetUsers') else None,
                        json.dumps(product_data.get('keyFeatures')) if product_data.get(
                            'keyFeatures') else None,
                        json.dumps(product_data.get('uniqueSellingPoints')) if product_data.get(
                            'uniqueSellingPoints') else None,
                        json.dumps(product_data.get('painPointsSolved')) if product_data.get(
                            'painPointsSolved') else None,
                        json.dumps(product_data.get('competitiveAdvantages')) if product_data.get(
                            'competitiveAdvantages') else None,
                        json.dumps(product_data.get('pricing')) if product_data.get(
                            'pricing') else None,
                        json.dumps(product_data.get('pricingRules')) if product_data.get(
                            'pricingRules') else None,
                        product_data.get('productWebsite'), product_data.get(
                            'demoAvailable', False),
                        product_data.get('trialAvailable', False), product_data.get(
                            'salesContactEmail'),
                        product_data.get('imageUrl'),
                        json.dumps(product_data.get('salesMetrics')) if product_data.get(
                            'salesMetrics') else None,
                        json.dumps(product_data.get('customerFeedback')) if product_data.get(
                            'customerFeedback') else None,
                        json.dumps(product_data.get('keywords')) if product_data.get(
                            'keywords') else None,
                        json.dumps(product_data.get('relatedProducts')) if product_data.get(
                            'relatedProducts') else None,
                        json.dumps(product_data.get('seasonalDemand')) if product_data.get(
                            'seasonalDemand') else None,
                        json.dumps(product_data.get('marketInsights')) if product_data.get(
                            'marketInsights') else None,
                        json.dumps(product_data.get('caseStudies')) if product_data.get(
                            'caseStudies') else None,
                        json.dumps(product_data.get('testimonials')) if product_data.get(
                            'testimonials') else None,
                        json.dumps(product_data.get('successMetrics')) if product_data.get(
                            'successMetrics') else None,
                        json.dumps(product_data.get('productVariants')) if product_data.get(
                            'productVariants') else None,
                        product_data.get('availability'),
                        json.dumps(product_data.get('technicalSpecifications')) if product_data.get(
                            'technicalSpecifications') else None,
                        json.dumps(product_data.get('compatibility')) if product_data.get(
                            'compatibility') else None,
                        json.dumps(product_data.get('supportInfo')) if product_data.get(
                            'supportInfo') else None,
                        json.dumps(product_data.get('regulatoryCompliance')) if product_data.get(
                            'regulatoryCompliance') else None,
                        json.dumps(product_data.get('localization')) if product_data.get(
                            'localization') else None,
                        product_data.get('installationRequirements'), product_data.get(
                            'userManualUrl'),
                        product_data.get('returnPolicy'),
                        json.dumps(product_data.get('shippingInfo')) if product_data.get(
                            'shippingInfo') else None,
                        status_value
                    ))

                conn.commit()
                self.logger.debug(f"Saved product: {product_id}")
                return product_id

        except Exception as e:
            self.logger.error(f"Failed to save product: {str(e)}")
            raise

    def search_products(
        self,
        org_id: str,
        status: Optional[str] = "active",
        search_term: Optional[str] = None,
        limit: Optional[int] = None,
        sort: Optional[str] = "name"
    ) -> List[Dict[str, Any]]:
        """
        Search products for an organization with optional filters.

        Args:
            org_id: Organization identifier
            status: Product status filter ("active", "inactive", or "all")
            search_term: Keyword to match against name, descriptions, or keywords
            limit: Maximum number of products to return
            sort: Sort order ("name", "created_at", "updated_at")

        Returns:
            List of product dictionaries
        """
        try:
            def _is_placeholder(value: Any) -> bool:
                return isinstance(value, str) and value.strip().startswith("{{") and value.strip().endswith("}}")

            # Normalize status
            normalized_status: Optional[str] = status
            if _is_placeholder(normalized_status):
                normalized_status = None
            if isinstance(normalized_status, str):
                normalized_status = normalized_status.strip().lower()
            if normalized_status not in {'active', 'inactive', 'all'}:
                normalized_status = 'active'

            # Normalize sort
            normalized_sort: Optional[str] = sort
            if _is_placeholder(normalized_sort):
                normalized_sort = None
            if isinstance(normalized_sort, str):
                normalized_sort = normalized_sort.strip().lower()
            sort_map = {
                'name': ("product_name COLLATE NOCASE", "ASC"),
                'created_at': ("datetime(created_at)", "DESC"),
                'updated_at': ("datetime(updated_at)", "DESC"),
            }
            order_by, direction = sort_map.get(normalized_sort, sort_map['name'])

            # Normalize search term
            normalized_search: Optional[str] = None
            if not _is_placeholder(search_term) and search_term is not None:
                normalized_search = str(search_term).strip()
            if normalized_search == "":
                normalized_search = None

            # Normalize limit
            normalized_limit: Optional[int] = None
            if not _is_placeholder(limit) and limit is not None:
                try:
                    normalized_limit = int(limit)
                    if normalized_limit <= 0:
                        normalized_limit = None
                except (TypeError, ValueError):
                    normalized_limit = None

            where_clauses = ["org_id = ?"]
            params: List[Any] = [org_id]

            if normalized_status != 'all':
                where_clauses.append("status = ?")
                params.append(normalized_status)

            query = "SELECT * FROM products WHERE " + " AND ".join(where_clauses)

            if normalized_search:
                like_value = f"%{normalized_search.lower()}%"
                query += (
                    " AND ("
                    "LOWER(product_name) LIKE ? OR "
                    "LOWER(COALESCE(short_description, '')) LIKE ? OR "
                    "LOWER(COALESCE(long_description, '')) LIKE ? OR "
                    "LOWER(COALESCE(keywords, '')) LIKE ?)"
                )
                params.extend([like_value] * 4)

            query += f" ORDER BY {order_by} {direction}"

            if normalized_limit is not None:
                query += " LIMIT ?"
                params.append(normalized_limit)

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

            return [self._deserialize_product_row(row) for row in rows]

        except Exception as e:
            self.logger.error(f"Failed to search products: {str(e)}")
            raise

    def get_products_by_org(self, org_id: str) -> List[Dict[str, Any]]:
        """
        Backward-compatible helper that returns active products for an organization.

        Args:
            org_id: Organization identifier

        Returns:
            List of active product dictionaries
        """
        return self.search_products(org_id=org_id, status="active")

    def get_products_by_team(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get products configured for a specific team.

        Args:
            team_id: Team identifier

        Returns:
            List of product dictionaries
        """
        try:
            # Get team settings first
            team_settings = self.get_team_settings(team_id)
            if not team_settings or not team_settings.get('gs_team_product'):
                return []

            # Extract product IDs from team settings
            product_settings = team_settings['gs_team_product']
            if not isinstance(product_settings, list):
                return []

            product_ids = [p.get('product_id')
                           for p in product_settings if p.get('product_id')]
            if not product_ids:
                return []

            # Get products by IDs
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                placeholders = ','.join(['?' for _ in product_ids])
                cursor.execute(
                    f"SELECT * FROM products WHERE product_id IN ({placeholders}) AND status = 'active'", product_ids)

                return [self._deserialize_product_row(row)
                        for row in cursor.fetchall()]

        except Exception as e:
            self.logger.error(f"Failed to get products by team: {str(e)}")
            raise

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get product by ID.

        Args:
            product_id: Product identifier

        Returns:
            Product data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
                row = cursor.fetchone()

                if row:
                    return self._deserialize_product_row(row)
                return None

        except Exception as e:
            self.logger.error(f"Error getting product {product_id}: {str(e)}")
            raise

    def update_product(self, product_id: str, product_data: Dict[str, Any]) -> bool:
        """
        Update product information.

        Args:
            product_id: Product identifier
            product_data: Updated product data

        Returns:
            True if updated successfully
        """
        try:
            # Get existing product data first
            existing_product = self.get_product(product_id)
            if not existing_product:
                self.logger.error(f"Product not found: {product_id}")
                return False
            
            # Convert existing data to save_product format (snake_case to camelCase)
            converted_existing = {
                'product_id': existing_product.get('product_id'),
                'org_id': existing_product.get('org_id'),
                'org_name': existing_product.get('org_name'),
                'project_code': existing_product.get('project_code'),
                'productName': existing_product.get('product_name'),
                'shortDescription': existing_product.get('short_description'),
                'longDescription': existing_product.get('long_description'),
                'category': existing_product.get('category'),
                'subcategory': existing_product.get('subcategory'),
                'targetUsers': existing_product.get('target_users'),
                'keyFeatures': existing_product.get('key_features'),
                'uniqueSellingPoints': existing_product.get('unique_selling_points'),
                'painPointsSolved': existing_product.get('pain_points_solved'),
                'competitiveAdvantages': existing_product.get('competitive_advantages'),
                'pricing': existing_product.get('pricing'),
                'pricingRules': existing_product.get('pricing_rules'),
                'productWebsite': existing_product.get('product_website'),
                'demoAvailable': existing_product.get('demo_available'),
                'trialAvailable': existing_product.get('trial_available'),
                'salesContactEmail': existing_product.get('sales_contact_email'),
                'imageUrl': existing_product.get('image_url'),
                'salesMetrics': existing_product.get('sales_metrics'),
                'customerFeedback': existing_product.get('customer_feedback'),
                'keywords': existing_product.get('keywords'),
                'relatedProducts': existing_product.get('related_products'),
                'seasonalDemand': existing_product.get('seasonal_demand'),
                'marketInsights': existing_product.get('market_insights'),
                'caseStudies': existing_product.get('case_studies'),
                'testimonials': existing_product.get('testimonials'),
                'successMetrics': existing_product.get('success_metrics'),
                'productVariants': existing_product.get('product_variants'),
                'availability': existing_product.get('availability'),
                'technicalSpecifications': existing_product.get('technical_specifications'),
                'compatibility': existing_product.get('compatibility'),
                'supportInfo': existing_product.get('support_info'),
                'regulatoryCompliance': existing_product.get('regulatory_compliance'),
                'localization': existing_product.get('localization'),
                'installationRequirements': existing_product.get('installation_requirements'),
                'userManualUrl': existing_product.get('user_manual_url'),
                'returnPolicy': existing_product.get('return_policy'),
                'shippingInfo': existing_product.get('shipping_info'),
                'status': existing_product.get('status')
            }
            
            # Merge existing data with updates
            merged_data = converted_existing.copy()
            merged_data.update(product_data)
            merged_data['product_id'] = product_id
            
            # Use save_product with merged data
            updated_id = self.save_product(merged_data)
            return updated_id == product_id

        except Exception as e:
            self.logger.error(f"Error updating product {product_id}: {str(e)}")
            raise

    def update_product_status(self, product_id: str, status: Union[str, bool]) -> bool:
        """
        Update activation status for a product.

        Args:
            product_id: Product identifier
            status: Target status ("active" or "inactive")

        Returns:
            True if a product record was updated
        """
        normalized_status = self._normalize_status_value(status)
        if normalized_status is None:
            raise ValueError("Status is required when updating product status")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE products
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ?
                    """,
                    (normalized_status, product_id)
                )
                conn.commit()
                if cursor.rowcount:
                    self.logger.debug(f"Updated product status: {product_id} -> {normalized_status}")
                return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"Failed to update product status {product_id}: {str(e)}")
            raise

    def save_scoring_criteria(self, org_id: str, criteria: List[Dict[str, Any]]) -> None:
        """
        Save scoring criteria for an organization.

        Args:
            org_id: Organization identifier
            criteria: List of scoring criteria
        """
        try:
            # Save to configuration file
            criteria_file = self.config_dir / "scoring_criteria.json"

            # Load existing criteria
            existing_criteria = {}
            if criteria_file.exists():
                with open(criteria_file, 'r') as f:
                    existing_criteria = json.load(f)

            # Update criteria for this org
            existing_criteria[org_id] = criteria

            # Save back to file
            with open(criteria_file, 'w') as f:
                json.dump(existing_criteria, f, indent=2)

            self.logger.debug(f"Saved scoring criteria for org: {org_id}")

        except Exception as e:
            self.logger.error(f"Failed to save scoring criteria: {str(e)}")
            raise

    def get_scoring_criteria(self, org_id: str) -> List[Dict[str, Any]]:
        """
        Get scoring criteria for an organization.

        Args:
            org_id: Organization identifier

        Returns:
            List of scoring criteria
        """
        try:
            criteria_file = self.config_dir / "scoring_criteria.json"

            if criteria_file.exists():
                with open(criteria_file, 'r') as f:
                    all_criteria = json.load(f)
                    return all_criteria.get(org_id, [])

            return []

        except Exception as e:
            self.logger.error(f"Failed to get scoring criteria: {str(e)}")
            return []

    def _generate_product_id(self) -> str:
        """Generate unique product ID."""
        import uuid
        return f"uuid:{str(uuid.uuid4())}"

    def _initialize_default_data(self):
        """Initialize default data for llm_worker_plan and gs_company_criteria tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if llm_worker_plan has data
                cursor.execute("SELECT COUNT(*) FROM llm_worker_plan")
                plan_count = cursor.fetchone()[0]

                if plan_count == 0:
                    # Insert default llm_worker_plan record
                    default_plan = {
                        'id': '569cdcbd-cf6d-4e33-b0b2-d2f6f15a0832',
                        'name': 'FuseSell AI (v1.025)',
                        'description': 'Default FuseSell AI plan for local development',
                        'org_id': 'rta',
                        'status': 'published',
                        'executors': json.dumps([
                            {
                                'llm_worker_executor_id': {
                                    'name': 'gs_161_data_acquisition',
                                    'display_name': 'Data Acquisition'
                                }
                            },
                            {
                                'llm_worker_executor_id': {
                                    'name': 'gs_161_data_preparation',
                                    'display_name': 'Data Preparation'
                                }
                            },
                            {
                                'llm_worker_executor_id': {
                                    'name': 'gs_161_lead_scoring',
                                    'display_name': 'Lead Scoring'
                                }
                            },
                            {
                                'llm_worker_executor_id': {
                                    'name': 'gs_162_initial_outreach',
                                    'display_name': 'Initial Outreach'
                                }
                            },
                            {
                                'llm_worker_executor_id': {
                                    'name': 'gs_162_follow_up',
                                    'display_name': 'Follow Up'
                                }
                            }
                        ]),
                        'settings': json.dumps({}),
                        'date_created': datetime.now().isoformat(),
                        'user_created': 'system'
                    }

                    cursor.execute("""
                        INSERT INTO llm_worker_plan 
                        (id, name, description, org_id, status, executors, settings, 
                         date_created, user_created)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        default_plan['id'],
                        default_plan['name'],
                        default_plan['description'],
                        default_plan['org_id'],
                        default_plan['status'],
                        default_plan['executors'],
                        default_plan['settings'],
                        default_plan['date_created'],
                        default_plan['user_created']
                    ))

                    self.logger.debug(
                        "Initialized default llm_worker_plan data")

                # Check if gs_company_criteria has data
                cursor.execute("SELECT COUNT(*) FROM gs_company_criteria")
                criteria_count = cursor.fetchone()[0]

                if criteria_count == 0:
                    # Insert default gs_company_criteria records (based on fetched data)
                    default_criteria = [
                        {
                            'id': 'criteria_industry_fit',
                            'name': 'industry_fit',
                            'definition': 'How well the customer\'s industry aligns with the product\'s target market',
                            'weight': 0.15,
                            'guidelines': json.dumps({
                                'low': {'range': [0, 49], 'description': "Industries with minimal overlap or relevance to product capabilities"},
                                'medium': {'range': [50, 79], 'description': 'Industries with potential for product adoption but limited case studies'},
                                'high': {'range': [80, 100], 'description': 'Industries where product has proven success (e.g., IT services, software development, project management firms)'}
                            }),
                            'scoring_factors': json.dumps([
                                'Perfect industry match: 80-100',
                                'Related industry: 60-79',
                                'Adjacent industry: 40-59',
                                'Unrelated industry: 0-39'
                            ]),
                            'org_id': 'rta',
                            'status': 'published',
                            'date_created': datetime.now().isoformat(),
                            'user_created': 'system'
                        },
                        {
                            'id': 'criteria_company_size',
                            'name': 'company_size',
                            'definition': 'Company size alignment with product\'s ideal customer profile',
                            'weight': 0.15,
                            'guidelines': json.dumps({
                                'low': {'range': [0, 49], 'description': 'Companies below 20 or above 1000 employees, or outside the specified revenue ranges'},
                                'medium': {'range': [50, 79], 'description': 'Companies with 20-49 or 501-1000 employees, $1M-$4.9M or $50.1M-$100M revenue'},
                                'high': {'range': [80, 100], 'description': 'Companies with 50-500 employees and $5M-$50M annual revenue'}
                            }),
                            'scoring_factors': json.dumps([
                                'Ideal size range: 80-100',
                                'Close to ideal: 60-79',
                                'Acceptable size: 40-59',
                                'Poor size fit: 0-39'
                            ]),
                            'org_id': 'rta',
                            'status': 'published',
                            'date_created': datetime.now().isoformat(),
                            'user_created': 'system'
                        },
                        {
                            'id': 'criteria_pain_points',
                            'name': 'pain_points',
                            'definition': 'How well the product addresses customer\'s identified pain points',
                            'weight': 0.3,
                            'guidelines': json.dumps({
                                'low': {'range': [0, 49], 'description': "Few or no relevant pain points, or challenges outside product's primary focus"},
                                'medium': {'range': [50, 79], 'description': 'Some relevant pain points addressed, with potential for significant impact'},
                                'high': {'range': [80, 100], 'description': "Multiple critical pain points directly addressed by product's core features"}
                            }),
                            'scoring_factors': json.dumps([
                                'Addresses all major pain points: 80-100',
                                'Addresses most pain points: 60-79',
                                'Addresses some pain points: 40-59',
                                'Addresses few/no pain points: 0-39'
                            ]),
                            'org_id': 'rta',
                            'status': 'published',
                            'date_created': datetime.now().isoformat(),
                            'user_created': 'system'
                        },
                        {
                            'id': 'criteria_product_fit',
                            'name': 'product_fit',
                            'definition': 'Overall product-customer compatibility',
                            'weight': 0.2,
                            'guidelines': json.dumps({
                                'low': {'range': [0, 49], 'description': "Significant gaps between product's capabilities and the prospect's needs, or extensive customization required"},
                                'medium': {'range': [50, 79], 'description': 'Product addresses most key needs, some customization or additional features may be necessary'},
                                'high': {'range': [80, 100], 'description': "Product's features closely match the prospect's primary needs with minimal customization required"}
                            }),
                            'scoring_factors': json.dumps([
                                'Excellent feature match: 80-100',
                                'Good feature match: 60-79',
                                'Basic feature match: 40-59',
                                'Poor feature match: 0-39'
                            ]),
                            'org_id': 'rta',
                            'status': 'published',
                            'date_created': datetime.now().isoformat(),
                            'user_created': 'system'
                        },
                        {
                            'id': 'criteria_geographic_fit',
                            'name': 'geographic_market_fit',
                            'definition': 'Geographic alignment between customer location and product availability',
                            'weight': 0.2,
                            'guidelines': json.dumps({
                                'low': {'range': [0, 30], 'description': "Customer location is outside of the product's designated target markets"},
                                'medium': {'range': [31, 70], 'description': "Customer location is in regions adjacent to or with strong ties to the product's primary markets"},
                                'high': {'range': [71, 100], 'description': "Customer location is within the product's primary target markets"}
                            }),
                            'scoring_factors': json.dumps([
                                'Strong market presence: 80-100',
                                'Moderate presence: 60-79',
                                'Limited presence: 40-59',
                                'No market presence: 0-39'
                            ]),
                            'org_id': 'rta',
                            'status': 'published',
                            'date_created': datetime.now().isoformat(),
                            'user_created': 'system'
                        }
                    ]

                    for criteria in default_criteria:
                        cursor.execute("""
                            INSERT INTO gs_company_criteria 
                            (id, name, definition, weight, guidelines, scoring_factors, org_id, status,
                             date_created, user_created)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            criteria['id'],
                            criteria['name'],
                            criteria['definition'],
                            criteria['weight'],
                            criteria['guidelines'],
                            criteria['scoring_factors'],
                            criteria['org_id'],
                            criteria['status'],
                            criteria['date_created'],
                            criteria['user_created']
                        ))

                    self.logger.debug(
                        f"Initialized {len(default_criteria)} default gs_company_criteria records")

                # Initialize default products if none exist
                cursor.execute(
                    "SELECT COUNT(*) FROM products WHERE org_id = 'rta'")
                product_count = cursor.fetchone()[0]

                if product_count == 0:
                    default_products = [
                        {
                            'product_id': 'prod-12345678-1234-1234-1234-123456789012',
                            'org_id': 'rta',
                            'org_name': 'RTA',
                            'project_code': 'FUSESELL',
                            'product_name': 'FuseSell AI Pro',
                            'short_description': 'AI-powered sales automation platform',
                            'long_description': 'Comprehensive sales automation solution with AI-driven lead scoring, email generation, and customer analysis capabilities',
                            'category': 'Sales Automation',
                            'subcategory': 'AI-Powered CRM',
                            'target_users': json.dumps(['Sales teams', 'Marketing professionals', 'Business development managers']),
                            'key_features': json.dumps(['AI lead scoring', 'Automated email generation', 'Customer data analysis', 'Pipeline management']),
                            'pain_points_solved': json.dumps(['Manual lead qualification', 'Inconsistent email outreach', 'Poor lead prioritization']),
                            'competitive_advantages': json.dumps(['Advanced AI algorithms', 'Local data processing', 'Customizable workflows']),
                            'localization': json.dumps(['North America', 'Europe', 'Asia-Pacific', 'Vietnam']),
                            'market_insights': json.dumps({'targetIndustries': ['Technology', 'SaaS', 'Professional Services'], 'idealCompanySize': '50-500 employees'}),
                            'status': 'active'
                        },
                        {
                            'product_id': 'prod-87654321-4321-4321-4321-210987654321',
                            'org_id': 'rta',
                            'org_name': 'RTA',
                            'project_code': 'FUSESELL',
                            'product_name': 'FuseSell Starter',
                            'short_description': 'Entry-level sales automation tool',
                            'long_description': 'Basic sales automation features for small teams getting started with sales technology',
                            'category': 'Sales Automation',
                            'subcategory': 'Basic CRM',
                            'target_users': json.dumps(['Small sales teams', 'Startups', 'Solo entrepreneurs']),
                            'key_features': json.dumps(['Contact management', 'Email templates', 'Basic reporting', 'Lead tracking']),
                            'pain_points_solved': json.dumps(['Manual contact management', 'Basic email automation needs']),
                            'competitive_advantages': json.dumps(['Easy to use', 'Affordable pricing', 'Quick setup']),
                            'localization': json.dumps(['Global']),
                            'market_insights': json.dumps({'targetIndustries': ['All industries'], 'idealCompanySize': '1-50 employees'}),
                            'status': 'active'
                        }
                    ]

                    for product in default_products:
                        cursor.execute("""
                            INSERT INTO products 
                            (product_id, org_id, org_name, project_code, product_name, short_description, 
                             long_description, category, subcategory, target_users, key_features, 
                             pain_points_solved, competitive_advantages, localization, market_insights, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            product['product_id'], product['org_id'], product['org_name'], product['project_code'],
                            product['product_name'], product['short_description'], product['long_description'],
                            product['category'], product['subcategory'], product['target_users'], product['key_features'],
                            product['pain_points_solved'], product['competitive_advantages'], product['localization'],
                            product['market_insights'], product['status']
                        ))

                    self.logger.debug(
                        f"Initialized {len(default_products)} default products")

                # Initialize default team settings if none exist
                cursor.execute(
                    "SELECT COUNT(*) FROM team_settings WHERE org_id = 'rta'")
                team_count = cursor.fetchone()[0]

                if team_count == 0:
                    default_team_settings = {
                        'id': 'team_rta_default_settings',
                        'team_id': 'team_rta_default',
                        'org_id': 'rta',
                        'plan_id': '569cdcbd-cf6d-4e33-b0b2-d2f6f15a0832',
                        'plan_name': 'FuseSell AI (v1.025)',
                        'project_code': 'FUSESELL',
                        'team_name': 'RTA Default Team',
                        'gs_team_organization': json.dumps({
                            'name': 'RTA',
                            'industry': 'Technology',
                            'website': 'https://rta.vn'
                        }),
                        'gs_team_rep': json.dumps([{
                            'name': 'Sales Team',
                            'email': 'sales@rta.vn',
                            'position': 'Sales Representative',
                            'is_primary': True
                        }]),
                        'gs_team_product': json.dumps([
                            {'product_id': 'prod-12345678-1234-1234-1234-123456789012',
                             'enabled': True, 'priority': 1},
                            {'product_id': 'prod-87654321-4321-4321-4321-210987654321',
                             'enabled': True, 'priority': 2}
                        ]),
                        'gs_team_schedule_time': json.dumps({
                            'business_hours_start': '08:00',
                            'business_hours_end': '20:00',
                            'default_delay_hours': 2,
                            'respect_weekends': True
                        }),
                        'gs_team_initial_outreach': json.dumps({
                            'default_tone': 'professional',
                            'approaches': [
                                'professional_direct',
                                'consultative',
                                'industry_expert',
                                'relationship_building'
                            ],
                            'subject_line_variations': 1
                        }),
                        'gs_team_follow_up': json.dumps({
                            'max_follow_ups': 5,
                            'default_interval_days': 3,
                            'strategies': [
                                'gentle_reminder',
                                'value_add',
                                'alternative_approach',
                                'final_attempt',
                                'graceful_farewell'
                            ]
                        }),
                        'gs_team_auto_interaction': json.dumps({
                            'enabled': True,
                            'handoff_threshold': 0.8,
                            'monitoring': 'standard'
                        }),
                        'gs_team_followup_schedule_time': json.dumps({
                            'timezone': 'Asia/Ho_Chi_Minh',
                            'window': 'business_hours'
                        }),
                        'gs_team_birthday_email': json.dumps({
                            'enabled': True,
                            'template': 'birthday_2025'
                        })
                    }

                    cursor.execute("""
                        INSERT INTO team_settings 
                        (id, team_id, org_id, plan_id, plan_name, project_code, team_name,
                         gs_team_organization, gs_team_rep, gs_team_product,
                         gs_team_schedule_time, gs_team_initial_outreach, gs_team_follow_up,
                         gs_team_auto_interaction, gs_team_followup_schedule_time, gs_team_birthday_email)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        default_team_settings['id'],
                        default_team_settings['team_id'],
                        default_team_settings['org_id'],
                        default_team_settings['plan_id'],
                        default_team_settings['plan_name'],
                        default_team_settings['project_code'],
                        default_team_settings['team_name'],
                        default_team_settings['gs_team_organization'],
                        default_team_settings['gs_team_rep'],
                        default_team_settings['gs_team_product'],
                        default_team_settings['gs_team_schedule_time'],
                        default_team_settings['gs_team_initial_outreach'],
                        default_team_settings['gs_team_follow_up'],
                        default_team_settings['gs_team_auto_interaction'],
                        default_team_settings['gs_team_followup_schedule_time'],
                        default_team_settings['gs_team_birthday_email']
                    ))

                    self.logger.debug("Initialized default team settings")

                conn.commit()

        except Exception as e:
            self.logger.warning(f"Failed to initialize default data: {str(e)}")
            # Don't raise exception - this is not critical for basic functionality

    def get_gs_company_criteria(self, org_id: str) -> List[Dict[str, Any]]:
        """
        Get scoring criteria from gs_company_criteria table (server schema).

        Args:
            org_id: Organization identifier

        Returns:
            List of scoring criteria from gs_company_criteria table
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM gs_company_criteria 
                    WHERE org_id = ? AND status = 'published'
                    ORDER BY name
                """, (org_id,))

                criteria = []
                for row in cursor.fetchall():
                    criterion = dict(row)

                    # Parse JSON fields
                    if criterion['guidelines']:
                        try:
                            criterion['guidelines'] = json.loads(
                                criterion['guidelines'])
                        except json.JSONDecodeError:
                            pass

                    if criterion['scoring_factors']:
                        try:
                            criterion['scoring_factors'] = json.loads(
                                criterion['scoring_factors'])
                        except json.JSONDecodeError:
                            pass

                    criteria.append(criterion)

                return criteria

        except Exception as e:
            self.logger.error(f"Failed to get gs_company_criteria: {str(e)}")
            return []

    def get_llm_worker_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get llm_worker_plan data by plan ID.

        Args:
            plan_id: Plan identifier

        Returns:
            Plan data dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM llm_worker_plan WHERE id = ?", (plan_id,))
                row = cursor.fetchone()

                if row:
                    result = dict(row)

                    # Parse JSON fields
                    if result['executors']:
                        try:
                            result['executors'] = json.loads(
                                result['executors'])
                        except json.JSONDecodeError:
                            result['executors'] = []

                    if result['settings']:
                        try:
                            result['settings'] = json.loads(result['settings'])
                        except json.JSONDecodeError:
                            result['settings'] = {}

                    return result
                return None

        except Exception as e:
            self.logger.error(f"Failed to get llm_worker_plan: {str(e)}")
            return None

   # ===== TASK MANAGEMENT METHODS (Correct Schema Implementation) =====

    def save_task(
        self,
        task_id: str,
        plan_id: str,
        org_id: str,
        status: str = "running",
        messages: Optional[List[str]] = None,
        request_body: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save sales process task (equivalent to llm_worker_task).

        Args:
            task_id: Unique task identifier (sales process ID)
            plan_id: Plan identifier
            org_id: Organization identifier
            status: Task status (running, completed, failed)
            messages: Optional messages for the task
            request_body: Initial request data for the sales process
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO llm_worker_task 
                    (task_id, plan_id, org_id, status, current_runtime_index, messages, request_body)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id, plan_id, org_id, status, 0,
                    json.dumps(messages) if messages else None,
                    json.dumps(request_body) if request_body else None
                ))
                conn.commit()
                self.logger.debug(f"Saved task: {task_id}")

        except Exception as e:
            self.logger.error(f"Failed to save task: {str(e)}")
            raise

    def update_task_status(
        self,
        task_id: str,
        status: str,
        runtime_index: Optional[int] = None
    ) -> None:
        """
        Update task status and runtime index.

        Args:
            task_id: Task identifier
            status: New status
            runtime_index: Current runtime index (stage number)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if runtime_index is not None:
                    cursor.execute("""
                        UPDATE llm_worker_task 
                        SET status = ?, current_runtime_index = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    """, (status, runtime_index, task_id))
                else:
                    cursor.execute("""
                        UPDATE llm_worker_task 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    """, (status, task_id))

                conn.commit()
                self.logger.debug(
                    f"Updated task status: {task_id} -> {status}")

        except Exception as e:
            self.logger.error(f"Failed to update task status: {str(e)}")
            raise

    def save_operation(
        self,
        operation_id: str,
        task_id: str,
        executor_id: str,
        chain_order: int,
        chain_index: int,
        runtime_index: int,
        item_index: int,
        execution_status: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        user_messages: Optional[List[str]] = None
    ) -> None:
        """
        Save stage operation execution (equivalent to llm_worker_operation).

        Args:
            operation_id: Unique operation identifier
            task_id: Parent task identifier
            executor_id: Stage executor identifier (e.g., 'data_acquisition')
            chain_order: Order in the execution chain
            chain_index: Chain index
            runtime_index: Runtime index (stage number)
            item_index: Item index
            execution_status: Operation status (running, done, failed)
            input_data: Input data for the operation
            output_data: Output data from the operation
            payload: Additional payload data
            user_messages: User messages for the operation
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO llm_worker_operation 
                    (operation_id, task_id, executor_id, chain_order, chain_index, 
                     runtime_index, item_index, execution_status, input_data, 
                     output_data, payload, user_messages)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    operation_id, task_id, executor_id, chain_order, chain_index,
                    runtime_index, item_index, execution_status,
                    json.dumps(input_data) if input_data else None,
                    json.dumps(output_data) if output_data else None,
                    json.dumps(payload) if payload else None,
                    json.dumps(user_messages) if user_messages else None
                ))
                conn.commit()
                self.logger.debug(f"Saved operation: {operation_id}")

        except Exception as e:
            self.logger.error(f"Failed to save operation: {str(e)}")
            raise

    def get_task_operations(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all operations for a specific task.

        Args:
            task_id: Task identifier

        Returns:
            List of operation records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM llm_worker_operation 
                    WHERE task_id = ? 
                    ORDER BY runtime_index, chain_order
                """, (task_id,))

                columns = [description[0]
                           for description in cursor.description]
                operations = []

                for row in cursor.fetchall():
                    operation = dict(zip(columns, row))
                    # Parse JSON fields
                    for field in ['input_data', 'output_data', 'payload', 'user_messages']:
                        if operation[field]:
                            try:
                                operation[field] = json.loads(operation[field])
                            except json.JSONDecodeError:
                                pass
                    operations.append(operation)

                return operations

        except Exception as e:
            self.logger.error(f"Failed to get task operations: {str(e)}")
            return []

    def get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task record or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM llm_worker_task WHERE task_id = ?", (task_id,))

                row = cursor.fetchone()
                if row:
                    columns = [description[0]
                               for description in cursor.description]
                    task = dict(zip(columns, row))

                    # Parse JSON fields
                    for field in ['messages', 'request_body']:
                        if task[field]:
                            try:
                                task[field] = json.loads(task[field])
                            except json.JSONDecodeError:
                                pass

                    return task

                return None

        except Exception as e:
            self.logger.error(f"Failed to get task: {str(e)}")
            return None

    def list_tasks(
        self,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering.

        Args:
            org_id: Optional organization filter
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of task records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM llm_worker_task"
                params = []
                conditions = []

                if org_id:
                    conditions.append("org_id = ?")
                    params.append(org_id)

                if status:
                    conditions.append("status = ?")
                    params.append(status)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)

                columns = [description[0]
                           for description in cursor.description]
                tasks = []

                for row in cursor.fetchall():
                    task = dict(zip(columns, row))
                    # Parse JSON fields
                    for field in ['messages', 'request_body']:
                        if task[field]:
                            try:
                                task[field] = json.loads(task[field])
                            except json.JSONDecodeError:
                                pass
                    tasks.append(task)

                return tasks

        except Exception as e:
            self.logger.error(f"Failed to list tasks: {str(e)}")
            return []
 # ===== SALES PROCESS QUERY METHODS =====

    def find_sales_processes_by_customer(self, customer_name: str) -> List[Dict[str, Any]]:
        """
        Find all sales processes for a specific customer.

        Args:
            customer_name: Customer name to search for

        Returns:
            List of task records matching the customer
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.*, 
                           json_extract(t.request_body, '$.customer_info') as customer_info,
                           json_extract(t.request_body, '$.org_name') as org_name
                    FROM llm_worker_task t
                    WHERE json_extract(t.request_body, '$.customer_info') LIKE ?
                    ORDER BY t.created_at DESC
                """, (f'%{customer_name}%',))

                columns = [description[0]
                           for description in cursor.description]
                processes = []

                for row in cursor.fetchall():
                    process = dict(zip(columns, row))
                    # Parse JSON fields
                    for field in ['messages', 'request_body']:
                        if process[field]:
                            try:
                                process[field] = json.loads(process[field])
                            except json.JSONDecodeError:
                                pass
                    processes.append(process)

                return processes

        except Exception as e:
            self.logger.error(
                f"Failed to find sales processes by customer: {str(e)}")
            return []

    def get_sales_process_stages(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all stage executions for a specific sales process.

        Args:
            task_id: Sales process (task) identifier

        Returns:
            List of operation records for the sales process
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        operation_id,
                        executor_id,
                        runtime_index,
                        execution_status,
                        input_data,
                        output_data,
                        created_at,
                        updated_at
                    FROM llm_worker_operation 
                    WHERE task_id = ? 
                    ORDER BY runtime_index, chain_order
                """, (task_id,))

                columns = [description[0]
                           for description in cursor.description]
                stages = []

                for row in cursor.fetchall():
                    stage = dict(zip(columns, row))
                    # Parse JSON fields
                    for field in ['input_data', 'output_data']:
                        if stage[field]:
                            try:
                                stage[field] = json.loads(stage[field])
                            except json.JSONDecodeError:
                                pass

                    # Map executor_id to readable stage name
                    executor_mapping = {
                        'gs_161_data_acquisition': 'Data Acquisition',
                        'gs_161_data_preparation': 'Data Preparation',
                        'gs_161_lead_scoring': 'Lead Scoring',
                        'gs_162_initial_outreach': 'Initial Outreach',
                        'gs_162_follow_up': 'Follow-up'
                    }
                    stage['stage_name'] = executor_mapping.get(
                        stage['executor_id'], stage['executor_id'])

                    stages.append(stage)

                return stages

        except Exception as e:
            self.logger.error(f"Failed to get sales process stages: {str(e)}")
            return []

    def get_sales_process_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a complete summary of a sales process including task info and all stages.

        Args:
            task_id: Sales process (task) identifier

        Returns:
            Complete sales process summary or None if not found
        """
        try:
            # Get task info
            task = self.get_task_by_id(task_id)
            if not task:
                return None

            # Get all stage operations
            stages = self.get_sales_process_stages(task_id)

            # Get related data
            lead_scores = []
            email_drafts = []

            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()

                    # Get lead scores
                    cursor.execute("""
                        SELECT product_id, score, criteria_breakdown, created_at
                        FROM lead_scores 
                        WHERE execution_id = ?
                    """, (task_id,))

                    for row in cursor.fetchall():
                        lead_scores.append({
                            'product_id': row[0],
                            'score': row[1],
                            'criteria_breakdown': json.loads(row[2]) if row[2] else {},
                            'created_at': row[3]
                        })

                    # Get email drafts
                    cursor.execute("""
                        SELECT draft_id, subject, content, draft_type, priority_order, created_at
                        FROM email_drafts 
                        WHERE execution_id = ?
                    """, (task_id,))

                    for row in cursor.fetchall():
                        email_drafts.append({
                            'draft_id': row[0],
                            'subject': row[1],
                            # Truncate content
                            'content': row[2][:200] + '...' if len(row[2]) > 200 else row[2],
                            'draft_type': row[3],
                            'priority_order': row[4],
                            'created_at': row[5]
                        })

            except Exception as e:
                self.logger.warning(
                    f"Failed to get related data for task {task_id}: {str(e)}")

            return {
                'task_info': task,
                'stages': stages,
                'lead_scores': lead_scores,
                'email_drafts': email_drafts,
                'summary': {
                    'total_stages': len(stages),
                    'completed_stages': len([s for s in stages if s['execution_status'] == 'done']),
                    'failed_stages': len([s for s in stages if s['execution_status'] == 'failed']),
                    'total_lead_scores': len(lead_scores),
                    'total_email_drafts': len(email_drafts)
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to get sales process summary: {str(e)}")
            return None

    # ===== CUSTOMER DATA PERSISTENCE METHODS =====

    def update_customer_from_profile(self, customer_id: str, profile_data: Dict[str, Any]) -> None:
        """
        Update customer record with profile data from data preparation stage.

        Args:
            customer_id: Customer identifier
            profile_data: Structured profile data from data preparation
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Extract data from profile structure
                company_info = profile_data.get('companyInfo', {})
                contact_info = profile_data.get('primaryContact', {})

                cursor.execute("""
                    UPDATE customers 
                    SET company_name = ?, website = ?, industry = ?, 
                        contact_name = ?, contact_email = ?, contact_phone = ?,
                        address = ?, profile_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE customer_id = ?
                """, (
                    company_info.get('name', ''),
                    company_info.get('website', ''),
                    company_info.get('industry', ''),
                    contact_info.get('name', ''),
                    contact_info.get('email', ''),
                    contact_info.get('phone', ''),
                    company_info.get('address', ''),
                    json.dumps(profile_data),
                    customer_id
                ))

                conn.commit()
                self.logger.debug(f"Updated customer profile: {customer_id}")

        except Exception as e:
            self.logger.error(f"Failed to update customer profile: {str(e)}")
            raise

    def get_customer_task(self, task_id: str, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get customer task data by task_id and customer_id.

        Args:
            task_id: Task identifier
            customer_id: Customer identifier

        Returns:
            Customer task data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM gs_customer_llmtask 
                    WHERE task_id = ? AND customer_id = ?
                """, (task_id, customer_id))

                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

        except Exception as e:
            self.logger.error(f"Failed to get customer task: {str(e)}")
            return None

    # ===== SCHEMA MIGRATION METHODS =====

    def backup_existing_schema(self) -> str:
        """
        Create backup of existing execution data before migration.

        Returns:
            Backup file path
        """
        try:
            import shutil
            from datetime import datetime

            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, backup_path)

            self.logger.info(f"Database backup created: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            raise

    def migrate_executions_to_tasks(self) -> int:
        """
        Migrate existing executions table data to new llm_worker_task table format.

        Returns:
            Number of records migrated
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if old executions table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='executions'
                """)
                if not cursor.fetchone():
                    self.logger.info(
                        "No executions table found, skipping migration")
                    return 0

                # Get existing executions
                cursor.execute("""
                    SELECT execution_id, org_id, org_name, status, started_at, 
                           completed_at, config_json
                    FROM executions
                """)
                executions = cursor.fetchall()

                migrated_count = 0
                for execution in executions:
                    execution_id, org_id, org_name, status, started_at, completed_at, config_json = execution

                    # Parse config_json to extract request_body
                    request_body = {}
                    if config_json:
                        try:
                            config_data = json.loads(config_json)
                            request_body = {
                                'org_id': org_id,
                                'org_name': org_name,
                                'customer_info': config_data.get('customer_name', ''),
                                'language': config_data.get('language', 'english'),
                                'input_website': config_data.get('customer_website', ''),
                                'execution_id': execution_id
                            }
                        except json.JSONDecodeError:
                            request_body = {
                                'org_id': org_id, 'org_name': org_name}

                    # Map execution status to task status
                    task_status = 'completed' if status == 'completed' else 'failed' if status == 'failed' else 'running'

                    # Insert into llm_worker_task table
                    cursor.execute("""
                        INSERT OR REPLACE INTO llm_worker_task 
                        (task_id, plan_id, org_id, status, current_runtime_index, 
                         messages, request_body, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        execution_id,
                        '569cdcbd-cf6d-4e33-b0b2-d2f6f15a0832',  # Default plan ID
                        org_id,
                        task_status,
                        0,  # Default runtime index
                        json.dumps([]),  # Empty messages
                        json.dumps(request_body),
                        started_at,
                        completed_at or started_at
                    ))

                    migrated_count += 1

                conn.commit()
                self.logger.info(
                    f"Migrated {migrated_count} executions to llm_worker_task table")
                return migrated_count

        except Exception as e:
            self.logger.error(
                f"Failed to migrate executions to tasks: {str(e)}")
            raise

    def migrate_stage_results_to_operations(self) -> int:
        """
        Migrate existing stage_results table data to new llm_worker_operation table format.

        Returns:
            Number of records migrated
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if old stage_results table exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='stage_results'
                """)
                if not cursor.fetchone():
                    self.logger.info(
                        "No stage_results table found, skipping migration")
                    return 0

                # Get existing stage results
                cursor.execute("""
                    SELECT id, execution_id, stage_name, status, input_data, 
                           output_data, started_at, completed_at, error_message
                    FROM stage_results
                    ORDER BY execution_id, started_at
                """)
                stage_results = cursor.fetchall()

                migrated_count = 0
                current_execution = None
                chain_index = 0

                for stage_result in stage_results:
                    (stage_id, execution_id, stage_name, status, input_data,
                     output_data, started_at, completed_at, error_message) = stage_result

                    # Reset chain_index for new execution
                    if current_execution != execution_id:
                        current_execution = execution_id
                        chain_index = 0

                    # Parse JSON data
                    input_json = {}
                    output_json = {}

                    if input_data:
                        try:
                            input_json = json.loads(input_data) if isinstance(
                                input_data, str) else input_data
                        except (json.JSONDecodeError, TypeError):
                            input_json = {'raw_input': str(input_data)}

                    if output_data:
                        try:
                            output_json = json.loads(output_data) if isinstance(
                                output_data, str) else output_data
                        except (json.JSONDecodeError, TypeError):
                            output_json = {'raw_output': str(output_data)}

                    # Add error message to output if failed
                    if status == 'failed' and error_message:
                        output_json['error'] = error_message

                    # Map stage status to execution status
                    execution_status = 'done' if status == 'success' else 'failed' if status == 'failed' else 'running'

                    # Generate operation ID
                    operation_id = f"{execution_id}_{stage_name}_{chain_index}"

                    # Insert into llm_worker_operation table
                    cursor.execute("""
                        INSERT OR REPLACE INTO llm_worker_operation 
                        (operation_id, task_id, executor_name, runtime_index, 
                         chain_index, execution_status, input_data, output_data, 
                         date_created, date_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        operation_id,
                        execution_id,
                        stage_name,
                        0,  # Default runtime index
                        chain_index,
                        execution_status,
                        json.dumps(input_json),
                        json.dumps(output_json),
                        started_at,
                        completed_at or started_at
                    ))

                    chain_index += 1
                    migrated_count += 1

                conn.commit()
                self.logger.info(
                    f"Migrated {migrated_count} stage results to llm_worker_operation table")
                return migrated_count

        except Exception as e:
            self.logger.error(
                f"Failed to migrate stage results to operations: {str(e)}")
            raise

    def validate_migration(self) -> bool:
        """
        Validate that migration was successful by comparing data integrity.

        Returns:
            True if migration is valid, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                validation_errors = []

                # Check if new tables exist
                required_tables = ['tasks', 'operations']
                for table in required_tables:
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table,))
                    if not cursor.fetchone():
                        validation_errors.append(
                            f"Required table '{table}' not found")

                # Check if old tables still exist (for rollback capability)
                legacy_tables = ['executions', 'stage_results']
                for table in legacy_tables:
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table,))
                    if not cursor.fetchone():
                        validation_errors.append(
                            f"Legacy table '{table}' not found for rollback")

                # Validate data counts match
                cursor.execute("SELECT COUNT(*) FROM executions")
                old_execution_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM llm_worker_task")
                new_task_count = cursor.fetchone()[0]

                if old_execution_count != new_task_count:
                    validation_errors.append(
                        f"Execution count mismatch: {old_execution_count} executions vs {new_task_count} tasks"
                    )

                cursor.execute("SELECT COUNT(*) FROM stage_results")
                old_stage_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM llm_worker_operation")
                new_operation_count = cursor.fetchone()[0]

                if old_stage_count != new_operation_count:
                    validation_errors.append(
                        f"Stage count mismatch: {old_stage_count} stage_results vs {new_operation_count} operations"
                    )

                # Validate JSON data integrity
                cursor.execute(
                    "SELECT operation_id, input_data, output_data FROM llm_worker_operation LIMIT 10")
                for operation_id, input_data, output_data in cursor.fetchall():
                    try:
                        if input_data:
                            json.loads(input_data)
                        if output_data:
                            json.loads(output_data)
                    except json.JSONDecodeError as e:
                        validation_errors.append(
                            f"Invalid JSON in operation {operation_id}: {e}")

                # Validate foreign key relationships
                cursor.execute("""
                    SELECT COUNT(*) FROM llm_worker_operation o 
                    LEFT JOIN llm_worker_task t ON o.task_id = t.task_id 
                    WHERE t.task_id IS NULL
                """)
                orphaned_operations = cursor.fetchone()[0]
                if orphaned_operations > 0:
                    validation_errors.append(
                        f"Found {orphaned_operations} orphaned operations")

                if validation_errors:
                    self.logger.error(
                        f"Migration validation failed: {validation_errors}")
                    return False

                self.logger.info("Migration validation successful")
                return True

        except Exception as e:
            self.logger.error(f"Migration validation error: {str(e)}")
            return False

    def rollback_migration(self, backup_path: str = None) -> bool:
        """
        Rollback migration by restoring from backup.

        Args:
            backup_path: Path to backup file, if None will find latest backup

        Returns:
            True if rollback successful, False otherwise
        """
        try:
            import shutil
            import glob

            # Find backup file if not provided
            if not backup_path:
                backup_pattern = f"{self.db_path}.backup_*"
                backup_files = glob.glob(backup_pattern)
                if not backup_files:
                    self.logger.error("No backup files found for rollback")
                    return False
                backup_path = max(backup_files)  # Get most recent backup

            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False

            # Create a backup of current state before rollback
            current_backup = f"{self.db_path}.pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, current_backup)

            # Restore from backup
            shutil.copy2(backup_path, self.db_path)

            self.logger.info(
                f"Migration rolled back from backup: {backup_path}")
            self.logger.info(f"Current state backed up to: {current_backup}")
            return True

        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return False

    def execute_full_migration(self) -> bool:
        """
        Execute complete migration process with error handling and rollback.

        Returns:
            True if migration successful, False otherwise
        """
        backup_path = None
        try:
            self.logger.info("Starting schema migration process")

            # Step 1: Create backup
            backup_path = self.backup_existing_schema()

            # Step 2: Migrate executions to tasks
            task_count = self.migrate_executions_to_tasks()

            # Step 3: Migrate stage results to operations
            operation_count = self.migrate_stage_results_to_operations()

            # Step 4: Validate migration
            if not self.validate_migration():
                self.logger.error("Migration validation failed, rolling back")
                self.rollback_migration(backup_path)
                return False

            self.logger.info(
                f"Migration completed successfully: {task_count} tasks, {operation_count} operations")
            return True

        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            if backup_path:
                self.logger.info("Attempting rollback...")
                self.rollback_migration(backup_path)
            return False

 # ===== SERVER-COMPATIBLE TASK MANAGEMENT METHODS =====

    def create_task(
        self,
        task_id: str,
        plan_id: str,
        org_id: str,
        request_body: Dict[str, Any],
        status: str = "running"
    ) -> None:
        """
        Create task record with proper server schema (llm_worker_task).

        Args:
            task_id: Unique task identifier (sales process ID)
            plan_id: Plan identifier
            org_id: Organization identifier
            request_body: Initial request data for the sales process
            status: Task status (running, completed, failed)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO llm_worker_task 
                    (task_id, plan_id, org_id, status, current_runtime_index, 
                     messages, request_body, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    task_id,
                    plan_id,
                    org_id,
                    status,
                    0,  # Initial runtime index
                    json.dumps([]),  # Empty messages initially
                    json.dumps(request_body)
                ))
                conn.commit()
                self.logger.debug(f"Created task: {task_id}")

        except Exception as e:
            self.logger.error(f"Failed to create task: {str(e)}")
            raise

    def update_task_status(
        self,
        task_id: str,
        status: str,
        runtime_index: Optional[int] = None
    ) -> None:
        """
        Update task status and runtime_index with proper server schema.

        Args:
            task_id: Task identifier
            status: New task status (running, completed, failed)
            runtime_index: Optional runtime index to update
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if runtime_index is not None:
                    cursor.execute("""
                        UPDATE llm_worker_task 
                        SET status = ?, current_runtime_index = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    """, (status, runtime_index, task_id))
                else:
                    cursor.execute("""
                        UPDATE llm_worker_task 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    """, (status, task_id))

                conn.commit()
                self.logger.debug(
                    f"Updated task {task_id}: status={status}, runtime_index={runtime_index}")

        except Exception as e:
            self.logger.error(f"Failed to update task status: {str(e)}")
            raise

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task record with all related data.

        Args:
            task_id: Task identifier

        Returns:
            Task data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM llm_worker_task WHERE task_id = ?
                """, (task_id,))

                row = cursor.fetchone()
                if row:
                    task_data = dict(row)

                    # Parse JSON fields
                    if task_data['messages']:
                        try:
                            task_data['messages'] = json.loads(
                                task_data['messages'])
                        except json.JSONDecodeError:
                            task_data['messages'] = []

                    if task_data['request_body']:
                        try:
                            task_data['request_body'] = json.loads(
                                task_data['request_body'])
                        except json.JSONDecodeError:
                            task_data['request_body'] = {}

                    return task_data

                return None

        except Exception as e:
            self.logger.error(f"Failed to get task: {str(e)}")
            return None

    def add_task_message(self, task_id: str, message: str) -> None:
        """
        Add message to task messages array.

        Args:
            task_id: Task identifier
            message: Message to add
        """
        try:
            task = self.get_task(task_id)
            if not task:
                self.logger.warning(f"Task not found: {task_id}")
                return

            messages = task.get('messages', [])
            messages.append({
                'message': message,
                'timestamp': datetime.now().isoformat()
            })

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE llm_worker_task 
                    SET messages = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                """, (json.dumps(messages), task_id))
                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to add task message: {str(e)}")
            raise

    # ===== SERVER-COMPATIBLE OPERATION MANAGEMENT METHODS =====

    def create_operation(
        self,
        task_id: str,
        executor_name: str,
        runtime_index: int,
        chain_index: int,
        input_data: Dict[str, Any]
    ) -> str:
        """
        Create operation record with input_data (llm_worker_operation).

        Args:
            task_id: Parent task identifier
            executor_name: Stage name (data_acquisition, lead_scoring, etc.)
            runtime_index: Execution attempt number
            chain_index: Position in execution chain
            input_data: Stage-specific input data

        Returns:
            Generated operation_id
        """
        try:
            # Generate unique operation ID
            operation_id = f"{task_id}_{executor_name}_{runtime_index}_{chain_index}"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO llm_worker_operation 
                    (operation_id, task_id, executor_name, runtime_index, 
                     chain_index, execution_status, input_data, output_data,
                     date_created, date_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    operation_id,
                    task_id,
                    executor_name,
                    runtime_index,
                    chain_index,
                    'running',  # Initial status
                    json.dumps(input_data),
                    json.dumps({})  # Empty output initially
                ))
                conn.commit()
                self.logger.debug(f"Created operation: {operation_id}")
                return operation_id

        except Exception as e:
            self.logger.error(f"Failed to create operation: {str(e)}")
            raise

    def update_operation_status(
        self,
        operation_id: str,
        execution_status: str,
        output_data: Dict[str, Any]
    ) -> None:
        """
        Update operation execution_status and output_data.

        Args:
            operation_id: Operation identifier
            execution_status: New status (done, failed, running)
            output_data: Stage-specific output data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE llm_worker_operation 
                    SET execution_status = ?, output_data = ?, date_updated = CURRENT_TIMESTAMP
                    WHERE operation_id = ?
                """, (execution_status, json.dumps(output_data), operation_id))

                conn.commit()
                self.logger.debug(
                    f"Updated operation {operation_id}: status={execution_status}")

        except Exception as e:
            self.logger.error(f"Failed to update operation status: {str(e)}")
            raise

    def get_operations_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all operations for a specific task.

        Args:
            task_id: Task identifier

        Returns:
            List of operation records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM llm_worker_operation 
                    WHERE task_id = ?
                    ORDER BY runtime_index, chain_index
                """, (task_id,))

                operations = []
                for row in cursor.fetchall():
                    operation = dict(row)

                    # Parse JSON fields
                    if operation['input_data']:
                        try:
                            operation['input_data'] = json.loads(
                                operation['input_data'])
                        except json.JSONDecodeError:
                            operation['input_data'] = {}

                    if operation['output_data']:
                        try:
                            operation['output_data'] = json.loads(
                                operation['output_data'])
                        except json.JSONDecodeError:
                            operation['output_data'] = {}

                    operations.append(operation)

                return operations

        except Exception as e:
            self.logger.error(f"Failed to get operations by task: {str(e)}")
            return []

    def get_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get individual operation record.

        Args:
            operation_id: Operation identifier

        Returns:
            Operation data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM llm_worker_operation WHERE operation_id = ?
                """, (operation_id,))

                row = cursor.fetchone()
                if row:
                    operation = dict(row)

                    # Parse JSON fields
                    if operation['input_data']:
                        try:
                            operation['input_data'] = json.loads(
                                operation['input_data'])
                        except json.JSONDecodeError:
                            operation['input_data'] = {}

                    if operation['output_data']:
                        try:
                            operation['output_data'] = json.loads(
                                operation['output_data'])
                        except json.JSONDecodeError:
                            operation['output_data'] = {}

                    return operation

                return None

        except Exception as e:
            self.logger.error(f"Failed to get operation: {str(e)}")
            return None

    def get_operations_by_executor(
        self,
        executor_name: str,
        org_id: Optional[str] = None,
        execution_status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get operations by executor name (stage-specific queries).

        Args:
            executor_name: Stage name to filter by
            org_id: Optional organization filter
            execution_status: Optional status filter

        Returns:
            List of matching operations
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = """
                    SELECT o.* FROM llm_worker_operation o
                    JOIN llm_worker_task t ON o.task_id = t.task_id
                    WHERE o.executor_name = ?
                """
                params = [executor_name]

                if org_id:
                    query += " AND t.org_id = ?"
                    params.append(org_id)

                if execution_status:
                    query += " AND o.execution_status = ?"
                    params.append(execution_status)

                query += " ORDER BY o.date_created DESC"

                cursor.execute(query, params)

                operations = []
                for row in cursor.fetchall():
                    operation = dict(row)

                    # Parse JSON fields
                    if operation['input_data']:
                        try:
                            operation['input_data'] = json.loads(
                                operation['input_data'])
                        except json.JSONDecodeError:
                            operation['input_data'] = {}

                    if operation['output_data']:
                        try:
                            operation['output_data'] = json.loads(
                                operation['output_data'])
                        except json.JSONDecodeError:
                            operation['output_data'] = {}

                    operations.append(operation)

                return operations

        except Exception as e:
            self.logger.error(
                f"Failed to get operations by executor: {str(e)}")
            return []

    # ===== SERVER-COMPATIBLE QUERY METHODS =====

    def get_task_with_operations(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete task details with all related operations.

        Args:
            task_id: Task identifier

        Returns:
            Complete task data with operations or None if not found
        """
        try:
            task = self.get_task(task_id)
            if not task:
                return None

            operations = self.get_operations_by_task(task_id)

            # Add operations to task data
            task['operations'] = operations

            # Add summary statistics
            task['summary'] = {
                'total_operations': len(operations),
                'completed_operations': len([op for op in operations if op['execution_status'] == 'done']),
                'failed_operations': len([op for op in operations if op['execution_status'] == 'failed']),
                'running_operations': len([op for op in operations if op['execution_status'] == 'running'])
            }

            return task

        except Exception as e:
            self.logger.error(f"Failed to get task with operations: {str(e)}")
            return None

    def get_execution_timeline(self, task_id: str, runtime_index: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get chronological operation tracking for specific execution attempt.

        Args:
            task_id: Task identifier
            runtime_index: Optional specific runtime index

        Returns:
            List of operations in chronological order
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = """
                    SELECT * FROM llm_worker_operation 
                    WHERE task_id = ?
                """
                params = [task_id]

                if runtime_index is not None:
                    query += " AND runtime_index = ?"
                    params.append(runtime_index)

                query += " ORDER BY runtime_index, chain_index, date_created"

                cursor.execute(query, params)

                timeline = []
                for row in cursor.fetchall():
                    operation = dict(row)

                    # Parse JSON fields
                    if operation['input_data']:
                        try:
                            operation['input_data'] = json.loads(
                                operation['input_data'])
                        except json.JSONDecodeError:
                            operation['input_data'] = {}

                    if operation['output_data']:
                        try:
                            operation['output_data'] = json.loads(
                                operation['output_data'])
                        except json.JSONDecodeError:
                            operation['output_data'] = {}

                    timeline.append(operation)

                return timeline

        except Exception as e:
            self.logger.error(f"Failed to get execution timeline: {str(e)}")
            return []

    def get_stage_performance_metrics(
        self,
        executor_name: str,
        org_id: Optional[str] = None,
        date_range: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """
        Get performance analysis for specific stage.

        Args:
            executor_name: Stage name
            org_id: Optional organization filter
            date_range: Optional (start_date, end_date) tuple

        Returns:
            Performance metrics dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT 
                        o.execution_status,
                        COUNT(*) as count,
                        AVG(julianday(o.date_updated) - julianday(o.date_created)) * 24 * 60 as avg_duration_minutes
                    FROM llm_worker_operation o
                    JOIN llm_worker_task t ON o.task_id = t.task_id
                    WHERE o.executor_name = ?
                """
                params = [executor_name]

                if org_id:
                    query += " AND t.org_id = ?"
                    params.append(org_id)

                if date_range:
                    query += " AND o.date_created BETWEEN ? AND ?"
                    params.extend(date_range)

                query += " GROUP BY o.execution_status"

                cursor.execute(query, params)

                metrics = {
                    'executor_name': executor_name,
                    'org_id': org_id,
                    'total_executions': 0,
                    'success_rate': 0.0,
                    'failure_rate': 0.0,
                    'avg_duration_minutes': 0.0,
                    'status_breakdown': {}
                }

                total_count = 0
                success_count = 0
                total_duration = 0.0

                for row in cursor.fetchall():
                    status, count, avg_duration = row
                    total_count += count
                    metrics['status_breakdown'][status] = {
                        'count': count,
                        'avg_duration_minutes': avg_duration or 0.0
                    }

                    if status == 'done':
                        success_count = count

                    if avg_duration:
                        total_duration += avg_duration * count

                if total_count > 0:
                    metrics['total_executions'] = total_count
                    metrics['success_rate'] = (
                        success_count / total_count) * 100
                    metrics['failure_rate'] = (
                        (total_count - success_count) / total_count) * 100
                    metrics['avg_duration_minutes'] = total_duration / \
                        total_count

                return metrics

        except Exception as e:
            self.logger.error(
                f"Failed to get stage performance metrics: {str(e)}")
            return {'error': str(e)}

    def find_failed_operations(
        self,
        org_id: Optional[str] = None,
        executor_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find failed operations for debugging.

        Args:
            org_id: Optional organization filter
            executor_name: Optional stage filter
            limit: Maximum number of results

        Returns:
            List of failed operations with error details
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = """
                    SELECT o.*, t.org_id FROM llm_worker_operation o
                    JOIN llm_worker_task t ON o.task_id = t.task_id
                    WHERE o.execution_status = 'failed'
                """
                params = []

                if org_id:
                    query += " AND t.org_id = ?"
                    params.append(org_id)

                if executor_name:
                    query += " AND o.executor_name = ?"
                    params.append(executor_name)

                query += " ORDER BY o.date_created DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)

                failed_operations = []
                for row in cursor.fetchall():
                    operation = dict(row)

                    # Parse output_data to extract error information
                    if operation['output_data']:
                        try:
                            output_data = json.loads(operation['output_data'])
                            operation['output_data'] = output_data
                            operation['error_summary'] = output_data.get(
                                'error', 'Unknown error')
                        except json.JSONDecodeError:
                            operation['error_summary'] = 'JSON parse error in output_data'
                    else:
                        operation['error_summary'] = 'No error details available'

                    failed_operations.append(operation)

                return failed_operations

        except Exception as e:
            self.logger.error(f"Failed to find failed operations: {str(e)}")
            return []

    def create_task(
        self,
        task_id: str,
        plan_id: str,
        org_id: str,
        request_body: Dict[str, Any],
        status: str = "running"
    ) -> str:
        """
        Create a new task record in llm_worker_task table.

        Args:
            task_id: Unique task identifier
            plan_id: Plan identifier
            org_id: Organization identifier
            request_body: Task request body data
            status: Initial task status

        Returns:
            Task ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO llm_worker_task 
                    (task_id, plan_id, org_id, status, current_runtime_index, messages, request_body)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    plan_id,
                    org_id,
                    status,
                    0,  # initial runtime_index
                    json.dumps([]),  # empty messages initially
                    json.dumps(request_body)
                ))

                conn.commit()
                self.logger.debug(f"Created task: {task_id}")
                return task_id

        except Exception as e:
            self.logger.error(f"Failed to create task: {str(e)}")
            raise

    def create_operation(
        self,
        task_id: str,
        executor_name: str,
        runtime_index: int,
        chain_index: int,
        input_data: Dict[str, Any]
    ) -> str:
        """
        Create a new operation record in llm_worker_operation table.

        Args:
            task_id: Task identifier
            executor_name: Name of the executor/stage
            runtime_index: Runtime execution index
            chain_index: Chain execution index
            input_data: Operation input data

        Returns:
            Operation ID
        """
        try:
            operation_id = f"{task_id}_{executor_name}_{runtime_index}_{chain_index}"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO llm_worker_operation 
                    (operation_id, task_id, executor_name, runtime_index, chain_index, 
                     execution_status, input_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    operation_id,
                    task_id,
                    executor_name,
                    runtime_index,
                    chain_index,
                    'running',
                    json.dumps(input_data)
                ))

                conn.commit()
                self.logger.debug(f"Created operation: {operation_id}")
                return operation_id

        except Exception as e:
            self.logger.error(f"Failed to create operation: {str(e)}")
            raise

    def update_operation_status(
        self,
        operation_id: str,
        execution_status: str,
        output_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update operation status and output data.

        Args:
            operation_id: Operation identifier
            execution_status: New execution status
            output_data: Optional output data
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if output_data:
                    cursor.execute("""
                        UPDATE llm_worker_operation 
                        SET execution_status = ?, output_data = ?, date_updated = CURRENT_TIMESTAMP
                        WHERE operation_id = ?
                    """, (execution_status, json.dumps(output_data), operation_id))
                else:
                    cursor.execute("""
                        UPDATE llm_worker_operation 
                        SET execution_status = ?, date_updated = CURRENT_TIMESTAMP
                        WHERE operation_id = ?
                    """, (execution_status, operation_id))

                conn.commit()
                self.logger.debug(
                    f"Updated operation status: {operation_id} -> {execution_status}")

        except Exception as e:
            self.logger.error(f"Failed to update operation status: {str(e)}")
            raise

    def update_task_status(
        self,
        task_id: str,
        status: str,
        runtime_index: Optional[int] = None
    ) -> None:
        """
        Update task status and runtime index.

        Args:
            task_id: Task identifier
            status: New task status
            runtime_index: Optional runtime index
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if runtime_index is not None:
                    cursor.execute("""
                        UPDATE llm_worker_task 
                        SET status = ?, current_runtime_index = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    """, (status, runtime_index, task_id))
                else:
                    cursor.execute("""
                        UPDATE llm_worker_task 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    """, (status, task_id))

                conn.commit()
                self.logger.debug(
                    f"Updated task status: {task_id} -> {status}")

        except Exception as e:
            self.logger.error(f"Failed to update task status: {str(e)}")
            raise
