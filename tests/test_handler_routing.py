"""Tests for main API handler routing."""

import json
import pytest
from unittest.mock import patch
from src.handlers.api import handler


class TestHandlerRouting:
    """Test route matching in main handler."""

    def test_health_check(self):
        """Health check endpoint returns 200."""
        event = {"path": "/health", "httpMethod": "GET"}
        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "healthy"

    def test_health_check_includes_table_name(self):
        """Health check includes TABLE_NAME env var."""
        event = {"path": "/health", "httpMethod": "GET"}
        with patch.dict("os.environ", {"TABLE_NAME": "TestTable"}):
            result = handler(event, None)

        body = json.loads(result["body"])
        assert body["table"] == "TestTable"

    def test_options_cors(self):
        """OPTIONS request returns CORS headers."""
        event = {"path": "/any/path", "httpMethod": "OPTIONS"}
        result = handler(event, None)

        assert result["statusCode"] == 200
        assert (
            result["headers"]["Access-Control-Allow-Methods"]
            == "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        )
        assert result["body"] == ""

    def test_suites_route(self):
        """Route /suites calls handle_suites."""
        event = {"path": "/suites", "httpMethod": "GET"}

        with patch("src.handlers.api.handle_suites") as mock:
            mock.return_value = {"statusCode": 200, "body": "{}"}
            result = handler(event, None)
            mock.assert_called_once_with(event)

    def test_suite_by_id_route(self):
        """Route /suites/{id} calls handle_suite_by_id with pathParameters."""
        event = {"path": "/suites/abc123", "httpMethod": "GET"}

        with patch("src.handlers.api.handle_suite_by_id") as mock:
            mock.return_value = {"statusCode": 200, "body": "{}"}
            result = handler(event, None)
            expected = {**event, "pathParameters": {"suiteId": "abc123"}}
            mock.assert_called_once_with(expected)
            assert "pathParameters" not in event

    def test_cases_route(self):
        """Route /suites/{id}/cases calls handle_cases with pathParameters."""
        event = {"path": "/suites/abc123/cases", "httpMethod": "GET"}

        with patch("src.handlers.api.handle_cases") as mock:
            mock.return_value = {"statusCode": 200, "body": "{}"}
            result = handler(event, None)
            expected = {**event, "pathParameters": {"suiteId": "abc123"}}
            mock.assert_called_once_with(expected)
            assert "pathParameters" not in event

    def test_case_by_id_route(self):
        """Route /suites/{id}/cases/{caseId} calls handle_case_by_id."""
        event = {"path": "/suites/abc123/cases/def456", "httpMethod": "GET"}

        with patch("src.handlers.api.handle_case_by_id") as mock:
            mock.return_value = {"statusCode": 200, "body": "{}"}
            result = handler(event, None)
            expected = {
                **event,
                "pathParameters": {"suiteId": "abc123", "caseId": "def456"},
            }
            mock.assert_called_once_with(expected)
            assert "pathParameters" not in event

    def test_unknown_route_returns_404(self):
        """Unknown routes return 404."""
        event = {"path": "/unknown", "httpMethod": "GET"}
        result = handler(event, None)

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["message"] == "Not found"

    def test_route_order_case_before_suite(self):
        """Cases route matches before suite route for /suites/{id}/cases."""
        event = {"path": "/suites/abc/cases", "httpMethod": "GET"}

        with patch("src.handlers.api.handle_cases") as mock:
            mock.return_value = {"statusCode": 200, "body": "{}"}
            result = handler(event, None)
            mock.assert_called_once()
