"""Tests for Bedrock operations module."""

import json
import io
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from src.handlers.api import bedrock


class TestGetBedrockClient:
    @patch("src.handlers.api.bedrock.boto3")
    def test_returns_bedrock_runtime_client(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        result = bedrock.get_bedrock_client()

        mock_boto3.client.assert_called_once_with("bedrock-runtime")
        assert result is mock_client


class TestInvokeModel:
    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_claude_model_returns_output(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_body = io.BytesIO(json.dumps({"completion": "Hello world"}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        output, latency = bedrock.invoke_model(
            model_id="anthropic.claude-3-sonnet",
            prompt="Say hello",
            temperature=0.5,
            max_tokens=512,
        )

        assert output == "Hello world"
        assert isinstance(latency, float)
        assert latency >= 0

        call_args = mock_client.invoke_model.call_args
        assert call_args.kwargs["modelId"] == "anthropic.claude-3-sonnet"
        body = json.loads(call_args.kwargs["body"])
        assert body["prompt"] == "Say hello"
        assert body["max_tokens_to_sample"] == 512
        assert body["temperature"] == 0.5

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_non_claude_model_uses_generation_key(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_body = io.BytesIO(json.dumps({"generation": "Generated text"}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        output, latency = bedrock.invoke_model(
            model_id="amazon.titan-text-express",
            prompt="Generate text",
        )

        assert output == "Generated text"
        assert isinstance(latency, float)

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_claude_model_missing_completion_returns_empty(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_body = io.BytesIO(json.dumps({}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        output, latency = bedrock.invoke_model(
            model_id="anthropic.claude-3-sonnet",
            prompt="test",
        )

        assert output == ""

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_client_error_propagates(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        error_response = {
            "Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}
        }
        mock_client.invoke_model.side_effect = ClientError(
            error_response, "InvokeModel"
        )

        with pytest.raises(ClientError):
            bedrock.invoke_model(
                model_id="anthropic.claude-3-sonnet",
                prompt="test",
            )

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_latency_is_in_milliseconds(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_body = io.BytesIO(json.dumps({"completion": "ok"}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        _, latency = bedrock.invoke_model(
            model_id="anthropic.claude-3-sonnet",
            prompt="test",
        )

        assert latency >= 0


class TestEvaluateOutput:
    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_valid_json_response(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = json.dumps(
            {
                "score": 4,
                "confidence": "high",
                "rationale": "Good response",
                "violations": [],
            }
        )
        mock_body = io.BytesIO(json.dumps({"completion": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test output",
            rubric="Rate 1-5",
            model_id="anthropic.claude-3-sonnet",
        )

        assert result["score"] == 4
        assert result["confidence"] == "high"
        assert result["rationale"] == "Good response"
        assert result["violations"] == []

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_json_wrapped_in_markdown(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = '```json\n{"score": 3, "confidence": "medium", "rationale": "OK", "violations": []}\n```'
        mock_body = io.BytesIO(json.dumps({"completion": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test output",
            rubric="Rate 1-5",
            model_id="anthropic.claude-3-sonnet",
        )

        assert result["score"] == 3
        assert result["confidence"] == "medium"

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_json_wrapped_in_generic_markdown(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = '```\n{"score": 2, "confidence": "low", "rationale": "Poor", "violations": ["bad"]}\n```'
        mock_body = io.BytesIO(json.dumps({"generation": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test output",
            rubric="Rate 1-5",
            model_id="amazon.titan-text-express",
        )

        assert result["score"] == 2
        assert result["violations"] == ["bad"]

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_score_clamped_to_1_5(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = json.dumps(
            {
                "score": 10,
                "confidence": "high",
                "rationale": "test",
                "violations": [],
            }
        )
        mock_body = io.BytesIO(json.dumps({"completion": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test",
            rubric="rubric",
            model_id="anthropic.claude-3-sonnet",
        )

        assert result["score"] == 5

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_score_clamped_below_1(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = json.dumps(
            {
                "score": 0,
                "confidence": "high",
                "rationale": "test",
                "violations": [],
            }
        )
        mock_body = io.BytesIO(json.dumps({"completion": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test",
            rubric="rubric",
            model_id="anthropic.claude-3-sonnet",
        )

        assert result["score"] == 1

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_invalid_confidence_defaults_to_low(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = json.dumps(
            {
                "score": 3,
                "confidence": "invalid",
                "rationale": "test",
                "violations": [],
            }
        )
        mock_body = io.BytesIO(json.dumps({"completion": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test",
            rubric="rubric",
            model_id="anthropic.claude-3-sonnet",
        )

        assert result["confidence"] == "low"

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_malformed_json_returns_defaults(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_body = io.BytesIO(json.dumps({"completion": "not json at all"}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test",
            rubric="rubric",
            model_id="anthropic.claude-3-sonnet",
        )

        assert result["score"] == 3
        assert result["confidence"] == "low"
        assert result["rationale"] == "Unable to parse evaluator response"
        assert result["violations"] == []

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_non_numeric_score_defaults_to_3(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = json.dumps(
            {
                "score": "abc",
                "confidence": "high",
                "rationale": "test",
                "violations": [],
            }
        )
        mock_body = io.BytesIO(json.dumps({"completion": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test",
            rubric="rubric",
            model_id="anthropic.claude-3-sonnet",
        )

        assert result["score"] == 3

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_missing_fields_use_defaults(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = json.dumps({})
        mock_body = io.BytesIO(json.dumps({"completion": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test",
            rubric="rubric",
            model_id="anthropic.claude-3-sonnet",
        )

        assert result["score"] == 3
        assert result["confidence"] == "low"
        assert result["rationale"] == "No rationale provided"
        assert result["violations"] == []

    @patch("src.handlers.api.bedrock.get_bedrock_client")
    def test_non_claude_model_uses_generation_key(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        eval_response = json.dumps(
            {
                "score": 5,
                "confidence": "high",
                "rationale": "Excellent",
                "violations": [],
            }
        )
        mock_body = io.BytesIO(json.dumps({"generation": eval_response}).encode())
        mock_client.invoke_model.return_value = {"body": mock_body}

        result = bedrock.evaluate_output(
            output="Test",
            rubric="rubric",
            model_id="amazon.titan-text-express",
        )

        assert result["score"] == 5


class TestClassifyResult:
    def test_improved(self):
        assert bedrock.classify_result(3, 4) == "Improved"

    def test_regressed(self):
        assert bedrock.classify_result(4, 3) == "Regressed"

    def test_unchanged(self):
        assert bedrock.classify_result(3, 3) == "Unchanged"

    def test_improved_from_low(self):
        assert bedrock.classify_result(1, 5) == "Improved"

    def test_regressed_from_high(self):
        assert bedrock.classify_result(5, 1) == "Regressed"

    def test_both_high(self):
        assert bedrock.classify_result(5, 5) == "Unchanged"

    def test_both_low(self):
        assert bedrock.classify_result(1, 1) == "Unchanged"
