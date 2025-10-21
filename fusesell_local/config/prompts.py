"""
Prompt Manager for FuseSell Local
Handles LLM prompt templates and variable substitution
"""

from typing import Dict, Any, Optional
import re
import logging
from .settings import ConfigManager


class PromptManager:
    """
    Manages LLM prompts with template substitution and customization.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize prompt manager.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger("fusesell.prompts")
    
    def get_prompt(
        self, 
        stage: str, 
        prompt_key: str, 
        variables: Optional[Dict[str, Any]] = None,
        team_id: Optional[str] = None,
        language: str = "english"
    ) -> str:
        """
        Get formatted prompt for a specific stage and key.
        
        Args:
            stage: Pipeline stage name
            prompt_key: Specific prompt identifier
            variables: Variables for template substitution
            team_id: Optional team ID for customization
            language: Language for prompts
            
        Returns:
            Formatted prompt string
        """
        try:
            # Get prompts configuration
            prompts = self.config_manager.get_prompts(team_id, language)
            
            # Get stage-specific prompts
            stage_prompts = prompts.get(stage, {})
            if not stage_prompts:
                self.logger.warning(f"No prompts found for stage: {stage}")
                return ""
            
            # Get specific prompt template
            prompt_template = stage_prompts.get(prompt_key, "")
            if not prompt_template:
                self.logger.warning(f"No prompt found for {stage}.{prompt_key}")
                return ""
            
            # Apply variable substitution
            if variables:
                prompt_template = self._substitute_variables(prompt_template, variables)
            
            return prompt_template
            
        except Exception as e:
            self.logger.error(f"Failed to get prompt {stage}.{prompt_key}: {str(e)}")
            return ""
    
    def get_data_acquisition_prompts(self, variables: Dict[str, Any], **kwargs) -> Dict[str, str]:
        """Get all prompts for data acquisition stage."""
        return {
            'website_extraction': self.get_prompt('data_acquisition', 'website_extraction', variables, **kwargs),
            'business_card_ocr': self.get_prompt('data_acquisition', 'business_card_ocr', variables, **kwargs),
            'social_media_analysis': self.get_prompt('data_acquisition', 'social_media_analysis', variables, **kwargs),
            'data_consolidation': self.get_prompt('data_acquisition', 'data_consolidation', variables, **kwargs)
        }
    
    def get_data_preparation_prompts(self, variables: Dict[str, Any], **kwargs) -> Dict[str, str]:
        """Get all prompts for data preparation stage."""
        return {
            'extract_company_info': self.get_prompt('data_preparation', 'extract_company_info', variables, **kwargs),
            'identify_pain_points': self.get_prompt('data_preparation', 'identify_pain_points', variables, **kwargs),
            'financial_analysis': self.get_prompt('data_preparation', 'financial_analysis', variables, **kwargs),
            'development_plans': self.get_prompt('data_preparation', 'development_plans', variables, **kwargs),
            'technology_analysis': self.get_prompt('data_preparation', 'technology_analysis', variables, **kwargs)
        }
    
    def get_lead_scoring_prompts(self, variables: Dict[str, Any], **kwargs) -> Dict[str, str]:
        """Get all prompts for lead scoring stage."""
        return {
            'evaluate_fit': self.get_prompt('lead_scoring', 'evaluate_fit', variables, **kwargs),
            'score_calculation': self.get_prompt('lead_scoring', 'score_calculation', variables, **kwargs),
            'competitive_analysis': self.get_prompt('lead_scoring', 'competitive_analysis', variables, **kwargs),
            'recommendation': self.get_prompt('lead_scoring', 'recommendation', variables, **kwargs)
        }
    
    def get_initial_outreach_prompts(self, variables: Dict[str, Any], **kwargs) -> Dict[str, str]:
        """Get all prompts for initial outreach stage."""
        return {
            'email_generation': self.get_prompt('initial_outreach', 'email_generation', variables, **kwargs),
            'subject_line': self.get_prompt('initial_outreach', 'subject_line', variables, **kwargs),
            'tone_adjustment': self.get_prompt('initial_outreach', 'tone_adjustment', variables, **kwargs),
            'personalization': self.get_prompt('initial_outreach', 'personalization', variables, **kwargs)
        }
    
    def get_follow_up_prompts(self, variables: Dict[str, Any], **kwargs) -> Dict[str, str]:
        """Get all prompts for follow-up stage."""
        return {
            'analyze_interaction': self.get_prompt('follow_up', 'analyze_interaction', variables, **kwargs),
            'generate_followup': self.get_prompt('follow_up', 'generate_followup', variables, **kwargs),
            'timing_analysis': self.get_prompt('follow_up', 'timing_analysis', variables, **kwargs),
            'sequence_planning': self.get_prompt('follow_up', 'sequence_planning', variables, **kwargs)
        }
    
    def _substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Substitute variables in prompt template.
        
        Args:
            template: Prompt template with placeholders
            variables: Variables to substitute
            
        Returns:
            Template with variables substituted
        """
        try:
            # Handle nested dictionary access (e.g., {customer.name})
            def replace_nested(match):
                var_path = match.group(1)
                value = self._get_nested_value(variables, var_path)
                return str(value) if value is not None else f"{{{var_path}}}"
            
            # Replace {variable} and {nested.variable} patterns
            result = re.sub(r'\{([^}]+)\}', replace_nested, template)
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Variable substitution failed: {str(e)}")
            return template
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        Get value from nested dictionary using dot notation.
        
        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., 'customer.name')
            
        Returns:
            Value at path or None if not found
        """
        try:
            keys = path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            return value
            
        except Exception:
            return None
    
    def validate_prompt_variables(self, template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that all required variables are provided for a template.
        
        Args:
            template: Prompt template
            variables: Available variables
            
        Returns:
            Dictionary with validation results
        """
        # Find all variable placeholders
        placeholders = re.findall(r'\{([^}]+)\}', template)
        
        missing_vars = []
        available_vars = []
        
        for placeholder in placeholders:
            value = self._get_nested_value(variables, placeholder)
            if value is None:
                missing_vars.append(placeholder)
            else:
                available_vars.append(placeholder)
        
        return {
            'valid': len(missing_vars) == 0,
            'missing_variables': missing_vars,
            'available_variables': available_vars,
            'total_placeholders': len(placeholders)
        }
    
    def create_variable_context(self, 
                              customer_data: Optional[Dict[str, Any]] = None,
                              lead_scores: Optional[Dict[str, Any]] = None,
                              org_info: Optional[Dict[str, Any]] = None,
                              team_info: Optional[Dict[str, Any]] = None,
                              **additional_vars) -> Dict[str, Any]:
        """
        Create a comprehensive variable context for prompt substitution.
        
        Args:
            customer_data: Customer information
            lead_scores: Lead scoring results
            org_info: Organization information
            team_info: Team information
            **additional_vars: Additional variables
            
        Returns:
            Complete variable context
        """
        context = {}
        
        if customer_data:
            context['customer'] = customer_data
            context['company'] = customer_data.get('companyInfo', {})
            context['contact'] = customer_data.get('primaryContact', {})
            context['pain_points'] = customer_data.get('painPoints', [])
        
        if lead_scores:
            context['lead_scores'] = lead_scores
            context['top_score'] = max(lead_scores.get('scores', []), key=lambda x: x.get('score', 0), default={})
        
        if org_info:
            context['org'] = org_info
            context['seller'] = org_info
        
        if team_info:
            context['team'] = team_info
        
        # Add additional variables
        context.update(additional_vars)
        
        return context