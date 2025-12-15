"""
FuseSell Utilities - Common utilities and helper functions
"""

from .data_manager import LocalDataManager
from .llm_client import LLMClient, normalize_llm_base_url
from .validators import InputValidator
from .logger import setup_logging
from .output_helpers import write_full_output_html
from .auto_setup import (
    check_settings_completion,
    auto_initialize_auto_interaction,
    auto_populate_from_email,
    generate_agent_context,
    should_update_agent_context,
    get_gmail_email_safe,
)
from .agent_context import notify_action_completed, write_agent_md, get_agent_md_path

__all__ = [
    'LocalDataManager',
    'LLMClient',
    'normalize_llm_base_url',
    'InputValidator',
    'setup_logging',
    'write_full_output_html',
    'check_settings_completion',
    'auto_initialize_auto_interaction',
    'auto_populate_from_email',
    'generate_agent_context',
    'should_update_agent_context',
    'get_gmail_email_safe',
    'notify_action_completed',
    'write_agent_md',
    'get_agent_md_path',
]
