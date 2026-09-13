"""Bedrock operations for prompt invocation and evaluation."""

import json
import os
import time
from typing import Tuple, Optional
import boto3
from botocore.exceptions import ClientError


def get_bedrock_client():
    """Get Bedrock runtime client."""
    return boto3.client("bedrock-runtime")


def invoke_model(
    model_id: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Tuple[str, float]:
    """Invoke a Bedrock model and return output with latency.

    Args:
        model_id: Bedrock model ID
        prompt: Input prompt
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Tuple of (output_text, latency_ms)

    Raises:
        ClientError: If Bedrock invocation fails
    """
    client = get_bedrock_client()

    start_time = time.time()

    body = json.dumps(
        {
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": temperature,
        }
    )

    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    latency_ms = (time.time() - start_time) * 1000

    response_body = json.loads(response["body"].read())

    # Extract text based on model type
    if "claude" in model_id.lower():
        output_text = response_body.get("completion", "")
    else:
        output_text = response_body.get("generation", "")

    return output_text, latency_ms


def evaluate_output(
    output: str,
    rubric: str,
    model_id: str,
    temperature: float = 0.3,
) -> dict:
    """Evaluate output against rubric using Bedrock.

    Args:
        output: The output to evaluate
        rubric: Evaluation criteria
        model_id: Bedrock model ID for evaluation
        temperature: Sampling temperature (lower for more consistent scoring)

    Returns:
        Dictionary with score, confidence, rationale, violations

    """
    client = get_bedrock_client()

    evaluation_prompt = f"""You are an expert evaluator. Score the following output based on the rubric.

Output to evaluate:
{output}

Evaluation rubric:
{rubric}

Provide your evaluation as a JSON object with exactly these fields:
- "score": an integer from 1 to 5 (1=poor, 5=excellent)
- "confidence": "high", "medium", or "low"
- "rationale": a brief explanation of your scoring
- "violations": an array of specific rubric violations (empty array if none)

Respond ONLY with the JSON object, no other text."""

    body = json.dumps(
        {
            "prompt": evaluation_prompt,
            "max_tokens_to_sample": 1024,
            "temperature": temperature,
        }
    )

    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    response_body = json.loads(response["body"].read())

    # Extract text based on model type
    if "claude" in model_id.lower():
        response_text = response_body.get("completion", "")
    else:
        response_text = response_body.get("generation", "")

    # Parse JSON response
    try:
        # Try to extract JSON from response (may be wrapped in markdown)
        json_match = response_text.strip()
        if "```json" in json_match:
            json_match = json_match.split("```json")[1].split("```")[0]
        elif "```" in json_match:
            json_match = json_match.split("```")[1].split("```")[0]

        evaluation = json.loads(json_match)

        # Validate and clamp score
        score = evaluation.get("score", 3)
        if not isinstance(score, (int, float)):
            score = 3
        score = max(1, min(5, int(score)))

        # Validate confidence
        confidence = evaluation.get("confidence", "low")
        if confidence not in ["high", "medium", "low"]:
            confidence = "low"

        return {
            "score": score,
            "confidence": confidence,
            "rationale": evaluation.get("rationale", "No rationale provided"),
            "violations": evaluation.get("violations", []),
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        # Malformed response - return default "Needs review" scoring
        return {
            "score": 3,
            "confidence": "low",
            "rationale": "Unable to parse evaluator response",
            "violations": [],
        }


def classify_result(baseline_score: int, candidate_score: int) -> str:
    """Classify result based on score comparison.

    Args:
        baseline_score: Score for baseline output (1-5)
        candidate_score: Score for candidate output (1-5)

    Returns:
        Classification string
    """
    if candidate_score > baseline_score:
        return "Improved"
    elif candidate_score < baseline_score:
        return "Regressed"
    else:
        return "Unchanged"
