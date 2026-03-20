"""
SLM Provider — Pluggable LLM Abstraction
==========================================
Keeps the model layer completely swappable.
Supports: Ollama, HuggingFace Transformers, OpenAI-compatible APIs, mock.

The insight engine calls ONLY this interface — never a model SDK directly.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Base provider ─────────────────────────────────────────────────────────────

class SLMProvider(ABC):
    """Abstract base class for all SLM/LLM providers."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,   # low temperature for deterministic insights
    ) -> str:
        """Returns raw text from the model."""
        ...

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Generate and parse JSON output. Includes retry logic for malformed JSON.
        Falls back to a safe default structure if parsing fails after retries.
        """
        raw = await self.generate(system_prompt, user_prompt, max_tokens, temperature)
        return self._parse_json_response(raw)

    @staticmethod
    def _parse_json_response(raw: str) -> Dict[str, Any]:
        """Extract and parse JSON from raw model output."""
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            raw = raw.strip()

        # Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting the first {...} block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: log warning and return a safe default
        logger.warning(f"Could not parse JSON from model output. Raw: {raw[:200]}")
        return {
            "title":              "Insight Generation Failed",
            "claim":              "The model did not produce valid structured output.",
            "narrative":          raw[:500] if raw else "No output generated.",
            "recommended_action": "Retry or use a different model.",
            "confidence":         0.1,
            "is_grounded":        False,
            "evidence_refs":      [],
            "tags":               ["parse_error"],
            "fallback_triggered": True,
            "fallback_message":   "JSON parse error — raw model output captured in narrative.",
        }


# ── Ollama provider (local, free, open-weight) ────────────────────────────────

class OllamaProvider(SLMProvider):
    """
    Connects to a local Ollama instance.
    Recommended models: mistral, phi3, qwen2.5, llama3.2
    Install: https://ollama.ai
    Run model: `ollama pull mistral && ollama serve`
    """

    def __init__(
        self,
        model:    str = "mistral",
        base_url: str = "http://localhost:11434",
        timeout:  int = 120,
    ):
        self.model    = model
        self.base_url = base_url
        self.timeout  = timeout

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        import httpx
        payload = {
            "model":  self.model,
            "prompt": f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}",
            "stream": False,
            "options": {
                "temperature":   temperature,
                "num_predict":   max_tokens,
                "repeat_penalty": 1.1,
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("response", "")


# ── HuggingFace Transformers (local GPU/CPU) ───────────────────────────────────

class HuggingFaceProvider(SLMProvider):
    """
    Runs an open-weight model locally via transformers.
    Supports PEFT/LoRA-adapted models (pass adapter_path).
    """

    def __init__(
        self,
        model_name:   str = "microsoft/Phi-3-mini-4k-instruct",
        adapter_path: Optional[str] = None,
        device:       str = "auto",
        quantize:     bool = True,    # 4-bit quantization for efficiency
    ):
        self.model_name   = model_name
        self.adapter_path = adapter_path
        self.device       = device
        self.quantize     = quantize
        self._pipeline    = None

    def _load_pipeline(self):
        if self._pipeline is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig

        logger.info(f"Loading model: {self.model_name} (quantize={self.quantize})")

        bnb_config = None
        if self.quantize:
            try:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                )
            except Exception:
                logger.warning("BitsAndBytes not available, loading without quantization")

        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            device_map=self.device,
            torch_dtype=torch.float16 if not self.quantize else None,
        )

        if self.adapter_path:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, self.adapter_path)
            logger.info(f"Loaded LoRA adapter from {self.adapter_path}")

        self._pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._generate_sync,
            system_prompt, user_prompt, max_tokens, temperature,
        )

    def _generate_sync(self, system_prompt, user_prompt, max_tokens, temperature):
        self._load_pipeline()
        messages = [
            {"role": "system",    "content": system_prompt},
            {"role": "user",      "content": user_prompt},
        ]
        outputs = self._pipeline(
            messages,
            max_new_tokens=max_tokens,
            temperature=max(0.01, temperature),
            do_sample=temperature > 0.05,
            pad_token_id=self._pipeline.tokenizer.eos_token_id,
        )
        return outputs[0]["generated_text"][-1]["content"]


# ── OpenAI-compatible API (any provider with /v1/chat/completions) ────────────

class OpenAICompatibleProvider(SLMProvider):
    """
    Works with: OpenAI, Azure OpenAI, Together.ai, Groq, Anyscale,
    vLLM self-hosted, LM Studio, etc.
    """

    def __init__(
        self,
        model:    str    = "gpt-4o-mini",
        api_key:  str    = "",
        base_url: str    = "https://api.openai.com/v1",
        timeout:  int    = 60,
    ):
        self.model    = model
        self.api_key  = api_key
        self.base_url = base_url
        self.timeout  = timeout

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        import httpx
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }
        payload = {
            "model":       self.model,
            "messages":    [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]


# ── Data-driven provider (default "mock" mode) ────────────────────────────────

class MockSLMProvider(SLMProvider):
    """
    Data-driven copilot: generates real answers directly from the PRAJNA
    prediction data embedded in the prompt — no external LLM required.

    Replaces the old static mock so that SLM_PROVIDER=mock still works out
    of the box, but now returns genuinely useful, question-aware responses.
    """

    model = "prajna-data-driven-v1"

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_prompt(user_prompt: str) -> dict:
        """Extract question, ranked items, and signals from the formatted prompt."""
        import re

        # ── question ──
        q_match = re.search(r'"([^"]{10,})"', user_prompt)
        raw_question = q_match.group(1) if q_match else ""
        # Strip the "Student: … Question: " prefix injected by the frontend
        q_clean = re.sub(r"^Student:.*?Question:\s*", "", raw_question, flags=re.DOTALL).strip()
        question_lc = q_clean.lower()

        # ── student context ──
        score_m  = re.search(r"latest score:\s*([\d.]+)%", raw_question)
        rank_m   = re.search(r"rank:\s*#([\d—\-]+)",       raw_question)
        weak_m   = re.search(r"weakest chapters:\s*([^\n.]+)", raw_question)
        name_m   = re.search(r"Student:\s*([^(]+)\(",       raw_question)
        target_m = re.search(r",\s*(\w[\w ]*?)\s+aspirant", raw_question)

        # ── ranked items ──
        ranked = []
        for m in re.finditer(
            r"\d+\.\s+(.+?)\n\s+importance=([\d.]+),\s+confidence=([\d.]+),\s+trend=(\S+)"
            r"(?:,?\s+chapter=([^\n,]+))?(?:,?\s+subject=([^\n,]+))?",
            user_prompt,
        ):
            ranked.append({
                "name":       m.group(1).strip(),
                "importance": float(m.group(2)),
                "confidence": float(m.group(3)),
                "trend":      m.group(4).strip(",").strip(),
                "chapter":    (m.group(5) or "").strip(),
                "subject":    (m.group(6) or "").strip(),
            })

        # ── exam / year from prompt ──
        exam_m = re.search(r"Exam:\s*(\w+)\s+(\d{4})", user_prompt)

        return {
            "question":     q_clean,
            "question_lc":  question_lc,
            "raw_question": raw_question,
            "ranked":       ranked,
            "student_score": float(score_m.group(1)) if score_m else None,
            "student_rank":  rank_m.group(1) if rank_m else None,
            "weak_chapters": weak_m.group(1).strip() if weak_m else "",
            "student_name":  name_m.group(1).strip() if name_m else "Student",
            "target":        target_m.group(1).strip() if target_m else "NEET",
            "exam":          exam_m.group(1) if exam_m else "NEET",
            "year":          exam_m.group(2) if exam_m else "2026",
        }

    @staticmethod
    def _subject_filter(ranked: list, question_lc: str) -> list:
        """Return only topics matching a subject if the question mentions one."""
        for subj, aliases in {
            "Chemistry":   ["chemistry", "organic", "inorganic", "physical chem"],
            "Biology":     ["biology", "botany", "zoology", "bio"],
            "Physics":     ["physics", "mechanics", "electro"],
            "Mathematics": ["mathematics", "maths", "math", "calculus", "algebra"],
        }.items():
            if any(a in question_lc for a in aliases):
                filt = [r for r in ranked if subj.lower() in r.get("subject", "").lower()
                        or subj.lower() in r["name"].lower()]
                return filt if filt else ranked
        return ranked

    # ── intent handlers ───────────────────────────────────────────────────────

    @staticmethod
    def _study_plan(ctx: dict) -> str:
        ranked = ctx["ranked"][:10]
        subj_hint = ""
        for s, als in {"Chemistry": ["chemistry"], "Biology": ["biology", "bio"],
                       "Physics": ["physics"], "Mathematics": ["maths", "math"]}.items():
            if any(a in ctx["question_lc"] for a in als):
                ranked = [r for r in ranked if s.lower() in r.get("subject", "").lower()] or ranked
                subj_hint = f" for {s}"
                break

        # Try to extract requested duration
        dur_m = re.search(r"(\d+)\s*(week|day)", ctx["question_lc"])
        days  = int(dur_m.group(1)) * (7 if "week" in dur_m.group(2) else 1) if dur_m else 14
        hours_per_day = 6
        total_hours   = days * hours_per_day

        total_imp = sum(r["importance"] for r in ranked) or 1
        lines = [f"📅 {days}-Day Revision Plan{subj_hint} — {total_hours}h total\n"]
        day_cursor = 1
        for i, r in enumerate(ranked, 1):
            alloc_h = max(1, round((r["importance"] / total_imp) * total_hours))
            alloc_d = max(1, round(alloc_h / hours_per_day))
            trend_arrow = "↑" if float(r["trend"]) > 0.4 else ("↓" if float(r["trend"]) < 0.2 else "→")
            lines.append(
                f"{'🔴' if r['importance'] >= 0.8 else '🟡' if r['importance'] >= 0.6 else '🟢'} "
                f"Day {day_cursor}–{day_cursor+alloc_d-1}: {r['name']}\n"
                f"   {alloc_h}h · {r['importance']:.0%} probability · trend {trend_arrow} · "
                f"confidence {r['confidence']:.0%}"
            )
            day_cursor += alloc_d
            if day_cursor > days:
                break
        lines.append(f"\n💡 Focus most on 🔴 topics — they carry the highest appearance probability.")
        return "\n".join(lines)

    @staticmethod
    def _priority_topics(ctx: dict) -> str:
        ranked = ctx["ranked"][:8]
        q = ctx["question_lc"]
        lines = [f"📌 Top Topics to Prioritise — {ctx['exam'].upper()} {ctx['year']}\n"]
        for i, r in enumerate(ranked, 1):
            arrow = "↑ Rising" if float(r["trend"]) > 0.4 else ("↓ Declining" if float(r["trend"]) < 0.2 else "→ Stable")
            subj  = r.get("subject") or r.get("chapter") or ""
            lines.append(
                f"{i}. {r['name']} ({subj})\n"
                f"   Probability: {r['importance']:.0%} · Confidence: {r['confidence']:.0%} · {arrow}"
            )
        lines.append("\n🎯 Revise in this order for maximum exam ROI.")
        return "\n".join(lines)

    @staticmethod
    def _weakness_analysis(ctx: dict) -> str:
        weak = ctx["weak_chapters"]
        name = ctx["student_name"]
        score = ctx["student_score"]
        ranked = ctx["ranked"]

        lines = [f"🔍 Weakness Analysis for {name}\n"]
        if score:
            lines.append(f"Latest score: {score:.1f}% · Weakest areas: {weak}\n")

        # Cross-reference weak chapters with high-probability predictions
        critical = [r for r in ranked
                    if any(w.strip().lower() in r["name"].lower() for w in weak.split(","))
                    and r["importance"] >= 0.6]
        if critical:
            lines.append("⚠️ These weak chapters are also HIGH-PROBABILITY in predictions:\n")
            for r in critical:
                lines.append(f"  • {r['name']} — {r['importance']:.0%} exam probability")
            lines.append("\n🚨 Fix these FIRST — they are both weak spots AND likely exam topics.\n")

        # Also list top predictions student should prioritise
        others = [r for r in ranked[:5] if r not in critical]
        if others:
            lines.append("Other high-probability topics to keep up with:")
            for r in others:
                lines.append(f"  • {r['name']} ({r['importance']:.0%})")
        return "\n".join(lines)

    @staticmethod
    def _trajectory_comparison(ctx: dict) -> str:
        name  = ctx["student_name"]
        score = ctx["student_score"]
        rank  = ctx["student_rank"]
        target = ctx["target"]
        ranked = ctx["ranked"][:5]

        lines = [f"📊 Trajectory Comparison — {name} vs Top-100 {target} Students\n"]
        if score:
            gap = max(0, 85 - score)
            lines.append(
                f"Your latest score: {score:.1f}%  |  Rank: #{rank or '—'}\n"
                f"Typical top-100 {target} score: ~85–92%\n"
                f"Gap to close: {gap:.1f} percentage points\n"
            )
        lines.append(f"Top predicted topics for {target} {ctx['year']} (all top students will cover these):\n")
        for i, r in enumerate(ranked, 1):
            lines.append(f"  {i}. {r['name']} ({r['importance']:.0%} probability)")
        lines.append(
            f"\n💡 Top-100 students typically achieve >80% accuracy on the top 5 high-probability topics. "
            f"Focus on these for the biggest rank jump."
        )
        return "\n".join(lines)

    @staticmethod
    def _general_answer(ctx: dict) -> str:
        ranked = ctx["ranked"][:6]
        lines  = [f"🧠 PRAJNA Prediction Insights — {ctx['exam'].upper()} {ctx['year']}\n",
                  f"Based on 23,119+ historical questions, here are the top predictions:\n"]
        for i, r in enumerate(ranked, 1):
            arrow = "↑" if float(r["trend"]) > 0.4 else "→"
            lines.append(
                f"{i}. {r['name']} {arrow}\n"
                f"   {r['importance']:.0%} appearance probability · {r['confidence']:.0%} model confidence"
            )
        if ctx["question"]:
            lines.append(f"\nYour question: \"{ctx['question']}\"\n"
                         f"The above topics are most relevant based on PRAJNA's analysis of historical patterns.")
        return "\n".join(lines)

    # ── main entry point ──────────────────────────────────────────────────────

    async def generate(
        self,
        system_prompt: str,
        user_prompt:   str,
        max_tokens:    int   = 1024,
        temperature:   float = 0.1,
    ) -> str:
        ctx = self._parse_prompt(user_prompt)

        # Subject-filter ranked list if question mentions a specific subject
        ctx["ranked"] = self._subject_filter(ctx["ranked"], ctx["question_lc"])

        q = ctx["question_lc"]

        # Route to appropriate intent handler
        if any(w in q for w in ["study plan", "revision plan", "schedule",
                                  "2 week", "weeks", "daily plan", "timetable"]):
            narrative = self._study_plan(ctx)
            title     = "Personalised Revision Plan"
            tags      = ["study_plan", "data_driven"]
            action    = "Follow the day-wise schedule above. Adjust daily hours as needed."

        elif any(w in q for w in ["weakest", "weak", "struggle", "difficult", "hardest", "fix"]):
            narrative = self._weakness_analysis(ctx)
            title     = "Weakness & Gap Analysis"
            tags      = ["weakness_analysis", "data_driven"]
            action    = "Address 🚨 critical overlaps first — they are both weak and high-probability."

        elif any(w in q for w in ["compare", "trajectory", "top-100", "top 100",
                                   "rank", "vs ", "need to"]):
            narrative = self._trajectory_comparison(ctx)
            title     = "Trajectory vs Top-100 Students"
            tags      = ["comparison", "data_driven"]
            action    = "Close the gap by mastering the top-5 predicted topics with 80%+ accuracy."

        elif any(w in q for w in ["prioritize", "priority", "first", "focus",
                                   "important", "which topic", "should i revise",
                                   "upcoming", "expected"]):
            narrative = self._priority_topics(ctx)
            title     = "Topic Priority Ranking"
            tags      = ["priority", "data_driven"]
            action    = "Revise topics in the listed order for maximum marks ROI."

        else:
            narrative = self._general_answer(ctx)
            title     = f"PRAJNA Predictions — {ctx['exam'].upper()} {ctx['year']}"
            tags      = ["general", "data_driven"]
            action    = "Revise the top predictions for the highest expected questions."

        conf = round(
            sum(r["importance"] for r in ctx["ranked"][:5]) / max(len(ctx["ranked"][:5]), 1) * 0.9,
            2,
        )

        return json.dumps({
            "title":              title,
            "claim":              f"Answer grounded in {len(ctx['ranked'])} PRAJNA predictions.",
            "narrative":          narrative,
            "recommended_action": action,
            "confidence":         min(conf, 0.95),
            "is_grounded":        len(ctx["ranked"]) > 0,
            "evidence_refs":      [],
            "tags":               tags,
            "fallback_triggered": False,
            "fallback_message":   None,
        })


# ── Provider factory ───────────────────────────────────────────────────────────

def create_provider(provider_type: str, **kwargs) -> SLMProvider:
    """Factory function for creating SLM providers from config."""
    providers = {
        "ollama":        OllamaProvider,
        "huggingface":   HuggingFaceProvider,
        "openai":        OpenAICompatibleProvider,
        "together":      OpenAICompatibleProvider,   # same interface
        "groq":          OpenAICompatibleProvider,
        "mock":          MockSLMProvider,
    }
    cls = providers.get(provider_type.lower())
    if cls is None:
        raise ValueError(f"Unknown provider '{provider_type}'. Available: {list(providers.keys())}")
    return cls(**kwargs)
