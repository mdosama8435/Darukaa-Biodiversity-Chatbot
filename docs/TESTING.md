# Darukaa.Earth — Testing & Verification Guide

## 1. Automated Test Suites

### Backend Unit & Integration Tests (Pytest)
The backend test suite verifies domain schemas, relationship activation rules, multi-metric reasoning, vector embeddings, pgvector retrieval, conversational turn processing, and scenario state immutability.

**Command**:
```bash
docker compose exec backend pytest -v
```

**Verified Results**:
- **Total Tests**: 91
- **Passed**: 91 (100%)
- **Failed**: 0
- **Warnings**: 1 (Deprecated starlette BlockingPortal alias in test client)
- **Execution Time**: ~29.1 seconds

#### Test Module Breakdown:
1. `tests/test_environmental.py`: Environmental state extraction, deterministic text parsing, multi-turn state merge, relationship heuristics, compound interaction discovery.
2. `tests/test_evidence.py`: Multi-dimensional query builder, evidence scoring formula, source authenticity verification, empty evidence failure.
3. `tests/test_health.py`: Live endpoint availability.
4. `tests/test_models.py`: Pydantic validation for soil, climate, land, and location; LangGraph skeleton execution; vector column dimension configurability; unconfigured LLM provider failure.
5. `tests/test_rag.py`: Markdown, txt, PDF loaders; controlled vocabulary tagging; section-aware chunking; embedding generation; vector dimension mismatch failure; search schemas; idempotency; real PostgreSQL/pgvector integration.
6. `tests/test_recommendations.py`: No universal species hardcoding; three-tier generic quantitative claim guard (Case A, B, C, D); associative language softening; explainable confidence factors.
7. `tests/test_scenarios.py`: Scenario schemas; evaluation matrix items; relative arithmetic tier A; absolute transition; categorical transition; baseline immutability; unknown baseline preservation; ambiguous scenario clarification; outcome metric guard; invalid boundary rejection; negative rainfall rejection; multi-metric genuine support check; evidence-driven trade-offs without hardcoding; three-tier claim guard; Torralba exclusion; structured and natural-language scenario APIs; zero fake fallback integration; 9 value loss and multi-metric regressions (`test_a` through `test_i`).

---

### Frontend Production Build
Verifies that the React 19 / Tailwind CSS v4 client compiles cleanly without syntax errors, missing asset references, or unresolved imports.

**Command**:
```bash
npm --prefix frontend run build
```

**Verified Results**:
- **Status**: Exit Code 0 (Success)
- **Modules Transformed**: 1,880 modules
- **Build Time**: ~1.13 seconds
- **Assets**:
  - `dist/index.html`: `0.96 kB`
  - `dist/assets/index-BrENyf6c.css`: `39.99 kB`
  - `dist/assets/index-344n_HvJ.js`: `316.44 kB`

---

## 2. Docker & Infrastructure Acceptance Verification

**Command**:
```bash
docker compose ps
```

**Expected Operational Containers**:
- `darukaa_db` (`pgvector/pgvector:pg16`): Port 5432, status `healthy`.
- `darukaa_backend` (`biodiversity_chatbot-backend`): Port 8000, status `Up`.
- `darukaa_frontend` (`biodiversity_chatbot-frontend`): Port 3000, status `Up`.

**Extension Verification**:
```bash
docker compose exec db psql -U darukaa -d darukaa_earth -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```
- **Result**: `vector | 0.8.6`

---

## 3. End-to-End Acceptance Tests (Live API)

### A. RAG Vector Search Acceptance
Validates that cosine distance semantic search against `knowledge_chunks` returns expected chunks from FAO (2020) and IPCC (2019):
```bash
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "soil organic carbon biodiversity", "top_k": 3}'
```
- **Verified**: Returns Chunk 6 (FAO, sim 0.8194) and Chunk 7 (FAO, sim 0.6896).

### B. Conversational Memory & Override Acceptance
Validates context accumulation and explicit override tracking:
1. Turn 1: *"My farm has declining biodiversity."* $\to$ Status `clarification_needed`. Zero variables invented.
2. Turn 2: *"I grow wheat continuously."* $\to$ `land_use: wheat continuous cropping` stored with Turn 2 provenance.
3. Turn 3: *"Annual rainfall is around 600 mm."* $\to$ `rainfall: 600.0 mm` stored with Turn 3 provenance.
4. Turn 4: *"My soil organic carbon is 0.3%."* $\to$ `soil_organic_carbon: 0.3%` stored, triggering compound interaction synthesis ($\ge 3$ variables).
5. Turn 5: *"Actually, I switched from wheat to maize this year."* $\to$ Overrides `land_use` to `maize`, logging the override event with previous value `wheat continuous cropping`.

### C. What-If Scenario Acceptance
Validates arithmetic and categorical delta resolution against an immutable baseline:
- Baseline: SOC = 0.3%, Rainfall = 600.0 mm, Land Use = wheat monoculture.
- Change: Rainfall -15%, Land Use = intercropping.
- **Verified Output**:
  - Rainfall: $600.0\text{ mm} \to 510.0\text{ mm}$ (`relative_change`).
  - Land Use: `wheat monoculture` $\to$ `intercropping` (`categorical_change`).
  - Baseline SOC remains 0.3%.
  - Assumptions explicitly stated.
  - Evaluation matrix populated with directional indicators and limitations.

### D. Error Handling Acceptance
- **Database Offline**: `KnowledgeRetriever` raises an explicit exception; `POST /api/v1/assessment` emits HTTP 503; `POST /api/v1/scenarios/analyze` raises a `RuntimeError`. No fake evidence or fallback recommendations are returned.
- **Invalid Metrics**: Out-of-range metrics (e.g. soil pH $>14$) trigger HTTP 422 / 500 validation rejections.
- **Unsupported Scenarios**: Reductions $>100\%$ trigger HTTP 422 rejection.

---

## 4. Manual / Browser Evaluator Acceptance

Evaluators can verify the full interactive experience at [http://localhost:3000](http://localhost:3000):
1. **Header Verification**: Check dynamic green indicator (`Backend Connected`, `pgvector 0.8.6`).
2. **Sidebar Benchmark Demo**: Click `#1 Bio Decline` $\to$ `#2 Continuous Wheat` $\to$ `#3 600 mm Rain` $\to$ `#4 SOC 0.3%` $\to$ `#5 Override: Maize`.
3. **Context Panel**: Inspect real-time parameter table with provenance badges (`Source: User statement • Turn X`).
4. **Scenario Workspace**: Switch to `Scenario Analysis` tab, select preset `Benchmark: Rain -15% & Intercropping`, and verify the before/after transition cards and evaluation matrix.
5. **Browser Console**: Confirm zero critical errors or unhandled promise rejections.
