#!/usr/bin/env python3
"""
Backward-compatible CLI entry point for running the FuseSell pipeline.

Delegates to ``fusesell_local.cli.main`` so both the installed console script
and direct script execution share the same implementation.
"""

from fusesell_local.cli import FuseSellCLI, main

__all__ = ["FuseSellCLI", "main"]


if __name__ == "__main__":
    main()
