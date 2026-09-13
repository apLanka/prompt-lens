"""Seed data for demo suite."""

import os
import boto3
from datetime import datetime, timezone


def seed_demo_suite():
    """Create a demo suite with sample test cases."""
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(os.environ.get("TABLE_NAME", "PromptLens"))

    # Demo suite
    suite_id = "demo-support-replies"
    suite_name = "Customer Support Replies"
    now = datetime.now(timezone.utc).isoformat()

    # Create suite metadata
    table.put_item(
        Item={
            "PK": f"SUITE#{suite_id}",
            "SK": "META",
            "suite_id": suite_id,
            "name": suite_name,
            "created_at": now,
            "updated_at": now,
        }
    )

    # Demo cases
    cases = [
        {
            "case_id": "case-001",
            "input": "I can't access my account. I've tried resetting my password but the email never arrives.",
            "expected_behavior": "Empathize with the user, provide troubleshooting steps for password reset, offer alternative verification methods",
            "tags": ["account-access", "password-reset"],
        },
        {
            "case_id": "case-002",
            "input": "Your product is too expensive. I found a competitor offering similar features for half the price.",
            "expected_behavior": "Acknowledge the concern, highlight unique value propositions, offer to discuss pricing options without being defensive",
            "tags": ["pricing", "competitive"],
        },
        {
            "case_id": "case-003",
            "input": "I've been waiting 3 days for a response to my support ticket. This is unacceptable.",
            "expected_behavior": "Apologize for the delay, explain the reason if known, escalate the issue, provide direct contact information",
            "tags": ["response-time", "escalation"],
        },
    ]

    # Create cases
    for case in cases:
        table.put_item(
            Item={
                "PK": f"SUITE#{suite_id}",
                "SK": f"CASE#{case['case_id']}",
                "case_id": case["case_id"],
                "suite_id": suite_id,
                "input": case["input"],
                "expected_behavior": case["expected_behavior"],
                "tags": case["tags"],
            }
        )

    print(f"Seeded demo suite '{suite_name}' with {len(cases)} cases")
    return suite_id


if __name__ == "__main__":
    seed_demo_suite()
