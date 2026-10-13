"""Pytest configuration for MerchantGuard test suite.

Forces LLM_MODE=replay for all non-live-marked tests so the default suite
never touches the AMD Token Factory gateway, avoids quota consumption, and
runs deterministically without network dependencies.
"""

import os
import pytest


def pytest_configure(config):
    """Override LLM_MODE to 'replay' before any test module is imported."""
    os.environ.setdefault("LLM_MODE", "replay")
    # Ensure the app module picks up replay mode even if .env sets live
    os.environ["LLM_MODE"] = "replay"
