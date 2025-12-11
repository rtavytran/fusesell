"""
Shared HTML output helper for FuseSell flows.

Renders a friendly key/value view and embeds the raw JSON for debugging.
"""

from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
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
        for idx, item in enumerate(value, start=1):
            parts.append(
                "<div class='kv kv-array' style='margin-left:"
                f"{array_indent_px}px'>"
                f"<div class='k k-array'><span class='badge'>{idx}</span></div>"
                f"<div class='v'>{_render_value(item, depth + 1, None, html_render_keys)}</div>"
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
        cleaned = _prune_empty(sanitized, hidden_keys=hidden, root_hidden_keys=root_hidden)
        display_payload = _humanize_keys(cleaned if cleaned is not None else {"Info": "No non-empty fields"})

        raw_serialized = json.dumps(sanitized, indent=2, ensure_ascii=False)
        escaped_raw = html.escape(raw_serialized)
        friendly_view = _render_value(display_payload, html_render_keys=render_keys)

        filename = f"{flow_name}_{uuid4().hex}.html"
        path = html_dir / filename

        timestamp = f"{datetime.utcnow().isoformat()}Z"
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
            ".kv-array{grid-template-columns:min-content 1fr!important;}"
            ".k-array{padding:4px 8px!important;text-align:center;min-width:32px;}"
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
