"""
LLM Client for OpenAI API integration
"""

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

from typing import Dict, Any, List, Optional
import logging
import time
import json


class LLMClient:
    """
    Client for interacting with OpenAI's API.
    Handles authentication, rate limiting, and error handling.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        """
        Initialize LLM client.
        
        Args:
            api_key: OpenAI API key
            model: Model to use for completions
            base_url: Optional base URL for API (for custom endpoints)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger("fusesell.llm_client")
        
        # Initialize OpenAI client
        if base_url:
            self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = openai.OpenAI(api_key=api_key)
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Create a chat completion.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            response_format: Optional response format specification
            **kwargs: Additional parameters for the API call
            
        Returns:
            Response content as string
            
        Raises:
            Exception: If API call fails after retries
        """
        try:
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens:
                api_params["max_tokens"] = max_tokens
            
            if response_format:
                api_params["response_format"] = response_format
            
            self.logger.debug(f"Making API call with {len(messages)} messages")
            
            # Make API call with retry logic
            response = self._make_api_call_with_retry(api_params)
            
            # Extract content from response
            # Handle both OpenAI format and direct string responses
            if isinstance(response, str):
                # Check if response is HTML (indicates error)
                if response.strip().startswith('<!doctype html') or response.strip().startswith('<html'):
                    raise ValueError(f"Received HTML response instead of JSON from LLM endpoint. This usually indicates an authentication or endpoint configuration issue.")
                content = response
            elif hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                # Check if content is HTML
                if content and (content.strip().startswith('<!doctype html') or content.strip().startswith('<html')):
                    raise ValueError(f"Received HTML response instead of text from LLM endpoint. This usually indicates an authentication or endpoint configuration issue.")
            else:
                # Fallback: try to extract content from response
                content = str(response)
                if content.strip().startswith('<!doctype html') or content.strip().startswith('<html'):
                    raise ValueError(f"Received HTML response instead of JSON from LLM endpoint. This usually indicates an authentication or endpoint configuration issue.")
            
            # Log token usage if available
            if hasattr(response, 'usage'):
                self.logger.debug(f"Token usage - Prompt: {response.usage.prompt_tokens}, "
                                f"Completion: {response.usage.completion_tokens}, "
                                f"Total: {response.usage.total_tokens}")
            
            return content
            
        except Exception as e:
            self.logger.error(f"Chat completion failed: {str(e)}")
            raise
    
    def _make_api_call_with_retry(self, api_params: Dict[str, Any], max_retries: int = 3) -> Any:
        """
        Make API call with exponential backoff retry logic.
        
        Args:
            api_params: Parameters for the API call
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response object
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(**api_params)
                return response
                
            except openai.RateLimitError as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 1  # Exponential backoff
                    self.logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error("Rate limit exceeded, max retries reached")
                    raise
                    
            except openai.APIError as e:
                last_exception = e
                if attempt < max_retries and e.status_code >= 500:
                    wait_time = (2 ** attempt) + 1
                    self.logger.warning(f"API error {e.status_code}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"API error: {str(e)}")
                    raise
                    
            except Exception as e:
                last_exception = e
                self.logger.error(f"Unexpected error in API call: {str(e)}")
                raise
        
        # If we get here, all retries failed
        raise last_exception
    
    def structured_completion(
        self, 
        prompt: str, 
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Get structured JSON response from LLM.
        
        Args:
            prompt: The prompt to send
            schema: JSON schema for the expected response
            temperature: Sampling temperature
            
        Returns:
            Parsed JSON response
            
        Raises:
            ValueError: If response doesn't match schema or isn't valid JSON
        """
        # Add JSON formatting instruction to prompt
        json_prompt = f"""{prompt}

Please respond with valid JSON that matches this schema:
{json.dumps(schema, indent=2)}

Response:"""
        
        messages = [{"role": "user", "content": json_prompt}]
        
        try:
            # Try with JSON response format if supported
            response = self.chat_completion(
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
        except Exception:
            # Fallback to regular completion
            response = self.chat_completion(
                messages=messages,
                temperature=temperature
            )
        
        # Parse JSON response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            return self._extract_json_from_response(response)
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response that may contain additional text.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Extracted JSON dictionary
            
        Raises:
            ValueError: If no valid JSON found
        """
        # Try to find JSON in code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                json_str = response[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        # Try to find JSON by braces
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON array
        start = response.find("[")
        end = response.rfind("]") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"Could not extract valid JSON from response: {response[:200]}...")
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key works by making a simple test call.
        
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            response = self.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return len(response) > 0
        except Exception as e:
            self.logger.error(f"API key validation failed: {str(e)}")
            return False