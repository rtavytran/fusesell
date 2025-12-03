"""
FuseSell Local - AI-powered sales automation platform for local execution.

This package exposes a programmatic API so the pipeline can be embedded in
workflows and code interpreters without launching the CLI entry point.
"""

from .api import (
    ConfigValidationError,
    build_config,
    configure_logging,
    execute_pipeline,
    generate_execution_id,
    prepare_data_directory,
    run_pipeline,
    validate_config,
)
from .cli import FuseSellCLI, main as cli_main
from .pipeline import FuseSellPipeline

__all__ = [
    "ConfigValidationError",
    "FuseSellCLI",
    "FuseSellPipeline",
    "build_config",
    "cli_main",
    "configure_logging",
    "execute_pipeline",
    "generate_execution_id",
    "prepare_data_directory",
    "run_pipeline",
    "validate_config",
]

__version__ = "1.3.3"
__author__ = "RealTimeX Team (info@realtimex.ai)"
__description__ = "Complete AI-powered sales automation pipeline that runs entirely on your local machine."
