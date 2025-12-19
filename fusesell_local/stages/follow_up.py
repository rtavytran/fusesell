"""
Follow-up Stage - Generate contextual follow-up emails based on interaction history
Converted from fusesell_follow_up.yaml with enhanced LLM-powered generation
"""

import json
import uuid
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_stage import BaseStage


class FollowUpStage(BaseStage):
    """
    Follow-up stage for managing ongoing customer engagement with intelligent context analysis.
    Supports multiple follow-up strategies based on interaction history and customer behavior.
    """
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute follow-up stage with action-based routing and interaction history analysis.
        
        Actions supported:
        - draft_write: Generate new follow-up drafts based on interaction history
        - draft_rewrite: Modify existing draft using selected_draft_id
        - send: Send approved draft to recipient_address with follow-up scheduling
        - close: Close follow-up sequence when customer responds or shows disinterest
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result
        """
        try:
            # Get action from input data (matching server schema)
            input_data = context.get('input_data', {})
            action = input_data.get('action', 'draft_write')  # Default to draft_write
            
            self.logger.info(f"Executing follow-up with action: {action}")
            
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
        Handle draft_write action - Generate new follow-up drafts based on interaction history.
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result with new follow-up drafts
        """
        # Analyze interaction history and determine follow-up strategy
        interaction_analysis = self._analyze_interaction_history(context)
        
        # Determine if follow-up is needed and what type
        follow_up_strategy = self._determine_follow_up_strategy(interaction_analysis, context)
        
        if not follow_up_strategy['should_follow_up']:
            return self.create_success_result({
                'action': 'draft_write',
                'status': 'follow_up_not_needed',
                'reason': follow_up_strategy['reason'],
                'interaction_analysis': interaction_analysis,
                'recommendation': 'No follow-up required at this time',
                'customer_id': context.get('execution_id')
            }, context)
        
        # Get data from previous stages or context
        customer_data = self._get_customer_data(context)
        scoring_data = self._get_scoring_data(context)
        
        # Get the recommended product (same as initial outreach)
        recommended_product = self._get_recommended_product(scoring_data)
        
        if not recommended_product:
            raise ValueError("No product recommendation available for follow-up email generation")
        
        # Generate follow-up email drafts based on strategy
        follow_up_drafts = self._generate_follow_up_drafts(
            customer_data, recommended_product, scoring_data, 
            interaction_analysis, follow_up_strategy, context
        )
        
        # Save drafts to local files and database
        saved_drafts = self._save_follow_up_drafts(context, follow_up_drafts)
        
        # Prepare final output
        follow_up_data = {
            'action': 'draft_write',
            'status': 'follow_up_drafts_generated',
            'follow_up_drafts': saved_drafts,
            'follow_up_strategy': follow_up_strategy,
            'interaction_analysis': interaction_analysis,
            'recommended_product': recommended_product,
            'customer_summary': self._create_customer_summary(customer_data),
            'total_drafts_generated': len(saved_drafts),
            'generation_timestamp': datetime.now().isoformat(),
            'customer_id': context.get('execution_id'),
            'sequence_number': follow_up_strategy.get('sequence_number', 1)
        }
        
        # Save to database
        self.save_stage_result(context, follow_up_data)
        
        result = self.create_success_result(follow_up_data, context)
        # Logging handled by execute_with_timing wrapper
        
        return result

    def _analyze_interaction_history(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze interaction history to understand customer engagement and response patterns.
        
        Args:
            context: Execution context
            
        Returns:
            Interaction analysis results
        """
        try:
            input_data = context.get('input_data', {})
            execution_id = context.get('execution_id')
            
            # Get data manager for database operations
            data_manager = self.get_data_manager()
            
            # Get previous email drafts and interactions for this customer
            previous_drafts = data_manager.get_email_drafts_by_execution(execution_id)
            
            # Analyze interaction patterns
            interaction_analysis = {
                'total_emails_sent': 0,
                'total_follow_ups': 0,
                'last_interaction_date': None,
                'days_since_last_interaction': 0,
                'response_received': False,
                'engagement_level': 'unknown',
                'interaction_timeline': [],
                'follow_up_sequence': [],
                'customer_sentiment': 'neutral',
                'recommended_approach': 'gentle_reminder'
            }
            
            # Count emails and follow-ups
            initial_emails = [d for d in previous_drafts if d.get('draft_type') == 'initial']
            follow_up_emails = [d for d in previous_drafts if d.get('draft_type') in ['follow_up', 'initial_rewrite']]
            
            interaction_analysis['total_emails_sent'] = len(initial_emails)
            interaction_analysis['total_follow_ups'] = len(follow_up_emails)
            
            # Determine last interaction
            all_emails = sorted(previous_drafts, key=lambda x: x.get('created_at', ''), reverse=True)
            if all_emails:
                last_email = all_emails[0]
                interaction_analysis['last_interaction_date'] = last_email.get('created_at')
                
                # Calculate days since last interaction
                try:
                    last_date = datetime.fromisoformat(last_email.get('created_at', '').replace('Z', '+00:00'))
                    days_diff = (datetime.now() - last_date.replace(tzinfo=None)).days
                    interaction_analysis['days_since_last_interaction'] = days_diff
                except:
                    interaction_analysis['days_since_last_interaction'] = 0
            
            # Analyze engagement level based on interaction patterns
            interaction_analysis['engagement_level'] = self._determine_engagement_level(interaction_analysis)
            
            # Determine customer sentiment (simplified - in real implementation, this could analyze responses)
            interaction_analysis['customer_sentiment'] = self._analyze_customer_sentiment(context, interaction_analysis)
            
            # Recommend approach based on analysis
            interaction_analysis['recommended_approach'] = self._recommend_follow_up_approach(interaction_analysis)
            
            # Create interaction timeline
            interaction_analysis['interaction_timeline'] = self._create_interaction_timeline(previous_drafts)
            
            return interaction_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze interaction history: {str(e)}")
            # Return default analysis
            return {
                'total_emails_sent': 0,
                'total_follow_ups': 0,
                'days_since_last_interaction': 0,
                'engagement_level': 'unknown',
                'customer_sentiment': 'neutral',
                'recommended_approach': 'gentle_reminder',
                'analysis_error': str(e)
            }

    def _determine_follow_up_strategy(self, interaction_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the appropriate follow-up strategy based on interaction analysis.
        
        Args:
            interaction_analysis: Results from interaction history analysis
            context: Execution context
            
        Returns:
            Follow-up strategy recommendations
        """
        try:
            total_follow_ups = interaction_analysis.get('total_follow_ups', 0)
            days_since_last = interaction_analysis.get('days_since_last_interaction', 0)
            engagement_level = interaction_analysis.get('engagement_level', 'unknown')
            customer_sentiment = interaction_analysis.get('customer_sentiment', 'neutral')
            
            strategy = {
                'should_follow_up': True,
                'sequence_number': total_follow_ups + 1,
                'strategy_type': 'gentle_reminder',
                'timing_recommendation': 'immediate',
                'approach_tone': 'professional',
                'content_focus': 'value_add',
                'reason': 'Standard follow-up sequence'
            }
            
            # Determine if follow-up should continue
            if total_follow_ups >= 5:
                strategy.update({
                    'should_follow_up': False,
                    'reason': 'Maximum follow-up attempts reached (5)',
                    'recommendation': 'Consider closing this lead or trying a different approach'
                })
                return strategy
            
            if customer_sentiment == 'negative':
                strategy.update({
                    'should_follow_up': False,
                    'reason': 'Customer sentiment is negative',
                    'recommendation': 'Respect customer preference and close follow-up sequence'
                })
                return strategy
            
            if days_since_last < 3 and total_follow_ups > 0:
                strategy.update({
                    'should_follow_up': False,
                    'reason': 'Too soon since last interaction (less than 3 days)',
                    'recommendation': 'Wait at least 3 days between follow-ups'
                })
                return strategy
            
            # Determine strategy type based on sequence number
            if total_follow_ups == 0:
                strategy.update({
                    'strategy_type': 'gentle_reminder',
                    'content_focus': 'gentle_nudge',
                    'approach_tone': 'friendly',
                    'timing_recommendation': 'after_5_days'
                })
            elif total_follow_ups == 1:
                strategy.update({
                    'strategy_type': 'value_add',
                    'content_focus': 'additional_insights',
                    'approach_tone': 'helpful',
                    'timing_recommendation': 'after_1_week'
                })
            elif total_follow_ups == 2:
                strategy.update({
                    'strategy_type': 'alternative_approach',
                    'content_focus': 'different_angle',
                    'approach_tone': 'consultative',
                    'timing_recommendation': 'after_2_weeks'
                })
            elif total_follow_ups == 3:
                strategy.update({
                    'strategy_type': 'final_attempt',
                    'content_focus': 'last_chance',
                    'approach_tone': 'respectful_closure',
                    'timing_recommendation': 'after_1_month'
                })
            else:
                strategy.update({
                    'strategy_type': 'graceful_close',
                    'content_focus': 'relationship_maintenance',
                    'approach_tone': 'professional_farewell',
                    'timing_recommendation': 'final_attempt'
                })
            
            # Adjust based on engagement level
            if engagement_level == 'high':
                strategy['approach_tone'] = 'enthusiastic'
                strategy['content_focus'] = 'detailed_proposal'
            elif engagement_level == 'low':
                strategy['approach_tone'] = 'gentle'
                strategy['content_focus'] = 'simple_question'
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"Failed to determine follow-up strategy: {str(e)}")
            return {
                'should_follow_up': True,
                'sequence_number': 1,
                'strategy_type': 'gentle_reminder',
                'approach_tone': 'professional',
                'content_focus': 'value_add',
                'reason': 'Default strategy due to analysis error'
            }

    def _generate_follow_up_drafts(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], 
                                 scoring_data: Dict[str, Any], interaction_analysis: Dict[str, Any], 
                                 follow_up_strategy: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate multiple follow-up email drafts based on strategy and interaction history.
        
        Args:
            customer_data: Customer information
            recommended_product: Product recommendation
            scoring_data: Lead scoring results
            interaction_analysis: Interaction history analysis
            follow_up_strategy: Follow-up strategy
            context: Execution context
            
        Returns:
            List of generated follow-up drafts
        """
        if self.is_dry_run():
            return self._get_mock_follow_up_drafts(customer_data, follow_up_strategy, context)
        
        try:
            input_data = context.get('input_data', {})
            company_info = customer_data.get('companyInfo', {})
            contact_info = customer_data.get('primaryContact', {})
            
            # Define follow-up approaches based on strategy
            follow_up_approaches = self._get_follow_up_approaches(follow_up_strategy)
            
            generated_drafts = []
            
            for approach in follow_up_approaches:
                try:
                    # Generate follow-up content for this approach
                    email_content = self._generate_single_follow_up_draft(
                        customer_data, recommended_product, scoring_data,
                        interaction_analysis, follow_up_strategy, approach, context
                    )
                    
                    # Generate subject lines for this approach
                    subject_lines = self._generate_follow_up_subject_lines(
                        customer_data, recommended_product, interaction_analysis, 
                        follow_up_strategy, approach, context
                    )
                    
                    draft_id = f"uuid:{str(uuid.uuid4())}"
                    draft_approach = approach['name']
                    draft_type = "followup"
                    
                    draft = {
                        'draft_id': draft_id,
                        'approach': approach['name'],
                        'strategy_type': follow_up_strategy.get('strategy_type', 'gentle_reminder'),
                        'sequence_number': follow_up_strategy.get('sequence_number', 1),
                        'tone': approach['tone'],
                        'focus': approach['focus'],
                        'subject_lines': subject_lines,
                        'email_body': email_content,
                        'call_to_action': self._extract_call_to_action(email_content),
                        'personalization_score': self._calculate_personalization_score(email_content, customer_data),
                        'follow_up_context': {
                            'days_since_last_interaction': interaction_analysis.get('days_since_last_interaction', 0),
                            'total_previous_attempts': interaction_analysis.get('total_follow_ups', 0),
                            'engagement_level': interaction_analysis.get('engagement_level', 'unknown'),
                            'recommended_timing': follow_up_strategy.get('timing_recommendation', 'immediate')
                        },
                        'generated_at': datetime.now().isoformat(),
                        'status': 'draft',
                        'metadata': {
                            'customer_company': company_info.get('name', 'Unknown'),
                            'contact_name': contact_info.get('name', 'Unknown'),
                            'recommended_product': recommended_product.get('product_name', 'Unknown'),
                            'follow_up_type': follow_up_strategy.get('strategy_type', 'gentle_reminder'),
                            'generation_method': 'llm_powered_followup'
                        }
                    }

                    priority_order = self._get_draft_priority_order(
                        draft,
                        position=len(generated_drafts) + 1
                    )
                    draft['priority_order'] = priority_order
                    draft['metadata']['priority_order'] = priority_order
                    
                    generated_drafts.append(draft)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to generate follow-up draft for approach {approach['name']}: {str(e)}")
                    continue
            
            if not generated_drafts:
                # Fallback to simple template if all LLM generations fail
                self.logger.warning("All LLM follow-up draft generations failed, using fallback template")
                return self._generate_fallback_follow_up_draft(customer_data, recommended_product, follow_up_strategy, context)
            
            self.logger.info(f"Generated {len(generated_drafts)} follow-up drafts successfully")
            return generated_drafts
            
        except Exception as e:
            self.logger.error(f"Follow-up draft generation failed: {str(e)}")
            return self._generate_fallback_follow_up_draft(customer_data, recommended_product, follow_up_strategy, context)

    def _get_follow_up_approaches(self, follow_up_strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get follow-up approaches based on strategy type.
        
        Args:
            follow_up_strategy: Follow-up strategy
            
        Returns:
            List of follow-up approaches
        """
        strategy_type = follow_up_strategy.get('strategy_type', 'gentle_reminder')
        sequence_number = follow_up_strategy.get('sequence_number', 1)
        
        if strategy_type == 'gentle_reminder':
            return [
                {
                    'name': 'friendly_check_in',
                    'tone': 'friendly and casual',
                    'focus': 'gentle reminder with soft touch',
                    'length': 'short'
                },
                {
                    'name': 'professional_follow_up',
                    'tone': 'professional and respectful',
                    'focus': 'polite follow-up on previous conversation',
                    'length': 'medium'
                }
            ]
        elif strategy_type == 'value_add':
            return [
                {
                    'name': 'insights_sharing',
                    'tone': 'helpful and informative',
                    'focus': 'sharing valuable insights or resources',
                    'length': 'medium'
                },
                {
                    'name': 'industry_trends',
                    'tone': 'expert and consultative',
                    'focus': 'relevant industry trends and opportunities',
                    'length': 'detailed'
                }
            ]
        elif strategy_type == 'alternative_approach':
            return [
                {
                    'name': 'different_angle',
                    'tone': 'creative and engaging',
                    'focus': 'new perspective or different value proposition',
                    'length': 'medium'
                },
                {
                    'name': 'case_study_approach',
                    'tone': 'evidence-based and compelling',
                    'focus': 'success stories and social proof',
                    'length': 'detailed'
                }
            ]
        elif strategy_type == 'final_attempt':
            return [
                {
                    'name': 'respectful_final_reach',
                    'tone': 'respectful and understanding',
                    'focus': 'final attempt with graceful exit option',
                    'length': 'short'
                }
            ]
        else:  # graceful_close
            return [
                {
                    'name': 'graceful_farewell',
                    'tone': 'professional and gracious',
                    'focus': 'maintaining relationship for future opportunities',
                    'length': 'short'
                }
            ]

    def _generate_single_follow_up_draft(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any],
                                       scoring_data: Dict[str, Any], interaction_analysis: Dict[str, Any],
                                       follow_up_strategy: Dict[str, Any], approach: Dict[str, Any], 
                                       context: Dict[str, Any]) -> str:
        """
        Generate a single follow-up email draft using LLM with specific approach.
        
        Args:
            customer_data: Customer information
            recommended_product: Product recommendation
            scoring_data: Lead scoring results
            interaction_analysis: Interaction history analysis
            follow_up_strategy: Follow-up strategy
            approach: Specific approach for this draft
            context: Execution context
            
        Returns:
            Generated follow-up email content
        """
        try:
            input_data = context.get('input_data', {})
            company_info = customer_data.get('companyInfo', {})
            contact_info = customer_data.get('primaryContact', {})
            pain_points = customer_data.get('painPoints', [])
            
            # Prepare context for LLM
            follow_up_context = {
                'company_name': company_info.get('name', 'the company'),
                'contact_name': contact_info.get('name', 'there'),
                'contact_title': contact_info.get('title', ''),
                'industry': company_info.get('industry', 'technology'),
                'main_pain_points': [p.get('description', '') for p in pain_points[:3]],
                'recommended_product': recommended_product.get('product_name', 'our solution'),
                'sender_name': input_data.get('staff_name', 'Sales Team'),
                'sender_company': input_data.get('org_name', 'Our Company'),
                'sequence_number': follow_up_strategy.get('sequence_number', 1),
                'days_since_last': interaction_analysis.get('days_since_last_interaction', 0),
                'total_attempts': interaction_analysis.get('total_follow_ups', 0),
                'strategy_type': follow_up_strategy.get('strategy_type', 'gentle_reminder'),
                'approach_tone': approach.get('tone', 'professional'),
                'approach_focus': approach.get('focus', 'follow-up'),
                'approach_length': approach.get('length', 'medium')
            }
            
            # Create LLM prompt for follow-up generation
            prompt = self._create_follow_up_generation_prompt(follow_up_context, approach)
            
            # Generate follow-up using LLM
            email_content = self.call_llm(
                prompt=prompt,
                temperature=0.7,
                max_tokens=800
            )
            
            # Clean and validate the generated content
            cleaned_content = self._clean_email_content(email_content)
            
            return cleaned_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate single follow-up draft: {str(e)}")
            return self._generate_template_follow_up_email(customer_data, recommended_product, follow_up_strategy, approach, context)

    def _create_follow_up_generation_prompt(self, follow_up_context: Dict[str, Any], approach: Dict[str, Any]) -> str:
        """
        Create LLM prompt for follow-up email generation.
        
        Args:
            follow_up_context: Context for follow-up generation
            approach: Specific approach details
            
        Returns:
            LLM prompt for follow-up generation
        """
        
        pain_points_text = ""
        if follow_up_context['main_pain_points']:
            pain_points_text = f"Their key challenges: {', '.join(follow_up_context['main_pain_points'])}"
        
        # Create context about previous interactions
        interaction_context = f"""
FOLLOW-UP CONTEXT:
- This is follow-up #{follow_up_context['sequence_number']}
- {follow_up_context['days_since_last']} days since last interaction
- Total previous attempts: {follow_up_context['total_attempts']}
- Follow-up strategy: {follow_up_context['strategy_type']}"""
        
        prompt = f"""Generate a personalized follow-up email with the following specifications:

CUSTOMER INFORMATION:
- Company: {follow_up_context['company_name']}
- Contact: {follow_up_context['contact_name']} ({follow_up_context['contact_title']})
- Industry: {follow_up_context['industry']}
{pain_points_text}

OUR OFFERING:
- Product/Solution: {follow_up_context['recommended_product']}

SENDER INFORMATION:
- Sender: {follow_up_context['sender_name']}
- Company: {follow_up_context['sender_company']}

{interaction_context}

EMAIL APPROACH:
- Tone: {follow_up_context['approach_tone']}
- Focus: {follow_up_context['approach_focus']}
- Length: {follow_up_context['approach_length']}

FOLLOW-UP REQUIREMENTS:
1. Reference that this is a follow-up (don't repeat everything from initial email)
2. Acknowledge the time that has passed since last contact
3. Provide new value or perspective (don't just repeat the same message)
4. Be respectful of their time and attention
5. Include a clear, low-pressure call-to-action
6. Match the {follow_up_context['approach_tone']} tone
7. Focus on {follow_up_context['approach_focus']}
8. Keep it {follow_up_context['approach_length']} in length

STRATEGY-SPECIFIC GUIDELINES:
- If gentle_reminder: Be soft, friendly, and non-pushy
- If value_add: Provide genuine insights, resources, or industry information
- If alternative_approach: Try a different angle or value proposition
- If final_attempt: Be respectful and offer a graceful exit
- If graceful_close: Focus on maintaining the relationship for future

Generate only the email content, no additional commentary:"""

        return prompt

    # Import utility methods from initial outreach (they're the same)
    def _extract_call_to_action(self, email_content: str) -> str:
        """Extract the main call-to-action from email content."""
        # Look for common CTA patterns
        cta_patterns = [
            r"Would you be (?:interested in|available for|open to) ([^?]+\?)",
            r"Can we schedule ([^?]+\?)",
            r"I'd love to ([^.]+\.)",
            r"Let's ([^.]+\.)",
            r"Would you like to ([^?]+\?)"
        ]
        
        import re
        for pattern in cta_patterns:
            match = re.search(pattern, email_content, re.IGNORECASE)
            if match:
                return match.group(0)
        
        # Fallback: look for question marks
        sentences = email_content.split('.')
        for sentence in sentences:
            if '?' in sentence:
                return sentence.strip() + ('.' if not sentence.strip().endswith('?') else '')
        
        return "Would you be interested in learning more?"

    def _calculate_personalization_score(self, email_content: str, customer_data: Dict[str, Any]) -> int:
        """Calculate personalization score based on customer data usage."""
        score = 0
        company_info = customer_data.get('companyInfo', {})
        contact_info = customer_data.get('primaryContact', {})
        
        # Check for company name usage
        if company_info.get('name', '').lower() in email_content.lower():
            score += 25
        
        # Check for contact name usage
        if contact_info.get('name', '').lower() in email_content.lower():
            score += 25
        
        # Check for industry mention
        if company_info.get('industry', '').lower() in email_content.lower():
            score += 20
        
        # Check for pain points reference
        pain_points = customer_data.get('painPoints', [])
        for pain_point in pain_points:
            if any(keyword.lower() in email_content.lower() for keyword in pain_point.get('description', '').split()[:3]):
                score += 15
                break
        
        # Check for specific details (company size, location, etc.)
        if any(detail in email_content.lower() for detail in [
            company_info.get('size', '').lower(),
            company_info.get('location', '').lower()
        ] if detail):
            score += 15
        
        return min(score, 100)

    def _get_draft_priority_order(self, draft: Dict[str, Any], position: int = 1) -> int:
        """Compute a priority order for follow-up drafts."""
        try:
            explicit = int(draft.get('priority_order'))
            if explicit > 0:
                return explicit
        except (TypeError, ValueError):
            pass

        base_priority = max(1, position)
        try:
            personalization_score = float(draft.get('personalization_score', 0))
        except (TypeError, ValueError):
            personalization_score = 0

        if personalization_score >= 80:
            return base_priority
        if personalization_score >= 60:
            return base_priority + 1
        return base_priority + 2

    def _remove_tagline_block(self, content: str) -> str:
        """Remove tagline rows (e.g., 'Tagline: ...') that often follow the greeting."""
        if not content:
            return ''

        import re

        tagline_pattern = re.compile(r'^\s*(tag\s*line|tagline)\b[:\-]?', re.IGNORECASE)
        lines = content.splitlines()
        filtered = [line for line in lines if not tagline_pattern.match(line)]
        return '\n'.join(filtered).strip() if len(filtered) != len(lines) else content

    def _clean_email_content(self, raw_content: str) -> str:
        """Clean and validate generated email content."""
        # Remove any unwanted prefixes or suffixes
        content = raw_content.strip()
        
        # Remove common LLM artifacts
        artifacts_to_remove = [
            "Here's the follow-up email:",
            "Here is the follow-up email:",
            "Follow-up email content:",
            "Generated follow-up email:",
            "Subject:",
            "Email:"
        ]
        
        for artifact in artifacts_to_remove:
            if content.startswith(artifact):
                content = content[len(artifact):].strip()

        content = self._remove_tagline_block(content)

        # Ensure proper email structure
        if not content.startswith(('Dear', 'Hi', 'Hello', 'Greetings')):
            # Add a greeting if missing
            content = f"Hi there,\n\n{content}"
        
        # Ensure proper closing
        if not any(closing in content.lower() for closing in ['best regards', 'sincerely', 'best', 'thanks']):
            content += "\n\nBest regards"
        
        return content

    def _handle_draft_rewrite(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle draft_rewrite action - Modify existing follow-up draft.
        
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
            raise ValueError(f"Follow-up draft not found: {selected_draft_id}")
        
        # Get customer data for context
        customer_data = self._get_customer_data(context)
        scoring_data = self._get_scoring_data(context)
        interaction_analysis = self._analyze_interaction_history(context)
        
        # Rewrite the draft based on reason
        rewritten_draft = self._rewrite_follow_up_draft(existing_draft, reason, customer_data, interaction_analysis, context)
        
        # Save the rewritten draft
        saved_draft = self._save_rewritten_follow_up_draft(context, rewritten_draft, selected_draft_id)
        
        # Prepare output
        follow_up_data = {
            'action': 'draft_rewrite',
            'status': 'follow_up_draft_rewritten',
            'original_draft_id': selected_draft_id,
            'rewritten_draft': saved_draft,
            'rewrite_reason': reason,
            'generation_timestamp': datetime.now().isoformat(),
            'customer_id': context.get('execution_id')
        }
        
        # Save to database
        self.save_stage_result(context, follow_up_data)
        
        result = self.create_success_result(follow_up_data, context)
        # Logging handled by execute_with_timing wrapper
        
        return result

    def _handle_send(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle send action - Send approved follow-up draft to recipient.
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result with send status
        """
        input_data = context.get('input_data', {})
        selected_draft_id = input_data.get('selected_draft_id')
        recipient_address = input_data.get('recipient_address')
        recipient_name = input_data.get('recipient_name', 'Dear Customer')
        send_immediately = input_data.get('send_immediately', False)
        
        # Retrieve the draft to send
        draft_to_send = self._get_draft_by_id(selected_draft_id)
        if not draft_to_send:
            raise ValueError(f"Follow-up draft not found: {selected_draft_id}")
        
        # Check if we should send immediately or schedule
        if send_immediately:
            # Send immediately
            send_result = self._send_follow_up_email(draft_to_send, recipient_address, recipient_name, context)
        else:
            # Schedule for optimal timing
            send_result = self._schedule_follow_up_email(draft_to_send, recipient_address, recipient_name, context)
        
        # Prepare output
        follow_up_data = {
            'action': 'send',
            'status': 'follow_up_sent' if send_immediately else 'follow_up_scheduled',
            'draft_id': selected_draft_id,
            'recipient_address': recipient_address,
            'recipient_name': recipient_name,
            'send_result': send_result,
            'sent_immediately': send_immediately,
            'send_timestamp': datetime.now().isoformat(),
            'customer_id': context.get('execution_id')
        }
        
        # Save to database
        self.save_stage_result(context, follow_up_data)
        
        result = self.create_success_result(follow_up_data, context)
        # Logging handled by execute_with_timing wrapper
        
        return result

    def _handle_close(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle close action - Close follow-up sequence.
        
        Args:
            context: Execution context
            
        Returns:
            Stage execution result with close status
        """
        input_data = context.get('input_data', {})
        reason = input_data.get('reason', 'Follow-up sequence closed')
        
        # Prepare output
        follow_up_data = {
            'action': 'close',
            'status': 'follow_up_closed',
            'close_reason': reason,
            'closed_timestamp': datetime.now().isoformat(),
            'customer_id': context.get('execution_id')
        }
        
        # Save to database
        self.save_stage_result(context, follow_up_data)
        
        result = self.create_success_result(follow_up_data, context)
        # Logging handled by execute_with_timing wrapper
        
        return result

    def _schedule_follow_up_email(self, draft: Dict[str, Any], recipient_address: str, recipient_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schedule follow-up email event in database for external app to handle.
        
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
            reminder_context = self._build_follow_up_reminder_context(
                draft,
                recipient_address,
                recipient_name,
                context
            )
            
            # Schedule the follow-up email event
            schedule_result = scheduler.schedule_email_event(
                draft_id=draft.get('draft_id'),
                recipient_address=recipient_address,
                recipient_name=recipient_name,
                org_id=input_data.get('org_id', 'default'),
                team_id=input_data.get('team_id'),
                customer_timezone=input_data.get('customer_timezone'),
                email_type='follow_up',
                send_immediately=send_immediately,
                reminder_context=reminder_context
            )
            
            if schedule_result['success']:
                self.logger.info(f"Follow-up email event scheduled successfully: {schedule_result['event_id']} for {schedule_result['scheduled_time']}")
                return {
                    'success': True,
                    'message': f'Follow-up email event scheduled for {schedule_result["scheduled_time"]}',
                    'event_id': schedule_result['event_id'],
                    'scheduled_time': schedule_result['scheduled_time'],
                    'service': 'Database Event Scheduler'
                }
            else:
                self.logger.error(f"Follow-up email event scheduling failed: {schedule_result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'message': f'Follow-up email event scheduling failed: {schedule_result.get("error", "Unknown error")}',
                    'service': 'Database Event Scheduler'
                }
                
        except Exception as e:
            self.logger.error(f"Follow-up email scheduling failed: {str(e)}")
            return {
                'success': False,
                'message': f'Follow-up email scheduling failed: {str(e)}',
                'error': str(e)
            } 

    def _build_follow_up_reminder_context(
        self,
        draft: Dict[str, Any],
        recipient_address: str,
        recipient_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build reminder_task metadata for scheduled follow-up emails.
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
        interaction_type = input_data.get('interaction_type', 'follow_up')
        follow_up_iteration = input_data.get('current_follow_up_time') or 1
        reminder_room = self.config.get('reminder_room_id') or input_data.get('reminder_room_id')
        draft_id = draft.get('draft_id') or 'unknown_draft'
        product_name = draft.get('product_name') or input_data.get('product_name')

        customextra = {
            'reminder_content': 'follow_up',
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
            'interaction_type': interaction_type,
            'action_status': 'scheduled',
            'current_follow_up_time': follow_up_iteration,
            'draft_id': draft_id,
            'import_uuid': f"{org_id}_{customer_id}_{task_id}_{draft_id}"
        }

        if product_name:
            customextra['product_name'] = product_name
        if draft.get('approach'):
            customextra['approach'] = draft.get('approach')
        if draft.get('mail_tone'):
            customextra['mail_tone'] = draft.get('mail_tone')
        if draft.get('message_type'):
            customextra['message_type'] = draft.get('message_type')

        return {
            'status': 'published',
            'task': f"FuseSell follow-up {org_id}_{customer_id} - {task_id}",
            'tags': ['fusesell', 'follow-up'],
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
   # Data access methods (similar to initial outreach)
    def _get_customer_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get customer data from previous stages or input."""
        stage_results = context.get('stage_results', {})
        
        # Try to get from data preparation stage first
        if 'data_preparation' in stage_results:
            return stage_results['data_preparation']
        
        # Fallback to input data
        input_data = context.get('input_data', {})
        return {
            'companyInfo': input_data.get('companyInfo', {}),
            'primaryContact': input_data.get('primaryContact', {}),
            'painPoints': input_data.get('painPoints', [])
        }

    def _get_scoring_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get scoring data from previous stages."""
        stage_results = context.get('stage_results', {})
        return stage_results.get('lead_scoring', {})

    def _get_recommended_product(self, scoring_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the recommended product from scoring data."""
        product_scores = scoring_data.get('product_scores', [])
        if product_scores:
            # Return the highest scoring product
            best_product = max(product_scores, key=lambda x: x.get('overall_score', 0))
            return best_product
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

    def _get_draft_by_id(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve follow-up draft by ID from database."""
        if self.is_dry_run():
            return {
                'draft_id': draft_id,
                'subject_lines': ['Mock Follow-up Subject Line'],
                'email_body': 'Mock follow-up email content for testing purposes.',
                'approach': 'mock',
                'tone': 'professional',
                'status': 'mock',
                'call_to_action': 'Mock follow-up call to action',
                'personalization_score': 75,
                'sequence_number': 1
            }
        
        try:
            # Get data manager for database operations
            data_manager = self.get_data_manager()
            
            # Query database for draft
            draft_record = data_manager.get_email_draft_by_id(draft_id)
            
            if not draft_record:
                self.logger.warning(f"Follow-up draft not found in database: {draft_id}")
                return None
            
            # Parse metadata
            metadata = {}
            if draft_record.get('metadata'):
                try:
                    metadata = json.loads(draft_record['metadata'])
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse metadata for follow-up draft {draft_id}")
            
            # Reconstruct draft object
            draft = {
                'draft_id': draft_record['draft_id'],
                'execution_id': draft_record['execution_id'],
                'customer_id': draft_record['customer_id'],
                'subject_lines': metadata.get('all_subject_lines', [draft_record['subject']]),
                'email_body': draft_record['content'],
                'approach': metadata.get('approach', 'unknown'),
                'tone': metadata.get('tone', 'professional'),
                'focus': metadata.get('focus', 'general'),
                'call_to_action': metadata.get('call_to_action', ''),
                'personalization_score': metadata.get('personalization_score', 0),
                'status': draft_record['status'],
                'version': draft_record['version'],
                'draft_type': draft_record['draft_type'],
                'sequence_number': metadata.get('sequence_number', 1),
                'created_at': draft_record['created_at'],
                'updated_at': draft_record['updated_at'],
                'metadata': metadata
            }
            
            self.logger.info(f"Retrieved follow-up draft {draft_id} from database")
            return draft
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve follow-up draft {draft_id}: {str(e)}")
            return None

    # Helper methods for analysis
    def _determine_engagement_level(self, interaction_analysis: Dict[str, Any]) -> str:
        """Determine customer engagement level based on interaction patterns."""
        total_emails = interaction_analysis.get('total_emails_sent', 0)
        total_follow_ups = interaction_analysis.get('total_follow_ups', 0)
        days_since_last = interaction_analysis.get('days_since_last_interaction', 0)
        
        # Simple engagement scoring
        if total_emails == 0:
            return 'unknown'
        elif days_since_last <= 3 and total_follow_ups < 2:
            return 'high'
        elif days_since_last <= 7 and total_follow_ups < 3:
            return 'medium'
        else:
            return 'low'

    def _analyze_customer_sentiment(self, context: Dict[str, Any], interaction_analysis: Dict[str, Any]) -> str:
        """Analyze customer sentiment (simplified - could be enhanced with response analysis)."""
        # In a real implementation, this would analyze actual customer responses
        # For now, we'll use simple heuristics
        total_follow_ups = interaction_analysis.get('total_follow_ups', 0)
        
        if total_follow_ups >= 4:
            return 'negative'  # Too many follow-ups without response
        elif total_follow_ups >= 2:
            return 'neutral'   # Some follow-ups, neutral response
        else:
            return 'positive'  # Early in sequence, assume positive

    def _recommend_follow_up_approach(self, interaction_analysis: Dict[str, Any]) -> str:
        """Recommend follow-up approach based on interaction analysis."""
        engagement_level = interaction_analysis.get('engagement_level', 'unknown')
        total_follow_ups = interaction_analysis.get('total_follow_ups', 0)
        
        if total_follow_ups == 0:
            return 'gentle_reminder'
        elif total_follow_ups == 1:
            return 'value_add'
        elif total_follow_ups == 2:
            return 'alternative_approach'
        elif total_follow_ups >= 3:
            return 'final_attempt'
        else:
            return 'gentle_reminder'

    def _create_interaction_timeline(self, previous_drafts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create interaction timeline from previous drafts."""
        timeline = []
        
        for draft in sorted(previous_drafts, key=lambda x: x.get('created_at', '')):
            timeline.append({
                'date': draft.get('created_at'),
                'type': draft.get('draft_type', 'unknown'),
                'draft_id': draft.get('draft_id'),
                'status': draft.get('status', 'unknown')
            })
        
        return timeline

    def _create_customer_summary(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create customer summary for follow-up context."""
        company_info = customer_data.get('companyInfo', {})
        contact_info = customer_data.get('primaryContact', {})
        
        return {
            'company_name': company_info.get('name', 'Unknown'),
            'industry': company_info.get('industry', 'Unknown'),
            'contact_name': contact_info.get('name', 'Unknown'),
            'contact_email': contact_info.get('email', 'Unknown'),
            'follow_up_context': 'Generated for follow-up sequence'
        }

    # Mock and fallback methods
    def _get_mock_follow_up_drafts(self, customer_data: Dict[str, Any], follow_up_strategy: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get mock follow-up drafts for dry run."""
        company_info = customer_data.get('companyInfo', {})
        
        mock_draft = {
            'draft_id': 'mock_followup_001',
            'approach': 'gentle_reminder',
            'strategy_type': follow_up_strategy.get('strategy_type', 'gentle_reminder'),
            'sequence_number': follow_up_strategy.get('sequence_number', 1),
            'tone': 'friendly and professional',
            'focus': 'gentle follow-up',
            'subject_lines': [
                f"Following up on our conversation - {company_info.get('name', 'Test Company')}",
                f"Quick check-in with {company_info.get('name', 'Test Company')}",
                f"Thoughts on our discussion?"
            ],
            'email_body': f"""[DRY RUN] Mock follow-up email content for {company_info.get('name', 'Test Company')}

This is a mock follow-up email that would be generated for testing purposes. In a real execution, this would contain contextual follow-up content based on the interaction history and follow-up strategy.""",
            'call_to_action': 'Mock follow-up call to action',
            'personalization_score': 80,
            'generated_at': datetime.now().isoformat(),
            'status': 'mock',
            'metadata': {
                'generation_method': 'mock_data',
                'note': 'This is mock data for dry run testing'
            }
        }

        mock_draft['priority_order'] = self._get_draft_priority_order(mock_draft, position=1)
        mock_draft['metadata']['priority_order'] = mock_draft['priority_order']

        return [mock_draft]

    def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        Validate input data for follow-up stage.
        
        Args:
            context: Execution context
            
        Returns:
            True if input is valid
        """
        # Follow-up stage can work with minimal input since it analyzes history
        return True

    def _save_follow_up_drafts(self, context: Dict[str, Any], follow_up_drafts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Save follow-up drafts to database and files."""
        try:
            execution_id = context.get('execution_id')
            saved_drafts = []
            
            # Get data manager for database operations
            data_manager = self.get_data_manager()
            
            for draft in follow_up_drafts:
                try:
                    priority_order = draft.get('priority_order')
                    if not isinstance(priority_order, int) or priority_order < 1:
                        priority_order = self._get_draft_priority_order(
                            draft,
                            position=len(saved_drafts) + 1
                        )
                        draft['priority_order'] = priority_order
                        draft.setdefault('metadata', {})['priority_order'] = priority_order

                    # Prepare draft data for database
                    draft_data = {
                        'draft_id': draft['draft_id'],
                        'execution_id': execution_id,
                        'customer_id': execution_id,  # Using execution_id as customer_id for now
                        'subject': draft['subject_lines'][0] if draft['subject_lines'] else 'Follow-up',
                        'content': draft['email_body'],
                        'draft_type': 'follow_up',
                        'version': 1,
                        'status': 'draft',
                        'metadata': json.dumps({
                            'approach': draft.get('approach', 'unknown'),
                            'strategy_type': draft.get('strategy_type', 'gentle_reminder'),
                            'sequence_number': draft.get('sequence_number', 1),
                            'tone': draft.get('tone', 'professional'),
                            'focus': draft.get('focus', 'general'),
                            'all_subject_lines': draft.get('subject_lines', []),
                            'call_to_action': draft.get('call_to_action', ''),
                            'personalization_score': draft.get('personalization_score', 0),
                            'follow_up_context': draft.get('follow_up_context', {}),
                            'generation_method': 'llm_powered_followup',
                            'priority_order': priority_order,
                            'generated_at': draft.get('generated_at', datetime.now().isoformat())
                        })
                    }
                    
                    # Save to database
                    if not self.is_dry_run():
                        data_manager.save_email_draft(draft_data)
                        self.logger.info(f"Saved follow-up draft {draft['draft_id']} to database")
                    
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
                    self.logger.error(f"Failed to save individual follow-up draft {draft.get('draft_id', 'unknown')}: {str(e)}")
                    # Still add to saved_drafts but mark as failed
                    draft_with_context = draft.copy()
                    draft_with_context['execution_id'] = execution_id
                    draft_with_context['save_error'] = str(e)
                    draft_with_context['database_saved'] = False
                    saved_drafts.append(draft_with_context)
            
            self.logger.info(f"Successfully saved {len([d for d in saved_drafts if d.get('database_saved', False)])} follow-up drafts to database")
            return saved_drafts
            
        except Exception as e:
            self.logger.error(f"Failed to save follow-up drafts: {str(e)}")
            # Return drafts with error information
            for draft in follow_up_drafts:
                draft['save_error'] = str(e)
                draft['database_saved'] = False
            return follow_up_drafts

    def _save_draft_to_file(self, execution_id: str, draft: Dict[str, Any]) -> str:
        """Save follow-up draft to file system as backup."""
        try:
            import os
            
            # Create drafts directory if it doesn't exist
            drafts_dir = os.path.join(self.config.get('data_dir', './fusesell_data'), 'drafts')
            os.makedirs(drafts_dir, exist_ok=True)
            
            # Create file path
            file_name = f"{execution_id}_{draft['draft_id']}_followup.json"
            file_path = os.path.join(drafts_dir, file_name)
            
            # Save draft to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(draft, f, indent=2, ensure_ascii=False)
            
            return f"drafts/{file_name}"
            
        except Exception as e:
            self.logger.warning(f"Failed to save follow-up draft to file: {str(e)}")
            return f"drafts/{execution_id}_{draft['draft_id']}_followup.json"

    def _generate_follow_up_subject_lines(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any],
                                        interaction_analysis: Dict[str, Any], follow_up_strategy: Dict[str, Any],
                                        approach: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Generate follow-up subject lines using LLM."""
        try:
            input_data = context.get('input_data', {})
            company_info = customer_data.get('companyInfo', {})
            
            prompt = f"""Generate 3 compelling follow-up email subject lines for {company_info.get('name', 'a company')} in the {company_info.get('industry', 'technology')} industry.

CONTEXT:
- This is follow-up #{follow_up_strategy.get('sequence_number', 1)}
- Days since last contact: {interaction_analysis.get('days_since_last_interaction', 0)}
- Follow-up strategy: {follow_up_strategy.get('strategy_type', 'gentle_reminder')}
- Target Company: {company_info.get('name', 'the company')}
- Our Solution: {recommended_product.get('product_name', 'our solution')}
- Approach Tone: {approach.get('tone', 'professional')}

REQUIREMENTS:
1. Keep subject lines under 50 characters
2. Make them appropriate for a follow-up (not initial contact)
3. Reference the passage of time appropriately
4. Match the {approach.get('tone', 'professional')} tone
5. Avoid being pushy or aggressive

Generate 3 subject lines, one per line, no numbering or bullets:"""

            response = self.call_llm(
                prompt=prompt,
                temperature=0.8,
                max_tokens=150
            )
            
            # Parse subject lines from response
            subject_lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            # Ensure we have at least 3 subject lines
            if len(subject_lines) < 3:
                subject_lines.extend(self._generate_fallback_follow_up_subject_lines(customer_data, follow_up_strategy))
            
            return subject_lines[:3]  # Return max 3 subject lines
            
        except Exception as e:
            self.logger.warning(f"Failed to generate follow-up subject lines: {str(e)}")
            return self._generate_fallback_follow_up_subject_lines(customer_data, follow_up_strategy)

    def _generate_fallback_follow_up_subject_lines(self, customer_data: Dict[str, Any], follow_up_strategy: Dict[str, Any]) -> List[str]:
        """Generate fallback follow-up subject lines using templates."""
        company_info = customer_data.get('companyInfo', {})
        company_name = company_info.get('name', 'Your Company')
        sequence_number = follow_up_strategy.get('sequence_number', 1)
        
        if sequence_number == 1:
            return [
                f"Following up on {company_name}",
                f"Quick check-in",
                f"Thoughts on our discussion?"
            ]
        elif sequence_number == 2:
            return [
                f"Additional insights for {company_name}",
                f"One more thought",
                f"Quick update for you"
            ]
        else:
            return [
                f"Final follow-up for {company_name}",
                f"Last check-in",
                f"Closing the loop"
            ]

    def _generate_fallback_follow_up_draft(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any], 
                                         follow_up_strategy: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fallback follow-up draft when LLM generation fails."""
        draft_id = f"uuid:{str(uuid.uuid4())}"
        draft_approach = "fallback"
        draft_type = "followup"
        
        fallback_draft = {
            'draft_id': draft_id,
            'approach': 'fallback_template',
            'strategy_type': follow_up_strategy.get('strategy_type', 'gentle_reminder'),
            'sequence_number': follow_up_strategy.get('sequence_number', 1),
            'tone': 'professional',
            'focus': 'general follow-up',
            'subject_lines': self._generate_fallback_follow_up_subject_lines(customer_data, follow_up_strategy),
            'email_body': self._generate_template_follow_up_email(customer_data, recommended_product, follow_up_strategy, {'tone': 'professional'}, context),
            'call_to_action': 'Would you be interested in continuing our conversation?',
            'personalization_score': 50,
            'generated_at': datetime.now().isoformat(),
            'status': 'draft',
            'metadata': {
                'generation_method': 'template_fallback',
                'note': 'Generated using template due to LLM failure'
            }
        }

        fallback_draft['priority_order'] = self._get_draft_priority_order(fallback_draft, position=1)
        fallback_draft['metadata']['priority_order'] = fallback_draft['priority_order']

        return [fallback_draft]

    def _generate_template_follow_up_email(self, customer_data: Dict[str, Any], recommended_product: Dict[str, Any],
                                         follow_up_strategy: Dict[str, Any], approach: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate follow-up email using template as fallback."""
        input_data = context.get('input_data', {})
        company_info = customer_data.get('companyInfo', {})
        contact_info = customer_data.get('primaryContact', {})
        sequence_number = follow_up_strategy.get('sequence_number', 1)
        
        if sequence_number == 1:
            return f"""Hi {contact_info.get('name', 'there')},

I wanted to follow up on my previous message regarding {company_info.get('name', 'your company')} and how our {recommended_product.get('product_name', 'solution')} might be able to help.

I understand you're probably busy, but I'd love to hear your thoughts when you have a moment.

Would you be available for a brief 15-minute call this week?

Best regards,
{input_data.get('staff_name', 'Sales Team')}
{input_data.get('org_name', 'Our Company')}"""
        else:
            return f"""Hi {contact_info.get('name', 'there')},

I hope this message finds you well. I wanted to reach out one more time regarding the opportunity to help {company_info.get('name', 'your company')} with {recommended_product.get('product_name', 'our solution')}.

If now isn't the right time, I completely understand. Please feel free to reach out whenever it makes sense for your team.

Best regards,
{input_data.get('staff_name', 'Sales Team')}
{input_data.get('org_name', 'Our Company')}"""

    def _rewrite_follow_up_draft(self, existing_draft: Dict[str, Any], reason: str, customer_data: Dict[str, Any], 
                               interaction_analysis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Rewrite existing follow-up draft based on reason using LLM."""
        try:
            if self.is_dry_run():
                rewritten = existing_draft.copy()
                rewritten['draft_id'] = f"uuid:{str(uuid.uuid4())}"
                rewritten['draft_approach'] = "rewrite"
                rewritten['draft_type'] = "followup_rewrite"
                rewritten['email_body'] = f"[DRY RUN - REWRITTEN: {reason}] " + existing_draft.get('email_body', '')
                rewritten['rewrite_reason'] = reason
                rewritten['rewritten_at'] = datetime.now().isoformat()
                return rewritten
            
            # Use similar logic to initial outreach rewrite but with follow-up context
            input_data = context.get('input_data', {})
            company_info = customer_data.get('companyInfo', {})
            contact_info = customer_data.get('primaryContact', {})
            
            # Create rewrite prompt with follow-up context
            rewrite_prompt = f"""Rewrite the following follow-up email based on the feedback provided. Keep the follow-up nature and context but address the specific concerns mentioned.

ORIGINAL FOLLOW-UP EMAIL:
{existing_draft.get('email_body', '')}

FEEDBACK/REASON FOR REWRITE:
{reason}

FOLLOW-UP CONTEXT:
- This is follow-up #{existing_draft.get('sequence_number', 1)}
- Days since last interaction: {interaction_analysis.get('days_since_last_interaction', 0)}
- Company: {company_info.get('name', 'the company')}
- Contact: {contact_info.get('name', 'the contact')}

REQUIREMENTS:
1. Address the feedback/reason provided
2. Maintain the follow-up context and tone
3. Keep it respectful and professional
4. Don't be pushy or aggressive
5. Include a clear but gentle call-to-action

Generate only the rewritten follow-up email content:"""

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
            rewritten['draft_type'] = "followup_rewrite"
            rewritten['email_body'] = cleaned_content
            rewritten['rewrite_reason'] = reason
            rewritten['rewritten_at'] = datetime.now().isoformat()
            rewritten['version'] = existing_draft.get('version', 1) + 1
            rewritten['call_to_action'] = self._extract_call_to_action(cleaned_content)
            rewritten['personalization_score'] = self._calculate_personalization_score(cleaned_content, customer_data)
            
            return rewritten
            
        except Exception as e:
            self.logger.error(f"Failed to rewrite follow-up draft: {str(e)}")
            # Fallback to simple modification
            rewritten = existing_draft.copy()
            rewritten['draft_id'] = f"uuid:{str(uuid.uuid4())}"
            rewritten['draft_approach'] = "rewrite"
            rewritten['draft_type'] = "followup_rewrite"
            rewritten['email_body'] = f"[REWRITTEN: {reason}]\n\n" + existing_draft.get('email_body', '')
            rewritten['rewrite_reason'] = reason
            rewritten['rewritten_at'] = datetime.now().isoformat()
            return rewritten

    def _save_rewritten_follow_up_draft(self, context: Dict[str, Any], rewritten_draft: Dict[str, Any], original_draft_id: str) -> Dict[str, Any]:
        """Save rewritten follow-up draft to database and file system."""
        # Use similar logic to initial outreach but mark as follow-up rewrite
        rewritten_draft['original_draft_id'] = original_draft_id
        rewritten_draft['execution_id'] = context.get('execution_id')
        rewritten_draft['draft_type'] = 'follow_up_rewrite'
        
        # Save using the same method as regular drafts
        saved_drafts = self._save_follow_up_drafts(context, [rewritten_draft])
        return saved_drafts[0] if saved_drafts else rewritten_draft

    def _send_follow_up_email(self, draft: Dict[str, Any], recipient_address: str, recipient_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send follow-up email immediately (similar to initial outreach but for follow-up)."""
        if self.is_dry_run():
            return {
                'success': True,
                'message': f'[DRY RUN] Would send follow-up email to {recipient_address}',
                'email_id': f'mock_followup_email_{uuid.uuid4().hex[:8]}'
            }

        try:
            # Use similar email sending logic as initial outreach
            # This would integrate with the RTA email service
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
                "instanceName": f"Send follow-up email to {recipient_name} ({recipient_address}) from {auto_interaction_config.get('from_name', input_data.get('org_name', 'Unknown'))}",
                "instanceID": f"{context.get('execution_id')}_{input_data.get('customer_id', 'unknown')}",
                "uuid": f"{context.get('execution_id')}_{input_data.get('customer_id', 'unknown')}",
                "action_type": auto_interaction_config.get('tool_type', 'email').lower(),
                "email": recipient_address,
                "number": auto_interaction_config.get('from_number', input_data.get('customer_phone', '')),
                "subject": draft['subject_lines'][0] if draft.get('subject_lines') else 'Follow-up',
                "content": draft.get('email_body', ''),
                "team_id": input_data.get('team_id', ''),
                "from_email": auto_interaction_config.get('from_email', ''),
                "from_name": auto_interaction_config.get('from_name', ''),
                "email_cc": auto_interaction_config.get('email_cc', ''),
                "email_bcc": auto_interaction_config.get('email_bcc', ''),
                "extraData": {
                    "org_id": input_data.get('org_id'),
                    "human_action_id": input_data.get('human_action_id', ''),
                    "email_tags": "gs_162_follow_up",
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
                    self.logger.info(f"Follow-up email sent successfully via RTA service: {execution_id}")
                    return {
                        'success': True,
                        'message': f'Follow-up email sent to {recipient_address}',
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
            self.logger.error(f"Follow-up email sending failed: {str(e)}")
            return {
                'success': False,
                'message': f'Follow-up email sending failed: {str(e)}',
                'error': str(e)
            }
