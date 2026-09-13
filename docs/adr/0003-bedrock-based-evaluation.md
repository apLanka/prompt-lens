# 0003: Bedrock-Based Evaluation with Strict JSON Schema

We decided to use Amazon Bedrock for evaluation, calling a (potentially cheaper) allowlisted model to score outputs against the rubric. The evaluator returns a strict JSON schema:

```json
{
  "score": 1-5,
  "confidence": "high|medium|low",
  "rationale": "...",
  "violations": ["..."]
}
```

We chose this approach because:
1. Leverages existing Bedrock infrastructure; no additional services needed
2. Natural language rubrics are easier to write and maintain than code-based assertions
3. Structured JSON output enables automated classification

Key constraints:
- Scores are clamped to 1-5 range; out-of-range values are normalized
- Malformed JSON or low confidence triggers "Needs review" classification
- The evaluator prompt must assess only supplied evidence, not invent policy or facts
- We record the evaluator model ID for reproducibility

This keeps evaluation flexible while maintaining structured, machine-readable results.
