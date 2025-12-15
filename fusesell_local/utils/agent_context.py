"""
Agent context helpers for FuseSell.

Provides a lightweight agent.md writer and an action hook that can be used by
RealtimeX flows (or other consumers) to refresh agent context after critical
mutations. The helpers are resilient to missing realtimex_toolkit; when the
toolkit is unavailable, agent.md is written directly to the expected path.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .auto_setup import generate_agent_context, should_update_agent_context
from .data_manager import LocalDataManager

# Default action priorities, aligned with the RealtimeX flows.
CRITICAL_ACTIONS = [
    'product_create', 'product_update', 'product_delete', 'product_status_change', 'product_bulk_import',
    'process_create',
    'team_create', 'team_update',
    'gs_organization', 'sales_rep', 'product_team', 'auto_interaction',
    'initial_outreach', 'follow_up', 'schedule_time', 'followup_schedule_time',
]

SKIP_ACTIONS = [
    'product_view', 'product_list', 'team_view', 'team_list', 'settings_view',
    'process_query', 'process_status_change', 'draft_list', 'event_list', 'event_update',
    'knowledge_query', 'proposal_generate',
]


def get_agent_md_path(workspace_slug: str, agent_id: str) -> Path:
    """
    Construct the standardized agent.md path used by RealtimeX.
    """
    home_dir = Path.home()
    return (
        home_dir
        / ".realtimex.ai"
        / "Resources"
        / "agent-skills"
        / "workspaces"
        / workspace_slug
        / agent_id
        / "agent.md"
    )


def _format_products(products: List[Dict[str, Any]], limit: int = 8, detail_limit: int = 160) -> str:
    if not products:
        return "None configured"

    lines: List[str] = []
    for product in products[:limit]:
        name = product.get('product_name') or product.get('name') or 'Unknown product'
        status = product.get('status')
        desc = product.get('short_description') or product.get('long_description') or ''
        desc = desc.strip()
        if desc and len(desc) > detail_limit:
            desc = desc[:detail_limit] + '...'
        line = f"- {name}"
        if status:
            line += f" ({status})"
        lines.append(line)
        if desc:
            lines.append(f"  - {desc}")
    if len(products) > limit:
        lines.append(f"... ({len(products) - limit} more)")
    return "\n".join(lines)


def _format_processes(processes: List[Dict[str, Any]], limit: int = 8, detail_limit: int = 160) -> str:
    if not processes:
        return "None"

    lines: List[str] = []
    for process in processes[:limit]:
        task_id = process.get('task_id') or process.get('id') or 'unknown'
        customer = process.get('customer_name') or process.get('customer_company') or 'unknown customer'
        status = process.get('status') or 'unknown'
        notes = process.get('notes') or ''
        if notes and len(notes) > detail_limit:
            notes = notes[:detail_limit] + '...'
        lines.append(f"- {task_id}: {customer} [{status}]")
        if notes:
            lines.append(f"  - notes: {notes}")
    if len(processes) > limit:
        lines.append(f"... ({len(processes) - limit} more)")
    return "\n".join(lines)


def _render_agent_markdown(context: Dict[str, Any]) -> str:
    """
    Render the structured context returned by generate_agent_context into markdown.
    """
    stats = context.get('statistics') or {}
    team_settings = context.get('team_settings') or {}

    settings_completion = stats.get('settings_completion') or {}
    products = context.get('products') or []
    active_processes = context.get('active_processes') or []

    # Product counts
    active_products = [p for p in products if (p.get('status') or '').lower() == 'active']
    inactive_products = [p for p in products if (p.get('status') or '').lower() != 'active']
    total_products = stats.get('total_products', len(products))

    # Process counts (best effort)
    active_processes_count = stats.get('active_processes', len(active_processes))
    total_processes = stats.get('total_processes', active_processes_count)

    # Quick settings flags (condensed)
    org_profile_configured = bool(team_settings.get('gs_team_organization'))
    reps_configured = bool(team_settings.get('gs_team_rep'))
    products_linked = bool(team_settings.get('gs_team_product'))
    auto_interaction_configured = bool(team_settings.get('gs_team_auto_interaction'))
    follow_up_configured = bool(team_settings.get('gs_team_follow_up'))

    completion_lines = [
        f"- auto_interaction: {bool(settings_completion.get('auto_interaction_completed'))}",
        f"- rep: {bool(settings_completion.get('rep_completed'))}",
        f"- product: {bool(settings_completion.get('product_completed'))}",
        f"- organization: {bool(settings_completion.get('organization_completed'))}",
        f"- follow_up: {bool(settings_completion.get('follow_up_completed'))}",
    ]

    workspace_slug = context.get('workspace_slug', 'workspace-default')
    org_id = context.get('org_id', 'unknown@example.com')
    team_id = context.get('team_id', 'N/A')
    team_name = context.get('team_name', 'Workspace Team')
    team_created_at = context.get('team_created_at', 'N/A')

    return f"""# Workspace Context: {team_name}

> Auto-generated workspace context for FuseSell agent  
> Last Updated: {context.get('last_updated', 'unknown')}

## Workspace Identity

- **Workspace ID**: `{workspace_slug}`
- **Primary User (Org ID)**: {org_id}

## Hidden Team (Single Team Model)

- **Team ID**: `{team_id}`
- **Team Name**: {team_name}
- **Created**: {team_created_at}

## Product Catalog

**Total Products**: {total_products} ({len(active_products)} active, {len(inactive_products)} inactive)

### Products
{_format_products(products)}

## Active Sales Processes

**Total Active**: {active_processes_count}
**Total Processes**: {total_processes}

### In Progress
{_format_processes(active_processes)}

## Sales Settings Completion

{chr(10).join(completion_lines)}

## Settings Snapshot

- Organization Profile: {"Configured" if org_profile_configured else "Not configured"}
- Sales Reps: {"Configured" if reps_configured else "Not configured"}
- Linked Products: {"Configured" if products_linked else "Not configured"}
- Auto Interaction: {"Configured" if auto_interaction_configured else "Not configured"}
- Follow-up: {"Configured" if follow_up_configured else "Not configured"}
"""


def write_agent_md(
    workspace_slug: Optional[str] = None,
    force: bool = False,
    *,
    manager: Optional[LocalDataManager] = None,
    org_id: Optional[str] = None,
    data_dir: Optional[str] = None,
    detail_limit: int = 180,
) -> Optional[Path]:
    """
    Generate and write agent.md using package helpers, preserving agent-written content.

    If realtimex_toolkit is available, uses save_agent_memory to write to the
    standardized path. Otherwise writes directly to the expected path on disk.
    """
    try:
        from realtimex_toolkit import (  # type: ignore
            get_flow_variable,
            get_workspace_slug,
            get_workspace_data_dir,
            get_agent_id,
            save_agent_memory,
        )
    except Exception:  # noqa: BLE001
        get_flow_variable = None
        get_workspace_slug = None
        get_workspace_data_dir = None
        get_agent_id = None
        save_agent_memory = None

    # Resolve workspace slug from provided arg, toolkit, or flow variables
    if workspace_slug is None:
        resolved_slug = None
        if get_flow_variable:
            try:
                resolved_slug = get_flow_variable("workspace_slug", default_value=None)
                if not resolved_slug:
                    resolved_slug = get_flow_variable("workspace", default_value=None)
            except Exception:
                resolved_slug = None
        if not resolved_slug and get_workspace_slug:
            resolved_slug = get_workspace_slug(default_value="workspace-default")
        workspace_slug = resolved_slug or "workspace-default"

    if org_id is None and get_flow_variable:
        user = get_flow_variable("user", default_value={'email': 'unknown@example.com'})
        org_id = user.get('email', 'unknown@example.com') if isinstance(user, dict) else 'unknown@example.com'
    if org_id is None:
        org_id = "unknown@example.com"

    agent_id = "agent-default"
    if get_agent_id:
        agent_id = get_agent_id(default_value="ef0f035a-84c1-4b88-9050-cd7f6fa40ed6")

    # Resolve workspace and data directories
    workspace_dir = None
    if get_workspace_data_dir:
        try:
            workspace_dir = Path(get_workspace_data_dir(default_workspace_slug=workspace_slug)).expanduser()
        except Exception:
            workspace_dir = None
    if workspace_dir is None:
        workspace_dir = Path.home() / ".realtimex.ai" / "Workspaces" / workspace_slug

    data_dir_path = Path(data_dir).expanduser() if data_dir else workspace_dir / "fusesell_data"

    agent_md_path = get_agent_md_path(workspace_slug, agent_id)

    # TTL check (5 minutes)
    if not force and agent_md_path.exists():
        age_minutes = (time.time() - agent_md_path.stat().st_mtime) / 60
        if age_minutes < 5:
            return agent_md_path

    agent_section = ""
    if agent_md_path.exists():
        try:
            existing_content = agent_md_path.read_text(encoding='utf-8')
            if "<!-- END AUTO-GENERATED -->" in existing_content:
                parts = existing_content.split("<!-- END AUTO-GENERATED -->", 1)
                if len(parts) > 1:
                    agent_section = parts[1].strip()
        except Exception as exc:  # noqa: BLE001
            print(f"[WARNING] Could not read existing agent.md: {exc}", file=sys.stderr)

    try:
        dm = manager or LocalDataManager(data_dir=str(data_dir_path))
        context_data = generate_agent_context(
            manager=dm,
            org_id=org_id,
            detail_limit=detail_limit,
        )
        # Inject workspace metadata for rendering
        context_data['workspace_slug'] = workspace_slug
        context_data['org_id'] = org_id
        if context_data.get('team_name') is None:
            context_data['team_name'] = workspace_slug
        if context_data.get('team_id') is None:
            context_data['team_id'] = 'N/A'
        if context_data.get('team_created_at') is None:
            context_data['team_created_at'] = 'N/A'
        auto_generated_content = _render_agent_markdown(context_data)

        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        complete_content = f"""<!-- AUTO-GENERATED SECTION -->
<!-- Last Updated: {timestamp} -->
<!-- WARNING: Do not edit content between AUTO-GENERATED and END AUTO-GENERATED markers -->
<!-- This section is automatically regenerated from database on critical actions -->

{auto_generated_content}

<!-- END AUTO-GENERATED -->"""

        if agent_section:
            complete_content += f"\n{agent_section}"
        else:
            complete_content += """

<!-- AGENT SECTION -->
<!-- The FuseSell agent can write below this line to record learnings and context -->

## Agent Learnings & Insights

_The agent will record important learnings, patterns, and customer insights here._

## Active Initiatives

_Current focus areas and ongoing work._

## Key Decisions & Context

_Important decisions and context that should persist across sessions._
"""

        if save_agent_memory:
            new_agent_path = save_agent_memory(
                workspace_slug=workspace_slug,
                agent_id=agent_id,
                content=complete_content,
                mode="overwrite",
            )
            return Path(new_agent_path)

        agent_md_path.parent.mkdir(parents=True, exist_ok=True)
        agent_md_path.write_text(complete_content, encoding='utf-8')
        return agent_md_path

    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to generate agent.md: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None


def notify_action_completed(
    action: str,
    *,
    workspace_slug: Optional[str] = None,
    force: bool = False,
    manager: Optional[LocalDataManager] = None,
    org_id: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update agent.md if action requires it. Returns a status dictionary.
    """
    if not should_update_agent_context(
        action=action,
        critical_actions=CRITICAL_ACTIONS,
        skip_actions=SKIP_ACTIONS,
    ):
        return {
            'status': 'skipped',
            'message': 'Agent context skipped (read-only action)',
            'updated': False,
        }

    should_force = force or action in CRITICAL_ACTIONS

    agent_md_path = write_agent_md(
        workspace_slug=workspace_slug,
        force=should_force,
        manager=manager,
        org_id=org_id,
        data_dir=data_dir,
    )

    if agent_md_path:
        return {
            'status': 'success',
            'message': 'Agent context updated',
            'updated': True,
            'path': str(agent_md_path),
        }

    return {
        'status': 'error',
        'message': 'Failed to update agent context',
        'updated': False,
    }


__all__ = [
    'notify_action_completed',
    'write_agent_md',
    'get_agent_md_path',
]
