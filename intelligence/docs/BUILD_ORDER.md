# PRAJNA Intelligence Layer — Build Order & Phased Roadmap

## Overview

Four phases, each independently deployable and testable.
Each phase delivers concrete user value without requiring the next.

---

## Phase 1 — MVP: Topic Intelligence API (no SLM)
**Goal:** Ship a working prediction + ranking API that exercises the full
data pipeline without any SLM. Validate the data contracts end-to-end.

**Timeline:** 3–5 days

### What you build:
| File | Purpose |
|------|---------|
| `packages/schemas/prediction.py` | ✅ Done — micro-topic prediction contracts |
| `packages/schemas/intelligence.py` | ✅ Done — insight/priority object schemas |
| `packages/utils/hierarchy.py` | ✅ Done — aggregation helpers |
| `packages/utils/confidence.py` | ✅ Done — priority scoring formula |
| `services/prediction_adapter/client.py` | ✅ Done — PRAJNA engine wrapper |
| `services/topic_intelligence/aggregator.py` | ✅ Done — batch builder + ranker |
| `services/topic_intelligence/cluster_detector.py` | ✅ Done — topic cluster detection |
| `services/api/routers/predictions.py` | ✅ Done — raw prediction endpoints |
| `config/settings.py` | ✅ Done — typed config |
| `services/api/main.py` | ✅ Done — FastAPI app |

### What you can demo after Phase 1:
- `GET /api/v1/predictions/batch-summary` — subject importance overview
- `GET /api/v1/predictions/rank-all` — global topic ranking
- `GET /api/v1/predictions/chapter/{chapter}` — chapter-level breakdown
- Priority scores, urgency tiers, topic clusters — all without an SLM

### Smoke test:
```bash
cd intelligence
python -m scripts.seed_data --exam neet --year 2025
uvicorn services.api.main:app --port 8001 --reload
curl http://localhost:8001/api/v1/predictions/batch-summary?exam_type=neet&target_year=2025
```

---

## Phase 2 — Grounded SLM Insight Generation
**Goal:** Wire in the open-weight SLM with anti-hallucination prompts.
Generate explanatory insights for topics, chapters, and subjects.

**Timeline:** 1–2 weeks

### Prerequisites:
- Phase 1 complete and smoke-tested
- Ollama running locally (`ollama serve`) OR OpenAI API key
- ChromaDB running for RAG

### What you build:
| File | Purpose |
|------|---------|
| `packages/prompts/formats.py` | ✅ Done — JSON output schemas |
| `packages/prompts/system.py` | ✅ Done — system prompts + anti-hallucination |
| `packages/prompts/templates.py` | ✅ Done — task-specific prompt templates |
| `services/insight_engine/slm_provider.py` | ✅ Done — Ollama/HF/OpenAI providers |
| `services/insight_engine/generator.py` | ✅ Done — insight generation pipeline |
| `services/rag/indexer.py` | ✅ Done — document indexer |
| `services/rag/retriever.py` | ✅ Done — metadata-filtered retrieval |
| `services/api/routers/insights.py` | ✅ Done — SLM insight endpoints |
| `services/api/routers/reports.py` | ✅ Done — revision plan + trend analysis |

### Setup steps:
```bash
# 1. Install Ollama and pull a model
curl https://ollama.ai/install.sh | sh
ollama pull mistral:7b-instruct

# 2. Index documents into ChromaDB
python -m scripts.index_documents --source all --exam neet

# 3. Update .env
SLM_PROVIDER=ollama
RAG_ENABLED=true
CHROMA_HOST=localhost

# 4. Restart API
uvicorn services.api.main:app --port 8001 --reload
```

### What you can demo after Phase 2:
- `POST /api/v1/insights/micro-topic` — SLM explains any micro-topic with citations
- `POST /api/v1/insights/chapter` — chapter-level intelligence with clusters
- `POST /api/v1/reports/revision-plan` — full cross-subject revision plan
- All outputs grounded in prediction signals + RAG-retrieved evidence

### Switching SLM providers:
```bash
# Use Phi-3 on Apple Silicon
SLM_PROVIDER=huggingface
HF_MODEL_ID=microsoft/phi-3-mini-4k-instruct
HF_DEVICE=mps

# Use OpenAI (cloud)
SLM_PROVIDER=openai_compatible
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

---

## Phase 3 — Academic Copilot & Dashboards
**Goal:** Add conversational NL interface + connect to student data for personalized recommendations.

**Timeline:** 1–2 weeks

### What you build:
| File | Purpose |
|------|---------|
| `services/api/routers/copilot.py` | ✅ Done — NL Q&A with conversation history |
| Student integration adapter | Link student weakness data (from analyzer.py) to copilot |
| Frontend dashboard widgets | Embed intelligence insights in student-dashboard.html |
| Personalized revision plan | Cross-reference student weak zones + prediction priorities |

### New capabilities:
- Multi-turn conversation memory (`conversation_history` field)
- Student-personalized recommendations: "Riya is weak in Genetics (42% accuracy) + Genetics has 92% prediction probability → critical alert"
- Dashboard widget: "Your PRAJNA Risk Zones" panel
- Teacher dashboard: class-level weakness vs. predicted exam topics

### Integration with student dashboard:
```javascript
// Fetch intelligence insights and merge with student weakness data
const resp = await fetch('/api/v1/copilot/ask', {
    method: 'POST',
    body: JSON.stringify({
        exam_type: 'neet', target_year: 2025,
        question: `I scored ${accuracy}% in Genetics. Should I prioritize it?`,
        persona: 'student'
    })
});
```

---

## Phase 4 — Automated Evaluation & Continuous Improvement
**Goal:** Close the feedback loop. Auto-evaluate insight quality, detect hallucinations at scale, and improve prompts iteratively.

**Timeline:** 2–3 weeks

### What you build:
| File | Purpose |
|------|---------|
| `services/evaluation/metrics.py` | ✅ Done — grounding, factual, ranking, usefulness |
| `services/evaluation/benchmark.py` | ✅ Done — benchmark suite + latency tracking |
| A/B prompt testing harness | Compare prompts on grounding accuracy |
| Feedback collection endpoint | `POST /api/v1/feedback` — thumbs up/down on insights |
| Auto-regression tests | Run benchmark in CI on every model/prompt change |

### Evaluation targets:
| Metric | Target |
|--------|--------|
| Grounding accuracy | ≥ 0.85 |
| Factual consistency | ≥ 0.75 |
| Ranking quality (Kendall τ) | ≥ 0.70 |
| Insight usefulness | ≥ 0.80 |
| Topic coverage (top-10) | ≥ 0.60 |
| P95 latency | ≤ 3000ms (Ollama 7B) |
| Fallback rate | ≤ 10% |

### Running evaluations:
```bash
# Benchmark with mock provider (fast, CI-friendly)
python -m services.evaluation.benchmark --exam neet --year 2025 --provider mock --output

# Benchmark with real SLM (slow, pre-deploy check)
python -m services.evaluation.benchmark --exam neet --year 2025 --provider ollama --output
```

---

## Directory Structure (Complete)

```
intelligence/
├── config/
│   ├── __init__.py
│   └── settings.py                   ✅ Pydantic Settings singleton
├── packages/
│   ├── prompts/
│   │   ├── formats.py                ✅ JSON output schemas
│   │   ├── system.py                 ✅ System prompts + anti-hallucination
│   │   └── templates.py              ✅ Task-specific prompt templates
│   ├── schemas/
│   │   ├── contracts.py              ✅ API request/response + SLM I/O
│   │   ├── intelligence.py           ✅ Internal intelligence objects
│   │   └── prediction.py             ✅ PRAJNA prediction contracts
│   └── utils/
│       ├── confidence.py             ✅ Priority scoring + confidence
│       └── hierarchy.py              ✅ Aggregation utilities
├── services/
│   ├── api/
│   │   ├── deps.py                   ✅ FastAPI dependency injection
│   │   ├── main.py                   ✅ App entrypoint + middleware
│   │   └── routers/
│   │       ├── copilot.py            ✅ NL copilot endpoint
│   │       ├── insights.py           ✅ SLM insight endpoints
│   │       ├── predictions.py        ✅ Raw prediction endpoints
│   │       └── reports.py            ✅ Revision plan + trend analysis
│   ├── evaluation/
│   │   ├── benchmark.py              ✅ Benchmark runner
│   │   └── metrics.py                ✅ Grounding/factual/ranking metrics
│   ├── insight_engine/
│   │   ├── generator.py              ✅ Insight generation pipeline
│   │   └── slm_provider.py           ✅ Ollama/HF/OpenAI abstraction
│   ├── prediction_adapter/
│   │   └── client.py                 ✅ PRAJNA engine adapter
│   ├── rag/
│   │   ├── indexer.py                ✅ Document indexer
│   │   └── retriever.py              ✅ Metadata-filtered retrieval
│   └── topic_intelligence/
│       ├── aggregator.py             ✅ Batch builder + ranker
│       └── cluster_detector.py       ✅ Topic cluster detection
├── scripts/
│   ├── index_documents.py            ✅ RAG indexing CLI
│   └── seed_data.py                  ✅ Smoke-test seed script
├── infra/
│   ├── docker-compose.yml            ✅ Full stack compose
│   └── Dockerfile.api                ✅ Multi-stage API image
├── docs/
│   ├── BUILD_ORDER.md                ✅ This file
│   └── sample_outputs/
│       ├── 01_subject_revision_strategy.json  ✅
│       ├── 02_chapter_priority_summary.json   ✅
│       ├── 03_micro_topic_importance.json     ✅
│       ├── 04_exam_brief_academic_team.json   ✅
│       └── 05_student_revision_recommendation.json ✅
├── .env.example                      ✅
└── requirements.txt                  ✅
```

---

## Quick Start (5 minutes to running)

```bash
cd exam-predictor/intelligence

# 1. Install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — set SLM_PROVIDER=mock for zero-setup testing

# 3. Smoke test (no external services needed with mock provider)
python3 -m scripts.seed_data --exam neet --year 2025 --output docs/sample_outputs

# 4. Start the API
uvicorn services.api.main:app --host 0.0.0.0 --port 8001 --reload

# 5. Explore the API docs
open http://localhost:8001/docs
```

---

## Production Deployment (Docker)

```bash
cd exam-predictor

# Start full stack
docker compose -f intelligence/infra/docker-compose.yml up -d

# Pull an SLM model into Ollama container
docker exec prajna-ollama ollama pull mistral:7b-instruct

# Index documents
docker exec prajna-intelligence-api \
    python -m scripts.index_documents --source all

# Verify health
curl http://localhost:8001/health
```
