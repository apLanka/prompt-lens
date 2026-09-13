"""API route handlers."""

from .suites import handle_suites, handle_suite_by_id
from .cases import handle_cases, handle_case_by_id

__all__ = ["handle_suites", "handle_suite_by_id", "handle_cases", "handle_case_by_id"]
