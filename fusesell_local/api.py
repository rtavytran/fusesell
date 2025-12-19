"""
Public library interface for FuseSell Local.

This module exposes helpers that embed FuseSell in external Python runtimes
without going through the CLI wrapper.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

from .pipeline import FuseSellPipeline
from .utils.logger import setup_logging as _setup_logging
from .utils.validators import InputValidator
from .utils.llm_client import normalize_llm_base_url


class ConfigValidationError(ValueError):
    """Raised when pipeline configuration fails validation."""


OptionsType = Union[Mapping[str, Any], object]


def generate_execution_id(prefix: str = "fusesell") -> str:
    """
    Generate a unique execution identifier.

    Args:
        prefix: Optional prefix for the identifier (default ``"fusesell"``).

    Returns:
        Execution ID string.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{unique_id}"


def build_config(options: OptionsType) -> Dict[str, Any]:
    """
    Build a pipeline configuration dictionary from a mapping or namespace.

    Args:
        options: Mapping, dataclass, or argparse namespace containing pipeline options.

    Returns:
        Normalised configuration dictionary suitable for ``FuseSellPipeline``.
    """

    def _get(name: str, default: Any = None) -> Any:
        if isinstance(options, Mapping):
            return options.get(name, default)
        return getattr(options, name, default)

    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
        return bool(value)

    def _ensure_list(value: Any) -> Sequence[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if item]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(value)]

    config: Dict[str, Any] = {
        # API and LLM settings
        "openai_api_key": _get("openai_api_key"),
        "serper_api_key": _get("serper_api_key"),
        "llm_model": _get("llm_model", "gpt-4.1-mini"),
        "llm_base_url": _get("llm_base_url"),
        "temperature": float(_get("temperature", 0.7) or 0.7),
        "max_retries": int(_get("max_retries", 3) or 3),

        # Organisation settings
        "org_id": _get("org_id"),
        "org_name": _get("org_name"),
        "team_id": _get("team_id"),
        "team_name": _get("team_name"),
        "project_code": _get("project_code"),
        "staff_name": _get("staff_name", "Sales Team"),

        # Data sources
        "input_website": _get("input_website") or "",
        "input_description": _get("input_description") or "",
        "input_business_card": _get("input_business_card") or "",
        "input_linkedin_url": _get("input_linkedin_url") or "",
        "input_facebook_url": _get("input_facebook_url") or "",
        "input_freetext": _get("input_freetext") or "",

        # Context fields
        "customer_id": _get("customer_id", "null"),
        "full_input": _get("full_input"),
        "language": (_get("language") or "english").lower(),

        # Processing control
        "skip_stages": list(_ensure_list(_get("skip_stages"))),
        "stop_after": _get("stop_after"),

        # Continuation / action parameters
        "continue_execution": _get("continue_execution"),
        "action": _get("action", "draft_write"),
        "selected_draft_id": _get("selected_draft_id"),
        "reason": _get("reason") or "",
        "recipient_address": _get("recipient_address"),
        "recipient_name": _get("recipient_name") or "",
        "interaction_type": _get("interaction_type", "email"),
        "human_action_id": _get("human_action_id") or "",

        # Scheduling preferences
        "send_immediately": _coerce_bool(_get("send_immediately"), False),
        "customer_timezone": _get("customer_timezone") or "",
        "business_hours_start": _get("business_hours_start", "08:00") or "08:00",
        "business_hours_end": _get("business_hours_end", "20:00") or "20:00",
        "delay_hours": int(_get("delay_hours", 2) or 2),

        # Output and storage settings
        "output_format": (_get("output_format") or "json").lower(),
        "data_dir": _get("data_dir", "./fusesell_data"),
        "execution_id": _get("execution_id") or generate_execution_id(),
        "save_intermediate": _coerce_bool(_get("save_intermediate")),

        # Logging and diagnostics
        "log_level": (_get("log_level") or "INFO").upper(),
        "log_file": _get("log_file"),
        "verbose": _coerce_bool(_get("verbose")),
        "dry_run": _coerce_bool(_get("dry_run")),
    }

    config["llm_base_url"] = normalize_llm_base_url(config.get("llm_base_url"))

    return config


def prepare_data_directory(
    config: MutableMapping[str, Any],
    *,
    assign_default_log: bool = True,
    on_create: Optional[Callable[[Path], None]] = None,
) -> Path:
    """
    Ensure the data directory structure exists for the given configuration.

    Args:
        config: Configuration dictionary (mutated in-place when log_file is assigned).
        assign_default_log: When True, write a default log file path if none provided.
        on_create: Optional callback invoked with the created ``Path``.

    Returns:
        Path to the resolved data directory.
    """
    data_dir = Path(config.get("data_dir") or "./fusesell_data").expanduser()
    directories = [
        data_dir,
        data_dir / "config",
        data_dir / "drafts",
        data_dir / "logs",
        data_dir / "exports",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    if assign_default_log and not config.get("log_file"):
        log_filename = f"fusesell_{config['execution_id']}.log"
        config["log_file"] = str((data_dir / "logs" / log_filename).resolve())

    if on_create:
        on_create(data_dir)

    return data_dir


def configure_logging(config: Mapping[str, Any]) -> logging.Logger:
    """
    Configure logging for the pipeline execution.

    Args:
        config: Pipeline configuration dictionary.

    Returns:
        Configured logger instance.
    """
    return _setup_logging(
        level=config.get("log_level", "INFO"),
        log_file=config.get("log_file"),
        verbose=bool(config.get("verbose", False)),
    )


def validate_config(config: Mapping[str, Any]) -> Tuple[bool, list]:
    """
    Validate pipeline configuration for common issues.

    Args:
        config: Configuration dictionary to validate.

    Returns:
        Tuple of ``(is_valid, errors)``.
    """
    errors: list = []
    validator = InputValidator()
    errors.extend(validator.validate_config(dict(config)))

    if not config.get("full_input"):
        errors.append("Missing required configuration: full_input")

    data_dir_valid, data_errors = validate_data_directory(config.get("data_dir"))
    if not data_dir_valid:
        errors.extend(data_errors)

    if config.get("continue_execution"):
        cont_valid, cont_errors = validate_continuation_params(config)
        if not cont_valid:
            errors.extend(cont_errors)

    return len(errors) == 0, errors


def validate_data_directory(data_dir: Optional[str]) -> Tuple[bool, list]:
    """
    Validate that the configured data directory is writable.

    Args:
        data_dir: Directory path supplied in configuration.

    Returns:
        Tuple of ``(is_valid, errors)``.
    """
    errors: list = []

    try:
        if not data_dir:
            raise ValueError("Data directory is not configured")

        path = Path(data_dir).expanduser()
        path.mkdir(parents=True, exist_ok=True)

        test_file = path / ".__fusesell_write_test__"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as exc:
        errors.append(f"Failed to prepare data directory '{data_dir}': {exc}")

    return len(errors) == 0, errors


def validate_continuation_params(config: Mapping[str, Any]) -> Tuple[bool, list]:
    """
    Validate continuation parameters for follow-up executions.

    Args:
        config: Configuration dictionary.

    Returns:
        Tuple of ``(is_valid, errors)``.
    """
    errors: list = []
    action = config.get("action")

    if not action:
        errors.append("Action is required when continuing execution")
        return False, errors

    valid_actions = {"draft_write", "draft_rewrite", "send", "close"}
    if action not in valid_actions:
        errors.append(f"Invalid action. Must be one of: {', '.join(sorted(valid_actions))}")

    if action in {"draft_rewrite", "send"} and not config.get("selected_draft_id"):
        errors.append("selected_draft_id is required for draft_rewrite and send actions")

    if action == "send" and not config.get("recipient_address"):
        errors.append("recipient_address is required for send actions")

    return len(errors) == 0, errors


def run_pipeline(config: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Execute the FuseSell pipeline with a prepared configuration.

    Args:
        config: Validated configuration dictionary.

    Returns:
        Pipeline execution result dictionary.
    """
    pipeline = FuseSellPipeline(dict(config))
    return pipeline.execute()


def execute_pipeline(
    options: OptionsType,
    *,
    auto_prepare: bool = True,
    auto_configure_logging: bool = True,
    auto_validate: bool = True,
) -> Dict[str, Any]:
    """
    High-level helper that builds configuration from options and executes the pipeline.

    Args:
        options: Mapping or namespace of pipeline options.
        auto_prepare: When True, prepare the data directory structure automatically.
        auto_configure_logging: When True, configure logging before execution.
        auto_validate: When True, validate configuration and raise ``ConfigValidationError`` on failure.

    Returns:
        Pipeline execution result dictionary.
    """
    config = build_config(options)

    if auto_prepare:
        prepare_data_directory(config)

    if auto_configure_logging:
        configure_logging(config)

    if auto_validate:
        valid, errors = validate_config(config)
        if not valid:
            raise ConfigValidationError("; ".join(errors))

    if config.get("dry_run"):
        return {
            "status": "dry_run",
            "execution_id": config["execution_id"],
            "config": config,
        }

    return run_pipeline(config)
