"""Cinderhaven Store Universe — synthetic data for CPG distribution analytics."""

from .authorization import get_auth_matrix
from .constants import DEMO_AS_OF_DATE
from .scans import get_scan_data
from .slow_leak import get_slow_leak_config
from .stores import get_stores

__all__ = [
    "DEMO_AS_OF_DATE",
    "get_stores",
    "get_auth_matrix",
    "get_scan_data",
    "get_slow_leak_config",
]
