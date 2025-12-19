"""
Birthday Email Management System for FuseSell Local
Handles birthday email template generation, validation, and processing
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
from .data_manager import LocalDataManager
from .llm_client import LLMClient


class BirthdayEmailManager:
    """
    Manages birthday email functionality including template generation,
    validation, and processing based on server-side logic from gs_scheduler.py
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize birthday email manager.

        Args:
            config: Configuration dictionary with API keys and settings
        """
        self.config = config
        self.data_manager = LocalDataManager(config.get('data_dir', './fusesell_data'))
        self.llm_client = LLMClient(
            api_key=config.get('openai_api_key'),
            model=config.get('llm_model', 'gpt-4.1-mini'),
            base_url=config.get('llm_base_url')
        )
        self.logger = logging.getLogger("fusesell.birthday_email")
        
        # Initialize database tables
        self._initialize_tables()

    def validate_birthday_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Validate birthday email prompt using LLM analysis.
        Based on gs_scheduler.py birthday email check logic.

        Args:
            prompt: User input prompt to validate

        Returns:
            Dictionary with validation results
        """
        try:
            validation_prompt = (
                "Analyze the following text and return a JSON object with exactly 2 fields: "
                "'is_complete_prompt' (boolean - true if it's a complete prompt for writing "
                "birthday email content/drafts with detailed instructions on what to write, "
                "tone, style, etc. NOT configuration/settings instructions) and 'is_enabled' "
                "(boolean - true if birthday email functionality is enabled, default to true). "
                "Configuration instructions like 'update settings', 'enable birthday email', "
                "'set timezone', etc. should return false for is_complete_prompt. "
                "Your output should be a valid JSON object only. Here's the text to analyze:\n\n"
                + prompt
            )

            messages = [{"role": "user", "content": validation_prompt}]
            response = self.llm_client.chat_completion(messages, temperature=0.3)
            
            try:
                validation_result = json.loads(response)
                return {
                    'is_complete_prompt': validation_result.get('is_complete_prompt', False),
                    'is_enabled': validation_result.get('is_enabled', True),
                    'validation_successful': True
                }
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse LLM validation response")
                return {
                    'is_complete_prompt': False,
                    'is_enabled': False,
                    'validation_successful': False
                }

        except Exception as e:
            self.logger.error(f"Birthday prompt validation failed: {str(e)}")
            return {
                'is_complete_prompt': False,
                'is_enabled': False,
                'validation_successful': False,
                'error': str(e)
            }

    def generate_birthday_settings_rule(self, prompt: str) -> Dict[str, Any]:
        """
        Generate birthday email settings rule from user prompt.
        Based on gs_scheduler.py birthday email rule generation logic.

        Args:
            prompt: User input prompt

        Returns:
            Dictionary with generated rule settings
        """
        try:
            rule_prompt = (
                "You are an AI assistant tasked with converting user input into a structured "
                "JSON format for birthday email composition. Analyze the following input and "
                "extract key parameters for crafting an email. Your output should be a valid "
                "JSON object with fields such as 'fewshots_strict_follow' (boolean, required, "
                "indicating if the drafts must follow the examples or not, false if is not mentioned), "
                "'maximum_words' (integer), 'mail_tone' (string), and 'org_timezone' (string, "
                "UTC timezone format like 'UTC+07' or 'UTC-04', extract from the input if mentioned).\n\n"
                "For example, if the input is \"Độ dài giới hạn 400 từ, xưng hô là 'mình' hoặc "
                "tên người gửi, múi giờ UTC+7.\", your output might be:\n"
                "{\n"
                "    \"maximum_words\": 400,\n"
                "    \"mail_tone\": \"Friendly\",\n"
                "    \"pronoun\": \"mình\",\n"
                "    \"fewshots_strict_follow\": true,\n"
                "    \"org_timezone\": \"UTC+07\"\n"
                "}\n\n"
                "Ensure your output is a single, valid JSON object. Include only the fields "
                "that are explicitly mentioned or strongly implied in the input. For org_timezone, "
                "look for timezone information in formats like 'UTC+7', 'GMT+7', '+7', 'timezone +7', "
                "etc. and convert to UTC format (UTC+07 or UTC-04). NO REDUNDANT WORDS. "
                "NO NEED TO BE WRAPPED IN ``` CODE BLOCK CHARACTERS. Here's the input to analyze:\n"
                + prompt
            )

            messages = [{"role": "user", "content": rule_prompt}]
            response = self.llm_client.chat_completion(messages, temperature=0.3)
            
            try:
                rule = json.loads(response)
                
                # Add default values and validation
                rule.setdefault('fewshots_strict_follow', False)
                rule.setdefault('maximum_words', 200)
                rule.setdefault('mail_tone', 'Friendly')
                rule.setdefault('org_timezone', 'UTC+07')
                
                # Add extra guide
                rule['extra_guide'] = prompt
                
                # Add birthday email check
                validation_result = self.validate_birthday_prompt(prompt)
                rule['birthday_email_check'] = {
                    'is_complete_prompt': validation_result['is_complete_prompt'],
                    'is_enabled': validation_result['is_enabled']
                }
                
                return rule

            except json.JSONDecodeError:
                self.logger.warning("Failed to parse LLM rule generation response")
                return self._get_default_birthday_rule(prompt)

        except Exception as e:
            self.logger.error(f"Birthday rule generation failed: {str(e)}")
            return self._get_default_birthday_rule(prompt)

    def _get_default_birthday_rule(self, prompt: str) -> Dict[str, Any]:
        """Get default birthday email rule when LLM processing fails."""
        return {
            'fewshots_strict_follow': False,
            'maximum_words': 200,
            'mail_tone': 'Friendly',
            'org_timezone': 'UTC+07',
            'extra_guide': prompt,
            'birthday_email_check': {
                'is_complete_prompt': False,
                'is_enabled': True
            }
        }

    def generate_birthday_template(self, team_id: str, org_id: str, 
                                 prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate birthday email template.
        Simulates the flowai/auto_interaction_generate_email_template workflow.

        Args:
            team_id: Team identifier
            org_id: Organization identifier
            prompt: User prompt for template generation
            **kwargs: Additional parameters

        Returns:
            Dictionary with template generation results
        """
        try:
            template_id = f"uuid:{str(uuid.uuid4())}"
            template_type = "birthday_email"
            
            # Generate template content using LLM
            template_prompt = (
                f"Generate a birthday email template based on the following requirements:\n"
                f"Team ID: {team_id}\n"
                f"Organization: {org_id}\n"
                f"Requirements: {prompt}\n\n"
                f"Create a professional birthday email template that can be personalized "
                f"for customers. Include placeholders for customer name, company name, "
                f"and other relevant details. The template should be warm, professional, "
                f"and appropriate for business relationships.\n\n"
                f"Return the template as a JSON object with fields: 'subject', 'content', "
                f"'placeholders' (list of available placeholders), and 'tone'."
            )

            messages = [{"role": "user", "content": template_prompt}]
            response = self.llm_client.chat_completion(messages, temperature=0.7)
            
            try:
                template_data = json.loads(response)
            except json.JSONDecodeError:
                # Fallback template
                template_data = {
                    'subject': 'Happy Birthday from {{company_name}}!',
                    'content': (
                        'Dear {{customer_name}},\n\n'
                        'On behalf of everyone at {{company_name}}, I wanted to take a moment '
                        'to wish you a very happy birthday!\n\n'
                        'We truly appreciate your partnership and look forward to continuing '
                        'our successful relationship in the year ahead.\n\n'
                        'Wishing you all the best on your special day!\n\n'
                        'Best regards,\n'
                        '{{sender_name}}\n'
                        '{{company_name}}'
                    ),
                    'placeholders': ['customer_name', 'company_name', 'sender_name'],
                    'tone': 'professional_warm'
                }

            # Save template to database
            template_record = {
                'template_id': template_id,
                'team_id': team_id,
                'org_id': org_id,
                'template_type': template_type,
                'subject': template_data.get('subject', ''),
                'content': template_data.get('content', ''),
                'placeholders': json.dumps(template_data.get('placeholders', [])),
                'tone': template_data.get('tone', 'professional'),
                'created_at': datetime.now().isoformat(),
                'created_by': kwargs.get('username', 'system'),
                'prompt': prompt
            }

            success = self._save_birthday_template(template_record)
            
            return {
                'template_id': template_id,
                'template_data': template_data,
                'saved': success,
                'message': 'Birthday email template generated successfully' if success else 'Template generated but save failed'
            }

        except Exception as e:
            self.logger.error(f"Birthday template generation failed: {str(e)}")
            return {
                'template_id': None,
                'template_data': None,
                'saved': False,
                'error': str(e)
            }

    def _save_birthday_template(self, template_record: Dict[str, Any]) -> bool:
        """Save birthday email template to database."""
        try:
            import sqlite3
            # Create birthday_templates table if it doesn't exist
            with sqlite3.connect(self.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS birthday_templates (
                        template_id TEXT PRIMARY KEY,
                        team_id TEXT NOT NULL,
                        org_id TEXT NOT NULL,
                        template_type TEXT DEFAULT 'birthday_email',
                        subject TEXT,
                        content TEXT,
                        placeholders TEXT,
                        tone TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT,
                        prompt TEXT,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)

                # Insert or update template
                cursor.execute("""
                    INSERT OR REPLACE INTO birthday_templates 
                    (template_id, team_id, org_id, template_type, subject, content, 
                     placeholders, tone, created_at, created_by, prompt, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template_record['template_id'],
                    template_record['team_id'],
                    template_record['org_id'],
                    template_record['template_type'],
                    template_record['subject'],
                    template_record['content'],
                    template_record['placeholders'],
                    template_record['tone'],
                    template_record['created_at'],
                    template_record['created_by'],
                    template_record['prompt'],
                    True
                ))

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"Failed to save birthday template: {str(e)}")
            return False

    def get_birthday_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get birthday email template by ID."""
        try:
            import sqlite3
            with sqlite3.connect(self.data_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM birthday_templates 
                    WHERE template_id = ? AND is_active = TRUE
                """, (template_id,))
                
                row = cursor.fetchone()
                if row:
                    # Parse placeholders JSON
                    if row['placeholders']:
                        try:
                            row['placeholders'] = json.loads(row['placeholders'])
                        except json.JSONDecodeError:
                            row['placeholders'] = []
                    return dict(row)
                return None

        except Exception as e:
            self.logger.error(f"Failed to get birthday template: {str(e)}")
            return None

    def list_birthday_templates(self, team_id: str = None, org_id: str = None) -> List[Dict[str, Any]]:
        """List birthday email templates."""
        try:
            import sqlite3
            with sqlite3.connect(self.data_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM birthday_templates WHERE is_active = TRUE"
                params = []
                
                if team_id:
                    query += " AND team_id = ?"
                    params.append(team_id)
                
                if org_id:
                    query += " AND org_id = ?"
                    params.append(org_id)
                
                query += " ORDER BY created_at DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                templates = []
                for row in rows:
                    row_dict = dict(row)
                    # Parse placeholders JSON
                    if row_dict['placeholders']:
                        try:
                            row_dict['placeholders'] = json.loads(row_dict['placeholders'])
                        except json.JSONDecodeError:
                            row_dict['placeholders'] = []
                    templates.append(row_dict)
                
                return templates

        except Exception as e:
            self.logger.error(f"Failed to list birthday templates: {str(e)}")
            return []

    def process_birthday_email_settings(self, team_id: str, prompt: str, 
                                      org_id: str, **kwargs) -> Dict[str, Any]:
        """
        Process birthday email settings configuration.
        Main entry point that combines validation, rule generation, and template creation.

        Args:
            team_id: Team identifier
            prompt: User input prompt
            org_id: Organization identifier
            **kwargs: Additional parameters

        Returns:
            Dictionary with processing results
        """
        try:
            # Step 1: Validate the prompt
            validation_result = self.validate_birthday_prompt(prompt)
            
            # Step 2: Generate settings rule
            rule = self.generate_birthday_settings_rule(prompt)
            
            # Step 3: Generate template if it's a complete prompt
            template_result = None
            if validation_result.get('is_complete_prompt', False):
                template_result = self.generate_birthday_template(
                    team_id, org_id, prompt, **kwargs
                )
            
            # Step 4: Prepare final settings
            birthday_settings = {
                'mail_tone': rule.get('mail_tone', 'Friendly'),
                'extra_guide': rule.get('extra_guide', prompt),
                'org_timezone': rule.get('org_timezone', 'UTC+07'),
                'maximum_words': rule.get('maximum_words', 200),
                'birthday_email_check': rule.get('birthday_email_check', {
                    'is_enabled': True,
                    'is_complete_prompt': False
                }),
                'fewshots_strict_follow': rule.get('fewshots_strict_follow', False)
            }
            
            return {
                'success': True,
                'settings': birthday_settings,
                'validation': validation_result,
                'rule': rule,
                'template': template_result,
                'message': 'Birthday email settings processed successfully'
            }

        except Exception as e:
            self.logger.error(f"Birthday email settings processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process birthday email settings'
            }

    def _initialize_tables(self) -> None:
        """Initialize birthday email database tables."""
        try:
            import sqlite3
            with sqlite3.connect(self.data_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS birthday_templates (
                        template_id TEXT PRIMARY KEY,
                        team_id TEXT NOT NULL,
                        org_id TEXT NOT NULL,
                        template_type TEXT DEFAULT 'birthday_email',
                        subject TEXT,
                        content TEXT,
                        placeholders TEXT,
                        tone TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT,
                        prompt TEXT,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to initialize birthday email tables: {str(e)}")
