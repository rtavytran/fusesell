"""
Input validation utilities for FuseSell Local
"""

import re
import urllib.parse
from typing import Any, Dict, List, Optional
import logging


class InputValidator:
    """
    Validates input data for FuseSell pipeline execution.
    Provides validation methods for URLs, emails, API keys, and other inputs.
    """
    
    def __init__(self):
        """Initialize validator with regex patterns."""
        self.logger = logging.getLogger("fusesell.validator")
        
        # Regex patterns
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        self.phone_pattern = re.compile(
            r'^[\+]?[1-9][\d]{0,15}$|^[\(]?[\d\s\-\(\)]{7,}$'
        )
        
        self.api_key_pattern = re.compile(
            r'^sk-[a-zA-Z0-9\-_]{3,}$'
        )
    
    def validate_url(self, url: str) -> bool:
        """
        Validate URL format and accessibility.
        
        Args:
            url: URL string to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        try:
            # Parse URL
            parsed = urllib.parse.urlparse(url)
            
            # Check required components
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check valid schemes
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check for valid domain format
            domain = parsed.netloc.lower()
            if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
                return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"URL validation failed for {url}: {str(e)}")
            return False
    
    def validate_email(self, email: str) -> bool:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email is valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        return bool(self.email_pattern.match(email.strip()))
    
    def validate_phone(self, phone: str) -> bool:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            True if phone is valid, False otherwise
        """
        if not phone or not isinstance(phone, str):
            return False
        
        # Clean phone number
        cleaned = re.sub(r'[^\d\+\(\)\-\s]', '', phone.strip())
        
        return bool(self.phone_pattern.match(cleaned))
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate OpenAI API key format.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if API key format is valid, False otherwise
        """
        if not api_key or not isinstance(api_key, str):
            return False
        
        return bool(self.api_key_pattern.match(api_key.strip()))
    
    def validate_execution_context(self, context: Dict[str, Any]) -> List[str]:
        """
        Validate execution context for pipeline stages.
        
        Args:
            context: Execution context dictionary
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        required_fields = ['execution_id', 'config']
        for field in required_fields:
            if field not in context:
                errors.append(f"Missing required field: {field}")
        
        # Validate config if present
        config = context.get('config', {})
        if config:
            config_errors = self.validate_config(config)
            errors.extend(config_errors)
        
        return errors
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate pipeline configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Required configuration fields
        required_fields = {
            'openai_api_key': 'OpenAI API key',
            'org_id': 'Organization ID',
            'org_name': 'Organization name'
        }
        
        for field, description in required_fields.items():
            if not config.get(field):
                errors.append(f"Missing required configuration: {description}")
        
        # Check that at least one data source is provided (matching new input schema)
        data_sources = [
            config.get('input_website'),
            config.get('input_description'),
            config.get('input_business_card'),
            config.get('input_linkedin_url'),
            config.get('input_facebook_url'),
            config.get('input_freetext')
        ]
        
        # Filter out empty strings and None values
        valid_sources = [s for s in data_sources if s and s.strip()]
        
        if not valid_sources:
            errors.append("At least one data source is required (input_website, input_description, input_business_card, input_linkedin_url, input_facebook_url, or input_freetext)")
        
        # Validate specific fields
        if config.get('openai_api_key') and not self.validate_api_key(config['openai_api_key']):
            errors.append("Invalid OpenAI API key format")
        
        # Validate URLs if provided (matching new input schema)
        url_fields = {
            'input_website': 'input website URL',
            'input_business_card': 'input business card URL',
            'input_linkedin_url': 'input LinkedIn URL',
            'input_facebook_url': 'input Facebook URL'
        }
        
        for field, description in url_fields.items():
            if config.get(field) and not self.validate_url(config[field]):
                errors.append(f"Invalid {description}")
        
        if config.get('contact_email') and not self.validate_email(config['contact_email']):
            errors.append("Invalid contact email address")
        
        if config.get('contact_phone') and not self.validate_phone(config['contact_phone']):
            errors.append("Invalid contact phone number")
        
        # Validate optional URLs
        url_fields = ['business_card_url', 'linkedin_url', 'facebook_url']
        for field in url_fields:
            if config.get(field) and not self.validate_url(config[field]):
                errors.append(f"Invalid {field.replace('_', ' ')}")
        
        # Validate numeric ranges
        if 'temperature' in config:
            temp = config['temperature']
            if not isinstance(temp, (int, float)) or not (0.0 <= temp <= 2.0):
                errors.append("Temperature must be a number between 0.0 and 2.0")
        
        if 'max_retries' in config:
            retries = config['max_retries']
            if not isinstance(retries, int) or retries < 0:
                errors.append("Max retries must be a non-negative integer")
        
        return errors
    
    def validate_stage_input(self, stage_name: str, input_data: Dict[str, Any]) -> List[str]:
        """
        Validate input data for specific pipeline stage.
        
        Args:
            stage_name: Name of the pipeline stage
            input_data: Input data to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if stage_name == 'data_acquisition':
            errors.extend(self._validate_data_acquisition_input(input_data))
        elif stage_name == 'data_preparation':
            errors.extend(self._validate_data_preparation_input(input_data))
        elif stage_name == 'lead_scoring':
            errors.extend(self._validate_lead_scoring_input(input_data))
        elif stage_name == 'initial_outreach':
            errors.extend(self._validate_initial_outreach_input(input_data))
        elif stage_name == 'follow_up':
            errors.extend(self._validate_follow_up_input(input_data))
        
        return errors
    
    def _validate_data_acquisition_input(self, input_data: Dict[str, Any]) -> List[str]:
        """Validate data acquisition stage input."""
        errors = []
        
        # Check that at least one data source is provided (matching new input schema)
        data_sources = [
            input_data.get('input_website'),
            input_data.get('input_description'),
            input_data.get('input_business_card'),
            input_data.get('input_linkedin_url'),
            input_data.get('input_facebook_url'),
            input_data.get('input_freetext')
        ]
        
        # Filter out empty strings and None values
        valid_sources = [s for s in data_sources if s and s.strip()]
        
        if not valid_sources:
            errors.append("At least one customer data source is required for data acquisition")
        
        # Validate URLs if provided (matching new input schema)
        if input_data.get('input_website') and not self.validate_url(input_data['input_website']):
            errors.append("Invalid input website URL")
        
        if input_data.get('input_business_card') and not self.validate_url(input_data['input_business_card']):
            errors.append("Invalid input business card URL")
            
        if input_data.get('input_linkedin_url') and not self.validate_url(input_data['input_linkedin_url']):
            errors.append("Invalid input LinkedIn URL")
            
        if input_data.get('input_facebook_url') and not self.validate_url(input_data['input_facebook_url']):
            errors.append("Invalid input Facebook URL")
        
        return errors
    
    def _validate_data_preparation_input(self, input_data: Dict[str, Any]) -> List[str]:
        """Validate data preparation stage input."""
        errors = []
        
        # Should have raw customer data from previous stage
        if not input_data.get('raw_customer_data'):
            errors.append("Raw customer data is required for data preparation")
        
        return errors
    
    def _validate_lead_scoring_input(self, input_data: Dict[str, Any]) -> List[str]:
        """Validate lead scoring stage input."""
        errors = []
        
        # Should have structured customer data
        required_fields = ['companyInfo', 'painPoints']
        for field in required_fields:
            if field not in input_data:
                errors.append(f"Missing required field for lead scoring: {field}")
        
        return errors
    
    def _validate_initial_outreach_input(self, input_data: Dict[str, Any]) -> List[str]:
        """Validate initial outreach stage input."""
        errors = []
        
        # Should have customer data and lead scores
        required_fields = ['customer_data', 'lead_scores']
        for field in required_fields:
            if field not in input_data:
                errors.append(f"Missing required field for initial outreach: {field}")
        
        # Validate contact information (check both old and new data structures)
        customer_data = input_data.get('customer_data', {})
        
        # Check old structure first
        has_old_contact = customer_data.get('contact_email') or customer_data.get('contact_name')
        
        # Check new structure (primaryContact)
        primary_contact = customer_data.get('primaryContact', {})
        has_new_contact = primary_contact.get('email') or primary_contact.get('name')
        
        if not has_old_contact and not has_new_contact:
            errors.append("Contact email or name is required for outreach")
        
        return errors
    
    def _validate_follow_up_input(self, input_data: Dict[str, Any]) -> List[str]:
        """Validate follow-up stage input."""
        errors = []
        
        # Should have previous interaction data
        if not input_data.get('previous_interactions'):
            errors.append("Previous interaction data is required for follow-up")
        
        return errors
    
    def sanitize_input(self, data: Any) -> Any:
        """
        Sanitize input data to prevent injection attacks.
        
        Args:
            data: Input data to sanitize
            
        Returns:
            Sanitized data
        """
        if isinstance(data, str):
            # Remove potentially dangerous characters
            sanitized = re.sub(r'[<>"\']', '', data)
            return sanitized.strip()
        
        elif isinstance(data, dict):
            return {key: self.sanitize_input(value) for key, value in data.items()}
        
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        
        else:
            return data
    
    def validate_json_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        Validate data against JSON schema.
        
        Args:
            data: Data to validate
            schema: JSON schema definition
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            # Basic schema validation (simplified)
            required = schema.get('required', [])
            properties = schema.get('properties', {})
            
            # Check required fields
            for field in required:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            # Check field types
            for field, value in data.items():
                if field in properties:
                    expected_type = properties[field].get('type')
                    if expected_type and not self._check_type(value, expected_type):
                        errors.append(f"Invalid type for field {field}: expected {expected_type}")
            
        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")
        
        return errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True