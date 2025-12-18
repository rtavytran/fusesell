"""
Shared HTML output helper for FuseSell flows.

Renders a friendly key/value view and embeds the raw JSON for debugging.
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import base64
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

DEFAULT_HIDDEN_KEYS: Set[str] = {"org_id", "org_name", "project_code", "plan_id", "plan_name"}
DEFAULT_ROOT_HIDDEN_KEYS: Set[str] = {"status", "summary"}
DEFAULT_HTML_RENDER_KEYS: Set[str] = {"email_body", "body_html", "html_body", "rendered_html"}


def _sanitize_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_for_json(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _prune_empty(value: Any, *, depth: int = 0, hidden_keys: Set[str], root_hidden_keys: Set[str]) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, dict):
        pruned: Dict[str, Any] = {}
        for k, v in value.items():
            k_lower = str(k).lower()
            if k_lower in hidden_keys:
                continue
            if depth == 0 and k_lower in root_hidden_keys:
                continue
            pruned_val = _prune_empty(v, depth=depth + 1, hidden_keys=hidden_keys, root_hidden_keys=root_hidden_keys)
            if pruned_val is not None:
                pruned[k] = pruned_val
        return pruned or None
    if isinstance(value, list):
        pruned_list = [
            _prune_empty(item, depth=depth + 1, hidden_keys=hidden_keys, root_hidden_keys=root_hidden_keys)
            for item in value
        ]
        pruned_list = [item for item in pruned_list if item is not None]
        return pruned_list or None
    return value


def _friendly_key(key: str) -> str:
    if not isinstance(key, str):
        return str(key)
    spaced: List[str] = []
    previous = ""
    for char in key:
        if previous and previous.islower() and char.isupper():
            spaced.append(" ")
        spaced.append(char)
        previous = char
    cleaned = "".join(spaced)
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned.title() if cleaned else key


def _humanize_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {_friendly_key(key): _humanize_keys(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_humanize_keys(item) for item in value]
    return value


def _is_complex_array(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(item, (dict, list)) for item in value)


def _render_value(value: Any, depth: int = 0, key: Optional[str] = None, html_render_keys: Set[str] = None) -> str:
    html_render_keys = html_render_keys or set()
    indent_px = depth * 14
    if isinstance(value, dict):
        parts = []
        for child_key, val in value.items():
            if _is_complex_array(val):
                parts.append(
                    f"<div class='section-header' style='margin-left:{indent_px}px'>"
                    f"{html.escape(_friendly_key(str(child_key)))}"
                    "</div>"
                )
                parts.append(_render_value(val, depth, child_key, html_render_keys))
            else:
                parts.append(
                    "<div class='kv' style='margin-left:"
                    f"{indent_px}px'>"
                    f"<div class='k'>{html.escape(_friendly_key(str(child_key)))}</div>"
                    f"<div class='v'>{_render_value(val, depth + 1, str(child_key), html_render_keys)}</div>"
                    "</div>"
                )
        return "".join(parts)
    if isinstance(value, list):
        if not any(isinstance(item, (dict, list)) for item in value):
            chips = "".join(f"<span class='chip'>{html.escape(str(item))}</span>" for item in value)
            return f"<div class='chips' style='margin-left:{indent_px}px'>{chips}</div>"
        parts = []
        array_indent_px = indent_px + 20
        for item in value:
            parts.append(
                "<div class='list-item' style='margin-left:"
                f"{array_indent_px}px'>"
                f"{_render_value(item, depth + 1, None, html_render_keys)}"
                "</div>"
            )
        return "".join(parts)
    if isinstance(value, str):
        normalized_key = (key or "").strip().lower().replace(" ", "_").replace("-", "_")
        if normalized_key in html_render_keys:
            escaped_srcdoc = html.escape(value, quote=True)
            escaped_raw = html.escape(value)
            return (
                "<div class='html-preview'>"
                "<div class='html-preview-label'>Rendered HTML</div>"
                "<iframe class='html-iframe' sandbox srcdoc=\""
                f"{escaped_srcdoc}"
                "\"></iframe>"
                "<details class='html-raw'>"
                "<summary>Show HTML Source</summary>"
                "<div class='pre-inline'>"
                f"{escaped_raw}"
                "</div>"
                "</details>"
                "</div>"
            )
    return f"<span class='text'>{html.escape(str(value))}</span>"


def _normalize_duration(value: Any) -> str:
    """Format a duration-like value to two decimals when possible."""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return _first_non_empty(value)


def _strip_keys(value: Any, *, drop_keys: Set[str], drop_id_like: bool = False) -> Any:
    """Recursively drop keys and optionally any key containing '_id'."""
    normalized_drop = {k.replace("_", "").replace("-", "") for k in drop_keys}
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, val in value.items():
            key_norm = str(key).lower().replace("_", "").replace("-", "")
            if key_norm in normalized_drop:
                continue
            lower_key = str(key).lower()
            if drop_id_like and ("_id" in lower_key or key_norm.endswith("id")):
                continue
            cleaned_val = _strip_keys(val, drop_keys=drop_keys, drop_id_like=drop_id_like)
            if cleaned_val in (None, {}, []):
                continue
            cleaned[key] = cleaned_val
        return cleaned or None
    if isinstance(value, list):
        cleaned_list = [
            _strip_keys(item, drop_keys=drop_keys, drop_id_like=drop_id_like)
            for item in value
        ]
        cleaned_list = [item for item in cleaned_list if item not in (None, {}, [])]
        return cleaned_list or None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return stripped
    return value

# =============================================================================
# Sales Process Rendering Helpers
# =============================================================================

def _format_percent(value: Any) -> str:
    """Format percentages with two decimal places."""
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.2f}%"


def _format_number(value: Any) -> str:
    """Format numbers with thousands separators."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.2f}"


def _format_timestamp(value: Any) -> str:
    """
    Format timestamps as local time strings (HH:MM DD/MM/YYYY) when possible.

    Assumptions:
    - ISO strings are treated as UTC if naive; otherwise respected and converted to local.
    - Numeric values >1e12 are treated as milliseconds.
    """
    if value is None:
        return ""

    try:
        local_tz = datetime.now().astimezone().tzinfo
    except Exception:
        local_tz = None

    def _to_local(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if local_tz:
            dt = dt.astimezone(local_tz)
        return dt.strftime("%H:%M %d/%m/%Y")

    if isinstance(value, (int, float)):
        try:
            ts = float(value)
            if ts > 1e12:  # Likely milliseconds
                ts = ts / 1000.0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return _to_local(dt)
        except (OSError, OverflowError, ValueError):
            return str(value)

    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return ""
        try:
            dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
            return _to_local(dt)
        except ValueError:
            return cleaned

    return str(value)


def _first_non_empty(*values: Any) -> str:
    """Return the first non-empty value from the arguments."""
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        elif isinstance(value, (int, float)):
            return _format_number(value)
        elif isinstance(value, list):
            if value:
                return ", ".join(str(item) for item in value if item is not None)
        else:
            return str(value)
    return ""


def _normalize_duration(value: Any) -> str:
    """Format a duration-like value to two decimal places when possible."""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return _first_non_empty(value)


def _filter_primary_drafts(drafts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return priority_order 1 drafts only; fallback to the first draft."""
    if not drafts:
        return drafts

    primary: List[Dict[str, Any]] = []
    for draft in drafts:
        if not isinstance(draft, dict):
            continue
        try:
            priority_val = int(draft.get("priority_order"))
        except (TypeError, ValueError):
            priority_val = None
        if priority_val == 1:
            primary.append(draft)

    if primary:
        return primary
    return drafts[:1]


def _row(label: str, value: str) -> str:
    """Generate a table row with label and value."""
    return f"<tr><th>{html.escape(label)}</th><td>{html.escape(value) if value else ''}</td></tr>"


def _render_filters(filters: Dict[str, Any]) -> str:
    """Render query filters as table rows."""
    if not isinstance(filters, dict):
        return ""
    rows = [
        _row("Org Id", _first_non_empty(filters.get('org_id'))),
        _row("Customer Name", _first_non_empty(filters.get('customer_name'))),
        _row("Status", _first_non_empty(filters.get('status'))),
        _row("Limit", _first_non_empty(filters.get('limit'))),
        _row("Include Operations", str(bool(filters.get('include_operations')))),
        _row("Include Scores", str(bool(filters.get('include_scores')))),
    ]
    return "".join(rows)


def _render_customer_details(details: Optional[Dict[str, Any]]) -> str:
    """Render customer details as table rows. FIX: Flatten nested profile_data and filter empty fields."""
    if not isinstance(details, dict) or not details:
        return "<div class='muted'>No customer details available.</div>"

    rows = []
    for key, val in details.items():
        # Filter out empty values
        if val is None or val == "" or val == [] or val == {}:
            continue

        label = _friendly_key(str(key))
        # FIX #3: Detect and flatten nested profile_data
        if key == "profile_data" and isinstance(val, dict):
            # Check if there's a nested profile_data inside
            inner_profile = val.get("profile_data")
            if isinstance(inner_profile, dict):
                # Use the inner profile_data and flatten it
                for inner_k, inner_v in inner_profile.items():
                    # Filter empty inner values
                    if inner_v is None or inner_v == "" or inner_v == [] or inner_v == {}:
                        continue
                    if isinstance(inner_v, (dict, list)):
                        # Render complex values as nested structure
                        inner_html = "<div class='nested-card'>" + _render_value(inner_v) + "</div>"
                        rows.append(f"<tr><th>{html.escape(_friendly_key(str(inner_k)))}</th><td>{inner_html}</td></tr>")
                    else:
                        rows.append(_row(_friendly_key(str(inner_k)), _first_non_empty(inner_v)))
            else:
                # No nested profile_data, render the dict normally
                inner_rows = []
                for inner_k, inner_v in val.items():
                    # Filter empty inner values
                    if inner_v is None or inner_v == "" or inner_v == [] or inner_v == {}:
                        continue
                    if isinstance(inner_v, (dict, list)):
                        inner_html = "<div class='nested-card'>" + _render_value(inner_v) + "</div>"
                        inner_rows.append(f"<tr><th>{html.escape(_friendly_key(str(inner_k)))}</th><td>{inner_html}</td></tr>")
                    else:
                        inner_rows.append(_row(_friendly_key(str(inner_k)), _first_non_empty(inner_v)))
                if inner_rows:  # Only add if there are non-empty rows
                    rows.append(
                        "<tr><th>Profile Data</th><td><table>"
                        + "".join(inner_rows)
                        + "</table></td></tr>"
                    )
        else:
            rows.append(_row(label, _first_non_empty(val)))
    return "".join(rows) if rows else "<div class='muted'>No customer details available.</div>"


def _render_lead_scores(lead_scores: Any) -> str:
    """Render lead scores as table rows. FIX: Render criteria_breakdown as structured data and optimize layout."""
    if not isinstance(lead_scores, list) or not lead_scores:
        return "<tr><td colspan='3'>No lead scores found.</td></tr>"
    parts = []
    for entry in lead_scores:
        if not isinstance(entry, dict):
            continue
        criteria = entry.get("criteria_breakdown")
        criteria_html = ""
        # FIX #1: Render criteria_breakdown as structured data instead of raw JSON
        if isinstance(criteria, dict):
            crit_rows = []
            idx = 0
            for c_key, c_val in criteria.items():
                idx += 1
                # Filter out empty values
                if c_val is None or c_val == "" or c_val == {} or c_val == []:
                    continue

                # Check if the value is a dict with score/justification
                if isinstance(c_val, dict):
                    score = c_val.get('score', '')
                    justification = c_val.get('justification', '')
                    # Skip if both are empty
                    if not score and not justification:
                        continue
                    # Optimized layout: number and category on same line, content below
                    crit_rows.append(
                        f"<div class='criteria-item'>"
                        f"<div class='criteria-header'>"
                        f"<span class='criteria-num'>{idx}</span>"
                        f"<span class='criteria-label'>{html.escape(_friendly_key(str(c_key)))}</span>"
                        f"</div>"
                        f"<div class='criteria-content'>"
                        f"<div><strong>Score:</strong> {html.escape(str(score))}</div>"
                        f"<div>{html.escape(str(justification))}</div>"
                        f"</div>"
                        f"</div>"
                    )
                else:
                    val_str = _first_non_empty(c_val)
                    if val_str:
                        crit_rows.append(
                            f"<div class='criteria-item'>"
                            f"<div class='criteria-header'>"
                            f"<span class='criteria-num'>{idx}</span>"
                            f"<span class='criteria-label'>{html.escape(_friendly_key(str(c_key)))}</span>"
                            f"</div>"
                            f"<div class='criteria-content'>{html.escape(val_str)}</div>"
                            f"</div>"
                        )
            if crit_rows:
                criteria_html = "<div class='criteria-list'>" + "".join(crit_rows) + "</div>"
        parts.append(
            "<tr>"
            f"<td>{html.escape(_first_non_empty(entry.get('product_name') or entry.get('product_id')))}</td>"
            f"<td>{html.escape(_format_number(entry.get('score')))}</td>"
            f"<td>{html.escape(_format_timestamp(entry.get('created_at')))}</td>"
            "</tr>"
            + (f"<tr><td colspan='3'>{criteria_html}</td></tr>" if criteria_html else "")
        )
    return "".join(parts) or "<tr><td colspan='3'>No lead scores found.</td></tr>"


def _render_email_drafts(drafts: Any) -> str:
    """Render email drafts with rendered HTML preview."""
    if not isinstance(drafts, list) or not drafts:
        return "<div class='muted'>No email drafts found.</div>"
    drafts = _filter_primary_drafts(drafts)
    if not drafts:
        return "<div class='muted'>No email drafts found.</div>"
    seen = set()
    rows = []
    for idx, draft in enumerate(drafts, start=1):
        if not isinstance(draft, dict):
            continue
        key = draft.get('draft_id') or draft.get('id') or id(draft)
        if key in seen:
            continue
        seen.add(key)
        subject = draft.get("subject") or f"Draft {idx}"
        created = _format_timestamp(draft.get("created_at"))
        draft_type = _first_non_empty(draft.get("draft_type") or draft.get("type"))
        priority = _first_non_empty(
            draft.get("priority_order"),
            (draft.get("metadata") or {}).get("priority_order"),
        )
        chips = []
        if priority:
            chips.append(f"<span class='chip'>Priority {html.escape(str(priority))}</span>")
        if draft_type:
            chips.append(f"<span class='chip'>{html.escape(draft_type)}</span>")
        if created:
            chips.append(f"<span class='chip'>{html.escape(created)}</span>")
        meta = "".join(chips)
        body_html = draft.get("content") or draft.get("email_body") or draft.get("body_html") or ""
        escaped_srcdoc = html.escape(body_html, quote=True)
        rows.append(
            "<div class='draft'>"
            f"<h4>{html.escape(subject)}</h4>"
            + (f"<div class='chips'>{meta}</div>" if meta else "")
            + f"<iframe class='iframe-draft' sandbox srcdoc=\"{escaped_srcdoc}\" loading='lazy'></iframe>"
            + "</div>"
        )
    return "".join(rows)


def _render_stage_cards(stages: Any) -> str:
    """Render stages as stacked cards with cleaned fields."""
    if not isinstance(stages, list) or not stages:
        return "<div class='muted'>No stages available.</div>"

    cards: List[str] = []
    for idx, stage in enumerate(stages, start=1):
        if not isinstance(stage, dict):
            continue

        stage_name = _friendly_key(
            str(
                stage.get("stage_name")
                or stage.get("stage")
                or stage.get("executor_name")
                or stage.get("executor")
                or f"Stage {idx}"
            )
        )

        # Clean top-level fields
        cleaned = _strip_keys(
            stage,
            drop_keys={"chain_index", "executor_name", "executor", "timing", "start_time", "end_time", "stage"},
            drop_id_like=True,
        ) or {}

        output_data = cleaned.pop("output_data", None)
        draft_section = ""
        primary_priority = None
        if isinstance(output_data, dict):
            # Capture drafts before stripping keys
            drafts = output_data.get("drafts") or output_data.get("email_drafts")
            nested_data = output_data.get("data")
            if isinstance(nested_data, dict):
                drafts = drafts or nested_data.get("drafts") or nested_data.get("email_drafts")

            output_data = _strip_keys(
                output_data,
                drop_keys={"start_time", "end_time", "stage", "timing", "drafts", "email_drafts"},
                drop_id_like=True,
            ) or None

            # Remove any lingering draft keys after stripping
            if isinstance(output_data, dict):
                output_data.pop("drafts", None)
                output_data.pop("email_drafts", None)
                data_block = output_data.get("data")
                if isinstance(data_block, dict):
                    data_block.pop("drafts", None)
                    data_block.pop("email_drafts", None)
                    if not data_block:
                        output_data.pop("data", None)

            if isinstance(drafts, list) and drafts:
                drafts = _filter_primary_drafts(drafts)
                if drafts:
                    primary_priority = drafts[0].get("priority_order") or (drafts[0].get("metadata") or {}).get("priority_order")
                first = drafts[0]
                subject = _first_non_empty(first.get("subject"), "Email Draft")
                body = first.get("email_body") or first.get("body_html") or first.get("content") or ""
                recipient = _first_non_empty(first.get("recipient_name") or (first.get("metadata") or {}).get("recipient_name"))
                email_type = _first_non_empty(
                    first.get("email_type")
                    or (first.get("metadata") or {}).get("email_type")
                    or first.get("draft_type")
                    or first.get("type")
                )
                chips = []
                if primary_priority is not None:
                    chips.append(f"<span class='chip'>Priority {html.escape(str(primary_priority))}</span>")
                if recipient:
                    chips.append(f"<span class='chip'>{html.escape(recipient)}</span>")
                if email_type:
                    chips.append(f"<span class='chip'>{html.escape(email_type)}</span>")

                iframe = (
                    "<div class='html-preview'>"
                    "<div class='html-preview-label'>Rendered HTML</div>"
                    f"<iframe class='html-iframe' sandbox srcdoc=\"{html.escape(body, quote=True)}\"></iframe>"
                    "</div>"
                )

                draft_section = (
                    "<div class='stage-subsection'>"
                    "<h4>Email Draft</h4>"
                    f"<h5>{html.escape(subject)}</h5>"
                    + ("<div class='chips'>" + "".join(chips) + "</div>" if chips else "")
                    + iframe
                    + "</div>"
                )

                # Hide the raw output_data block when showing the draft to avoid clutter
                output_data = None

            if isinstance(output_data, dict) and "duration_seconds" in output_data:
                output_data["duration_seconds"] = _normalize_duration(output_data.get("duration_seconds"))

        # Normalize durations
        if "duration_seconds" in cleaned:
            cleaned["duration_seconds"] = _normalize_duration(cleaned.get("duration_seconds"))

        # Remove stage labels from cleaned after capturing
        cleaned.pop("stage_name", None)
        cleaned.pop("stage", None)

        status = cleaned.pop("execution_status", None) or cleaned.pop("status", None)
        order = cleaned.pop("runtime_index", None) or cleaned.pop("order", None)
        created = cleaned.pop("created_at", None) or cleaned.pop("updated_at", None)

        meta_rows: List[str] = []
        if primary_priority is not None:
            meta_rows.append(f"<div class='kv'><div class='k'>Priority Order</div><div class='v'>{html.escape(str(primary_priority))}</div></div>")
        if status:
            meta_rows.append(f"<div class='kv'><div class='k'>Status</div><div class='v'>{html.escape(_friendly_key(str(status)))}</div></div>")
        if "duration_seconds" in cleaned and cleaned.get("duration_seconds") is not None:
            meta_rows.append(f"<div class='kv'><div class='k'>Duration Seconds</div><div class='v'>{html.escape(str(cleaned.get('duration_seconds')))}</div></div>")
            cleaned.pop("duration_seconds", None)
        if order is not None and order != "":
            meta_rows.append(f"<div class='kv'><div class='k'>Order</div><div class='v'>{html.escape(_friendly_key(str(order)))}</div></div>")
        if created:
            meta_rows.append(f"<div class='kv'><div class='k'>Created At</div><div class='v'>{html.escape(_friendly_key(str(created)))}</div></div>")

        # Render remaining fields (excluding output_data already handled)
        for key, val in list(cleaned.items()):
            if val in (None, {}, []):
                continue
            label = _friendly_key(str(key))
            if isinstance(val, (dict, list)):
                meta_rows.append(f"<div class='kv'><div class='k'>{html.escape(label)}</div><div class='v'>{_render_value(val)}</div></div>")
            else:
                meta_rows.append(f"<div class='kv'><div class='k'>{html.escape(label)}</div><div class='v'>{html.escape(_friendly_key(str(val)))}</div></div>")

        body_parts: List[str] = []
        if meta_rows:
            body_parts.append("".join(meta_rows))
        if output_data:
            body_parts.append(
                "<div class='stage-subsection'>"
                "<h4>Output Data</h4>"
                f"{_render_value(output_data, html_render_keys=DEFAULT_HTML_RENDER_KEYS)}"
                "</div>"
            )
        if draft_section:
            body_parts.append(
                "<div class='stage-subsection'>"
                f"{draft_section}"
                "</div>"
            )

        cards.append(
            "<div class='stage-card'>"
            "<div class='stage-header'>"
            f"<span class='stage-badge'>#{idx}</span>"
            f"<div class='stage-title'>{html.escape(stage_name)}</div>"
            "</div>"
            + "".join(body_parts)
            + "</div>"
        )

    return "".join(cards) or "<div class='muted'>No stages available.</div>"


def _render_query_results(payload: Dict[str, Any], raw_json: str) -> str:
    """Custom renderer for query sales processes."""
    filters = payload.get("filters") if isinstance(payload, dict) else {}
    results = payload.get("results") if isinstance(payload, dict) else []
    raw_escaped = html.escape(raw_json)

    filter_rows = []
    if isinstance(filters, dict):
        for key in ("org_id", "customer_name", "status", "limit", "include_operations", "include_scores"):
            val = filters.get(key)
            if val not in (None, "", [], {}):
                filter_rows.append(f"<div class='kv'><div class='k'>{html.escape(_friendly_key(str(key)))}</div><div class='v'>{html.escape(str(val))}</div></div>")

    cards: List[str] = []
    if isinstance(results, list):
        for idx, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                continue

            cleaned_item = _strip_keys(item, drop_keys=set(), drop_id_like=True) or {}

            # Task overview (drop customer details)
            overview_rows = []
            for key in ("task_id", "status", "customer", "team_name", "team_id", "current_stage", "created_at", "updated_at"):
                val = cleaned_item.get(key)
                if val not in (None, "", [], {}):
                    overview_rows.append(f"<div class='kv'><div class='k'>{html.escape(_friendly_key(str(key)))}</div><div class='v'>{html.escape(str(val))}</div></div>")

            lead_scores = cleaned_item.get("lead_scores")
            lead_block = ""
            if isinstance(lead_scores, list) and lead_scores:
                lead_parts: List[str] = []
                for score in lead_scores:
                    if not isinstance(score, dict):
                        continue
                    score_clean = _strip_keys(score, drop_keys=set(), drop_id_like=True) or {}
                    product = score_clean.get("product_name") or score_clean.get("product_id") or ""
                    val = score_clean.get("score")
                    created = score_clean.get("created_at")
                    lead_parts.append(
                        "<div class='kv'>"
                        f"<div class='k'>{html.escape(_friendly_key(str(product or 'Product')))}</div>"
                        f"<div class='v'>{html.escape(_friendly_key(str(val)))}"
                        + (f" <span class='chip'>{html.escape(_friendly_key(str(created)))}</span>" if created else "")
                        + "</div></div>"
                    )
                lead_block = "".join(lead_parts)

            stage_cards = _render_stage_cards(cleaned_item.get("stages"))

            cards.append(
                (
                    "<div class='card'>"
                    "<div class='card-header'>"
                    f"<span class='result-badge'>#{idx}</span>"
                    f"<h2>Result {idx}</h2>"
                    "</div>"
                    "<div class='section'>"
                    "<h3>Task Overview</h3>"
                    f"{''.join(overview_rows) if overview_rows else '<div class=\"muted\">No task info.</div>'}"
                    "</div>"
                    + (
                        "<div class='section'><h3>Lead Scores</h3>" + (lead_block or "<div class='muted'>No lead scores.</div>") + "</div>"
                        if lead_scores else ""
                    )
                    + "<div class='section'><h3>Stages</h3>" + stage_cards + "</div>"
                    + "</div>"
                )
            )

    style = (
        "body{font-family:'Segoe UI','Helvetica Neue',sans-serif;background:#f8fafc;color:#0f172a;line-height:1.6;padding:24px;}"
        ".container{width:100%;max-width:none;margin:0 auto;}"
        ".section{margin-bottom:24px;}"
        ".card{background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:18px 20px;box-shadow:0 2px 8px rgba(15,23,42,0.05);margin-bottom:18px;}"
        ".card-header{display:flex;align-items:center;gap:12px;margin-bottom:12px;}"
        ".result-badge{display:inline-flex;align-items:center;justify-content:center;background:#e0f2fe;color:#0f172a;padding:6px 10px;border-radius:999px;font-weight:700;font-size:14px;}"
        ".kv{display:grid;grid-template-columns:200px minmax(0,1fr);gap:8px 14px;padding:8px 0;border-bottom:1px solid #e2e8f0;}"
        ".kv:last-child{border-bottom:none;}"
        ".k{font-weight:600;color:#0f172a;}"
        ".v{color:#0f172a;}"
        ".chip{background:#e0f2fe;color:#0f172a;padding:2px 8px;border-radius:999px;font-weight:600;font-size:12px;margin-left:8px;}"
        ".stage-card{border:1px solid #e2e8f0;background:#f8fafc;border-radius:10px;padding:12px 14px;margin-bottom:12px;}"
        ".stage-header{display:flex;align-items:center;gap:10px;margin-bottom:8px;}"
        ".stage-badge{display:inline-flex;align-items:center;justify-content:center;background:#c7d2fe;color:#0f172a;font-weight:700;border-radius:8px;padding:4px 8px;min-width:32px;}"
        ".stage-title{font-weight:700;color:#0f172a;font-size:15px;}"
        ".stage-subsection{margin-top:10px;}"
        ".section-header{font-weight:700;color:#0f172a;background:#e2e8f0;padding:8px 12px;border-radius:6px;margin:10px 0 6px 0;font-size:13px;}"
        ".list-item{border:1px solid #e2e8f0;background:#f8fafc;border-radius:8px;padding:10px;margin:8px 0;}"
        ".nested-card{border:1px solid #e2e8f0;background:#f8fafc;border-radius:8px;padding:10px;margin-top:6px;}"
        ".text{background:#e2e8f0;border-radius:6px;padding:4px 8px;display:inline-block;}"
        ".muted{color:#64748b;font-style:italic;}"
        ".html-preview{margin-top:6px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;}"
        ".html-preview-label{background:#0f172a;color:#e2e8f0;padding:6px 10px;font-weight:700;font-size:12px;}"
        ".html-iframe{width:100%;min-height:240px;border:0;display:block;}"
        ".html-raw{margin:0;padding:10px;}"
        ".pre-inline{background:#0f172a;color:#e2e8f0;padding:8px;border-radius:8px;overflow:auto;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word;}"
    )

    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'>"
        "<title>FuseSell AI - Query Results</title>"
        f"<style>{style}</style>"
        "</head><body>"
        "<div class='container'>"
        "<h1>FuseSell AI - Query Results</h1>"
        + ("<div class='section'><h3>Filters</h3>" + ("".join(filter_rows) or "<div class='muted'>No filters.</div>") + "</div>" if filter_rows else "")
        + ("<div class='section'><h2>Results</h2>" + ("".join(cards) or "<div class='muted'>No results.</div>") + "</div>")
        + "<details><summary>View Raw JSON</summary>"
        "<pre class='pre-inline'>"
        f"{raw_escaped}"
        "</pre></details>"
        "</div>"
        "</body></html>"
    )


# =============================================================================
# Start Sales Process (fallback parity with flow script)
# =============================================================================

def _start_collect_customer_blob(payload: Dict[str, Any]) -> Dict[str, Any]:
    stage_results = payload.get("stage_results") or {}
    for candidate in (
        payload.get("customer_data"),
        payload.get("customer"),
        stage_results.get("data_preparation", {}).get("data"),
        stage_results.get("data_acquisition", {}).get("data"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _start_build_process_summary(payload: Dict[str, Any]) -> Dict[str, str]:
    perf = payload.get("performance_analytics") or {}
    insights = perf.get("performance_insights") or {}
    stage_timings = perf.get("stage_timings") or []
    return {
        "execution_id": _first_non_empty(payload.get("execution_id")),
        "status": _first_non_empty(payload.get("status")),
        "started_at": _format_timestamp(payload.get("started_at")),
        "duration_seconds": _format_number(payload.get("duration_seconds")),
        "stage_count": _first_non_empty(perf.get("stage_count") or len(stage_timings)),
        "avg_stage_duration": _format_number(perf.get("average_stage_duration")),
        "pipeline_overhead": _format_percent(perf.get("pipeline_overhead_percentage")),
        "slowest_stage": _first_non_empty((insights.get("slowest_stage") or {}).get("name")),
        "fastest_stage": _first_non_empty((insights.get("fastest_stage") or {}).get("name")),
    }


def _start_build_stage_rows(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    perf = payload.get("performance_analytics") or {}
    stage_timings = perf.get("stage_timings") or []
    total_duration = perf.get("total_stage_duration_seconds") or perf.get("total_duration_seconds")

    if isinstance(stage_timings, list) and stage_timings:
        for timing in stage_timings:
            if not isinstance(timing, dict):
                continue
            duration = timing.get("duration_seconds")
            percent = timing.get("percentage_of_total")
            if percent is None and duration and total_duration:
                try:
                    percent = (float(duration) / float(total_duration)) * 100
                except Exception:
                    percent = None
            rows.append(
                {
                    "stage": _first_non_empty(timing.get("stage")),
                    "duration": _format_number(duration),
                    "percent": _format_percent(percent),
                    "start": _format_timestamp(timing.get("start_time")),
                    "end": _format_timestamp(timing.get("end_time")),
                }
            )
    else:
        stage_results = payload.get("stage_results")
        if isinstance(stage_results, dict):
            durations: List[float] = []
            for stage_payload in stage_results.values():
                timing = stage_payload.get("timing") if isinstance(stage_payload, dict) else None
                if isinstance(timing, dict):
                    durations.append(timing.get("duration_seconds") or 0)
            total = float(sum(durations)) if durations else None
            for stage_name, stage_payload in stage_results.items():
                timing = stage_payload.get("timing") if isinstance(stage_payload, dict) else None
                duration = timing.get("duration_seconds") if isinstance(timing, dict) else None
                percent = None
                if duration and total:
                    try:
                        percent = (float(duration) / total) * 100
                    except Exception:
                        percent = None
                rows.append(
                    {
                        "stage": _friendly_key(stage_name),
                        "duration": _format_number(duration),
                        "percent": _format_percent(percent),
                        "start": _format_timestamp(timing.get("start_time") if isinstance(timing, dict) else None),
                        "end": _format_timestamp(timing.get("end_time") if isinstance(timing, dict) else None),
                    }
                )
    return rows


def _start_build_customer_info(payload: Dict[str, Any]) -> Dict[str, str]:
    blob = _start_collect_customer_blob(payload)
    company = blob.get("companyInfo") if isinstance(blob, dict) else {}
    primary = blob.get("primaryContact") if isinstance(blob, dict) else {}
    financial = blob.get("financialInfo") if isinstance(blob, dict) else {}
    health = financial.get("healthAssessment") if isinstance(financial, dict) else {}

    revenue = ""
    revenue_history = financial.get("revenueLastThreeYears") if isinstance(financial, dict) else None
    if isinstance(revenue_history, list) and revenue_history:
        parts = []
        for entry in revenue_history:
            if not isinstance(entry, dict):
                continue
            year = entry.get("year")
            rev = entry.get("revenue")
            if year is None and rev is None:
                continue
            parts.append(f"{year}: {_format_number(rev)}")
        revenue = ", ".join(parts)

    recommendations = ""
    recs = health.get("recommendations") if isinstance(health, dict) else None
    if isinstance(recs, list) and recs:
        recommendations = "; ".join(str(item) for item in recs if item is not None)

    funding_sources = ""
    sources = financial.get("fundingSources") if isinstance(financial, dict) else None
    if isinstance(sources, list) and sources:
        funding_sources = ", ".join(str(item) for item in sources if item is not None)
    elif sources:
        funding_sources = str(sources)

    industries = blob.get("company_industries")
    industry = (
        _first_non_empty(company.get("industry") if isinstance(company, dict) else None)
        or (", ".join(industries) if isinstance(industries, list) and industries else "")
    )

    return {
        "company_name": _first_non_empty(company.get("name") if isinstance(company, dict) else None, blob.get("company_name")),
        "industry": industry,
        "website": _first_non_empty(company.get("website") if isinstance(company, dict) else None, blob.get("company_website")),
        "contact_name": _first_non_empty(
            primary.get("name") if isinstance(primary, dict) else None,
            blob.get("contact_name"),
            blob.get("customer_name"),
        ),
        "contact_email": _first_non_empty(
            primary.get("email") if isinstance(primary, dict) else None,
            blob.get("customer_email"),
            blob.get("recipient_address"),
        ),
        "funding_sources": funding_sources,
        "revenue_last_three_years": revenue,
        "overall_rating": _first_non_empty(health.get("overallRating") if isinstance(health, dict) else None),
        "recommendations": recommendations,
    }


def _start_build_pain_points(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    blob = _start_collect_customer_blob(payload)
    pain_points = blob.get("painPoints") if isinstance(blob, dict) else None
    rows: List[Dict[str, str]] = []
    if isinstance(pain_points, list):
        for point in pain_points:
            if not isinstance(point, dict):
                continue
            rows.append(
                {
                    "category": _first_non_empty(point.get("category")),
                    "description": _first_non_empty(point.get("description")),
                    "impact": _first_non_empty(point.get("impact")),
                }
            )
    return rows


def _start_build_tech_stack(payload: Dict[str, Any]) -> List[str]:
    blob = _start_collect_customer_blob(payload)
    tech_and_innovation = blob.get("technologyAndInnovation") if isinstance(blob, dict) else {}
    stacks: List[str] = []
    for candidate in (
        blob.get("currentTechStack"),
        tech_and_innovation.get("likelyTechStack") if isinstance(tech_and_innovation, dict) else None,
        tech_and_innovation.get("recommendedTechnologies") if isinstance(tech_and_innovation, dict) else None,
    ):
        if isinstance(candidate, list):
            stacks.extend(str(item) for item in candidate if item is not None)
    seen = set()
    deduped: List[str] = []
    for item in stacks:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _start_build_innovation_points(payload: Dict[str, Any]) -> List[str]:
    blob = _start_collect_customer_blob(payload)
    tech_and_innovation = blob.get("technologyAndInnovation") if isinstance(blob, dict) else {}
    points: List[str] = []
    for candidate in (
        tech_and_innovation.get("technologyGaps") if isinstance(tech_and_innovation, dict) else None,
        tech_and_innovation.get("innovationOpportunities") if isinstance(tech_and_innovation, dict) else None,
    ):
        if isinstance(candidate, list):
            points.extend(str(item) for item in candidate if item is not None)
    return points


def _start_build_lead_fit(payload: Dict[str, Any]) -> Dict[str, str]:
    stage_results = payload.get("stage_results") or {}
    lead_stage = stage_results.get("lead_scoring", {}) if isinstance(stage_results, dict) else {}
    lead_data = lead_stage.get("data") if isinstance(lead_stage, dict) else {}
    lead_scores = []
    if isinstance(lead_data, dict):
        scores = lead_data.get("lead_scoring")
        if isinstance(scores, list) and scores:
            lead_scores = scores
    lead_entry = lead_scores[0] if lead_scores else {}
    analysis = lead_data.get("analysis") if isinstance(lead_data, dict) else {}
    recommended = analysis.get("recommended_product") if isinstance(analysis, dict) else {}
    scores = lead_entry.get("scores") if isinstance(lead_entry, dict) else {}
    return {
        "product_name": _first_non_empty(
            lead_entry.get("product_name"),
            recommended.get("product_name") if isinstance(recommended, dict) else None,
        ),
        "industry_fit": _format_number((scores.get("industry_fit") or {}).get("score") if isinstance(scores, dict) else None),
        "pain_points_addressed": _format_number((scores.get("pain_points") or {}).get("score") if isinstance(scores, dict) else None),
        "geographic_market_fit": _format_number((scores.get("geographic_market_fit") or {}).get("score") if isinstance(scores, dict) else None),
        "total_weighted_score": _format_number(lead_entry.get("total_weighted_score") if isinstance(lead_entry, dict) else None),
        "recommendation": _first_non_empty(
            (analysis.get("insights") or [None])[0] if isinstance(analysis, dict) and isinstance(analysis.get("insights"), list) else None
        ),
    }


def _start_filter_primary_drafts(drafts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only priority_order 1 drafts; fallback to the first draft."""
    if not drafts:
        return drafts

    primary: List[Dict[str, Any]] = []
    for draft in drafts:
        if not isinstance(draft, dict):
            continue
        try:
            priority_val = int(draft.get("priority_order"))
        except (TypeError, ValueError):
            priority_val = None
        if priority_val == 1:
            primary.append(draft)

    if primary:
        return primary
    return drafts[:1]


def _start_collect_email_drafts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    drafts: List[Dict[str, Any]] = []
    seen_ids = set()

    for candidate in (
        payload.get("email_drafts"),
        payload.get("stage_results", {}).get("initial_outreach", {}).get("data", {}).get("email_drafts"),
    ):
        if not isinstance(candidate, list):
            continue
        for item in candidate:
            if not isinstance(item, dict):
                continue
            dedupe_key = item.get("draft_id") or item.get("id") or id(item)
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            drafts.append(item)
    return drafts


def _start_extract_reminder_time(payload: Dict[str, Any]) -> Optional[str]:
    """Extract reminder scheduled_time from payload or stage results."""
    if not isinstance(payload, dict):
        return None

    stage_results = payload.get("stage_results", {})
    reminder_candidates = [payload.get("reminder_schedule")]
    if isinstance(stage_results, dict):
        initial_outreach = stage_results.get("initial_outreach", {})
        if isinstance(initial_outreach, dict):
            reminder_candidates.append(initial_outreach.get("reminder_schedule"))
            io_data = initial_outreach.get("data", {})
            if isinstance(io_data, dict):
                reminder_candidates.append(io_data.get("reminder_schedule"))

    for candidate in reminder_candidates:
        if isinstance(candidate, dict):
            scheduled = candidate.get("scheduled_time")
            if scheduled:
                return str(scheduled)
    return None


def _start_format_reminder_time(value: Any) -> str:
    """Normalize reminder time into a local time string (HH:MM DD/MM/YYYY)."""
    return _format_timestamp(value)


def _render_start_email_drafts(drafts: List[Dict[str, Any]], reminder_time: Optional[str] = None) -> str:
    """Render drafts in the compact start-sales style."""
    parts: List[str] = []
    formatted_reminder = _start_format_reminder_time(reminder_time)
    if formatted_reminder:
        parts.append(
            "<div class='chips'>"
            f"<span class='chip chip-soft'>Reminder scheduled: {html.escape(formatted_reminder)}</span>"
            "</div>"
        )
    if not drafts:
        parts.append("<div class='muted'>No email drafts generated.</div>")
        return "".join(parts)
    for idx, draft in enumerate(drafts, start=1):
        subject = draft.get("subject") or f"Draft {idx}"
        priority = _first_non_empty(draft.get("priority_order"), (draft.get("metadata") or {}).get("priority_order"))
        recipient = _first_non_empty(
            draft.get("recipient_name"),
            draft.get("recipient_email"),
            (draft.get("metadata") or {}).get("recipient_name"),
        )
        chips = []
        if priority:
            chips.append(f"<span class='chip chip-soft'>Priority {html.escape(str(priority))}</span>")
        if recipient:
            chips.append(f"<span class='chip chip-soft'>{html.escape(str(recipient))}</span>")
        body_html = draft.get("email_body") or draft.get("body_html") or draft.get("html_body") or ""

        # Extract body content if the email_body is a full HTML document
        body_content = body_html
        if body_html.strip().lower().startswith(('<!doctype', '<html')):
            # Extract content between <body> tags if present
            body_match = re.search(r'<body[^>]*>(.*?)</body>', body_html, re.DOTALL | re.IGNORECASE)
            if body_match:
                body_content = body_match.group(1)

        iframe_doc = (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'>"
            "<style>"
            "body{margin:0;padding:20px;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;color:#0f172a;"
            "line-height:1.6;background:#ffffff;}"
            "h1,h2,h3,h4,h5{margin:0 0 10px 0;color:#0f172a;}"
            "p{margin:0 0 12px 0;}"
            "ul{padding-left:20px;margin:0 0 12px 0;}"
            "li{margin:6px 0;}"
            "strong{font-weight:700;}"
            "</style>"
            "</head><body>"
            f"{body_content}"
            "</body></html>"
        )
        encoded_doc = base64.b64encode(iframe_doc.encode("utf-8")).decode("ascii")
        iframe = (
            "<div class='html-preview start-preview'>"
            "<div class='html-preview-label start-label'>Rendered HTML</div>"
            f"<iframe class='html-iframe' sandbox src=\"data:text/html;charset=utf-8;base64,{encoded_doc}\" loading='lazy'></iframe>"
            "</div>"
        )
        parts.append(
            "<div class='draft start-draft'>"
            "<h3>Email Draft</h3>"
            f"<h4>{html.escape(subject)}</h4>"
            + ("<div class='chips'>" + "".join(chips) + "</div>" if chips else "")
            + iframe
            + "</div>"
        )
    return "".join(parts)


def _render_start_sales_process_html(payload: Dict[str, Any], raw_json: str) -> str:
    summary = _start_build_process_summary(payload)
    stages = _start_build_stage_rows(payload)
    customer = _start_build_customer_info(payload)
    pains = _start_build_pain_points(payload)
    tech_stack = _start_build_tech_stack(payload)
    innovations = _start_build_innovation_points(payload)
    lead_fit = _start_build_lead_fit(payload)
    drafts = _start_collect_email_drafts(payload)
    drafts = _start_filter_primary_drafts(drafts)
    reminder_time = _start_extract_reminder_time(payload)

    def _row(label: str, value: str) -> str:
        return f"<tr><th>{html.escape(label)}</th><td>{html.escape(value) if value else ''}</td></tr>"

    stage_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(row.get('stage', ''))}</td>"
        f"<td>{html.escape(row.get('duration', ''))}</td>"
        f"<td>{html.escape(row.get('percent', ''))}</td>"
        f"<td>{html.escape(row.get('start', ''))}</td>"
        f"<td>{html.escape(row.get('end', ''))}</td>"
        "</tr>"
        for row in stages
    )

    pain_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(pain.get('category', ''))}</td>"
        f"<td>{html.escape(pain.get('description', ''))}</td>"
        f"<td>{html.escape(pain.get('impact', ''))}</td>"
        "</tr>"
        for pain in pains
    )

    tech_chips = "".join(f"<span class='chip'>{html.escape(item)}</span>" for item in tech_stack)
    innovation_list = "".join(f"<li>{html.escape(item)}</li>" for item in innovations)

    draft_html = _render_start_email_drafts(drafts, reminder_time)

    raw_escaped = html.escape(raw_json)
    style = (
        "html,body{margin:0;padding:0;}"
        "body{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;color:#0f172a;background:#f8fafc;line-height:1.6;}"
        "*{box-sizing:border-box;}"
        ".container{max-width:1200px;margin:40px auto;background:#fff;border-radius:10px;box-shadow:0 4px 16px rgba(15,23,42,0.07);padding:40px 36px;}"
        "h1,h2,h3,h4{color:#475569;}"
        ".section{margin-bottom:36px;}"
        "table{border-collapse:collapse;width:100%;margin-bottom:24px;table-layout:fixed;}"
        "th,td{text-align:left;padding:10px 14px;border-bottom:1px solid #e2e8f0;word-break:break-word;}"
        "th{background:#e2e8f0;font-weight:600;width:260px;}"
        ".stage-table th,.stage-table td{width:auto;padding:8px;}"
        ".badge{display:inline-block;background:#e0f2fe;color:#0f172a;padding:2px 10px;border-radius:999px;font-weight:600;font-size:13px;}"
        "details{margin-top:16px;}"
        "summary{cursor:pointer;color:#0ea5e9;font-weight:600;}"
        "pre{background:#e2e8f0;border-radius:8px;padding:12px;font-size:13px;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;overflow-x:auto;}"
        "ul{padding-left:18px;}"
        "li{margin:6px 0;}"
        ".chips{display:flex;gap:10px;flex-wrap:wrap;margin:4px 0;}"
        ".chip{background:#e0f2fe;color:#0f172a;padding:4px 14px;border-radius:999px;font-weight:600;font-size:12px;}"
        ".chip-soft{background:#e2e8f0;color:#0f172a;}"
        ".iframe-draft{width:100%;min-height:340px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:16px;}"
        ".draft{margin-bottom:20px;padding:16px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;}"
        ".start-draft{background:#f5f7fb;border:1px solid #e2e8f0;}"
        ".start-preview{margin-top:10px;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;background:#ffffff;}"
        ".start-label{background:#0f172a;color:#f8fafc;padding:10px;font-weight:700;}"
        ".draft-meta{font-size:13px;color:#475569;margin-bottom:8px;}"
        ".kv{display:grid;grid-template-columns:240px minmax(0,1fr);gap:8px 14px;padding:10px 0;border-bottom:1px solid #e2e8f0;align-items:flex-start;}"
        ".kv:last-child{border-bottom:none;}"
        ".k{font-weight:600;color:#0f172a;background:#e2e8f0;border-radius:6px;padding:8px 10px;}"
        ".v{color:#0f172a;min-width:0;}"
        ".text{background:#e2e8f0;border-radius:6px;padding:8px 10px;display:block;width:100%;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere;}"
        ".nested-card{border:1px solid #e2e8f0;background:#f8fafc;border-radius:8px;padding:10px;}"
        ".pre-inline{background:#e2e8f0;color:#0f172a;padding:10px;border-radius:6px;overflow:auto;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;font-size:12px;line-height:1.5;white-space:pre-wrap;word-break:break-word;}"
        ".html-preview{display:flex;flex-direction:column;gap:8px;}"
        ".html-preview-label{font-weight:600;color:#0f172a;font-size:13px;}"
        ".html-iframe{width:100%;min-height:340px;border:0;display:block;}"
        ".html-raw summary{cursor:pointer;color:#0ea5e9;font-weight:600;}"
        "@media (max-width: 900px){.kv{grid-template-columns:minmax(140px,1fr) minmax(0,2fr);padding:8px 10px;}}"
    )

    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'>"
        "<title>FuseSell AI - Sales Process Report</title>"
        f"<style>{style}</style>"
        "</head><body>"
        "<div class='container'>"
        "<h1>FuseSell AI - Sales Process Report</h1>"
        "<div class='section'>"
        "<h2>Process Summary</h2>"
        "<table>"
        f"{_row('Execution Id', summary.get('execution_id', ''))}"
        f"{_row('Status', summary.get('status', ''))}"
        f"{_row('Started At', summary.get('started_at', ''))}"
        f"{_row('Duration Seconds', summary.get('duration_seconds', ''))}"
        f"{_row('Stage Count', summary.get('stage_count', ''))}"
        f"{_row('Avg. Stage Duration', summary.get('avg_stage_duration', ''))}"
        f"{_row('Pipeline Overhead (%)', summary.get('pipeline_overhead', ''))}"
        f"{_row('Slowest Stage', summary.get('slowest_stage', ''))}"
        f"{_row('Fastest Stage', summary.get('fastest_stage', ''))}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Stage Results</h2>"
        "<table class='stage-table'>"
        "<tr><th>Stage</th><th>Duration (s)</th><th>% of Total</th><th>Start Time</th><th>End Time</th></tr>"
        f"{stage_rows_html or '<tr><td colspan=\"5\">No stage timings available.</td></tr>'}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Customer & Company Info</h2>"
        "<table>"
        f"{_row('Company Name', customer.get('company_name', ''))}"
        f"{_row('Industry', customer.get('industry', ''))}"
        f"{_row('Website', customer.get('website', ''))}"
        f"{_row('Contact Name', customer.get('contact_name', ''))}"
        f"{_row('Contact Email', customer.get('contact_email', ''))}"
        f"{_row('Funding Sources', customer.get('funding_sources', ''))}"
        f"{_row('Revenue Last 3 Years', customer.get('revenue_last_three_years', ''))}"
        f"{_row('Overall Rating', customer.get('overall_rating', ''))}"
        f"{_row('Recommendations', customer.get('recommendations', ''))}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Pain Points</h2>"
        "<table>"
        "<tr><th>Category</th><th>Description</th><th>Impact</th></tr>"
        f"{pain_rows_html or '<tr><td colspan=\"3\">No pain points captured.</td></tr>'}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Tech Stack & Innovation</h2>"
        f"<div class='chips'>{tech_chips or '<span class=\"chip\">Not specified</span>'}</div>"
        "<h4>Innovation Gaps & Opportunities</h4>"
        f"<ul>{innovation_list or '<li>No innovation insights captured.</li>'}</ul>"
        "</div>"
        "<div class='section'>"
        "<h2>Lead Scoring - Product Fit</h2>"
        "<table>"
        f"{_row('Product Name', lead_fit.get('product_name', ''))}"
        f"{_row('Industry Fit', lead_fit.get('industry_fit', ''))}"
        f"{_row('Pain Points Addressed', lead_fit.get('pain_points_addressed', ''))}"
        f"{_row('Geographic Market Fit', lead_fit.get('geographic_market_fit', ''))}"
        f"{_row('Total Weighted Score', lead_fit.get('total_weighted_score', ''))}"
        f"{_row('Recommendation', lead_fit.get('recommendation', ''))}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Email Outreach Drafts</h2>"
        "<details open>"
        "<summary>Show All Drafts</summary>"
        f"{draft_html}"
        "</details>"
        "</div>"
        "<div class='section'>"
        "<h2>Raw JSON</h2>"
        "<details>"
        "<summary>View Full Raw JSON</summary>"
        "<pre>"
        f"{raw_escaped}"
        "</pre>"
        "</details>"
        "</div>"
        "</div>"
        "</body></html>"
    )


def _collect_customer_blob(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract customer data from various locations in the payload."""
    stage_results = payload.get("stage_results") or {}
    for candidate in (
        payload.get("customer_data"),
        payload.get("customer"),
        stage_results.get("data_preparation", {}).get("data"),
        stage_results.get("data_acquisition", {}).get("data"),
    ):
        if isinstance(candidate, dict):
            return candidate
    return {}


def _build_process_summary(payload: Dict[str, Any]) -> Dict[str, str]:
    """Build process summary from payload."""
    perf = payload.get("performance_analytics") or {}
    insights = perf.get("performance_insights") or {}
    stage_timings = perf.get("stage_timings") or []
    return {
        "execution_id": _first_non_empty(payload.get("execution_id")),
        "status": _first_non_empty(payload.get("status")),
        "started_at": _first_non_empty(payload.get("started_at")),
        "duration_seconds": _format_number(payload.get("duration_seconds")),
        "stage_count": _first_non_empty(perf.get("stage_count") or len(stage_timings)),
        "avg_stage_duration": _format_number(perf.get("average_stage_duration")),
        "pipeline_overhead": _format_percent(perf.get("pipeline_overhead_percentage")),
        "slowest_stage": _first_non_empty((insights.get("slowest_stage") or {}).get("name")),
        "fastest_stage": _first_non_empty((insights.get("fastest_stage") or {}).get("name")),
    }


def _build_stage_rows(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build stage timing rows from payload."""
    rows: List[Dict[str, str]] = []
    perf = payload.get("performance_analytics") or {}
    stage_timings = perf.get("stage_timings") or []
    total_duration = perf.get("total_stage_duration_seconds") or perf.get("total_duration_seconds")

    if isinstance(stage_timings, list) and stage_timings:
        for timing in stage_timings:
            if not isinstance(timing, dict):
                continue
            duration = timing.get("duration_seconds")
            percent = timing.get("percentage_of_total")
            if percent is None and duration and total_duration:
                try:
                    percent = (float(duration) / float(total_duration)) * 100
                except Exception:
                    percent = None
            rows.append(
                {
                    "stage": _first_non_empty(timing.get("stage")),
                    "duration": _format_number(duration),
                    "percent": _format_percent(percent),
                    "start": _format_timestamp(timing.get("start_time")),
                    "end": _format_timestamp(timing.get("end_time")),
                }
            )
    else:
        stage_results = payload.get("stage_results")
        if isinstance(stage_results, dict):
            durations: List[float] = []
            for stage_payload in stage_results.values():
                timing = stage_payload.get("timing") if isinstance(stage_payload, dict) else None
                if isinstance(timing, dict):
                    durations.append(timing.get("duration_seconds") or 0)
            total = float(sum(durations)) if durations else None
            for stage_name, stage_payload in stage_results.items():
                timing = stage_payload.get("timing") if isinstance(stage_payload, dict) else None
                duration = timing.get("duration_seconds") if isinstance(timing, dict) else None
                percent = None
                if duration and total:
                    try:
                        percent = (float(duration) / total) * 100
                    except Exception:
                        percent = None
                rows.append(
                    {
                        "stage": _friendly_key(stage_name),
                        "duration": _format_number(duration),
                        "percent": _format_percent(percent),
                        "start": _format_timestamp(timing.get("start_time") if isinstance(timing, dict) else None),
                        "end": _format_timestamp(timing.get("end_time") if isinstance(timing, dict) else None),
                    }
                )
    return rows


def _build_customer_info(payload: Dict[str, Any]) -> Dict[str, str]:
    """Build customer info from payload."""
    blob = _collect_customer_blob(payload)
    company = blob.get("companyInfo") if isinstance(blob, dict) else {}
    primary = blob.get("primaryContact") if isinstance(blob, dict) else {}
    financial = blob.get("financialInfo") if isinstance(blob, dict) else {}
    health = financial.get("healthAssessment") if isinstance(financial, dict) else {}

    revenue = ""
    revenue_history = financial.get("revenueLastThreeYears") if isinstance(financial, dict) else None
    if isinstance(revenue_history, list) and revenue_history:
        parts = []
        for entry in revenue_history:
            if not isinstance(entry, dict):
                continue
            year = entry.get("year")
            rev = entry.get("revenue")
            if year is None and rev is None:
                continue
            parts.append(f"{year}: {_format_number(rev)}")
        revenue = ", ".join(parts)

    recommendations = ""
    recs = health.get("recommendations") if isinstance(health, dict) else None
    if isinstance(recs, list) and recs:
        recommendations = "; ".join(str(item) for item in recs if item is not None)

    funding_sources = ""
    sources = financial.get("fundingSources") if isinstance(financial, dict) else None
    if isinstance(sources, list) and sources:
        funding_sources = ", ".join(str(item) for item in sources if item is not None)
    elif sources:
        funding_sources = str(sources)

    industries = blob.get("company_industries")
    industry = (
        _first_non_empty(company.get("industry") if isinstance(company, dict) else None)
        or (", ".join(industries) if isinstance(industries, list) and industries else "")
    )

    return {
        "company_name": _first_non_empty(company.get("name") if isinstance(company, dict) else None, blob.get("company_name")),
        "industry": industry,
        "website": _first_non_empty(company.get("website") if isinstance(company, dict) else None, blob.get("company_website")),
        "contact_name": _first_non_empty(
            primary.get("name") if isinstance(primary, dict) else None,
            blob.get("contact_name"),
            blob.get("customer_name"),
        ),
        "contact_email": _first_non_empty(
            primary.get("email") if isinstance(primary, dict) else None,
            blob.get("customer_email"),
            blob.get("recipient_address"),
        ),
        "funding_sources": funding_sources,
        "revenue_last_three_years": revenue,
        "overall_rating": _first_non_empty(health.get("overallRating") if isinstance(health, dict) else None),
        "recommendations": recommendations,
    }


def _build_pain_points(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build pain points from payload."""
    blob = _collect_customer_blob(payload)
    pain_points = blob.get("painPoints") if isinstance(blob, dict) else None
    rows: List[Dict[str, str]] = []
    if isinstance(pain_points, list):
        for point in pain_points:
            if not isinstance(point, dict):
                continue
            rows.append(
                {
                    "category": _first_non_empty(point.get("category")),
                    "description": _first_non_empty(point.get("description")),
                    "impact": _first_non_empty(point.get("impact")),
                }
            )
    return rows


def _build_tech_stack(payload: Dict[str, Any]) -> List[str]:
    """Build tech stack from payload."""
    blob = _collect_customer_blob(payload)
    tech_and_innovation = blob.get("technologyAndInnovation") if isinstance(blob, dict) else {}
    stacks: List[str] = []
    for candidate in (
        blob.get("currentTechStack"),
        tech_and_innovation.get("likelyTechStack") if isinstance(tech_and_innovation, dict) else None,
        tech_and_innovation.get("recommendedTechnologies") if isinstance(tech_and_innovation, dict) else None,
    ):
        if isinstance(candidate, list):
            stacks.extend(str(item) for item in candidate if item is not None)
    seen = set()
    deduped: List[str] = []
    for item in stacks:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _build_innovation_points(payload: Dict[str, Any]) -> List[str]:
    """Build innovation points from payload."""
    blob = _collect_customer_blob(payload)
    tech_and_innovation = blob.get("technologyAndInnovation") if isinstance(blob, dict) else {}
    points: List[str] = []
    for candidate in (
        tech_and_innovation.get("technologyGaps") if isinstance(tech_and_innovation, dict) else None,
        tech_and_innovation.get("innovationOpportunities") if isinstance(tech_and_innovation, dict) else None,
    ):
        if isinstance(candidate, list):
            points.extend(str(item) for item in candidate if item is not None)
    return points


def _build_lead_fit(payload: Dict[str, Any]) -> Dict[str, str]:
    """Build lead fit scores from payload."""
    stage_results = payload.get("stage_results") or {}
    lead_stage = stage_results.get("lead_scoring", {}) if isinstance(stage_results, dict) else {}
    lead_data = lead_stage.get("data") if isinstance(lead_stage, dict) else {}
    lead_scores = []
    if isinstance(lead_data, dict):
        scores = lead_data.get("lead_scoring")
        if isinstance(scores, list) and scores:
            lead_scores = scores
    lead_entry = lead_scores[0] if lead_scores else {}
    analysis = lead_data.get("analysis") if isinstance(lead_data, dict) else {}
    recommended = analysis.get("recommended_product") if isinstance(analysis, dict) else {}
    scores = lead_entry.get("scores") if isinstance(lead_entry, dict) else {}
    return {
        "product_name": _first_non_empty(
            lead_entry.get("product_name"),
            recommended.get("product_name") if isinstance(recommended, dict) else None,
        ),
        "industry_fit": _format_number((scores.get("industry_fit") or {}).get("score") if isinstance(scores, dict) else None),
        "pain_points_addressed": _format_number((scores.get("pain_points") or {}).get("score") if isinstance(scores, dict) else None),
        "geographic_market_fit": _format_number((scores.get("geographic_market_fit") or {}).get("score") if isinstance(scores, dict) else None),
        "total_weighted_score": _format_number(lead_entry.get("total_weighted_score") if isinstance(lead_entry, dict) else None),
        "recommendation": _first_non_empty(
            (analysis.get("insights") or [None])[0] if isinstance(analysis, dict) and isinstance(analysis.get("insights"), list) else None
        ),
    }


def _collect_email_drafts(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Collect email drafts from payload."""
    drafts: List[Dict[str, Any]] = []
    for candidate in (
        payload.get("email_drafts"),
        payload.get("stage_results", {}).get("initial_outreach", {}).get("data", {}).get("email_drafts"),
    ):
        if isinstance(candidate, list):
            drafts.extend(item for item in candidate if isinstance(item, dict))
    return drafts


def _render_sales_process_html(payload: Dict[str, Any], raw_json: str) -> str:
    """Render the start sales process HTML output."""
    summary = _build_process_summary(payload)
    stages = _build_stage_rows(payload)
    customer = _build_customer_info(payload)
    pains = _build_pain_points(payload)
    tech_stack = _build_tech_stack(payload)
    innovations = _build_innovation_points(payload)
    lead_fit = _build_lead_fit(payload)
    drafts = _collect_email_drafts(payload)

    def _row(label: str, value: str) -> str:
        return f"<tr><th>{html.escape(label)}</th><td>{html.escape(value) if value else ''}</td></tr>"

    stage_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(row.get('stage', ''))}</td>"
        f"<td>{html.escape(row.get('duration', ''))}</td>"
        f"<td>{html.escape(row.get('percent', ''))}</td>"
        f"<td>{html.escape(row.get('start', ''))}</td>"
        f"<td>{html.escape(row.get('end', ''))}</td>"
        "</tr>"
        for row in stages
    )

    pain_rows_html = "".join(
        "<tr>"
        f"<td>{html.escape(pain.get('category', ''))}</td>"
        f"<td>{html.escape(pain.get('description', ''))}</td>"
        f"<td>{html.escape(pain.get('impact', ''))}</td>"
        "</tr>"
        for pain in pains
    )

    tech_chips = "".join(f"<span class='chip'>{html.escape(item)}</span>" for item in tech_stack)
    innovation_list = "".join(f"<li>{html.escape(item)}</li>" for item in innovations)

    draft_html_parts: List[str] = []
    for idx, draft in enumerate(drafts, start=1):
        subject = draft.get("subject") or f"Draft {idx}"
        recipient = _first_non_empty(
            draft.get("recipient_email"),
            draft.get("recipient_address"),
            draft.get("customer_email"),
        )
        approach = draft.get("approach")
        tone = draft.get("tone")
        call_to_action = draft.get("call_to_action")
        meta_chips = []
        for label in (approach, tone, recipient, draft.get("status")):
            if label:
                meta_chips.append(f"<span class='chip'>{html.escape(str(label))}</span>")
        meta = "".join(meta_chips)
        body_html = draft.get("email_body") or draft.get("body_html") or draft.get("html_body") or ""
        escaped_srcdoc = html.escape(body_html, quote=True)
        draft_html_parts.append(
            "<div class='draft'>"
            f"<h3>{html.escape(subject)}</h3>"
            + (f"<div class='chips'>{meta}</div>" if meta else "")
            + f"<iframe class='iframe-draft' sandbox srcdoc=\"{escaped_srcdoc}\" loading='lazy'></iframe>"
            + (
                f"<div class='draft-meta'><strong>Call to Action:</strong> {html.escape(call_to_action)}</div>"
                if call_to_action
                else ""
            )
            + "</div>"
        )

    raw_escaped = html.escape(raw_json)
    style = (
        "html,body{margin:0;padding:0;}"
        "body{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;color:#0f172a;background:#f8fafc;line-height:1.6;}"
        "*{box-sizing:border-box;}"
        ".container{max-width:1200px;margin:40px auto;background:#fff;border-radius:10px;box-shadow:0 4px 16px rgba(15,23,42,0.07);padding:40px 36px;}"
        "h1,h2,h3,h4{color:#475569;}"
        ".section{margin-bottom:36px;}"
        ".card{background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:18px 20px;box-shadow:0 2px 8px rgba(15,23,42,0.05);margin-bottom:18px;}"
        ".card-header{display:flex;align-items:center;gap:12px;margin-bottom:12px;}"
        ".result-badge{display:inline-flex;align-items:center;justify-content:center;background:#e0f2fe;color:#0f172a;padding:6px 10px;border-radius:999px;font-weight:700;font-size:14px;}"
        ".stage-card{border:1px solid #e2e8f0;background:#f8fafc;border-radius:10px;padding:12px 14px;margin-bottom:12px;}"
        ".stage-header{display:flex;align-items:center;gap:10px;margin-bottom:8px;}"
        ".stage-badge{display:inline-flex;align-items:center;justify-content:center;background:#c7d2fe;color:#0f172a;font-weight:700;border-radius:8px;padding:4px 8px;min-width:32px;}"
        ".stage-title{font-weight:700;color:#0f172a;font-size:15px;}"
        ".stage-subsection{margin-top:8px;}"
        ".kv{display:grid;grid-template-columns:200px minmax(0,1fr);gap:8px 14px;padding:8px 0;border-bottom:1px solid #e2e8f0;}"
        ".kv:last-child{border-bottom:none;}"
        ".k{font-weight:600;color:#0f172a;}"
        ".v{color:#0f172a;}"
        ".section-header{font-weight:700;color:#0f172a;background:#e2e8f0;padding:8px 12px;border-radius:6px;margin:10px 0 6px 0;font-size:13px;}"
        ".list-item{border:1px solid #e2e8f0;background:#f8fafc;border-radius:8px;padding:10px;margin:8px 0;}"
        ".nested-card{border:1px solid #e2e8f0;background:#f8fafc;border-radius:8px;padding:10px;margin-top:6px;}"
        ".text{background:#e2e8f0;border-radius:6px;padding:4px 8px;display:inline-block;}"
        ".html-preview{margin-top:6px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;}"
        ".html-preview-label{background:#0f172a;color:#e2e8f0;padding:6px 10px;font-weight:700;font-size:12px;}"
        ".html-iframe{width:100%;min-height:240px;border:0;display:block;}"
        ".html-raw{margin:0;padding:10px;}"
        ".pre-inline{background:#0f172a;color:#e2e8f0;padding:8px;border-radius:8px;overflow:auto;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word;}"
        ".muted{color:#64748b;font-style:italic;}"
        "table{border-collapse:collapse;width:100%;margin-bottom:24px;table-layout:fixed;}"
        "th,td{text-align:left;padding:10px 14px;border-bottom:1px solid #e2e8f0;word-break:break-word;}"
        "th{background:#e2e8f0;font-weight:600;width:260px;}"
        ".stage-table th,.stage-table td{width:auto;padding:8px;}"
        ".badge{display:inline-block;background:#e0f2fe;color:#0f172a;padding:2px 10px;border-radius:999px;font-weight:600;font-size:13px;}"
        "details{margin-top:16px;}"
        "summary{cursor:pointer;color:#0ea5e9;font-weight:600;}"
        "pre{background:#e2e8f0;border-radius:8px;padding:12px;font-size:13px;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;overflow-x:auto;}"
        "ul{padding-left:18px;}"
        "li{margin:6px 0;}"
        ".chips{display:flex;gap:10px;flex-wrap:wrap;margin:4px 0;}"
        ".chip{background:#e0f2fe;color:#0f172a;padding:4px 14px;border-radius:999px;font-weight:600;font-size:12px;}"
        ".iframe-draft{width:100%;min-height:340px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:16px;}"
        ".draft{margin-bottom:20px;padding:16px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;}"
        ".draft-meta{font-size:13px;color:#475569;margin-bottom:8px;}"
        "@media (max-width: 900px){th{width:180px;}}"
    )

    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'>"
        "<title>FuseSell AI - Sales Process Report</title>"
        f"<style>{style}</style>"
        "</head><body>"
        "<div class='container'>"
        "<h1>FuseSell AI - Sales Process Report</h1>"
        "<div class='section'>"
        "<h2>Process Summary</h2>"
        "<table>"
        f"{_row('Execution Id', summary.get('execution_id', ''))}"
        f"{_row('Status', summary.get('status', ''))}"
        f"{_row('Started At', summary.get('started_at', ''))}"
        f"{_row('Duration Seconds', summary.get('duration_seconds', ''))}"
        f"{_row('Stage Count', summary.get('stage_count', ''))}"
        f"{_row('Avg. Stage Duration', summary.get('avg_stage_duration', ''))}"
        f"{_row('Pipeline Overhead (%)', summary.get('pipeline_overhead', ''))}"
        f"{_row('Slowest Stage', summary.get('slowest_stage', ''))}"
        f"{_row('Fastest Stage', summary.get('fastest_stage', ''))}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Stage Results</h2>"
        "<table class='stage-table'>"
        "<tr><th>Stage</th><th>Duration (s)</th><th>% of Total</th><th>Start Time</th><th>End Time</th></tr>"
        f"{stage_rows_html or '<tr><td colspan=\"5\">No stage timings available.</td></tr>'}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Customer & Company Info</h2>"
        "<table>"
        f"{_row('Company Name', customer.get('company_name', ''))}"
        f"{_row('Industry', customer.get('industry', ''))}"
        f"{_row('Website', customer.get('website', ''))}"
        f"{_row('Contact Name', customer.get('contact_name', ''))}"
        f"{_row('Contact Email', customer.get('contact_email', ''))}"
        f"{_row('Funding Sources', customer.get('funding_sources', ''))}"
        f"{_row('Revenue Last 3 Years', customer.get('revenue_last_three_years', ''))}"
        f"{_row('Overall Rating', customer.get('overall_rating', ''))}"
        f"{_row('Recommendations', customer.get('recommendations', ''))}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Pain Points</h2>"
        "<table>"
        "<tr><th>Category</th><th>Description</th><th>Impact</th></tr>"
        f"{pain_rows_html or '<tr><td colspan=\"3\">No pain points captured.</td></tr>'}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Tech Stack & Innovation</h2>"
        f"<div class='chips'>{tech_chips or '<span class=\"chip\">Not specified</span>'}</div>"
        "<h4>Innovation Gaps & Opportunities</h4>"
        f"<ul>{innovation_list or '<li>No innovation insights captured.</li>'}</ul>"
        "</div>"
        "<div class='section'>"
        "<h2>Lead Scoring - Product Fit</h2>"
        "<table>"
        f"{_row('Product Name', lead_fit.get('product_name', ''))}"
        f"{_row('Industry Fit', lead_fit.get('industry_fit', ''))}"
        f"{_row('Pain Points Addressed', lead_fit.get('pain_points_addressed', ''))}"
        f"{_row('Geographic Market Fit', lead_fit.get('geographic_market_fit', ''))}"
        f"{_row('Total Weighted Score', lead_fit.get('total_weighted_score', ''))}"
        f"{_row('Recommendation', lead_fit.get('recommendation', ''))}"
        "</table>"
        "</div>"
        "<div class='section'>"
        "<h2>Email Outreach Drafts</h2>"
        "<details open>"
        "<summary>Show All Drafts</summary>"
        f"{''.join(draft_html_parts) if draft_html_parts else '<div>No email drafts generated.</div>'}"
        "</details>"
        "</div>"
        "<div class='section'>"
        "<h2>Raw JSON</h2>"
        "<details>"
        "<summary>View Full Raw JSON</summary>"
        "<pre>"
        f"{raw_escaped}"
        "</pre>"
        "</details>"
        "</div>"
        "</div>"
        "</body></html>"
    )


def _render_query_html(payload: Dict[str, Any], raw_json: str) -> str:
    """Render the query sales process HTML output."""
    filters = payload.get('filters') if isinstance(payload, dict) else {}
    results = payload.get('results') if isinstance(payload, dict) else []
    raw_escaped = html.escape(raw_json)
    filters_rows = _render_filters(filters)
    result_cards = _render_results(results if isinstance(results, list) else [])

    style = (
        "html,body{margin:0;padding:0;}"
        "body{font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;color:#0f172a;background:#f8fafc;line-height:1.6;}"
        "*{box-sizing:border-box;}"
        ".container{max-width:1200px;margin:40px auto;background:#fff;border-radius:10px;box-shadow:0 4px 16px rgba(15,23,42,0.07);padding:40px 36px;}"
        "h1,h2,h3,h4{color:#475569;}"
        ".section{margin-bottom:24px;}"
        "table{border-collapse:collapse;width:100%;margin-bottom:12px;table-layout:fixed;}"
        "th,td{text-align:left;padding:10px 14px;border-bottom:1px solid #e2e8f0;word-break:break-word;}"
        "th{background:#e2e8f0;font-weight:600;width:240px;}"
        ".badge{display:inline-block;background:#e0f2fe;color:#0f172a;padding:2px 10px;border-radius:999px;font-weight:600;font-size:13px;}"
        "details{margin-top:16px;}"
        "summary{cursor:pointer;color:#0ea5e9;font-weight:600;}"
        "pre{background:#e2e8f0;border-radius:8px;padding:12px;font-size:13px;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;overflow-x:auto;}"
        "ul,li{margin:0;padding:0;list-style:none;}"
        ".chips{display:flex;gap:10px;flex-wrap:wrap;margin:4px 0;}"
        ".chip{background:#e0f2fe;color:#0f172a;padding:4px 14px;border-radius:999px;font-weight:600;font-size:12px;}"
        ".iframe-draft{width:100%;min-height:340px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:16px;}"
        ".kv{display:grid;grid-template-columns:240px minmax(0,1fr);gap:8px 14px;padding:10px 0;border-bottom:1px solid #e2e8f0;align-items:flex-start;}"
        ".kv:last-child{border-bottom:none;} .list-item{border:1px solid #e2e8f0;background:#f8fafc;border-radius:8px;padding:10px;margin:8px 0;}"
        ".k{font-weight:600;color:#0f172a;background:#e2e8f0;border-radius:6px;padding:8px 10px;}"
        ".v{color:#0f172a;min-width:0;}"
        ".text{background:#e2e8f0;border-radius:6px;padding:8px 10px;display:block;width:100%;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere;}"
        ".nested-card{border:1px solid #e2e8f0;background:#f8fafc;border-radius:8px;padding:10px;}"
        ".pre-inline{background:#e2e8f0;color:#0f172a;padding:10px;border-radius:6px;overflow:auto;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;font-size:12px;line-height:1.5;white-space:pre-wrap;word-break:break-word;}"
        ".html-preview{display:flex;flex-direction:column;gap:8px;}"
        ".html-preview-label{font-weight:600;color:#0f172a;font-size:13px;}"
        ".html-iframe{width:100%;min-height:340px;border:0;display:block;}"
        ".html-raw summary{cursor:pointer;color:#0ea5e9;font-weight:600;}"
        ".card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:24px;margin-bottom:24px;box-shadow:0 2px 8px rgba(15,23,42,0.05);}"
        ".muted{color:#64748b;font-style:italic;}"
        ".draft{margin-bottom:20px;padding:16px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;}"
        ".criteria-list{display:flex;flex-direction:column;gap:12px;padding:10px;}"
        ".criteria-item{background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:10px;}"
        ".criteria-header{display:flex;align-items:center;gap:10px;margin-bottom:8px;}"
        ".criteria-num{display:inline-flex;align-items:center;justify-content:center;min-width:24px;height:24px;background:#0ea5e9;color:#fff;border-radius:50%;font-weight:700;font-size:12px;flex-shrink:0;}"
        ".criteria-label{font-weight:600;color:#0f172a;font-size:14px;flex:1;min-width:0;word-break:break-word;}"
        ".criteria-content{margin-left:34px;color:#475569;font-size:13px;line-height:1.6;}"
        ".criteria-content>div{margin-bottom:4px;}"
        ".criteria-content>div:last-child{margin-bottom:0;}"
        "@media (max-width: 900px){th{width:180px;} .kv{grid-template-columns:minmax(140px,1fr) minmax(0,2fr);padding:8px 10px;}}"
    )

    return (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'>"
        "<title>FuseSell AI - Query Results</title>"
        f"<style>{style}</style>"
        "</head><body>"
        "<div class='container'>"
        "<h1>FuseSell AI - Query Results</h1>"
        "<div class='section'>"
        "<h2>Filters</h2>"
        "<table>" + filters_rows + "</table>"
        "</div>"
        + ("<div class='section'><h2>Results</h2>" + (result_cards or "<div>No results found.</div>") + "</div>")
        + "<div class='section'>"
        + "<h2>Raw JSON</h2>"
        + "<details><summary>View Full Raw JSON</summary><pre>" + raw_escaped + "</pre></details>"
        + "</div>"
        + "</div>"
        + "</body></html>"
    )


def write_full_output_html(
    full_payload: Any,
    *,
    flow_name: str,
    data_dir: Path,
    hidden_keys: Optional[Set[str]] = None,
    root_hidden_keys: Optional[Set[str]] = None,
    html_render_keys: Optional[Set[str]] = None,
) -> Optional[dict]:
    """
    Write a friendly HTML view of the payload plus raw JSON for debugging.
    """
    try:
        html_dir = Path(data_dir) / "full_outputs"
        html_dir.mkdir(parents=True, exist_ok=True)

        hidden = hidden_keys or DEFAULT_HIDDEN_KEYS
        root_hidden = root_hidden_keys or DEFAULT_ROOT_HIDDEN_KEYS
        render_keys = html_render_keys or DEFAULT_HTML_RENDER_KEYS

        sanitized = _sanitize_for_json(full_payload)
        raw_serialized = json.dumps(sanitized, indent=2, ensure_ascii=False)

        # Specialized renderer for start_sales_process_compact (match flow fallback)
        if flow_name == "start_sales_process_compact":
            content = _render_start_sales_process_html(sanitized, raw_serialized)
            filename = f"{flow_name}_{uuid4().hex}.html"
            path = html_dir / filename
            path.write_text(content, encoding="utf-8")
            stat_result = path.stat()
            timestamp = f"{datetime.utcnow().isoformat()}Z"
            return {
                "path": str(path),
                "metadata": {
                    "mime": "text/html",
                    "size": stat_result.st_size,
                    "created": timestamp,
                    "filename": filename,
                    "originalFilename": filename,
                },
            }

        # Specialized renderer for query sales processes (by flow name or results array)
        if flow_name == "query_sales_processes_compact" or (
            isinstance(sanitized, dict) and isinstance(sanitized.get("results"), list)
        ) or isinstance(sanitized, list):
            payload_for_query = sanitized if isinstance(sanitized, dict) else {"results": sanitized}
            content = _render_query_results(payload_for_query, raw_serialized)
            filename = f"{flow_name}_{uuid4().hex}.html"
            path = html_dir / filename
            path.write_text(content, encoding="utf-8")
            stat_result = path.stat()
            return {
                "path": str(path),
                "metadata": {
                    "mime": "text/html",
                    "size": stat_result.st_size,
                    "created": f"{datetime.utcnow().isoformat()}Z",
                    "filename": filename,
                    "originalFilename": filename,
                },
            }

        filename = f"{flow_name}_{uuid4().hex}.html"
        path = html_dir / filename

        timestamp = f"{datetime.utcnow().isoformat()}Z"

        cleaned = _prune_empty(sanitized, hidden_keys=hidden, root_hidden_keys=root_hidden)
        display_payload = _humanize_keys(cleaned if cleaned is not None else {"Info": "No non-empty fields"})
        escaped_raw = html.escape(raw_serialized)
        friendly_view = _render_value(display_payload, html_render_keys=render_keys)

        content = (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'>"
            f"<title>{html.escape(flow_name)} full output</title>"
            "<style>"
            "body{font-family:'Segoe UI','Helvetica Neue',sans-serif;background:#f8fafc;color:#0f172a;"
            "line-height:1.6;padding:20px;}"
            ".meta{color:#475569;margin-bottom:16px;}"
            ".card{background:#ffffff;border:1px solid #e2e8f0;border-radius:10px;padding:14px 16px;"
            "box-shadow:0 4px 14px rgba(15,23,42,0.04);}"
            ".card + .card{margin-top:12px;}"
            ".kv{display:grid;grid-template-columns:minmax(120px,max-content) 1fr;gap:6px 10px;padding:6px 0;"
            "border-bottom:1px solid #e2e8f0;}"
            ".kv:last-child{border-bottom:none;}"
            ".section-header{font-weight:700;color:#0f172a;background:#e0f2fe;padding:8px 12px;"
            "border-radius:6px;margin:12px 0 6px 0;font-size:13px;}"
            ".k{font-weight:600;color:#0f172a;}"
            ".v{color:#0f172a;}"
            ".text{background:#e2e8f0;border-radius:6px;padding:4px 8px;display:inline-block;}"
            ".chips{display:flex;flex-wrap:wrap;gap:6px;}"
            ".chip{background:#e0f2fe;color:#0f172a;padding:4px 10px;border-radius:999px;font-weight:600;font-size:12px;}"
            ".badge{display:inline-block;background:#e2e8f0;color:#0f172a;padding:2px 8px;border-radius:999px;font-weight:700;font-size:11px;}"
            ".pre{background:#0f172a;color:#e2e8f0;padding:12px;border-radius:8px;"
            "overflow:auto;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;"
            "font-size:13px;line-height:1.55;white-space:pre-wrap;word-break:break-word;}"
            ".html-preview{margin-top:6px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;}"
            ".html-preview-label{background:#0f172a;color:#e2e8f0;padding:6px 10px;font-weight:700;font-size:12px;}"
            ".html-iframe{width:100%;min-height:240px;border:0;display:block;}"
            ".html-raw{margin:0;padding:10px;}"
            ".pre-inline{background:#0f172a;color:#e2e8f0;padding:8px;border-radius:8px;"
            "overflow:auto;font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace;"
            "font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word;}"
            "details{margin-top:10px;}"
            "details summary{cursor:pointer;color:#0ea5e9;font-weight:600;outline:none;}"
            "</style>"
            "</head><body>"
            f"<div class='meta'><strong>generated_at</strong>: {timestamp}</div>"
            "<div class='card'>"
            "<div>"
            f"{friendly_view}"
            "</div>"
            "<details>"
            "<summary>View Raw JSON</summary>"
            "<div class='pre' style='margin-top:8px;'>"
            f"{escaped_raw}"
            "</div>"
            "</details>"
            "</div>"
            "</body></html>"
        )

        path.write_text(content, encoding="utf-8")
        stat_result = path.stat()
        return {
            "path": str(path),
            "metadata": {
                "mime": "text/html",
                "size": stat_result.st_size,
                "created": timestamp,
                "filename": filename,
                "originalFilename": filename,
            },
        }
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: failed to write full output HTML for {flow_name}: {exc}", file=sys.stderr)
        return None
