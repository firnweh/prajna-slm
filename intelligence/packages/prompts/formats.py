"""
Output Format Definitions
===========================
JSON schemas and format instructions injected into prompts.
Using structured output forces the SLM to produce parseable responses
and reduces hallucination.
"""

# ── JSON schema for SLM output ────────────────────────────────────────────────

OUTPUT_FORMAT_SCHEMA = """
Always respond in valid JSON matching this schema:

```json
{
  "title": "<headline, max 80 chars>",
  "claim": "<core assertion in 1-2 sentences — must be backed by evidence>",
  "narrative": "<full explanation, 100-400 words, plain language for persona>",
  "recommended_action": "<specific, actionable step for the persona>",
  "confidence": <0.0 to 1.0, reflects prediction engine confidence>,
  "is_grounded": <true if supported by evidence, false otherwise>,
  "evidence_refs": ["<evidence_id_1>", "<evidence_id_2>"],
  "tags": ["<tag1>", "<tag2>"],
  "fallback_triggered": <true if evidence was insufficient>,
  "fallback_message": "<null or brief message explaining the gap>"
}
```

Rules:
- confidence must be <= the average confidence_score of cited prediction signals
- narrative must NOT include any data not provided in the context
- evidence_refs must only contain IDs from the provided evidence list
- If is_grounded is false, set fallback_triggered to true
"""

# ── Task-specific output schemas ──────────────────────────────────────────────

REVISION_PLAN_FORMAT = """
Respond with a JSON object:
```json
{
  "title": "...",
  "claim": "...",
  "narrative": "...",
  "recommended_action": "...",
  "confidence": 0.0,
  "is_grounded": true,
  "revision_schedule": [
    {
      "priority": 1,
      "topic": "...",
      "chapter": "...",
      "urgency": "critical|high|medium|low",
      "study_hours": 0.0,
      "why": "...",
      "key_micro_topics": ["..."]
    }
  ],
  "evidence_refs": [],
  "tags": [],
  "fallback_triggered": false,
  "fallback_message": null
}
```
"""

EXAM_BRIEF_FORMAT = """
Respond with a JSON object:
```json
{
  "title": "...",
  "claim": "...",
  "narrative": "...",
  "recommended_action": "...",
  "confidence": 0.0,
  "is_grounded": true,
  "must_cover_topics": ["..."],
  "high_value_clusters": ["..."],
  "trend_alerts": ["..."],
  "teacher_notes": "...",
  "evidence_refs": [],
  "tags": [],
  "fallback_triggered": false,
  "fallback_message": null
}
```
"""

COPILOT_ANSWER_FORMAT = """
Respond with a JSON object:
```json
{
  "title": "...",
  "claim": "...",
  "narrative": "...",
  "recommended_action": "...",
  "confidence": 0.0,
  "is_grounded": true,
  "follow_up_questions": ["...", "...", "..."],
  "evidence_refs": [],
  "tags": [],
  "fallback_triggered": false,
  "fallback_message": null
}
```
"""

CHAPTER_SUMMARY_FORMAT = """
Respond with a JSON object:
```json
{
  "title": "...",
  "claim": "...",
  "narrative": "...",
  "recommended_action": "...",
  "confidence": 0.0,
  "is_grounded": true,
  "importance_tier": "A|B|C",
  "expected_questions": "e.g. 3-5 questions",
  "top_micro_topics": ["...", "...", "..."],
  "teacher_notes": "...",
  "student_summary": "...",
  "evidence_refs": [],
  "tags": [],
  "fallback_triggered": false,
  "fallback_message": null
}
```
"""

FORMAT_MAP = {
    "revision_plan":    REVISION_PLAN_FORMAT,
    "exam_brief":       EXAM_BRIEF_FORMAT,
    "copilot_answer":   COPILOT_ANSWER_FORMAT,
    "chapter_summary":  CHAPTER_SUMMARY_FORMAT,
    "default":          OUTPUT_FORMAT_SCHEMA,
}


def get_format_instructions(task: str) -> str:
    return FORMAT_MAP.get(task, FORMAT_MAP["default"])
