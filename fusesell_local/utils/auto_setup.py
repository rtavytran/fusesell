"""
Auto-setup and intelligent initialization utilities for FuseSell.

This module provides functions for:
- Auto-initialization of settings with smart defaults (e.g., Gmail email)
- Settings completion checking
- Agent context generation and updates
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable

from .data_manager import LocalDataManager


logger = logging.getLogger("fusesell.auto_setup")


def get_gmail_email_safe(get_gmail_email_func: Optional[Callable[[], str]] = None) -> Optional[str]:
    """
    Safely retrieve Gmail email from MCP server.

    Args:
        get_gmail_email_func: Optional function to retrieve Gmail email.
                             If None, returns None.

    Returns:
        Gmail email address if available, None otherwise
    """
    if get_gmail_email_func is None:
        return None

    try:
        email = get_gmail_email_func()
        if email and isinstance(email, str) and email.strip():
            return email.strip()
    except Exception as exc:
        logger.warning(f"Could not retrieve Gmail email: {exc}")

    return None


def check_settings_completion(
    manager: LocalDataManager,
    team_id: str
) -> Dict[str, Any]:
    """
    Check which settings sections are completed for a team.

    Args:
        manager: LocalDataManager instance
        team_id: Team identifier

    Returns:
        Dictionary with completion status for each settings section:
        {
            "team_id": str,
            "auto_interaction_completed": bool,
            "rep_completed": bool,
            "product_completed": bool,
            "organization_completed": bool,
            "follow_up_completed": bool,
        }
    """
    settings = manager.get_team_settings(team_id)

    def _is_completed(value: Any) -> bool:
        """Check if a settings value is considered completed."""
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (list, tuple, set, frozenset)):
            return len(value) > 0
        if isinstance(value, dict):
            return len(value) > 0
        return True

    if not settings:
        return {
            "team_id": team_id,
            "auto_interaction_completed": False,
            "rep_completed": False,
            "product_completed": False,
            "organization_completed": False,
            "follow_up_completed": False,
        }

    return {
        "team_id": team_id,
        "auto_interaction_completed": _is_completed(settings.get("gs_team_auto_interaction")),
        "rep_completed": _is_completed(settings.get("gs_team_rep")),
        "product_completed": _is_completed(settings.get("gs_team_product")),
        "organization_completed": _is_completed(settings.get("gs_team_organization")),
        "follow_up_completed": _is_completed(settings.get("gs_team_follow_up")),
    }


def auto_initialize_auto_interaction(
    manager: LocalDataManager,
    team_id: str,
    gmail_email: Optional[str] = None,
    get_gmail_email_func: Optional[Callable[[], str]] = None
) -> bool:
    """
    Auto-initialize auto_interaction settings with Gmail email if:
    1. Gmail MCP is connected (or gmail_email is provided)
    2. auto_interaction is not yet set

    Args:
        manager: LocalDataManager instance
        team_id: Team identifier
        gmail_email: Optional pre-fetched Gmail email
        get_gmail_email_func: Optional function to retrieve Gmail email
                             (will be called if gmail_email is None)

    Returns:
        True if auto-initialization was performed, False otherwise
    """
    # Get Gmail email if not provided
    if gmail_email is None and get_gmail_email_func is not None:
        gmail_email = get_gmail_email_safe(get_gmail_email_func)

    if not gmail_email:
        return False

    # Check if already initialized
    settings = manager.get_team_settings(team_id)
    auto_interaction_value = settings.get("gs_team_auto_interaction") if settings else None

    # Check if auto_interaction is already completed
    if auto_interaction_value:
        if isinstance(auto_interaction_value, list) and len(auto_interaction_value) > 0:
            return False
        if isinstance(auto_interaction_value, dict) and len(auto_interaction_value) > 0:
            return False

    try:
        # Create default auto_interaction with Gmail email
        default_auto_interaction = [{
            "from_email": gmail_email,
            "from_name": "",
            "from_number": "",
            "tool_type": "Email",
            "email_cc": "",
            "email_bcc": "",
        }]

        manager.update_team_settings(
            team_id=team_id,
            gs_team_auto_interaction=default_auto_interaction
        )
        logger.info(f"Auto-initialized auto_interaction with Gmail: {gmail_email}")
        return True
    except Exception as exc:
        logger.error(f"Failed to auto-initialize auto_interaction: {exc}")
        return False


def auto_populate_from_email(
    from_email: str,
    gmail_email: Optional[str] = None,
    get_gmail_email_func: Optional[Callable[[], str]] = None
) -> str:
    """
    Auto-populate from_email field if empty using Gmail email.

    Args:
        from_email: Current from_email value
        gmail_email: Optional pre-fetched Gmail email
        get_gmail_email_func: Optional function to retrieve Gmail email

    Returns:
        Original from_email if not empty, otherwise Gmail email if available,
        otherwise empty string
    """
    # Return existing value if not empty
    if from_email and from_email.strip():
        return from_email.strip()

    # Get Gmail email if not provided
    if gmail_email is None and get_gmail_email_func is not None:
        gmail_email = get_gmail_email_safe(get_gmail_email_func)

    if gmail_email:
        logger.info(f"Auto-populated from_email with Gmail: {gmail_email}")
        return gmail_email

    return ""


def generate_agent_context(
    manager: LocalDataManager,
    org_id: str,
    detail_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive agent context for the workspace.

    This function collects and structures all relevant workspace data
    for agent memory/context updates.

    Args:
        manager: LocalDataManager instance
        org_id: Organization identifier
        detail_limit: Optional limit for detail fields in products/processes

    Returns:
        Dictionary containing:
        - workspace_summary: Overview text
        - products: List of active products
        - active_processes: List of active sales processes
        - team_settings: Team configuration
        - statistics: Usage statistics
        - last_updated: Timestamp
    """
    # Get teams
    teams = manager.list_teams(org_id=org_id, status='active')
    team = teams[0] if teams else None

    if not team:
        return {
            'workspace_summary': 'No team configured',
            'products': [],
            'active_processes': [],
            'team_settings': {},
            'statistics': {},
            'last_updated': datetime.utcnow().isoformat() + 'Z',
        }

    team_id = team.get('team_id')
    team_name = team.get('team_name', 'Unnamed Team')

    # Get products
    products = manager.list_products(org_id=org_id, status='active')

    # Apply detail limit if specified
    if detail_limit is not None and detail_limit > 0:
        for product in products:
            for key in ['short_description', 'long_description', 'category']:
                if key in product and isinstance(product[key], str):
                    if len(product[key]) > detail_limit:
                        product[key] = product[key][:detail_limit] + '...'

    # Get settings
    settings = manager.get_team_settings(team_id) or {}

    # Get processes
    all_processes = manager.list_tasks(org_id=org_id, limit=100)
    active_processes = [
        p for p in all_processes
        if p.get('status') in ('running', 'pending', 'in_progress')
    ]

    # Apply detail limit to processes
    if detail_limit is not None and detail_limit > 0:
        for process in active_processes:
            for key in ['customer_name', 'customer_company', 'notes']:
                if key in process and isinstance(process[key], str):
                    if len(process[key]) > detail_limit:
                        process[key] = process[key][:detail_limit] + '...'

    # Calculate completion status
    completion_status = check_settings_completion(manager, team_id)

    # Build workspace summary
    workspace_summary_parts = [
        f"Team: {team_name}",
        f"Products: {len(products)} active",
        f"Active Processes: {len(active_processes)}",
    ]

    if completion_status.get('auto_interaction_completed'):
        workspace_summary_parts.append("Auto interaction: configured")
    else:
        workspace_summary_parts.append("Auto interaction: not configured")

    workspace_summary = " | ".join(workspace_summary_parts)

    return {
        'workspace_summary': workspace_summary,
        'products': products,
        'active_processes': active_processes,
        'team_settings': settings,
        'statistics': {
            'total_products': len(products),
            'active_processes': len(active_processes),
            'total_processes': len(all_processes),
            'settings_completion': completion_status,
        },
        'last_updated': datetime.utcnow().isoformat() + 'Z',
    }


def should_update_agent_context(
    action: str,
    critical_actions: Optional[List[str]] = None,
    skip_actions: Optional[List[str]] = None
) -> bool:
    """
    Determine if agent context should be updated based on the action performed.

    Args:
        action: The action that was performed
        critical_actions: List of actions that trigger context updates
        skip_actions: List of actions that should NOT trigger updates

    Returns:
        True if agent context should be updated, False otherwise
    """
    # Default critical actions
    if critical_actions is None:
        critical_actions = [
            'product_create', 'product_update', 'product_delete',
            'product_status_change', 'product_bulk_import',
            'process_create',
            'team_create', 'team_update',
            'gs_organization', 'sales_rep', 'product_team', 'auto_interaction',
            'initial_outreach', 'follow_up', 'schedule_time', 'followup_schedule_time',
        ]

    # Default skip actions
    if skip_actions is None:
        skip_actions = [
            'product_view', 'product_list', 'team_view', 'team_list', 'settings_view',
            'process_query', 'process_status_change', 'draft_list', 'event_list',
            'event_update', 'knowledge_query', 'proposal_generate'
        ]

    # Skip actions take precedence
    if action in skip_actions:
        return False

    # Check if action is critical
    return action in critical_actions
