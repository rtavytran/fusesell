"""
Base Stage Interface for FuseSell Pipeline Stages
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import json
import time
from datetime import datetime
import uuid

from ..utils.llm_client import LLMClient
from ..utils.data_manager import LocalDataManager


class BaseStage(ABC):
    """
    Abstract base class for all FuseSell pipeline stages.
    Provides common functionality and interface for stage implementations.
    """
    
    def __init__(self, config: Dict[str, Any], data_manager: Optional[LocalDataManager] = None):
        """
        Initialize the stage with configuration.
        
        Args:
            config: Configuration dictionary containing API keys, settings, etc.
            data_manager: Optional shared data manager instance. If not provided, creates a new one.
        """
        self.config = config
        # Convert class name to snake_case stage name
        class_name = self.__class__.__name__.replace('Stage', '')
        # Convert CamelCase to snake_case
        import re
        self.stage_name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', class_name).lower()
        self.logger = logging.getLogger(f"fusesell.{self.stage_name}")
        
        # Initialize LLM client if API key provided
        if config.get('openai_api_key'):
            try:
                # Initialize with base URL if provided
                llm_kwargs = {
                    'api_key': config['openai_api_key'],
                    'model': config.get('llm_model', 'gpt-4o-mini')
                }
                if config.get('llm_base_url'):
                    llm_kwargs['base_url'] = config['llm_base_url']
                
                self.llm_client = LLMClient(**llm_kwargs)
            except ImportError as e:
                self.logger.warning(f"LLM client not available: {str(e)}")
                self.llm_client = None
        else:
            self.llm_client = None
            
        # Use provided data manager or create new one (for backward compatibility)
        if data_manager is not None:
            self.data_manager = data_manager
            self.logger.debug("Using shared data manager instance")
        else:
            self.data_manager = LocalDataManager(config.get('data_dir', './fusesell_data'))
            self.logger.warning("Created new data manager instance - this may cause performance overhead. Consider using shared data manager.")
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the stage logic and return results.
        
        Args:
            context: Execution context containing input data and previous results
            
        Returns:
            Dictionary containing stage results and metadata
        """
        pass
    
    @abstractmethod
    def validate_input(self, context: Dict[str, Any]) -> bool:
        """
        Validate input data for this stage.
        
        Args:
            context: Execution context to validate
            
        Returns:
            True if input is valid, False otherwise
        """
        pass
    
    def call_llm(self, prompt: str, **kwargs) -> str:
        """
        Standardized LLM calling interface.
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional parameters for the LLM call
            
        Returns:
            LLM response text
            
        Raises:
            ValueError: If LLM client is not initialized
        """
        if not self.llm_client:
            raise ValueError("LLM client not initialized. Provide openai_api_key in config.")
        
        self.logger.debug(f"Calling LLM with prompt length: {len(prompt)}")
        
        try:
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            self.logger.debug(f"LLM response length: {len(response)}")
            return response
            
        except Exception as e:
            self.logger.error(f"LLM call failed: {str(e)}")
            raise
    
    def call_llm_with_system(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Call LLM with system and user prompts.
        
        Args:
            system_prompt: System prompt to set context
            user_prompt: User prompt with the actual request
            **kwargs: Additional parameters for the LLM call
            
        Returns:
            LLM response text
        """
        if not self.llm_client:
            raise ValueError("LLM client not initialized. Provide openai_api_key in config.")
        
        self.logger.debug(f"Calling LLM with system prompt length: {len(system_prompt)}, user prompt length: {len(user_prompt)}")
        
        try:
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                **kwargs
            )
            
            self.logger.debug(f"LLM response length: {len(response)}")
            return response
            
        except Exception as e:
            self.logger.error(f"LLM call with system prompt failed: {str(e)}")
            raise
    
    def call_llm_structured(self, prompt: str, response_format: str = "json", **kwargs) -> Dict[str, Any]:
        """
        Call LLM and parse structured response.
        
        Args:
            prompt: The prompt to send to the LLM
            response_format: Expected response format ('json' or 'yaml')
            **kwargs: Additional parameters for the LLM call
            
        Returns:
            Parsed structured response
            
        Raises:
            ValueError: If response cannot be parsed
        """
        # Add format instruction to prompt
        if response_format.lower() == "json":
            formatted_prompt = f"{prompt}\n\nPlease respond with valid JSON format."
        else:
            formatted_prompt = prompt
        
        response = self.call_llm(formatted_prompt, **kwargs)
        
        if response_format.lower() == "json":
            return self.parse_json_response(response)
        else:
            return {"raw_response": response}
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM, handling common formatting issues.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        try:
            # Try direct parsing first
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
            
            # Try to extract JSON from the response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            
            raise ValueError(f"Could not parse JSON from LLM response: {response[:200]}...")
    
    def log_stage_start(self, context: Dict[str, Any]) -> None:
        """Log the start of stage execution."""
        execution_id = context.get('execution_id', 'unknown')
        self.logger.info(f"Starting {self.stage_name} stage for execution {execution_id}")
    
    def log_stage_complete(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Log the completion of stage execution."""
        execution_id = context.get('execution_id', 'unknown')
        status = result.get('status', 'unknown')
        self.logger.info(f"Completed {self.stage_name} stage for execution {execution_id} with status: {status}")
    
    def log_stage_error(self, context: Dict[str, Any], error: Exception) -> None:
        """Log stage execution errors."""
        execution_id = context.get('execution_id', 'unknown')
        self.logger.error(f"Error in {self.stage_name} stage for execution {execution_id}: {str(error)}")
    
    def execute_with_timing(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the stage with performance timing and consolidated logging.
        
        Args:
            context: Execution context containing input data and previous results
            
        Returns:
            Dictionary containing stage results and metadata with timing information
        """
        execution_id = context.get('execution_id', 'unknown')
        start_time = time.time()
        
        # Single start log message
        self.logger.info(f"Starting {self.stage_name} stage for execution {execution_id}")
        
        try:
            # Execute the actual stage logic (stages should NOT log completion themselves)
            result = self.execute(context)
            
            # Calculate timing
            end_time = time.time()
            duration = end_time - start_time
            
            # Add timing information to result
            if isinstance(result, dict):
                result['timing'] = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_seconds': duration
                }
            
            # Single completion log message with timing
            status = result.get('status', 'unknown') if isinstance(result, dict) else 'unknown'
            self.logger.info(f"Completed {self.stage_name} stage for execution {execution_id} with status: {status} in {duration:.2f} seconds")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            # Single error log message with timing
            self.logger.error(f"Error in {self.stage_name} stage for execution {execution_id} after {duration:.2f} seconds: {str(e)}")
            raise
    
    def save_stage_result(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Save stage result to local database (backward compatibility only).
        
        Note: Operation tracking is now handled by the pipeline using server-compatible schema.
        This method only maintains backward compatibility with the old stage_results table.
        
        Args:
            context: Execution context
            result: Stage execution result
        """
        try:
            # Save to stage_results table (backward compatibility only)
            # The pipeline now handles operation creation with server-compatible schema
            self.data_manager.save_stage_result(
                execution_id=context.get('execution_id'),
                stage_name=self.stage_name,
                input_data=context.get('input_data', {}),
                output_data=result,
                status=result.get('status', 'unknown')
            )
            
        except Exception as e:
            self.logger.debug(f"Backward compatibility save failed (expected): {str(e)}")
    
    def get_prompt_template(self, prompt_key: str) -> str:
        """
        Get prompt template from configuration.
        
        Args:
            prompt_key: Key for the prompt template
            
        Returns:
            Prompt template string
        """
        try:
            prompts = self.data_manager.load_prompts()
            stage_prompts = prompts.get(self.stage_name, {})
            return stage_prompts.get(prompt_key, "")
        except Exception as e:
            self.logger.warning(f"Failed to load prompt template {prompt_key}: {str(e)}")
            return ""
    
    def get_required_fields(self) -> list:
        """
        Get list of required input fields for this stage.
        
        Returns:
            List of required field names
        """
        # Default implementation - stages should override this
        return []
    
    def validate_required_fields(self, context: Dict[str, Any]) -> list:
        """
        Validate that all required fields are present in the context.
        
        Args:
            context: Execution context to validate
            
        Returns:
            List of missing required fields
        """
        input_data = context.get('input_data', {})
        required_fields = self.get_required_fields()
        missing_fields = []
        
        for field in required_fields:
            if field not in input_data or input_data[field] is None:
                missing_fields.append(field)
        
        return missing_fields
    
    def validate_context(self, context: Dict[str, Any]) -> tuple[bool, list]:
        """
        Comprehensive context validation.
        
        Args:
            context: Execution context to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for execution ID
        if not context.get('execution_id'):
            errors.append("Missing execution_id in context")
        
        # Check for input data
        if 'input_data' not in context:
            errors.append("Missing input_data in context")
        
        # Check required fields
        missing_fields = self.validate_required_fields(context)
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Stage-specific validation
        if not self.validate_input(context):
            errors.append("Stage-specific input validation failed")
        
        return len(errors) == 0, errors
    
    def format_prompt(self, template: str, **kwargs) -> str:
        """
        Format prompt template with provided variables.
        
        Args:
            template: Prompt template string
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted prompt string
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            self.logger.warning(f"Missing variable in prompt template: {str(e)}")
            return template
    
    def generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        return f"{self.stage_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    def should_stop_pipeline(self, result: Dict[str, Any]) -> bool:
        """
        Determine if pipeline should stop based on stage result.
        
        Args:
            result: Stage execution result
            
        Returns:
            True if pipeline should stop, False otherwise
        """
        # Stop if stage failed
        if result.get('status') in ['fail', 'error']:
            return True
        
        # Stop if explicit stop condition from business logic
        if result.get('pipeline_stop', False):
            return True
        
        # Stop if explicit stop condition (legacy)
        if result.get('stop_pipeline', False):
            return True
        
        return False
    
    def create_error_result(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create standardized error result.
        
        Args:
            error: Exception that occurred
            context: Execution context
            
        Returns:
            Error result dictionary
        """
        return {
            'status': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
            'stage': self.stage_name,
            'execution_id': context.get('execution_id'),
            'timestamp': datetime.now().isoformat()
        }
    
    def create_success_result(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create standardized success result.
        
        Args:
            data: Stage output data
            context: Execution context
            
        Returns:
            Success result dictionary
        """
        return {
            'status': 'success',
            'stage': self.stage_name,
            'execution_id': context.get('execution_id'),
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
    
    def create_skip_result(self, reason: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create standardized skip result.
        
        Args:
            reason: Reason for skipping the stage
            context: Execution context
            
        Returns:
            Skip result dictionary
        """
        return {
            'status': 'skipped',
            'reason': reason,
            'stage': self.stage_name,
            'execution_id': context.get('execution_id'),
            'timestamp': datetime.now().isoformat()
        }
    
    def handle_stage_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive error handling for stage execution.
        
        Args:
            error: Exception that occurred
            context: Execution context
            
        Returns:
            Error result dictionary
        """
        # Log the error
        self.log_stage_error(context, error)
        
        # Save error to database if possible
        try:
            self.data_manager.save_stage_result(
                execution_id=context.get('execution_id'),
                stage_name=self.stage_name,
                input_data=context.get('input_data', {}),
                output_data={'error': str(error)},
                status='error',
                error_message=str(error)
            )
        except Exception as save_error:
            self.logger.warning(f"Failed to save error result: {str(save_error)}")
        
        # Return standardized error result
        return self.create_error_result(error, context)
    
    def get_stage_config(self, key: str, default: Any = None) -> Any:
        """
        Get stage-specific configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        stage_config = self.config.get('stages', {}).get(self.stage_name, {})
        return stage_config.get(key, default)
    
    def is_dry_run(self) -> bool:
        """
        Check if this is a dry run execution.
        
        Returns:
            True if dry run mode is enabled
        """
        return self.config.get('dry_run', False)
    
    def get_team_settings(self, team_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get team settings for the current execution.
        
        Args:
            team_id: Team ID to get settings for. If None, uses team_id from config.
            
        Returns:
            Team settings dictionary or None if not found
        """
        if not team_id:
            team_id = self.config.get('team_id')
        
        if not team_id:
            return None
            
        try:
            settings = self.data_manager.get_team_settings(team_id)
            if settings:
                self.logger.debug(f"Loaded team settings for team: {team_id}")
            else:
                self.logger.debug(f"No team settings found for team: {team_id}")
            return settings
        except Exception as e:
            self.logger.warning(f"Failed to load team settings for team {team_id}: {str(e)}")
            return None
    
    def get_team_setting(self, setting_name: str, team_id: str = None, default: Any = None) -> Any:
        """
        Get a specific team setting value.
        
        Args:
            setting_name: Name of the setting to retrieve
            team_id: Team ID to get settings for. If None, uses team_id from config.
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        team_settings = self.get_team_settings(team_id)
        if team_settings and setting_name in team_settings:
            return team_settings[setting_name]
        return default

    def get_execution_metadata(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get execution metadata for logging and tracking.
        
        Args:
            context: Execution context
            
        Returns:
            Metadata dictionary
        """
        return {
            'execution_id': context.get('execution_id'),
            'stage': self.stage_name,
            'org_id': self.config.get('org_id'),
            'org_name': self.config.get('org_name'),
            'customer_name': context.get('input_data', {}).get('customer_name'),
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.is_dry_run()
        }