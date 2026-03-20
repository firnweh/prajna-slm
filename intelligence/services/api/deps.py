"""
FastAPI Dependency Injection
==============================
All service singletons are initialized here and injected via Depends().
This keeps the router code clean and testable.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from config.settings import get_settings
from services.prediction_adapter.client import PredictionAdapter, PredictionAdapterConfig
from services.topic_intelligence.aggregator import TopicIntelligenceAggregator
from services.topic_intelligence.cluster_detector import TopicClusterDetector
from services.insight_engine.slm_provider import create_provider, SLMProvider
from services.insight_engine.generator import InsightGenerator
from services.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_prediction_adapter() -> PredictionAdapter:
    settings = get_settings()
    config = PredictionAdapterConfig()
    config.mode          = settings.prediction_adapter_mode
    config.http_base_url = settings.prediction_engine_url
    config.cache_ttl_sec = settings.prediction_cache_ttl_sec
    return PredictionAdapter(config)


@lru_cache(maxsize=1)
def get_aggregator() -> TopicIntelligenceAggregator:
    return TopicIntelligenceAggregator()


@lru_cache(maxsize=1)
def get_cluster_detector() -> TopicClusterDetector:
    return TopicClusterDetector()


@lru_cache(maxsize=1)
def get_rag_retriever() -> Optional[RAGRetriever]:
    settings = get_settings()
    if not settings.rag_enabled:
        return None
    return RAGRetriever(
        collection_name = settings.chroma_collection,
        persist_dir     = "./data/rag_store",
        embedding_model = settings.embedding_model,
    )


@lru_cache(maxsize=1)
def get_slm_provider() -> SLMProvider:
    settings = get_settings()
    kwargs = settings.get_slm_kwargs()
    return create_provider(settings.slm_provider, **kwargs)


@lru_cache(maxsize=1)
def get_insight_generator() -> InsightGenerator:
    provider  = get_slm_provider()
    retriever = get_rag_retriever()
    return InsightGenerator(slm_provider=provider, rag_retriever=retriever)


# ── FastAPI Depends wrappers ───────────────────────────────────────────────────

def prediction_adapter_dep() -> PredictionAdapter:
    return get_prediction_adapter()

def aggregator_dep() -> TopicIntelligenceAggregator:
    return get_aggregator()

def cluster_detector_dep() -> TopicClusterDetector:
    return get_cluster_detector()

def insight_generator_dep() -> InsightGenerator:
    return get_insight_generator()

def rag_retriever_dep() -> Optional[RAGRetriever]:
    return get_rag_retriever()
