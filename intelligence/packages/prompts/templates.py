"""
Task-specific Prompt Templates
================================
Each template receives a structured context dict and returns a
complete user-turn message to send to the SLM.

All templates are deterministic — no randomness, no ambiguity.
"""

from __future__ import annotations
from typing import Any, Dict, List
from .formats import get_format_instructions


def _format_signals(signals: Dict[str, Any]) -> str:
    lines = []
    for k, v in signals.items():
        if isinstance(v, float):
            lines.append(f"  - {k}: {v:.3f}")
        else:
            lines.append(f"  - {k}: {v}")
    return "\n".join(lines)


def _format_evidence(evidence_list: List[Dict]) -> str:
    if not evidence_list:
        return "  [No retrieved evidence — low confidence mode]"
    lines = []
    for i, ev in enumerate(evidence_list, 1):
        lines.append(
            f"  [{ev.get('evidence_id','E'+str(i))}] "
            f"Source: {ev.get('source_name','Unknown')} | "
            f"Relevance: {ev.get('relevance_score',0):.2f}\n"
            f"  Excerpt: {ev.get('excerpt','')[:400]}"
        )
    return "\n\n".join(lines)


def _format_ranked_items(items: List[Dict]) -> str:
    if not items:
        return "  [No ranked items provided]"
    lines = []
    for i, item in enumerate(items[:10], 1):
        name = item.get("name", item.get("micro_topic_name", item.get("topic", "Unknown")))
        imp  = item.get("importance_probability", item.get("composite_importance", 0))
        conf = item.get("confidence_score", item.get("composite_confidence", 0))
        trend = item.get("trend_direction", item.get("topic_trend_score", "unknown"))
        chapter = item.get("chapter", "")
        subject = item.get("subject", "")
        meta = f", chapter={chapter}, subject={subject}" if (chapter or subject) else ""
        lines.append(
            f"  {i}. {name}\n"
            f"     importance={imp:.3f}, confidence={conf:.3f}, trend={trend}{meta}"
        )
    return "\n".join(lines)


# ── Template functions ────────────────────────────────────────────────────────

def topic_importance_template(ctx: Dict[str, Any]) -> str:
    """
    Explain why a micro-topic or topic is important for the upcoming exam.
    """
    return f"""\
## TASK: Explain Topic Importance

You are generating a **topic importance insight** for {ctx['persona']} persona.

### Scope
- Exam: {ctx['exam_type'].upper()} {ctx['target_year']}
- Level: {ctx['scope']} — {ctx['scope_name']}
- Subject: {ctx.get('subject', 'N/A')}
- Chapter: {ctx.get('chapter', 'N/A')}

### PRAJNA Prediction Signals
{_format_signals(ctx.get('prediction_signals', {}))}

### Top Ranked Items in Scope
{_format_ranked_items(ctx.get('ranked_items', []))}

### Retrieved Evidence
{_format_evidence(ctx.get('retrieved_passages', []))}

### Your task
Explain why **{ctx['scope_name']}** is important for {ctx['exam_type'].upper()} {ctx['target_year']}.
Specifically:
1. What do the prediction signals say?
2. What does the historical pattern show?
3. Why should the {ctx['persona']} pay attention to this?
4. What specific micro-topics or sub-concepts should be focused on?

{get_format_instructions('default')}
"""


def revision_priority_template(ctx: Dict[str, Any]) -> str:
    """
    Generate a revision priority plan for a subject or chapter.
    """
    available_days = ctx.get('available_days')
    days_str = f"{available_days} days remaining" if available_days else "unspecified timeline"

    return f"""\
## TASK: Generate Revision Priority Plan

You are generating a **revision priority plan** for {ctx['persona']} persona.

### Context
- Exam: {ctx['exam_type'].upper()} {ctx['target_year']}
- Subject: {ctx.get('subject', 'All subjects')}
- Timeline: {days_str}

### Top Predicted Topics (by PRAJNA SLM)
{_format_ranked_items(ctx.get('ranked_items', []))}

### Prediction Signal Summary
{_format_signals(ctx.get('prediction_signals', {}))}

### Retrieved Evidence (curriculum & history)
{_format_evidence(ctx.get('retrieved_passages', []))}

### Your task
Generate a prioritized revision plan. For each topic:
1. Rank it (1=highest priority)
2. Explain WHY it is high priority (signal-backed)
3. Estimate study hours
4. List the key micro-topics to cover
5. Flag if skipping this topic is risky

Be ruthlessly prioritized — a student cannot cover everything.

{get_format_instructions('revision_plan')}
"""


def chapter_summary_template(ctx: Dict[str, Any]) -> str:
    """
    Summarize a chapter's importance and key topics.
    """
    return f"""\
## TASK: Chapter Intelligence Summary

You are generating a **chapter importance summary** for {ctx['persona']} persona.

### Chapter
- Chapter: {ctx['scope_name']}
- Subject: {ctx.get('subject', 'N/A')}
- Exam: {ctx['exam_type'].upper()} {ctx['target_year']}

### Prediction Signals for This Chapter
{_format_signals(ctx.get('prediction_signals', {}))}

### Top Topics in Chapter (by importance)
{_format_ranked_items(ctx.get('ranked_items', []))}

### Historical Evidence
{_format_evidence(ctx.get('retrieved_passages', []))}

### Your task
1. Assign an importance tier: A (must revise), B (should revise), C (optional)
2. Estimate expected question count
3. List top 3-5 micro-topics the {ctx['persona']} should focus on
4. Explain the trend: is this chapter rising, stable, or declining in importance?
5. Provide persona-appropriate notes ({ctx['persona']}: teacher notes or student summary)

{get_format_instructions('chapter_summary')}
"""


def subject_strategy_template(ctx: Dict[str, Any]) -> str:
    """
    Generate full subject-level revision strategy.
    """
    return f"""\
## TASK: Subject Strategy Generation

You are generating a **subject-level exam strategy** for {ctx['persona']} persona.

### Subject Overview
- Subject: {ctx['scope_name']}
- Exam: {ctx['exam_type'].upper()} {ctx['target_year']}

### Subject-Level Prediction Signals
{_format_signals(ctx.get('prediction_signals', {}))}

### Chapter Rankings (by PRAJNA SLM)
{_format_ranked_items(ctx.get('ranked_items', []))}

### Topic Clusters (co-occurring high-importance groups)
{ctx.get('cluster_summary', '[No cluster data available]')}

### Trend vs Previous Year
{ctx.get('trend_summary', '[No trend data available]')}

### Retrieved Evidence
{_format_evidence(ctx.get('retrieved_passages', []))}

### Your task
Generate a complete subject strategy:
1. Overall subject importance for this exam (marks, percentage)
2. Must-revise chapters (A-tier) with justification
3. Should-revise chapters (B-tier)
4. Optional chapters (C-tier)
5. Top 5 micro-topics across the subject
6. Study hour recommendation
7. Risk alert: what happens if a student skips the top chapter

{get_format_instructions('default')}
"""


def exam_brief_template(ctx: Dict[str, Any]) -> str:
    """
    Generate an exam brief for academic teams.
    """
    return f"""\
## TASK: Academic Exam Brief

You are generating an **exam intelligence brief** for the {ctx['persona']} team.

### Exam
- Type: {ctx['exam_type'].upper()} {ctx['target_year']}
- Subjects covered: {ctx.get('subjects_covered', 'All')}

### Cross-Subject Top Predictions
{_format_ranked_items(ctx.get('ranked_items', []))}

### Key Trend Shifts (vs {ctx.get('compare_year', 'previous year')})
{ctx.get('trend_summary', '[No trend data available]')}

### High-Priority Clusters
{ctx.get('cluster_summary', '[No cluster data available]')}

### Prediction Confidence Overview
{_format_signals(ctx.get('prediction_signals', {}))}

### Retrieved Evidence
{_format_evidence(ctx.get('retrieved_passages', []))}

### Your task
Write a professional exam intelligence brief that:
1. Summarizes the top 5 most important chapters/topics across all subjects
2. Highlights significant trend shifts from previous exams
3. Identifies topic clusters that should be covered together
4. Provides teacher/content team action items
5. Flags any unusual patterns or anomalies

{get_format_instructions('exam_brief')}
"""


def copilot_answer_template(ctx: Dict[str, Any]) -> str:
    """
    Answer a natural language question from the user.
    """
    history_str = ""
    if ctx.get("conversation_history"):
        history_str = "### Previous Conversation\n"
        for turn in ctx["conversation_history"][-4:]:  # last 4 turns
            history_str += f"  {turn.get('role','user').title()}: {turn.get('content','')}\n"

    return f"""\
## TASK: Academic Copilot Answer

You are answering a question from a {ctx['persona']}.

### Question
"{ctx.get('question', '')}"

{history_str}

### Relevant Prediction Data
- Exam: {ctx['exam_type'].upper()} {ctx['target_year']}
- Subject filter: {ctx.get('subject_filter', 'None')}

### Top Relevant Predictions
{_format_ranked_items(ctx.get('ranked_items', []))}

### Prediction Signals
{_format_signals(ctx.get('prediction_signals', {}))}

### Retrieved Evidence
{_format_evidence(ctx.get('retrieved_passages', []))}

### Your task
Answer the question accurately, based only on the prediction data and evidence above.
- Be direct and specific
- Cite evidence IDs where possible
- Suggest 2-3 natural follow-up questions the user might ask
- If you cannot answer confidently, say so and explain what data is needed

{get_format_instructions('copilot_answer')}
"""


def trend_shift_template(ctx: Dict[str, Any]) -> str:
    """
    Analyze and explain trend shifts between years.
    """
    return f"""\
## TASK: Trend Shift Analysis

You are generating a **trend shift report** for {ctx['persona']} persona.

### Comparison
- Exam: {ctx['exam_type'].upper()}
- Current year: {ctx['target_year']}
- Baseline year: {ctx.get('compare_year', ctx['target_year'] - 1)}

### Rising Topics (importance increased significantly)
{_format_ranked_items(ctx.get('rising_topics', []))}

### Declining Topics (importance decreased significantly)
{_format_ranked_items(ctx.get('declining_topics', []))}

### New Topics (appearing in predictions for first time)
{', '.join(ctx.get('new_topics', [])) or '[None]'}

### Dropped Topics (no longer in top predictions)
{', '.join(ctx.get('dropped_topics', [])) or '[None]'}

### Retrieved Evidence
{_format_evidence(ctx.get('retrieved_passages', []))}

### Your task
1. Explain the most significant trend shifts
2. Identify the likely causes (curriculum changes, exam pattern shifts, etc.)
3. Recommend what action to take based on these shifts
4. Flag any counterintuitive patterns

{get_format_instructions('default')}
"""


# ── Template registry ──────────────────────────────────────────────────────────

TEMPLATE_REGISTRY = {
    "topic_importance":      topic_importance_template,
    "revision_priority":     revision_priority_template,
    "chapter_summary":       chapter_summary_template,
    "subject_strategy":      subject_strategy_template,
    "exam_brief":            exam_brief_template,
    "copilot_answer":        copilot_answer_template,
    "trend_shift":           trend_shift_template,
}


def build_prompt(task: str, ctx: Dict[str, Any]) -> str:
    """Build a task-specific prompt from a context dict."""
    template_fn = TEMPLATE_REGISTRY.get(task)
    if not template_fn:
        raise ValueError(f"Unknown task '{task}'. Available: {list(TEMPLATE_REGISTRY.keys())}")
    return template_fn(ctx)
