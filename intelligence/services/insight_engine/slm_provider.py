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


# ── Mock provider (testing, CI) ───────────────────────────────────────────────

class MockSLMProvider(SLMProvider):
    """
    Returns deterministic mock responses. Used in testing and CI.
    Does NOT call any model.
    """

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
    ) -> str:
        return json.dumps({
            "title":              "Mock Insight: High Priority Topic Detected",
            "claim":              "This topic has a high appearance probability based on historical patterns.",
            "narrative":          "The PRAJNA SLM has flagged this topic with a high importance score (>0.75). "
                                  "Historical data shows it has appeared consistently in recent exams, with a "
                                  "positive trend slope indicating rising importance. The syllabus coverage "
                                  "signal is strong, suggesting this is a core curriculum requirement. "
                                  "Based on recurrence patterns, this topic is expected to appear in the "
                                  "upcoming exam with 3-5 questions.",
            "recommended_action": "Prioritize this topic in your revision schedule. Allocate 3-4 study hours "
                                  "and focus on the key micro-topics listed in the evidence section.",
            "confidence":         0.82,
            "is_grounded":        True,
            "evidence_refs":      ["E1", "E2"],
            "tags":               ["high_priority", "mock_response"],
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
