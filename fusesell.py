#!/usr/bin/env python3
"""
Backward-compatible CLI entry point for running the FuseSell pipeline.

Delegates to ``fusesell_local.cli.main`` so both the installed console script
and direct script execution share the same implementation.
"""

from fusesell_local import __author__ as _AUTHOR, __description__ as _DESCRIPTION, __version__ as _VERSION
from fusesell_local.cli import FuseSellCLI, main

__all__ = ["FuseSellCLI", "main", "__version__", "__author__", "__description__"]

__author__ = _AUTHOR
__description__ = _DESCRIPTION
__version__ = _VERSION


if __name__ == "__main__":
    main()
