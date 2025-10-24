"""
Initial Outreach Stage - Generate personalized email drafts with action-based routing
Converted from gs_148_initial_outreach executor schema
"""

import json
import uuid
import requests
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base_stage import BaseStage


class InitialOutreachStage(BaseStage):
    """
    Initial Outreach stage with full server executor schema compliance.
    Supports: draft_write, draft_rewrite, send, close actions.
    """
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute initial outreach stage with action-based routing (matching server executor).
        
        Actions supported:
        - draft_write: Generate new email drafts
        - draft_rewrite: Modify existing draft using selected_draft_id
        - send: Send approved draft to recipient_address
        - close: Close outreach when customer feels negative
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result
        """
        try:
            # Get action from input data (matching server schema)
            input_data = context.get('input_data', {})
            action = input_data.get('action', 'draft_write')  # Default to draft_write
            
            self.logger.info(f"Executing initial outreach with action: {action}")
            
            # Validate required fields based on action
            self._validate_action_input(action, input_data)
            
            # Route based on action type (matching server executor schema)
            if action == 'draft_write':
                return self._handle_draft_write(context)
            elif action == 'draft_rewrite':
                return self._handle_draft_rewrite(context)
            elif action == 'send':
                return self._handle_send(context)
            elif action == 'close':
                return self._handle_close(context)
            else:
                raise ValueError(f"Invalid action: {action}. Must be one of: draft_write, draft_rewrite, send, close")
            
        except Exception as e:
            self.log_stage_error(context, e)
            return self.handle_stage_error(e, context)

    def _validate_action_input(self, action: str, input_data: Dict[str, Any]) -> None:
        """
        Validate required fields based on action type.
        
        Args:
            action: Action type
            input_data: Input data
            
        Raises:
            ValueError: If required fields are missing
        """
        if action in ['draft_rewrite', 'send']:
            if not input_data.get('selected_draft_id'):
                raise ValueError(f"selected_draft_id is required for {action} action")
        
        if action == 'send':
            if not input_data.get('recipient_address'):
                raise ValueError("recipient_address is required for send action")

    def _handle_draft_write(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle draft_write action - Generate new email drafts.
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result with new drafts
        """
        # Get data from previous stages
        customer_data = self._get_customer_data(context)
        scoring_data = self._get_scoring_data(context)
        
        # Get the best product recommendation
        recommended_product = self._get_recommended_product(scoring_data)
        
        if not recommended_product:
            raise ValueError("No product recommendation available for email generation")
        
        # Generate multiple email drafts
        email_drafts = self._generate_email_drafts(customer_data, recommended_product, scoring_data, context)
        
        # Save drafts to local files and database
        saved_drafts = self._save_email_drafts(context, email_drafts)
        
        # Prepare final output
        outreach_data = {
            'action': 'draft_write',
            'status': 'drafts_generated',
            'email_drafts': saved_drafts,
            'recommended_product': recommended_product,
            'customer_summary': self._create_customer_summary(customer_data),
            'total_drafts_generated': len(saved_drafts),
            'generation_timestamp': datetime.now().isoformat(),
            'customer_id': context.get('execution_id')
        }
        
        # Save to database
        self.save_stage_result(context, outreach_data)
        
        result = self.create_success_result(outreach_data, context)
        return result

    def _handle_draft_rewrite(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle draft_rewrite action - Modify existing draft using selected_draft_id.
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result with rewritten draft
        """
        input_data = context.get('input_data', {})
        selected_draft_id = input_data.get('selected_draft_id')
        reason = input_data.get('reason', 'No reason provided')
        
        # Retrieve existing draft
        existing_draft = self._get_draft_by_id(selected_draft_id)
        if not existing_draft:
            raise ValueError(f"Draft not found: {selected_draft_id}")
        
        # Get customer data for context
        customer_data = self._get_customer_data(context)
        scoring_data = self._get_scoring_data(context)
        
        # Rewrite the draft based on reason
        rewritten_draft = self._rewrite_draft(existing_draft, reason, customer_data, scoring_data, context)
        
        # Save the rewritten draft
        saved_draft = self._save_rewritten_draft(context, rewritten_draft, selected_draft_id)
        
        # Prepare output
        outreach_data = {
            'action': 'draft_rewrite',
            'status': 'draft_rewritten',
            'original_draft_id': selected_draft_id,
            'rewritten_draft': saved_draft,
            'rewrite_reason': reason,
            'generation_timestamp': datetime.now().isoformat(),
            'customer_id': context.get('execution_id')
        }
        
        # Save to database
        self.save_stage_result(context, outreach_data)
        
        result = self.create_success_result(outreach_data, context)
        # Logging handled by execute_with_timing wrapper
        
        return result

    def _handle_send(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle send action - Send approved draft to recipient (with optional scheduling).
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result with send status
        """
        input_data = context.get('input_data', {})
        selected_draft_id = input_data.get('selected_draft_id')
        recipient_address = input_data.get('recipient_address')
        recipient_name = input_data.get('recipient_name', 'Dear Customer')
        send_immediately = input_data.get('send_immediately', False)  # New parameter for immediate sending
        
        # Retrieve the draft to send
        draft_to_send = self._get_draft_by_id(selected_draft_id)
        if not draft_to_send:
            raise ValueError(f"Draft not found: {selected_draft_id}")
        
        # Check if we should send immediately or schedule
        if send_immediately:
            # Send immediately
            send_result = self._send_email(draft_to_send, recipient_address, recipient_name, context)
            
            outreach_data = {
                'action': 'send',
                'status': 'email_sent' if send_result['success'] else 'send_failed',
                'draft_id': selected_draft_id,
                'recipient_address': recipient_address,
                'recipient_name': recipient_name,
                'send_result': send_result,
                'sent_timestamp': datetime.now().isoformat(),
                'customer_id': context.get('execution_id'),
                'scheduling': 'immediate'
            }
        else:
            # Schedule for optimal time
            schedule_result = self._schedule_email(draft_to_send, recipient_address, recipient_name, context)
            
            outreach_data = {
                'action': 'send',
                'status': 'email_scheduled' if schedule_result['success'] else 'schedule_failed',
                'draft_id': selected_draft_id,
                'recipient_address': recipient_address,
                'recipient_name': recipient_name,
                'schedule_result': schedule_result,
                'scheduled_timestamp': datetime.now().isoformat(),
                'customer_id': context.get('execution_id'),
                'scheduling': 'delayed'
            }
        
        # Save to database
        self.save_stage_result(context, outreach_data)
        
        result = self.create_success_result(outreach_data, context)
        # Logging handled by execute_with_timing wrapper
        
        return result

    def _schedule_email(self, draft: Dict[str, Any], recipient_address: str, recipient_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schedule email event in database for external app to handle.
        
        Args:
            draft: Email draft to send
            recipient_address: Email address of recipient
            recipient_name: Name of recipient
            context: Execution context
            
        Returns:
            Scheduling result
        """
        try:
            from ..utils.event_scheduler import EventScheduler
            
            input_data = context.get('input_data', {})
            
            # Initialize event scheduler
            scheduler = EventScheduler(self.config.get('data_dir', './fusesell_data'))
            
            # Check if immediate sending is requested
            send_immediately = input_data.get('send_immediately', False)
            reminder_context = self._build_initial_reminder_context(
                draft,
                recipient_address,
                recipient_name,
                context
            )
            
            # Schedule the email event
            schedule_result = scheduler.schedule_email_event(
                draft_id=draft.get('draft_id'),
                recipient_address=recipient_address,
                recipient_name=recipient_name,
                org_id=input_data.get('org_id', 'default'),
                team_id=input_data.get('team_id'),
                customer_timezone=input_data.get('customer_timezone'),
                email_type='initial',
                send_immediately=send_immediately,
                reminder_context=reminder_context
            )
            
            if schedule_result['success']:
                self.logger.info(f"Email event scheduled successfully: {schedule_result['event_id']} for {schedule_result['scheduled_time']}")
                return {
                    'success': True,
                    'message': f'Email event scheduled for {schedule_result["scheduled_time"]}',
                    'event_id': schedule_result['event_id'],
                    'scheduled_time': schedule_result['scheduled_time'],
                    'follow_up_event_id': schedule_result.get('follow_up_event_id'),
                    'service': 'Database Event Scheduler'
                }
            else:
                self.logger.error(f"Email event scheduling failed: {schedule_result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'message': f'Email event scheduling failed: {schedule_result.get("error", "Unknown error")}',
                    'error': schedule_result.get('error')
                }
                
        except Exception as e:
            self.logger.error(f"Email scheduling failed: {str(e)}")
            return {
                'success': False,
                'message': f'Email scheduling failed: {str(e)}',
                'error': str(e)
            }

    def _build_initial_reminder_context(
        self,
        draft: Dict[str, Any],
        recipient_address: str,
        recipient_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build reminder_task metadata for scheduled initial outreach emails.
        """
        input_data = context.get('input_data', {})
        org_id = input_data.get('org_id', 'default') or 'default'
        customer_id = input_data.get('customer_id') or context.get('execution_id') or 'unknown'
        task_id = context.get('execution_id') or input_data.get('task_id') or 'unknown_task'
        team_id = input_data.get('team_id')
        team_name = input_data.get('team_name')
        language = input_data.get('language')
        customer_name = input_data.get('customer_name')
        staff_name = input_data.get('staff_name')
        reminder_room = self.config.get('reminder_room_id') or input_data.get('reminder_room_id')
        draft_id = draft.get('draft_id') or 'unknown_draft'

        customextra = {
            'reminder_content': 'draft_send',
            'org_id': org_id,
            'customer_id': customer_id,
            'task_id': task_id,
            'customer_name': customer_name,
            'language': language,
            'recipient_address': recipient_address,
            'recipient_name': recipient_name,
            'staff_name': staff_name,
            'team_id': team_id,
            'team_name': team_name,
            'interaction_type': input_data.get('interaction_type'),
            'draft_id': draft_id,
            'import_uuid': f"{org_id}_{customer_id}_{task_id}_{draft_id}"
        }

        if draft.get('product_name'):
            customextra['product_name'] = draft.get('product_name')
        if draft.get('approach'):
            customextra['approach'] = draft.get('approach')
        if draft.get('mail_tone'):
            customextra['mail_tone'] = draft.get('mail_tone')

        return {
            'status': 'published',
            'task': f"FuseSell initial outreach {org_id}_{customer_id} - {task_id}",
            'tags': ['fusesell', 'init-outreach'],
            'room_id': reminder_room,
            'org_id': org_id,
            'customer_id': customer_id,
            'task_id': task_id,
            'team_id': team_id,
            'team_name': team_name,
            'language': language,
            'customer_name': customer_name,
            'staff_name': staff_name,
            'customextra': customextra
        }

    def _handle_close(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle close action - Close outreach when customer feels negative.
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result with close status
        """
        input_data = context.get('input_data', {})
        reason = input_data.get('reason', 'Customer not interested')
        
        # Prepare output
        outreach_data = {
            'action': 'close',
            'status': 'outreach_closed',
            'close_reason': reason,
            'closed_timestamp': datetime.now().isoformat(),
            'customer_id': context.get('execution_id')
        }
        
        # Save to database
        self.save_stage_result(context, outreach_data)
        
        result = self.create_success_result(outreach_data, context)
        # Logging handled by execute_with_timing wrapper
        
        return result
    
    def _get_customer_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get customer data from previous stages or input."""
        # Try to get from stage results first
        stage_results = context.get('stage_results', {})
        if 'data_preparation' in stage_results:
            return stage_results['data_preparation'].get('data', {})
        
        # Fallback: get from input_data (for server compatibility)
        input_data = context.get('input_data', {})
        return {
            'companyInfo': input_data.get('companyInfo', {}),
            'primaryContact': input_data.get('primaryContact', {}),
            'painPoints': input_data.get('pain_points', [])
        }

    def _get_scoring_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get scoring data from previous stages or input."""
        # Try to get from stage results first
        stage_results = context.get('stage_results', {})
        if 'lead_scoring' in stage_results:
            return stage_results['lead_scoring'].get('data', {})
        
        # Fallback: get from input_data (for server compatibility)
        input_data = context.get('input_data', {})
        return {
            'lead_scoring': input_data.get('lead_scoring', [])
        }

    def _get_recommended_product(self, scoring_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get recommended product from scoring data."""
        try:
            # Try to get from analysis first
            analysis = scoring_data.get('analysis', {})
            if 'recommended_product' in analysis:
                return analysis['recommended_product']
            
            # Fallback: get highest scoring product
            lead_scores = scoring_data.get('lead_scoring', [])
            if lead_scores:
                sorted_scores = sorted(lead_scores, key=lambda x: x.get('total_weighted_score', 0), reverse=True)
                top_score = sorted_scores[0]
                return {
                    'product_name': top_score.get('product_name'),
                    'product_id': top_score.get('product_id'),
                    'score': top_score.get('total_weighted_score')
                }
            
            return None
        except Exception as e:
            self.logger.error(f"Failed to get recommended product: {str(e)}")
            return None

    def _get_auto_interaction_config(self, team_id: str = None) -> Dict[str, Any]:
        """
        Get auto interaction configuration from team settings.

        Args:
            team_id: Team ID to get settings for

        Returns:
            Auto interaction configuration dictionary with from_email, from_name, etc.
            If multiple configs exist, returns the first Email type config.
        """
        default_config = {
            'from_email': '',
            'from_name': '',
            'from_number': '',
            'tool_type': 'Email',
            'email_cc': '',
            'email_bcc': ''
        }

        if not team_id:
            return default_config

        try:
            # Get team settings
            auto_interaction_settings = self.get_team_setting('gs_team_auto_interaction', team_id, [])

            if not auto_interaction_settings or not isinstance(auto_interaction_settings, list):
                self.logger.debug(f"No auto interaction settings found for team {team_id}, using defaults")
                return default_config

            # Find Email type configuration (preferred for email sending)
            email_config = None
            for config in auto_interaction_settings:
                if config.get('tool_type') == 'Email':
                    email_config = config
                    break

            # If no Email config found, use the first one available
            if not email_config and len(auto_interaction_settings) > 0:
                email_config = auto_interaction_settings[0]
                self.logger.warning(f"No Email tool_type found in auto interaction settings, using first config with tool_type: {email_config.get('tool_type')}")

            if email_config:
                self.logger.debug(f"Using auto interaction config for team {team_id}: from_name={email_config.get('from_name')}, tool_type={email_config.get('tool_type')}")
                return email_config
            else:
                return default_config

        except Exception as e:
            self.logger.error(f"Failed to get auto interaction config for team {team_id}: {str(e)}")
            return default_config

    def _generate_email_drafts(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], scoring_data: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate multiple personalized email drafts using LLM."""
        if self.is_dry_run():
            return self._get_mock_email_drafts(customer_data, recommended_product, context)
        
        try:
            input_data = context.get('input_data', {})
            company_info = customer_data.get('companyInfo', {})
            contact_info = customer_data.get('primaryContact', {})
            pain_points = customer_data.get('painPoints', [])

            prompt_drafts = self._generate_email_drafts_from_prompt(
                customer_data,
                recommended_product,
                scoring_data,
                context
            )
            if prompt_drafts:
                return prompt_drafts

            # Generate multiple draft variations with different approaches
            draft_approaches = [
                {
                    'name': 'professional_direct',
                    'tone': 'professional and direct',
                    'focus': 'business value and ROI',
                    'length': 'concise'
                },
                {
                    'name': 'consultative',
                    'tone': 'consultative and helpful',
                    'focus': 'solving specific pain points',
                    'length': 'medium'
                },
                {
                    'name': 'industry_expert',
                    'tone': 'industry expert and insightful',
                    'focus': 'industry trends and challenges',
                    'length': 'detailed'
                },
                {
                    'name': 'relationship_building',
                    'tone': 'warm and relationship-focused',
                    'focus': 'building connection and trust',
                    'length': 'personal'
                }
            ]
            
            generated_drafts = []
            
            for approach in draft_approaches:
                try:
                    # Generate email content for this approach
                    email_content = self._generate_single_email_draft(
                        customer_data, recommended_product, scoring_data, 
                        approach, context
                    )
                    
                    # Generate subject lines for this approach
                    subject_lines = self._generate_subject_lines(
                        customer_data, recommended_product, approach, context
                    )
                    
                    draft_id = f"uuid:{str(uuid.uuid4())}"
                    draft_approach = approach['name']
                    draft_type = "initial"
                    
                    # Select the best subject line (first one, or most relevant)
                    selected_subject = subject_lines[0] if subject_lines else f"Partnership opportunity for {company_info.get('name', 'your company')}"
                    
                    draft = {
                        'draft_id': draft_id,
                        'approach': approach['name'],
                        'tone': approach['tone'],
                        'focus': approach['focus'],
                        'subject': selected_subject,  # Single subject instead of array
                        'subject_alternatives': subject_lines[1:4] if len(subject_lines) > 1 else [],  # Store alternatives separately
                        'email_body': email_content,
                        'call_to_action': self._extract_call_to_action(email_content),
                        'personalization_score': self._calculate_personalization_score(email_content, customer_data),
                        'generated_at': datetime.now().isoformat(),
                        'status': 'draft',
                        'metadata': {
                            'customer_company': company_info.get('name', 'Unknown'),
                            'contact_name': contact_info.get('name', 'Unknown'),
                            'recommended_product': recommended_product.get('product_name', 'Unknown'),
                            'pain_points_addressed': len([p for p in pain_points if p.get('severity') in ['high', 'medium']]),
                            'generation_method': 'llm_powered'
                        }
                    }
                    
                    generated_drafts.append(draft)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to generate draft for approach {approach['name']}: {str(e)}")
                    continue
            
            if not generated_drafts:
                # Fallback to simple template if all LLM generations fail
                self.logger.warning("All LLM draft generations failed, using fallback template")
                return self._generate_fallback_draft(customer_data, recommended_product, context)
            
            self.logger.info(f"Generated {len(generated_drafts)} email drafts successfully")
            return generated_drafts
            
        except Exception as e:
            self.logger.error(f"Email draft generation failed: {str(e)}")
            return self._generate_fallback_draft(customer_data, recommended_product, context)

    def _generate_email_drafts_from_prompt(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], scoring_data: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Attempt to generate drafts using configured prompt template."""
        prompt_template = self.get_prompt_template('email_generation')
        if not prompt_template:
            return []

        try:
            prompt = self._prepare_email_generation_prompt(
                prompt_template,
                customer_data,
                recommended_product,
                scoring_data,
                context
            )
        except Exception as exc:
            self.logger.warning(f"Failed to prepare email generation prompt: {str(exc)}")
            return []

        if not prompt or not prompt.strip():
            self.logger.warning('Email generation prompt resolved to empty content after placeholder replacement')
            return []

        temperature = self.get_stage_config('email_generation_temperature', 0.35)
        max_tokens = self.get_stage_config('email_generation_max_tokens', 3200)

        try:
            response = self.call_llm(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as exc:
            self.logger.error(f"LLM call for prompt-based email generation failed: {str(exc)}")
            return []

        try:
            parsed_entries = self._parse_prompt_response(response)
        except Exception as exc:
            self.logger.error(f"Failed to parse email generation response: {str(exc)}")
            return []

        drafts: List[Dict[str, Any]] = []
        for entry in parsed_entries:
            normalized = self._normalize_prompt_draft_entry(entry, customer_data, recommended_product, context)
            if normalized:
                drafts.append(normalized)

        if not drafts:
            self.logger.warning('Prompt-based email generation returned no usable drafts')
            return []

        valid_priority = all(
            isinstance(d.get('priority_order'), int) and d['priority_order'] > 0
            for d in drafts
        )

        if valid_priority:
            drafts.sort(key=lambda d: d['priority_order'])
        else:
            for idx, draft in enumerate(drafts, start=1):
                draft['priority_order'] = idx

        return drafts

    def _parse_prompt_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response produced by prompt template."""
        cleaned = self._strip_code_fences(response)
        parsed = self._extract_json_array(cleaned)

        if isinstance(parsed, dict):
            for key in ('emails', 'drafts', 'data', 'results'):
                value = parsed.get(key)
                if isinstance(value, list):
                    parsed = value
                    break
            else:
                raise ValueError('Prompt response JSON object does not contain an email list')

        if not isinstance(parsed, list):
            raise ValueError('Prompt response is not a list of drafts')

        return parsed

    def _prepare_email_generation_prompt(self, template: str, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], scoring_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        replacements = self._build_prompt_replacements(
            customer_data,
            recommended_product,
            scoring_data,
            context
        )

        prompt = template
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return prompt

    def _build_prompt_replacements(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], scoring_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, str]:
        input_data = context.get('input_data', {})
        company_info = customer_data.get('companyInfo', {}) or {}
        contact_info = customer_data.get('primaryContact', {}) or {}
        language = input_data.get('language') or company_info.get('language') or 'English'
        contact_name = contact_info.get('name') or input_data.get('customer_name') or input_data.get('recipient_name') or 'there'
        company_name = company_info.get('name') or input_data.get('company_name') or 'the company'
        staff_name = input_data.get('staff_name') or input_data.get('sender_name') or 'Sales Team'
        org_name = input_data.get('org_name') or 'Our Company'
        selected_product_name = recommended_product.get('product_name') if recommended_product else None

        action = input_data.get('action', 'draft_write')
        action_labels = {
            'draft_write': 'email drafts',
            'draft_rewrite': 'email rewrites',
            'send': 'email sends',
            'close': 'email workflow'
        }
        action_type = action_labels.get(action, action.replace('_', ' '))

        company_summary = self._build_company_info_summary(
            company_info,
            contact_info,
            customer_data.get('painPoints', []),
            scoring_data
        )
        product_summary = self._build_product_info_summary(recommended_product)
        first_name_guide = self._build_first_name_guide(language, contact_name)

        replacements = {
            '##action_type##': action_type,
            '##language##': language.title() if isinstance(language, str) else 'English',
            '##customer_name##': contact_name,
            '##company_name##': company_name,
            '##staff_name##': staff_name,
            '##org_name##': org_name,
            '##first_name_guide##': first_name_guide,
            '##selected_product##': selected_product_name or 'our solution',
            '##company_info##': company_summary,
            '##selected_product_info##': product_summary
        }

        return {key: (value if value is not None else '') for key, value in replacements.items()}

    def _build_company_info_summary(self, company_info: Dict[str, Any], contact_info: Dict[str, Any], pain_points: List[Dict[str, Any]], scoring_data: Dict[str, Any]) -> str:
        lines: List[str] = []

        if company_info.get('name'):
            lines.append(f"Company: {company_info.get('name')}")
        if company_info.get('industry'):
            lines.append(f"Industry: {company_info.get('industry')}")
        if company_info.get('size'):
            lines.append(f"Company size: {company_info.get('size')}")
        if company_info.get('location'):
            lines.append(f"Location: {company_info.get('location')}")

        if contact_info.get('name'):
            title = contact_info.get('title')
            if title:
                lines.append(f"Primary contact: {contact_info.get('name')} ({title})")
            else:
                lines.append(f"Primary contact: {contact_info.get('name')}")
        if contact_info.get('email'):
            lines.append(f"Contact email: {contact_info.get('email')}")

        visible_pain_points = [p for p in pain_points if p]
        if visible_pain_points:
            lines.append('Top pain points:')
            for point in visible_pain_points[:5]:
                description = str(point.get('description', '')).strip()
                if not description:
                    continue
                severity = point.get('severity')
                severity_text = f" (severity: {severity})" if severity else ''
                lines.append(f"- {description}{severity_text}")

        lead_scores = scoring_data.get('lead_scoring', []) or []
        if lead_scores:
            sorted_scores = sorted(lead_scores, key=lambda item: item.get('total_weighted_score', 0), reverse=True)
            top_score = sorted_scores[0]
            product_name = top_score.get('product_name')
            score_value = top_score.get('total_weighted_score')
            if product_name:
                if score_value is not None:
                    lines.append(f"Highest scoring product: {product_name} (score {score_value})")
                else:
                    lines.append(f"Highest scoring product: {product_name}")

        summary = "\n".join(lines).strip()
        return summary or 'Company details unavailable.'

    def _build_product_info_summary(self, recommended_product: Optional[Dict[str, Any]]) -> str:
        if not recommended_product:
            return "No specific product selected. Focus on aligning our solutions with the customer's pain points."

        lines: List[str] = []
        name = recommended_product.get('product_name')
        if name:
            lines.append(f"Product: {name}")
        description = recommended_product.get('description')
        if description:
            lines.append(f"Description: {description}")
        benefits = recommended_product.get('key_benefits')
        if isinstance(benefits, list) and benefits:
            lines.append('Key benefits: ' + ', '.join(str(b) for b in benefits if b))
        differentiators = recommended_product.get('differentiators')
        if isinstance(differentiators, list) and differentiators:
            lines.append('Differentiators: ' + ', '.join(str(d) for d in differentiators if d))
        score = recommended_product.get('score')
        if score is not None:
            lines.append(f"Lead score: {score}")

        summary = "\n".join(lines).strip()
        return summary or 'Product details unavailable.'

    def _build_first_name_guide(self, language: str, contact_name: str) -> str:
        if not language:
            return ''

        language_lower = language.lower()
        if language_lower in ('vietnamese', 'vi'):
            if not contact_name or contact_name.lower() == 'a person':
                return "If the recipient's name is unknown, use `anh/chi` in the greeting."
            first_name = self._extract_first_name(contact_name)
            if first_name:
                return f"For Vietnamese recipients, use `anh/chi {first_name}` in the greeting to keep it respectful."
            return "For Vietnamese recipients, use `anh/chi` followed by the recipient's first name in the greeting."

        return ''

    def _extract_first_name(self, full_name: str) -> str:
        if not full_name:
            return ''
        parts = full_name.strip().split()
        return parts[-1] if parts else full_name

    def _strip_code_fences(self, text: str) -> str:
        if not text:
            return ''
        cleaned = text.strip()
        if cleaned.startswith('```'):
            lines = cleaned.splitlines()
            normalized = '\n'.join(lines[1:]) if len(lines) > 1 else ''
            if '```' in normalized:
                normalized = normalized.rsplit('```', 1)[0]
            cleaned = normalized
        return cleaned.strip()

    def _extract_json_array(self, text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            snippet = text[start:end]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass

        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            snippet = text[start:end]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass

        raise ValueError('Could not parse JSON from prompt response')

    def _normalize_prompt_draft_entry(self, entry: Any, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(entry, dict):
            self.logger.debug('Skipping prompt entry because it is not a dict: %s', entry)
            return None

        email_body = entry.get('body') or entry.get('content') or ''
        if isinstance(email_body, dict):
            email_body = email_body.get('html') or email_body.get('text') or email_body.get('content') or ''
        email_body = str(email_body).strip()
        if not email_body:
            self.logger.debug('Skipping prompt entry because email body is empty: %s', entry)
            return None

        subject = entry.get('subject')
        if isinstance(subject, list):
            subject = subject[0] if subject else ''
        subject = str(subject).strip() if subject else ''

        subject_alternatives: List[str] = []
        for key in ('subject_alternatives', 'subject_variations', 'subject_variants', 'alternative_subjects', 'subjects'):
            variants = entry.get(key)
            if isinstance(variants, list):
                subject_alternatives = [str(item).strip() for item in variants if str(item).strip()]
                if subject_alternatives:
                    break

        if not subject and subject_alternatives:
            subject = subject_alternatives[0]

        if not subject:
            company_name = customer_data.get('companyInfo', {}).get('name', 'your organization')
            subject = f"Opportunity for {company_name}"

        mail_tone = str(entry.get('mail_tone') or entry.get('tone') or 'custom').strip()
        approach = str(entry.get('approach') or entry.get('strategy') or 'custom').strip()
        focus = str(entry.get('focus') or entry.get('value_focus') or 'custom_prompt').strip()

        priority_order = entry.get('priority_order')
        try:
            priority_order = int(priority_order)
            if priority_order < 1:
                raise ValueError
        except (TypeError, ValueError):
            priority_order = None

        product_name = entry.get('product_name') or (recommended_product.get('product_name') if recommended_product else None)
        product_mention = entry.get('product_mention')
        if isinstance(product_mention, str):
            product_mention = product_mention.strip().lower() in ('true', 'yes', '1')
        elif not isinstance(product_mention, bool):
            product_mention = bool(product_name)

        tags = entry.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]
        tags = [str(tag).strip() for tag in tags if str(tag).strip()]

        call_to_action = self._extract_call_to_action(email_body)
        personalization_score = self._calculate_personalization_score(email_body, customer_data)
        message_type = entry.get('message_type') or 'Email'

        metadata = {
            'customer_company': customer_data.get('companyInfo', {}).get('name', 'Unknown'),
            'contact_name': customer_data.get('primaryContact', {}).get('name', 'Unknown'),
            'recommended_product': product_name or 'Unknown',
            'generation_method': 'prompt_template',
            'tags': tags,
            'message_type': message_type
        }

        draft_id = entry.get('draft_id') or f"uuid:{str(uuid.uuid4())}"
        draft_approach = "prompt"
        draft_type = "initial"

        return {
            'draft_id': draft_id,
            'approach': approach,
            'tone': mail_tone,
            'focus': focus,
            'subject': subject,
            'subject_alternatives': subject_alternatives,
            'email_body': email_body,
            'call_to_action': call_to_action,
            'product_mention': product_mention,
            'product_name': product_name,
            'priority_order': priority_order if priority_order is not None else 0,
            'personalization_score': personalization_score,
            'generated_at': datetime.now().isoformat(),
            'status': 'draft',
            'metadata': metadata
        }

    def _strip_html_tags(self, html: str) -> str:
        if not html:
            return ''

        text = re.sub(r'(?i)<br\s*/?>', '\n', html)
        text = re.sub(r'(?i)</p>', '\n', text)
        text = re.sub(r'(?i)<li>', '\n- ', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _generate_single_email_draft(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], 
                                   scoring_data: Dict[str, Any], approach: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate a single email draft using LLM with specific approach."""
        try:
            input_data = context.get('input_data', {})
            company_info = customer_data.get('companyInfo', {})
            contact_info = customer_data.get('primaryContact', {})
            pain_points = customer_data.get('painPoints', [])
            
            # Prepare context for LLM
            customer_context = {
                'company_name': company_info.get('name', 'the company'),
                'contact_name': contact_info.get('name', 'there'),
                'contact_title': contact_info.get('title', ''),
                'industry': company_info.get('industry', 'technology'),
                'company_size': company_info.get('size', 'unknown'),
                'main_pain_points': [p.get('description', '') for p in pain_points[:3]],
                'recommended_product': recommended_product.get('product_name', 'our solution'),
                'product_benefits': recommended_product.get('key_benefits', []),
                'sender_name': input_data.get('staff_name', 'Sales Team'),
                'sender_company': input_data.get('org_name', 'Our Company'),
                'approach_tone': approach.get('tone', 'professional'),
                'approach_focus': approach.get('focus', 'business value'),
                'approach_length': approach.get('length', 'medium')
            }
            
            # Create LLM prompt for email generation
            prompt = self._create_email_generation_prompt(customer_context, approach)
            
            # Generate email using LLM
            email_content = self.call_llm(
                prompt=prompt,
                temperature=0.7,
                max_tokens=800
            )
            
            # Clean and validate the generated content
            cleaned_content = self._clean_email_content(email_content)
            
            return cleaned_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate single email draft: {str(e)}")
            return self._generate_template_email(customer_data, recommended_product, approach, context)

    def _create_email_generation_prompt(self, customer_context: Dict[str, Any], approach: Dict[str, Any]) -> str:
        """Create LLM prompt for email generation."""
        
        pain_points_text = ""
        if customer_context['main_pain_points']:
            pain_points_text = f"Key challenges they face: {', '.join(customer_context['main_pain_points'])}"
        
        benefits_text = ""
        if customer_context['product_benefits']:
            benefits_text = f"Our solution benefits: {', '.join(customer_context['product_benefits'])}"
        
        prompt = f"""Generate a personalized outreach email with the following specifications:

CUSTOMER INFORMATION:
- Company: {customer_context['company_name']}
- Contact: {customer_context['contact_name']} ({customer_context['contact_title']})
- Industry: {customer_context['industry']}
- Company Size: {customer_context['company_size']}
{pain_points_text}

OUR OFFERING:
- Product/Solution: {customer_context['recommended_product']}
{benefits_text}

SENDER INFORMATION:
- Sender: {customer_context['sender_name']}
- Company: {customer_context['sender_company']}

EMAIL APPROACH:
- Tone: {customer_context['approach_tone']}
- Focus: {customer_context['approach_focus']}
- Length: {customer_context['approach_length']}

REQUIREMENTS:
1. Write a complete email from greeting to signature
2. Personalize based on their company and industry
3. Address their specific pain points naturally
4. Present our solution as a potential fit
5. Include a clear, specific call-to-action
6. Keep the tone {customer_context['approach_tone']}
7. Focus on {customer_context['approach_focus']}
8. Make it {customer_context['approach_length']} in length

Generate only the email content, no additional commentary:"""

        return prompt

    def _generate_subject_lines(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], 
                              approach: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Generate multiple subject line variations using LLM."""
        try:
            input_data = context.get('input_data', {})
            company_info = customer_data.get('companyInfo', {})
            
            prompt = f"""Generate 4 compelling email subject lines for an outreach email to {company_info.get('name', 'a company')} in the {company_info.get('industry', 'technology')} industry.

CONTEXT:
- Target Company: {company_info.get('name', 'the company')}
- Industry: {company_info.get('industry', 'technology')}
- Our Solution: {recommended_product.get('product_name', 'our solution')}
- Sender Company: {input_data.get('org_name', 'our company')}
- Approach Tone: {approach.get('tone', 'professional')}

REQUIREMENTS:
1. Keep subject lines under 50 characters
2. Make them personalized and specific
3. Create urgency or curiosity
4. Avoid spam trigger words
5. Match the {approach.get('tone', 'professional')} tone

Generate 4 subject lines, one per line, no numbering or bullets:"""

            response = self.call_llm(
                prompt=prompt,
                temperature=0.8,
                max_tokens=200
            )
            
            # Parse subject lines from response
            subject_lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Ensure we have at least 3 subject lines
            if len(subject_lines) < 3:
                subject_lines.extend(self._generate_fallback_subject_lines(customer_data, recommended_product))
            
            return subject_lines[:4]  # Return max 4 subject lines
            
        except Exception as e:
            self.logger.warning(f"Failed to generate subject lines: {str(e)}")
            return self._generate_fallback_subject_lines(customer_data, recommended_product)

    def _generate_fallback_subject_lines(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any]) -> List[str]:
        """Generate fallback subject lines using templates."""
        company_info = customer_data.get('companyInfo', {})
        company_name = company_info.get('name', 'Your Company')
        
        return [
            f"Quick question about {company_name}",
            f"Partnership opportunity for {company_name}",
            f"Helping {company_name} with {company_info.get('industry', 'growth')}",
            f"5-minute chat about {company_name}?"
        ]

    def _clean_email_content(self, raw_content: str) -> str:
        """Clean and validate generated email content."""
        # Remove any unwanted prefixes or suffixes
        content = raw_content.strip()
        
        # Remove common LLM artifacts
        artifacts_to_remove = [
            "Here's the email:",
            "Here is the email:",
            "Email content:",
            "Generated email:",
            "Subject:",
            "Email:"
        ]
        
        for artifact in artifacts_to_remove:
            if content.startswith(artifact):
                content = content[len(artifact):].strip()
        
        # Ensure proper email structure
        if not content.startswith(('Dear', 'Hi', 'Hello', 'Greetings')):
            # Add a greeting if missing
            content = f"Dear Valued Customer,\n\n{content}"
        
        # Ensure proper closing
        if not any(closing in content.lower() for closing in ['best regards', 'sincerely', 'best', 'thanks']):
            content += "\n\nBest regards"
        
        return content

    def _extract_call_to_action(self, email_content: str) -> str:
        """Extract the main call-to-action from email content."""
        plain_content = self._strip_html_tags(email_content)
        cta_patterns = [
            r"Would you be (?:interested in|available for|open to) ([^?]+\?)",
            r"Can we schedule ([^?]+\?)",
            r"I'd love to ([^.]+\.)",
            r"Let's ([^.]+\.)",
            r"Would you like to ([^?]+\?)"
        ]

        for pattern in cta_patterns:
            match = re.search(pattern, plain_content, re.IGNORECASE)
            if match:
                return match.group(0).strip()

        question_index = plain_content.find('?')
        if question_index != -1:
            start_idx = plain_content.rfind('.', 0, question_index)
            start_idx = start_idx + 1 if start_idx != -1 else 0
            cta_sentence = plain_content[start_idx:question_index + 1].strip()
            if cta_sentence:
                return cta_sentence

        sentences = [sentence.strip() for sentence in re.split(r'[.\n]', plain_content) if sentence.strip()]
        for sentence in sentences:
            if '?' in sentence:
                return sentence if sentence.endswith('?') else f"{sentence}?"

        return "Would you be interested in learning more?"

    def _calculate_personalization_score(self, email_content: str, customer_data: Dict[str, Any]) -> int:
        """Calculate personalization score based on customer data usage."""
        plain_content = self._strip_html_tags(email_content)
        lower_content = plain_content.lower()
        score = 0
        company_info = customer_data.get('companyInfo', {})
        contact_info = customer_data.get('primaryContact', {})

        company_name = str(company_info.get('name', '')).lower()
        if company_name and company_name in lower_content:
            score += 25

        contact_name = str(contact_info.get('name', '')).lower()
        if contact_name and contact_name not in ('a person', '') and contact_name in lower_content:
            score += 25

        industry = str(company_info.get('industry', '')).lower()
        if industry and industry in lower_content:
            score += 20

        pain_points = customer_data.get('painPoints', [])
        for pain_point in pain_points:
            description = str(pain_point.get('description', '')).lower()
            if description and description in lower_content:
                score += 15
                break

        size = company_info.get('size')
        location = company_info.get('location') or company_info.get('address')
        for detail in (size, location):
            if detail:
                detail_text = str(detail).lower()
                if detail_text and detail_text in lower_content:
                    score += 15
                    break

        return min(score, 100)

    def _generate_template_email(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], 
                               approach: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate email using template as fallback."""
        input_data = context.get('input_data', {})
        company_info = customer_data.get('companyInfo', {})
        contact_info = customer_data.get('primaryContact', {})
        
        return f"""Dear {contact_info.get('name', 'there')},

I hope this email finds you well. I'm reaching out from {input_data.get('org_name', 'our company')} regarding a potential opportunity for {company_info.get('name', 'your company')}.

Based on our research of companies in the {company_info.get('industry', 'technology')} sector, I believe {company_info.get('name', 'your company')} could benefit from our {recommended_product.get('product_name', 'solution')}.

We've helped similar organizations achieve significant improvements in their operations. Would you be interested in a brief 15-minute call to discuss how we might be able to help {company_info.get('name', 'your company')} achieve its goals?

Best regards,
{input_data.get('staff_name', 'Sales Team')}
{input_data.get('org_name', 'Our Company')}"""

    def _generate_fallback_draft(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fallback draft when LLM generation fails."""
        draft_id = f"uuid:{str(uuid.uuid4())}"
        draft_approach = "fallback"
        draft_type = "initial"
        
        return [{
            'draft_id': draft_id,
            'approach': 'fallback_template',
            'tone': 'professional',
            'focus': 'general outreach',
            'subject': self._generate_fallback_subject_lines(customer_data, recommended_product)[0],
            'subject_alternatives': self._generate_fallback_subject_lines(customer_data, recommended_product)[1:],
            'email_body': self._generate_template_email(customer_data, recommended_product, {'tone': 'professional'}, context),
            'call_to_action': 'Would you be interested in a brief call?',
            'personalization_score': 50,
            'generated_at': datetime.now().isoformat(),
            'status': 'draft',
            'metadata': {
                'generation_method': 'template_fallback',
                'note': 'Generated using template due to LLM failure'
            }
        }]

    def _get_mock_email_drafts(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get mock email drafts for dry run."""
        input_data = context.get('input_data', {})
        company_info = customer_data.get('companyInfo', {})
        
        return [{
            'draft_id': 'mock_draft_001',
            'approach': 'professional_direct',
            'tone': 'professional and direct',
            'focus': 'business value and ROI',
            'subject': f"Partnership Opportunity for {company_info.get('name', 'Test Company')}",
            'subject_alternatives': [
                f"Quick Question About {company_info.get('name', 'Test Company')}",
                f"Helping Companies Like {company_info.get('name', 'Test Company')}"
            ],
            'email_body': f"""[DRY RUN] Mock email content for {company_info.get('name', 'Test Company')}

This is a mock email that would be generated for testing purposes. In a real execution, this would contain personalized content based on the customer's company information, pain points, and our product recommendations.""",
            'call_to_action': 'Mock call to action',
            'personalization_score': 85,
            'generated_at': datetime.now().isoformat(),
            'status': 'mock',
            'metadata': {
                'generation_method': 'mock_data',
                'note': 'This is mock data for dry run testing'
            }
        }]

    
    def _convert_draft_to_server_format(self, draft: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert local draft format to server-compatible gs_initial_outreach_mail_draft format.
        
        Server schema fields:
        - body (text): Email content
        - subject (text): Single subject line
        - mail_tone (text): Email tone
        - priority_order (integer): Draft priority
        - language (text): Email language
        - keyid (text): Unique identifier
        - customer_language (boolean): Whether using customer's language
        - task_id (text): Task identifier
        - org_id (text): Organization ID
        - customer_id (text): Customer identifier
        - retrieved_date (text): Creation timestamp
        - import_uuid (text): Import identifier
        - project_code (text): Project code
        - project_url (text): Project URL
        """
        input_data = context.get('input_data', {})
        execution_id = context.get('execution_id', 'unknown')
        
        # Generate server-compatible keyid
        keyid = f"{input_data.get('org_id', 'unknown')}_{draft.get('customer_id', 'unknown')}_{execution_id}_{draft['draft_id']}"
        
        # Map approach to mail_tone
        tone_mapping = {
            'professional_direct': 'Professional',
            'consultative': 'Consultative', 
            'industry_expert': 'Expert',
            'relationship_building': 'Friendly'
        }
        
        server_draft = {
            'body': draft.get('email_body', ''),
            'subject': draft.get('subject', ''),
            'mail_tone': tone_mapping.get(draft.get('approach', 'professional_direct'), 'Professional'),
            'priority_order': self._get_draft_priority_order(draft),
            'language': input_data.get('language', 'English').title(),
            'keyid': keyid,
            'customer_language': input_data.get('language', 'english').lower() != 'english',
            'task_id': execution_id,
            'org_id': input_data.get('org_id', 'unknown'),
            'customer_id': draft.get('customer_id', execution_id),
            'retrieved_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'import_uuid': f"{input_data.get('org_id', 'unknown')}_{draft.get('customer_id', execution_id)}_{execution_id}",
            'project_code': input_data.get('project_code', 'LOCAL'),
            'project_url': input_data.get('project_url', ''),
            
            # Keep local fields for compatibility
            'draft_id': draft.get('draft_id'),
            'approach': draft.get('approach'),
            'tone': draft.get('tone'),
            'focus': draft.get('focus'),
            'subject_alternatives': draft.get('subject_alternatives', []),
            'call_to_action': draft.get('call_to_action'),
            'personalization_score': draft.get('personalization_score'),
            'generated_at': draft.get('generated_at'),
            'status': draft.get('status'),
            'metadata': draft.get('metadata', {})
        }
        
        return server_draft
    
    def _get_draft_priority_order(self, draft: Dict[str, Any]) -> int:
        """Get priority order for draft based on approach and personalization score."""
        approach_priorities = {
            'professional_direct': 1,
            'consultative': 2,
            'industry_expert': 3,
            'relationship_building': 4
        }
        
        base_priority = approach_priorities.get(draft.get('approach', 'professional_direct'), 1)
        personalization_score = draft.get('personalization_score', 50)
        
        # Adjust priority based on personalization score
        if personalization_score >= 80:
            return base_priority
        elif personalization_score >= 60:
            return base_priority + 1
        else:
            return base_priority + 2

    
    def _convert_draft_to_server_format(self, draft: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert local draft format to server-compatible gs_initial_outreach_mail_draft format.
        
        Server schema fields:
        - body (text): Email content
        - subject (text): Single subject line
        - mail_tone (text): Email tone
        - priority_order (integer): Draft priority
        - language (text): Email language
        - keyid (text): Unique identifier
        - customer_language (boolean): Whether using customer's language
        - task_id (text): Task identifier
        - org_id (text): Organization ID
        - customer_id (text): Customer identifier
        - retrieved_date (text): Creation timestamp
        - import_uuid (text): Import identifier
        - project_code (text): Project code
        - project_url (text): Project URL
        """
        input_data = context.get('input_data', {})
        execution_id = context.get('execution_id', 'unknown')
        
        # Generate server-compatible keyid
        keyid = f"{input_data.get('org_id', 'unknown')}_{draft.get('customer_id', 'unknown')}_{execution_id}_{draft['draft_id']}"
        
        # Map approach to mail_tone
        tone_mapping = {
            'professional_direct': 'Professional',
            'consultative': 'Consultative', 
            'industry_expert': 'Expert',
            'relationship_building': 'Friendly'
        }
        
        server_draft = {
            'body': draft.get('email_body', ''),
            'subject': draft.get('subject', ''),
            'mail_tone': tone_mapping.get(draft.get('approach', 'professional_direct'), 'Professional'),
            'priority_order': self._get_draft_priority_order(draft),
            'language': input_data.get('language', 'English').title(),
            'keyid': keyid,
            'customer_language': input_data.get('language', 'english').lower() != 'english',
            'task_id': execution_id,
            'org_id': input_data.get('org_id', 'unknown'),
            'customer_id': draft.get('customer_id', execution_id),
            'retrieved_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'import_uuid': f"{input_data.get('org_id', 'unknown')}_{draft.get('customer_id', execution_id)}_{execution_id}",
            'project_code': input_data.get('project_code', 'LOCAL'),
            'project_url': input_data.get('project_url', ''),
            
            # Keep local fields for compatibility
            'draft_id': draft.get('draft_id'),
            'approach': draft.get('approach'),
            'tone': draft.get('tone'),
            'focus': draft.get('focus'),
            'subject_alternatives': draft.get('subject_alternatives', []),
            'call_to_action': draft.get('call_to_action'),
            'personalization_score': draft.get('personalization_score'),
            'generated_at': draft.get('generated_at'),
            'status': draft.get('status'),
            'metadata': draft.get('metadata', {})
        }
        
        return server_draft
    
    def _get_draft_priority_order(self, draft: Dict[str, Any]) -> int:
        """Get priority order for draft based on approach and personalization score."""
        approach_priorities = {
            'professional_direct': 1,
            'consultative': 2,
            'industry_expert': 3,
            'relationship_building': 4
        }
        
        base_priority = approach_priorities.get(draft.get('approach', 'professional_direct'), 1)
        personalization_score = draft.get('personalization_score', 50)
        
        # Adjust priority based on personalization score
        if personalization_score >= 80:
            return base_priority
        elif personalization_score >= 60:
            return base_priority + 1
        else:
            return base_priority + 2

    def _save_email_drafts(self, context: Dict[str, Any], email_drafts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Save email drafts to database and files."""
        try:
            execution_id = context.get('execution_id')
            saved_drafts = []
            
            # Get data manager for database operations
            data_manager = self.data_manager
            
            for draft in email_drafts:
                try:
                    # Prepare draft data for database
                    draft_data = {
                        'draft_id': draft['draft_id'],
                        'execution_id': execution_id,
                        'customer_id': execution_id,  # Using execution_id as customer_id for now
                        'subject': draft.get('subject', 'No Subject'),
                        'content': draft['email_body'],
                        'draft_type': 'initial',
                        'version': 1,
                        'status': 'draft',
                        'metadata': json.dumps({
                            'approach': draft.get('approach', 'unknown'),
                            'tone': draft.get('tone', 'professional'),
                            'focus': draft.get('focus', 'general'),
                            'all_subject_lines': [draft.get('subject', '')] + draft.get('subject_alternatives', []),
                            'call_to_action': draft.get('call_to_action', ''),
                            'personalization_score': draft.get('personalization_score', 0),
                            'generation_method': draft.get('metadata', {}).get('generation_method', 'llm'),
                            'generated_at': draft.get('generated_at', datetime.now().isoformat())
                        })
                    }
                    
                    # Save to database
                    if not self.is_dry_run():
                        data_manager.save_email_draft(
                            draft_id=draft_data['draft_id'],
                            execution_id=draft_data['execution_id'],
                            customer_id=draft_data['customer_id'],
                            subject=draft_data['subject'],
                            content=draft_data['content'],
                            draft_type=draft_data['draft_type'],
                            version=draft_data['version']
                        )
                        self.logger.info(f"Saved draft {draft['draft_id']} to database")
                    
                    # Save to file system for backup
                    draft_file_path = self._save_draft_to_file(execution_id, draft)
                    
                    # Add context to draft
                    draft_with_context = draft.copy()
                    draft_with_context['execution_id'] = execution_id
                    draft_with_context['file_path'] = draft_file_path
                    draft_with_context['database_saved'] = not self.is_dry_run()
                    draft_with_context['saved_at'] = datetime.now().isoformat()
                    
                    saved_drafts.append(draft_with_context)
                    
                except Exception as e:
                    self.logger.error(f"Failed to save individual draft {draft.get('draft_id', 'unknown')}: {str(e)}")
                    # Still add to saved_drafts but mark as failed
                    draft_with_context = draft.copy()
                    draft_with_context['execution_id'] = execution_id
                    draft_with_context['save_error'] = str(e)
                    draft_with_context['database_saved'] = False
                    saved_drafts.append(draft_with_context)
            
            self.logger.info(f"Successfully saved {len([d for d in saved_drafts if d.get('database_saved', False)])} drafts to database")
            return saved_drafts
            
        except Exception as e:
            self.logger.error(f"Failed to save email drafts: {str(e)}")
            # Return drafts with error information
            for draft in email_drafts:
                draft['save_error'] = str(e)
                draft['database_saved'] = False
            return email_drafts

    def _save_draft_to_file(self, execution_id: str, draft: Dict[str, Any]) -> str:
        """Save draft to file system as backup."""
        try:
            import os
            
            # Create drafts directory if it doesn't exist
            drafts_dir = os.path.join(self.config.get('data_dir', './fusesell_data'), 'drafts')
            os.makedirs(drafts_dir, exist_ok=True)
            
            # Create file path
            file_name = f"{execution_id}_{draft['draft_id']}.json"
            file_path = os.path.join(drafts_dir, file_name)
            
            # Save draft to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(draft, f, indent=2, ensure_ascii=False)
            
            return f"drafts/{file_name}"
            
        except Exception as e:
            self.logger.warning(f"Failed to save draft to file: {str(e)}")
            return f"drafts/{execution_id}_{draft['draft_id']}.json"

    def _get_draft_by_id(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve draft by ID from database."""
        if self.is_dry_run():
            return {
                'draft_id': draft_id,
                'subject': 'Mock Subject Line',
                'subject_alternatives': ['Alternative Mock Subject'],
                'email_body': 'Mock email content for testing purposes.',
                'approach': 'mock',
                'tone': 'professional',
                'status': 'mock',
                'call_to_action': 'Mock call to action',
                'personalization_score': 75
            }
        
        try:
            # Get data manager for database operations
            data_manager = self.data_manager
            
            # Query database for draft
            draft_record = data_manager.get_email_draft_by_id(draft_id)
            
            if not draft_record:
                self.logger.warning(f"Draft not found in database: {draft_id}")
                return None
            
            # Parse metadata
            metadata = {}
            if draft_record.get('metadata'):
                try:
                    metadata = json.loads(draft_record['metadata'])
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse metadata for draft {draft_id}")
            
            # Reconstruct draft object
            draft = {
                'draft_id': draft_record['draft_id'],
                'execution_id': draft_record['execution_id'],
                'customer_id': draft_record['customer_id'],
                'subject': draft_record['subject'],
                'subject_alternatives': metadata.get('all_subject_lines', [])[1:] if len(metadata.get('all_subject_lines', [])) > 1 else [],
                'email_body': draft_record['content'],
                'approach': metadata.get('approach', 'unknown'),
                'tone': metadata.get('tone', 'professional'),
                'focus': metadata.get('focus', 'general'),
                'call_to_action': metadata.get('call_to_action', ''),
                'personalization_score': metadata.get('personalization_score', 0),
                'status': draft_record['status'],
                'version': draft_record['version'],
                'draft_type': draft_record['draft_type'],
                'created_at': draft_record['created_at'],
                'updated_at': draft_record['updated_at'],
                'metadata': metadata
            }
            
            self.logger.info(f"Retrieved draft {draft_id} from database")
            return draft
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve draft {draft_id}: {str(e)}")
            return None

    def _rewrite_draft(self, existing_draft: Dict[str, Any], reason: str, customer_data: Dict[str, Any], scoring_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Rewrite existing draft based on reason using LLM."""
        try:
            if self.is_dry_run():
                rewritten = existing_draft.copy()
                rewritten['draft_id'] = f"uuid:{str(uuid.uuid4())}"
                rewritten['draft_approach'] = "rewrite"
                rewritten['draft_type'] = "rewrite"
                rewritten['email_body'] = f"[DRY RUN - REWRITTEN: {reason}] " + existing_draft.get('email_body', '')
                rewritten['rewrite_reason'] = reason
                rewritten['rewritten_at'] = datetime.now().isoformat()
                return rewritten
            
            input_data = context.get('input_data', {})
            company_info = customer_data.get('companyInfo', {})
            contact_info = customer_data.get('primaryContact', {})
            
            # Create rewrite prompt
            rewrite_prompt = f"""Rewrite the following email based on the feedback provided. Keep the core message and personalization but address the specific concerns mentioned.

ORIGINAL EMAIL:
{existing_draft.get('email_body', '')}

FEEDBACK/REASON FOR REWRITE:
{reason}

CUSTOMER CONTEXT:
- Company: {company_info.get('name', 'the company')}
- Contact: {contact_info.get('name', 'the contact')}
- Industry: {company_info.get('industry', 'technology')}

REQUIREMENTS:
1. Address the feedback/reason provided
2. Maintain personalization and relevance
3. Keep the professional tone
4. Ensure the email flows naturally
5. Include a clear call-to-action
6. Make improvements based on the feedback

Generate only the rewritten email content:"""

            # Generate rewritten content using LLM
            rewritten_content = self.call_llm(
                prompt=rewrite_prompt,
                temperature=0.6,
                max_tokens=800
            )
            
            # Clean the rewritten content
            cleaned_content = self._clean_email_content(rewritten_content)
            
            # Create rewritten draft object
            rewritten = existing_draft.copy()
            rewritten['draft_id'] = f"uuid:{str(uuid.uuid4())}"
            rewritten['draft_approach'] = "rewrite"
            rewritten['draft_type'] = "rewrite"
            rewritten['email_body'] = cleaned_content
            rewritten['rewrite_reason'] = reason
            rewritten['rewritten_at'] = datetime.now().isoformat()
            rewritten['version'] = existing_draft.get('version', 1) + 1
            rewritten['call_to_action'] = self._extract_call_to_action(cleaned_content)
            rewritten['personalization_score'] = self._calculate_personalization_score(cleaned_content, customer_data)
            
            # Update metadata
            if 'metadata' not in rewritten:
                rewritten['metadata'] = {}
            rewritten['metadata']['rewrite_history'] = rewritten['metadata'].get('rewrite_history', [])
            rewritten['metadata']['rewrite_history'].append({
                'reason': reason,
                'rewritten_at': datetime.now().isoformat(),
                'original_draft_id': existing_draft.get('draft_id')
            })
            rewritten['metadata']['generation_method'] = 'llm_rewrite'
            
            self.logger.info(f"Successfully rewrote draft based on reason: {reason}")
            return rewritten
            
        except Exception as e:
            self.logger.error(f"Failed to rewrite draft: {str(e)}")
            # Fallback to simple modification
            rewritten = existing_draft.copy()
            rewritten['draft_id'] = f"uuid:{str(uuid.uuid4())}"
            rewritten['draft_approach'] = "rewrite"
            rewritten['draft_type'] = "rewrite"
            rewritten['email_body'] = f"[REWRITTEN: {reason}]\n\n" + existing_draft.get('email_body', '')
            rewritten['rewrite_reason'] = reason
            rewritten['rewritten_at'] = datetime.now().isoformat()
            rewritten['metadata'] = {'generation_method': 'template_rewrite', 'error': str(e)}
            return rewritten

    def _save_rewritten_draft(self, context: Dict[str, Any], rewritten_draft: Dict[str, Any], original_draft_id: str) -> Dict[str, Any]:
        """Save rewritten draft to database and file system."""
        try:
            execution_id = context.get('execution_id')
            rewritten_draft['original_draft_id'] = original_draft_id
            rewritten_draft['execution_id'] = execution_id
            
            # Get data manager for database operations
            data_manager = self.data_manager
            
            # Prepare draft data for database
            draft_data = {
                'draft_id': rewritten_draft['draft_id'],
                'execution_id': execution_id,
                'customer_id': execution_id,  # Using execution_id as customer_id for now
                'subject': rewritten_draft.get('subject', 'Rewritten Draft'),
                'content': rewritten_draft['email_body'],
                'draft_type': 'initial_rewrite',
                'version': rewritten_draft.get('version', 2),
                'status': 'draft',
                'metadata': json.dumps({
                    'approach': rewritten_draft.get('approach', 'rewritten'),
                    'tone': rewritten_draft.get('tone', 'professional'),
                    'focus': rewritten_draft.get('focus', 'general'),
                    'all_subject_lines': [rewritten_draft.get('subject', '')] + rewritten_draft.get('subject_alternatives', []),
                    'call_to_action': rewritten_draft.get('call_to_action', ''),
                    'personalization_score': rewritten_draft.get('personalization_score', 0),
                    'generation_method': 'llm_rewrite',
                    'rewrite_reason': rewritten_draft.get('rewrite_reason', ''),
                    'original_draft_id': original_draft_id,
                    'rewritten_at': rewritten_draft.get('rewritten_at', datetime.now().isoformat()),
                    'rewrite_history': rewritten_draft.get('metadata', {}).get('rewrite_history', [])
                })
            }
            
            # Save to database
            if not self.is_dry_run():
                data_manager.save_email_draft(draft_data)
                self.logger.info(f"Saved rewritten draft {rewritten_draft['draft_id']} to database")
            
            # Save to file system for backup
            draft_file_path = self._save_draft_to_file(execution_id, rewritten_draft)
            
            # Add save information
            rewritten_draft['file_path'] = draft_file_path
            rewritten_draft['database_saved'] = not self.is_dry_run()
            rewritten_draft['saved_at'] = datetime.now().isoformat()
            
            return rewritten_draft
            
        except Exception as e:
            self.logger.error(f"Failed to save rewritten draft: {str(e)}")
            rewritten_draft['save_error'] = str(e)
            rewritten_draft['database_saved'] = False
            return rewritten_draft

    def _send_email(self, draft: Dict[str, Any], recipient_address: str, recipient_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send email using existing RTA email service (matching original YAML)."""
        if self.is_dry_run():
            return {
                'success': True,
                'message': f'[DRY RUN] Would send email to {recipient_address}',
                'email_id': f'mock_email_{uuid.uuid4().hex[:8]}'
            }

        try:
            input_data = context.get('input_data', {})

            # Get auto interaction settings from team settings
            auto_interaction_config = self._get_auto_interaction_config(input_data.get('team_id'))

            # Prepare email payload for RTA email service (matching trigger_auto_interaction)
            email_payload = {
                "project_code": input_data.get('project_code', ''),
                "event_type": "custom",
                "event_id": input_data.get('customer_id', context.get('execution_id')),
                "type": "interaction",
                "family": "GLOBALSELL_INTERACT_EVENT_ADHOC",
                "language": input_data.get('language', 'english'),
                "submission_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "instanceName": f"Send email to {recipient_name} ({recipient_address}) from {auto_interaction_config.get('from_name', input_data.get('org_name', 'Unknown'))}",
                "instanceID": f"{context.get('execution_id')}_{input_data.get('customer_id', 'unknown')}",
                "uuid": f"{context.get('execution_id')}_{input_data.get('customer_id', 'unknown')}",
                "action_type": auto_interaction_config.get('tool_type', 'email').lower(),
                "email": recipient_address,
                "number": auto_interaction_config.get('from_number', input_data.get('customer_phone', '')),
                "subject": draft.get('subject', ''),  # Use subject line
                "content": draft.get('email_body', ''),
                "team_id": input_data.get('team_id', ''),
                "from_email": auto_interaction_config.get('from_email', ''),
                "from_name": auto_interaction_config.get('from_name', ''),
                "email_cc": auto_interaction_config.get('email_cc', ''),
                "email_bcc": auto_interaction_config.get('email_bcc', ''),
                "extraData": {
                    "org_id": input_data.get('org_id'),
                    "human_action_id": input_data.get('human_action_id', ''),
                    "email_tags": "gs_148_initial_outreach",
                    "task_id": input_data.get('customer_id', context.get('execution_id'))
                }
            }
            
            # Send to RTA email service
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://automation.rta.vn/webhook/autoemail-trigger-by-inst-check',
                json=email_payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                execution_id = result.get('executionID', '')
                
                if execution_id:
                    self.logger.info(f"Email sent successfully via RTA service: {execution_id}")
                    return {
                        'success': True,
                        'message': f'Email sent to {recipient_address}',
                        'email_id': execution_id,
                        'service': 'RTA_email_service',
                        'response': result
                    }
                else:
                    self.logger.warning("Email service returned success but no execution ID")
                    return {
                        'success': False,
                        'message': 'Email service returned success but no execution ID',
                        'response': result
                    }
            else:
                self.logger.error(f"Email service returned error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f'Email service error: {response.status_code}',
                    'error': response.text
                }
                
        except Exception as e:
            self.logger.error(f"Email sending failed: {str(e)}")
            return {
                'success': False,
                'message': f'Email sending failed: {str(e)}',
                'error': str(e)
            }

    def get_drafts_for_execution(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get all drafts for a specific execution."""
        try:
            data_manager = self.data_manager
            draft_records = data_manager.get_email_drafts_by_execution(execution_id)
            
            drafts = []
            for record in draft_records:
                # Parse metadata
                metadata = {}
                if record.get('metadata'):
                    try:
                        metadata = json.loads(record['metadata'])
                    except json.JSONDecodeError:
                        pass
                
                draft = {
                    'draft_id': record['draft_id'],
                    'execution_id': record['execution_id'],
                    'subject': record['subject'],
                    'content': record['content'],
                    'approach': metadata.get('approach', 'unknown'),
                    'tone': metadata.get('tone', 'professional'),
                    'personalization_score': metadata.get('personalization_score', 0),
                    'status': record['status'],
                    'version': record['version'],
                    'created_at': record['created_at'],
                    'updated_at': record['updated_at'],
                    'metadata': metadata
                }
                drafts.append(draft)
            
            return drafts
            
        except Exception as e:
            self.logger.error(f"Failed to get drafts for execution {execution_id}: {str(e)}")
            return []

    def compare_drafts(self, draft_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple drafts and provide analysis."""
        try:
            drafts = []
            for draft_id in draft_ids:
                draft = self._get_draft_by_id(draft_id)
                if draft:
                    drafts.append(draft)
            
            if len(drafts) < 2:
                return {'error': 'Need at least 2 drafts to compare'}
            
            comparison = {
                'drafts_compared': len(drafts),
                'comparison_timestamp': datetime.now().isoformat(),
                'drafts': [],
                'analysis': {
                    'personalization_scores': {},
                    'approaches': {},
                    'length_analysis': {},
                    'tone_analysis': {},
                    'recommendations': []
                }
            }
            
            # Analyze each draft
            for draft in drafts:
                draft_analysis = {
                    'draft_id': draft['draft_id'],
                    'approach': draft.get('approach', 'unknown'),
                    'tone': draft.get('tone', 'professional'),
                    'personalization_score': draft.get('personalization_score', 0),
                    'word_count': len(draft.get('email_body', '').split()),
                    'has_call_to_action': bool(draft.get('call_to_action')),
                    'subject_line_count': 1 + len(draft.get('subject_alternatives', [])),
                    'version': draft.get('version', 1)
                }
                comparison['drafts'].append(draft_analysis)
                
                # Collect data for analysis
                comparison['analysis']['personalization_scores'][draft['draft_id']] = draft.get('personalization_score', 0)
                comparison['analysis']['approaches'][draft['draft_id']] = draft.get('approach', 'unknown')
                comparison['analysis']['length_analysis'][draft['draft_id']] = draft_analysis['word_count']
                comparison['analysis']['tone_analysis'][draft['draft_id']] = draft.get('tone', 'professional')
            
            # Generate recommendations
            best_personalization = max(comparison['analysis']['personalization_scores'].items(), key=lambda x: x[1])
            comparison['analysis']['recommendations'].append(
                f"Draft {best_personalization[0]} has the highest personalization score ({best_personalization[1]})"
            )
            
            # Length recommendations
            avg_length = sum(comparison['analysis']['length_analysis'].values()) / len(comparison['analysis']['length_analysis'])
            for draft_id, length in comparison['analysis']['length_analysis'].items():
                if length < avg_length * 0.7:
                    comparison['analysis']['recommendations'].append(f"Draft {draft_id} might be too short ({length} words)")
                elif length > avg_length * 1.5:
                    comparison['analysis']['recommendations'].append(f"Draft {draft_id} might be too long ({length} words)")
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Failed to compare drafts: {str(e)}")
            return {'error': str(e)}

    def select_best_draft(self, execution_id: str, criteria: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Select the best draft based on criteria."""
        try:
            drafts = self.get_drafts_for_execution(execution_id)
            
            if not drafts:
                return None
            
            if len(drafts) == 1:
                return drafts[0]
            
            # Default criteria if none provided
            if not criteria:
                criteria = {
                    'personalization_weight': 0.4,
                    'approach_preference': 'professional_direct',
                    'length_preference': 'medium',  # short, medium, long
                    'tone_preference': 'professional'
                }
            
            scored_drafts = []
            
            for draft in drafts:
                score = 0
                
                # Personalization score (0-100, normalize to 0-1)
                personalization_score = draft.get('personalization_score', 0) / 100
                score += personalization_score * criteria.get('personalization_weight', 0.4)
                
                # Approach preference
                if draft.get('approach') == criteria.get('approach_preference'):
                    score += 0.3
                
                # Length preference
                word_count = len(draft.get('email_body', '').split())
                if criteria.get('length_preference') == 'short' and word_count < 150:
                    score += 0.2
                elif criteria.get('length_preference') == 'medium' and 150 <= word_count <= 300:
                    score += 0.2
                elif criteria.get('length_preference') == 'long' and word_count > 300:
                    score += 0.2
                
                # Tone preference
                if draft.get('tone', '').lower().find(criteria.get('tone_preference', '').lower()) != -1:
                    score += 0.1
                
                scored_drafts.append((draft, score))
            
            # Sort by score and return best
            scored_drafts.sort(key=lambda x: x[1], reverse=True)
            best_draft = scored_drafts[0][0]
            
            # Add selection metadata
            best_draft['selection_metadata'] = {
                'selected_at': datetime.now().isoformat(),
                'selection_score': scored_drafts[0][1],
                'criteria_used': criteria,
                'total_drafts_considered': len(drafts)
            }
            
            return best_draft
            
        except Exception as e:
            self.logger.error(f"Failed to select best draft: {str(e)}")
            return None

    def get_draft_versions(self, original_draft_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a draft (original + rewrites)."""
        try:
            data_manager = self.data_manager
            
            # Get original draft
            original_draft = self._get_draft_by_id(original_draft_id)
            if not original_draft:
                return []
            
            versions = [original_draft]
            
            # Get all rewrites of this draft
            rewrite_records = data_manager.get_email_drafts_by_original_id(original_draft_id)
            
            for record in rewrite_records:
                # Parse metadata
                metadata = {}
                if record.get('metadata'):
                    try:
                        metadata = json.loads(record['metadata'])
                    except json.JSONDecodeError:
                        pass
                
                rewrite_draft = {
                    'draft_id': record['draft_id'],
                    'execution_id': record['execution_id'],
                    'subject': record['subject'],
                    'content': record['content'],
                    'approach': metadata.get('approach', 'rewritten'),
                    'tone': metadata.get('tone', 'professional'),
                    'personalization_score': metadata.get('personalization_score', 0),
                    'status': record['status'],
                    'version': record['version'],
                    'created_at': record['created_at'],
                    'updated_at': record['updated_at'],
                    'rewrite_reason': metadata.get('rewrite_reason', ''),
                    'original_draft_id': original_draft_id,
                    'metadata': metadata
                }
                versions.append(rewrite_draft)
            
            # Sort by version number
            versions.sort(key=lambda x: x.get('version', 1))
            
            return versions
            
        except Exception as e:
            self.logger.error(f"Failed to get draft versions for {original_draft_id}: {str(e)}")
            return []

    def archive_draft(self, draft_id: str, reason: str = "Archived by user") -> bool:
        """Archive a draft (mark as archived, don't delete)."""
        try:
            data_manager = self.data_manager
            
            # Update draft status to archived
            success = data_manager.update_email_draft_status(draft_id, 'archived')
            
            if success:
                self.logger.info(f"Archived draft {draft_id}: {reason}")
                return True
            else:
                self.logger.warning(f"Failed to archive draft {draft_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to archive draft {draft_id}: {str(e)}")
            return False

    def duplicate_draft(self, draft_id: str, modifications: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Create a duplicate of an existing draft with optional modifications."""
        try:
            # Get original draft
            original_draft = self._get_draft_by_id(draft_id)
            if not original_draft:
                return None
            
            # Create duplicate
            duplicate = original_draft.copy()
            duplicate['draft_id'] = f"uuid:{str(uuid.uuid4())}"
            duplicate['draft_approach'] = "duplicate"
            duplicate['draft_type'] = "duplicate"
            duplicate['version'] = 1
            duplicate['status'] = 'draft'
            duplicate['created_at'] = datetime.now().isoformat()
            duplicate['updated_at'] = datetime.now().isoformat()
            
            # Apply modifications if provided
            if modifications:
                for key, value in modifications.items():
                    if key in ['email_body', 'subject', 'subject_alternatives', 'approach', 'tone']:
                        duplicate[key] = value
            
            # Update metadata
            if 'metadata' not in duplicate:
                duplicate['metadata'] = {}
            duplicate['metadata']['duplicated_from'] = draft_id
            duplicate['metadata']['duplicated_at'] = datetime.now().isoformat()
            duplicate['metadata']['generation_method'] = 'duplicate'
            
            # Save duplicate
            execution_id = duplicate.get('execution_id', 'unknown')
            saved_duplicate = self._save_email_drafts({'execution_id': execution_id}, [duplicate])
            
            if saved_duplicate:
                return saved_duplicate[0]
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to duplicate draft {draft_id}: {str(e)}")
            return None

    def _create_customer_summary(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive customer summary for outreach context."""
        company_info = customer_data.get('companyInfo', {})
        contact_info = customer_data.get('primaryContact', {})
        pain_points = customer_data.get('painPoints', [])
        
        # Calculate summary metrics
        high_priority_pain_points = [p for p in pain_points if p.get('severity') == 'high']
        total_pain_points = len(pain_points)
        
        return {
            'company_name': company_info.get('name', 'Unknown'),
            'industry': company_info.get('industry', 'Unknown'),
            'company_size': company_info.get('size', 'Unknown'),
            'annual_revenue': company_info.get('annualRevenue', 'Unknown'),
            'location': company_info.get('location', 'Unknown'),
            'website': company_info.get('website', 'Unknown'),
            'contact_name': contact_info.get('name', 'Unknown'),
            'contact_title': contact_info.get('title', 'Unknown'),
            'contact_email': contact_info.get('email', 'Unknown'),
            'contact_phone': contact_info.get('phone', 'Unknown'),
            'total_pain_points': total_pain_points,
            'high_priority_pain_points': len(high_priority_pain_points),
            'key_challenges': [p.get('description', '') for p in high_priority_pain_points[:3]],
            'business_profile': {
                'industry_focus': company_info.get('industry', 'Technology'),
                'company_stage': self._determine_company_stage(company_info),
                'technology_maturity': self._assess_technology_maturity(customer_data),
                'growth_indicators': self._identify_growth_indicators(customer_data)
            },
            'outreach_readiness': self._calculate_outreach_readiness(customer_data),
            'summary_generated_at': datetime.now().isoformat()
        }

    def _determine_company_stage(self, company_info: Dict[str, Any]) -> str:
        """Determine company stage based on size and revenue."""
        size = company_info.get('size', '').lower()
        revenue = company_info.get('annualRevenue', '').lower()
        
        if 'startup' in size or 'small' in size:
            return 'startup'
        elif 'medium' in size or 'mid' in size:
            return 'growth'
        elif 'large' in size or 'enterprise' in size:
            return 'enterprise'
        elif any(indicator in revenue for indicator in ['million', 'billion']):
            return 'established'
        else:
            return 'unknown'

    def _assess_technology_maturity(self, customer_data: Dict[str, Any]) -> str:
        """Assess technology maturity based on available data."""
        tech_info = customer_data.get('technologyAndInnovation', {})
        pain_points = customer_data.get('painPoints', [])
        
        # Look for technology-related indicators
        tech_keywords = ['digital', 'automation', 'cloud', 'ai', 'software', 'platform']
        legacy_keywords = ['manual', 'paper', 'outdated', 'legacy', 'traditional']
        
        tech_score = 0
        legacy_score = 0
        
        # Check technology info
        tech_text = str(tech_info).lower()
        for keyword in tech_keywords:
            if keyword in tech_text:
                tech_score += 1
        for keyword in legacy_keywords:
            if keyword in tech_text:
                legacy_score += 1
        
        # Check pain points
        for pain_point in pain_points:
            description = pain_point.get('description', '').lower()
            for keyword in tech_keywords:
                if keyword in description:
                    tech_score += 1
            for keyword in legacy_keywords:
                if keyword in description:
                    legacy_score += 1
        
        if tech_score > legacy_score + 2:
            return 'advanced'
        elif tech_score > legacy_score:
            return 'moderate'
        elif legacy_score > tech_score:
            return 'traditional'
        else:
            return 'mixed'

    def _identify_growth_indicators(self, customer_data: Dict[str, Any]) -> List[str]:
        """Identify growth indicators from customer data."""
        indicators = []
        
        company_info = customer_data.get('companyInfo', {})
        development_plans = customer_data.get('developmentPlans', {})
        pain_points = customer_data.get('painPoints', [])
        
        # Check for growth keywords
        growth_keywords = {
            'expansion': 'Market expansion plans',
            'scaling': 'Scaling operations',
            'hiring': 'Team growth',
            'funding': 'Recent funding',
            'new market': 'New market entry',
            'international': 'International expansion',
            'acquisition': 'Acquisition activity',
            'partnership': 'Strategic partnerships'
        }
        
        # Check development plans
        dev_text = str(development_plans).lower()
        for keyword, indicator in growth_keywords.items():
            if keyword in dev_text:
                indicators.append(indicator)
        
        # Check pain points for growth-related challenges
        for pain_point in pain_points:
            description = pain_point.get('description', '').lower()
            if any(keyword in description for keyword in ['capacity', 'demand', 'volume', 'growth']):
                indicators.append('Growth-related challenges')
                break
        
        return list(set(indicators))  # Remove duplicates

    def _calculate_outreach_readiness(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate readiness score for outreach."""
        score = 0
        factors = []
        
        company_info = customer_data.get('companyInfo', {})
        contact_info = customer_data.get('primaryContact', {})
        pain_points = customer_data.get('painPoints', [])
        
        # Contact information completeness (0-30 points)
        if contact_info.get('name'):
            score += 10
            factors.append('Contact name available')
        if contact_info.get('email'):
            score += 15
            factors.append('Email address available')
        if contact_info.get('title'):
            score += 5
            factors.append('Contact title available')
        
        # Company information completeness (0-30 points)
        if company_info.get('name'):
            score += 10
            factors.append('Company name available')
        if company_info.get('industry'):
            score += 10
            factors.append('Industry information available')
        if company_info.get('size') or company_info.get('annualRevenue'):
            score += 10
            factors.append('Company size/revenue information available')
        
        # Pain points quality (0-40 points)
        high_severity_points = [p for p in pain_points if p.get('severity') == 'high']
        medium_severity_points = [p for p in pain_points if p.get('severity') == 'medium']
        
        if high_severity_points:
            score += 25
            factors.append(f'{len(high_severity_points)} high-severity pain points identified')
        if medium_severity_points:
            score += 15
            factors.append(f'{len(medium_severity_points)} medium-severity pain points identified')
        
        # Determine readiness level
        if score >= 80:
            readiness_level = 'high'
        elif score >= 60:
            readiness_level = 'medium'
        elif score >= 40:
            readiness_level = 'low'
        else:
            readiness_level = 'insufficient'
        
        return {
            'score': score,
            'level': readiness_level,
            'factors': factors,
            'recommendations': self._get_readiness_recommendations(score, factors)
        }

    def _get_readiness_recommendations(self, score: int, factors: List[str]) -> List[str]:
        """Get recommendations based on readiness score."""
        recommendations = []
        
        if score < 40:
            recommendations.append('Gather more customer information before outreach')
            recommendations.append('Focus on identifying key pain points')
        elif score < 60:
            recommendations.append('Consider additional research on company background')
            recommendations.append('Verify contact information accuracy')
        elif score < 80:
            recommendations.append('Outreach ready with minor improvements possible')
            recommendations.append('Consider personalizing based on specific pain points')
        else:
            recommendations.append('Excellent outreach readiness')
            recommendations.append('Proceed with highly personalized outreach')
        
        return recommendations

    def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        Validate input data for initial outreach stage (server schema compliant).
        
        Args:
            context: Execution context
            
        Returns:
            True if input is valid
        """
        input_data = context.get('input_data', {})
        
        # Check for required server schema fields
        required_fields = [
            'org_id', 'org_name', 'customer_name', 'customer_id',
            'interaction_type', 'action', 'language', 'recipient_address',
            'recipient_name', 'staff_name', 'team_id', 'team_name'
        ]
        
        # For draft_write action, we need data from previous stages or structured input
        action = input_data.get('action', 'draft_write')
        
        if action == 'draft_write':
            # Check if we have data from previous stages OR structured input
            stage_results = context.get('stage_results', {})
            has_stage_data = 'data_preparation' in stage_results and 'lead_scoring' in stage_results
            has_structured_input = input_data.get('companyInfo') and input_data.get('pain_points')
            
            return has_stage_data or has_structured_input
        
        # For other actions, basic validation
        return bool(input_data.get('org_id') and input_data.get('action'))

    def get_required_fields(self) -> List[str]:
        """
        Get list of required input fields for this stage.
        
        Returns:
            List of required field names
        """
        return [
            'org_id', 'org_name', 'customer_name', 'customer_id',
            'interaction_type', 'action', 'language', 'recipient_address',
            'recipient_name', 'staff_name', 'team_id', 'team_name'
        ]
