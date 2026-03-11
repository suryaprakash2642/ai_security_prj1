"""Common enums used by Layer 4 Policy Resolution."""

from enum import Enum


class TableDecision(str, Enum):
    """Access outcome for a table."""
    ALLOW = "ALLOW"
    DENY = "DENY"


class ColumnVisibility(str, Enum):
    """Visibility state for a column."""
    VISIBLE = "VISIBLE"
    MASKED = "MASKED"
    HIDDEN = "HIDDEN"
