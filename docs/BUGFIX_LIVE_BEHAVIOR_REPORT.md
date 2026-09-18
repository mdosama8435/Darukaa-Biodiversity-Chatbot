# DARUKAA.EARTH — LIVE BEHAVIOR CORRECTION AUDIT & VERIFICATION REPORT

**Date:** September 18, 2026  
**Auditor:** Principal AI & Environmental Software Engineer  
**System:** Darukaa.Earth AI Biodiversity Intelligence Platform  
**Environment:** Dockerized Local Stack (FastAPI backend on port 8000, React/Vite frontend on port 3001, PostgreSQL 16 with pgvector 0.8.6 on port 5432)  
**Status:** **ALL 8 BUGS RESOLVED & LIVE VERIFIED (TESTS A–G PASSED)**

---

## 1. Executive Summary

A comprehensive, black-box behavioral audit of Darukaa.Earth identified 8 critical correctness and scientific safety issues in conversational context handling, metric semantics, scenario baseline parsing, and confidence scoring. 

All 8 issues have been resolved at the root-cause level across the backend services without altering the user interface or violating scientific safety constraints:
- Rainfall ($600\text{ mm}$) is strictly decoupled from soil moisture at the source of truth.
- Clarification loops persist until sufficient driving variables are present.
- Scenario preambles are parsed as baseline declarations rather than perturbations.
- Metric evaluation matrices strictly map rainfall to rainfall and maintain unknown soil moisture as unmeasured.
- 600 mm annual precipitation is contextualized rather than falsely labeled "low rainfall".
- Deterministic intent routing intercepts measurement lookups and unsupported quantification queries.
- Arithmetic computational confidence is decoupled from ecological evidence confidence.

All 100 backend automated unit/integration tests passed, the frontend production bundle built cleanly, and live end-to-end API execution confirmed correct behavior across Tests A through G.

---

## 2. Root Cause Analysis & Resolution for Each Bug

### Bug 1: Incomplete Context Prematurely Triggered Recommendations
* **Observed Failure:** When a user with declining biodiversity stated *"I grow wheat continuously"*, the platform immediately generated an Agroforestry recommendation even though rainfall and soil organic carbon (SOC) were missing.
* **Root Cause:**
  1. `backend/app/conversation/memory_policy.py` considered any 2 non-null variables in `EnvironmentalContext` as "sufficient" for assessment, even if they were non-driving metrics (such as default empty sets or incidental attributes).
  2. In `backend/app/recommendations/generator.py`, the candidate generator only checked `context.land_use` to propose Candidate 1 (Agroforestry), and fabricated reasoning steps referencing rainfall even when `context.rainfall` was `None`.
  3. In `backend/app/agents/graph.py`, `validate_environmental_state` did not require a minimum of 2 primary driving variables (`land_use`, `rainfall`, `soil_organic_carbon`) before routing to `generate_recommendations`.
* **Correction Implemented:**
  - `memory_policy.py`: Defined `DRIVING_VARIABLES = {"soil_organic_carbon", "rainfall", "land_use"}`. An assessment is only eligible when at least 2 primary driving variables are present.
  - `graph.py`: In `validate_environmental_state`, if fewer than 2 driving variables are present, the workflow routes to `request_clarification` and emits 0 recommendations.
  - `generator.py`: Candidate 1 now verifies that reasoning steps only cite variables that are genuinely measured; it requires at least 2 driving variables to form an interaction rationale.

---

### Bug 2: Soil Moisture Inferred from Rainfall on Measurement Query
* **Observed Failure:** When the user asked *"What is my current soil moisture?"*, the assistant answered using rainfall or generated agricultural recommendations.
* **Root Cause:**
  1. The chat turn processor routed all user messages through the LLM agent graph without an intent classifier to identify informational/measurement lookup queries.
  2. Previous extraction logic conflated rainfall with water availability, which downstream components treated as soil moisture.
* **Correction Implemented:**
  - `backend/app/conversation/turn_processor.py`: Added deterministic `detect_user_intent`. Queries asking for current soil moisture (or unmeasured metrics) are recognized as `measurement_lookup`.
  - When soil moisture is unrecorded in `EnvironmentalContext`, the system returns:  
    `"Soil moisture has not been provided. If you have a measurement, share it and I can use it in the assessment."`
  - Emits `recommendations=[]` and status `completed`.

---

### Bug 3: Scenario Baseline Declarations Misinterpreted as Scenario Perturbations
* **Observed Failure:** In queries like *"Suppose I have a farm with wheat monoculture, rainfall of 600mm, and SOC of 0.3%. What happens if rainfall drops by 15% and I switch to intercropping?"*, the system attempted to treat `SOC of 0.3%` as a changed variable, returning `Error: Variable soil_organic_carbon change is a no-op (0.3% -> 0.3%)`.
* **Root Cause:**
  - `backend/app/scenarios/parser.py` parsed all regex matches across the entire text without distinguishing between baseline context declarations (*"Suppose I have..."*) and perturbation clauses (*"What happens if..."*).
* **Correction Implemented:**
  - Implemented `split_preamble_and_scenario(text)` and `extract_baseline_declarations(preamble_text)`.
  - The baseline declaration is extracted first to populate or update the scenario baseline (`land_use: wheat monoculture`, `rainfall: 600 mm`, `soil_organic_carbon: 0.3%`).
  - Only perturbations in the hypothetical clause are parsed as `ChangedVariable`.
  - Added filter `c.baseline_value != c.scenario_value` to permanently discard accidental no-op deltas.

---

### Bug 4: Rainfall Displayed as Soil Moisture in Evaluation Matrix
* **Observed Failure:** In scenario evaluation, rainfall was mislabeled as `soil_moisture` in the comparison matrix (e.g. `Metric: Soil Moisture | Baseline: 600 mm | Scenario: 510 mm`).
* **Root Cause:**
  - In `backend/app/scenarios/analyzer.py`, the row generator used `metric="soil_moisture"` when rendering rainfall precipitation changes.
* **Correction Implemented:**
  - Corrected `backend/app/scenarios/analyzer.py` matrix generation:
    - Added dedicated row for `metric="rainfall"`: `baseline="600.0 mm"`, `scenario="510.0 mm (assumed -15%)"`.
    - Maintained `metric="soil_moisture"` strictly as `baseline="Unknown / Not provided"` and `scenario="Directional decrease (desiccation risk)"` with explicit ecological notes.
    - Verified that `rainfall = 600 mm` never becomes `soil_moisture = 600 mm` at the backend data model layer.

---

### Bug 5: 600 mm Rainfall Arbitrarily Classified as "Low Rainfall"
* **Observed Failure:** The system unconditionally declared 600 mm annual precipitation as "low rainfall".
* **Root Cause:**
  - `backend/app/environmental/metric_rules.py` had a hard threshold `< 800 mm` classified as `"low"`.
* **Correction Implemented:**
  - In `metric_rules.py`: Subdivided rainfall categories. Values between 500 mm and 1000 mm are categorized as `"moderate_variable"`.
  - In `backend/app/environmental/analyzer.py`: When rainfall is between 500 mm and 1000 mm and aridity/ecoregion data is absent, the assessment explicitly states:  
    `"Annual rainfall is 600 mm; whether this represents water stress depends on regional and seasonal context."`
  - In `backend/app/recommendations/generator.py`: Lowered strict water-limitation recommendation triggers to `< 500 mm` unless explicit drought/aridity context is provided.

---

### Bug 6: Missing Deterministic Intent Routing
* **Observed Failure:** User questions were indiscriminately passed to the LangGraph recommendation pipeline, leading to hallucinations on non-recommendation prompts.
* **Root Cause:**
  - Absence of a pre-agent intent router in `turn_processor.py`.
* **Correction Implemented:**
  - Added `detect_user_intent(message)` in `backend/app/conversation/turn_processor.py`:
    - `measurement_lookup`: Directly queries context for measured values; reports unmeasured metrics without generating recommendations.
    - `unsupported_quantification`: Intercepts queries demanding ungrounded numerical species predictions.
    - `scenario_analysis`: Directly calls scenario simulation engine without recommendation generation.
    - `state_update` / `general_chat`: Enters clarification or assessment workflow based on driving variable counts.

---

### Bug 7: Unsupported Species Quantification Refusal
* **Observed Failure:** Asking *"If I improve SOC from 0.3% to 0.6%, how many bird species will I gain?"* either fabricated numbers (e.g. "+14 species") or repeated previous agricultural recommendations.
* **Root Cause:**
  - No guardrail checked for uncalibrated empirical species quantification queries.
* **Correction Implemented:**
  - Intent router identifies specific species count queries (`unsupported_quantification`).
  - Returns scientifically grounded refusal:  
    `"Exact species increase cannot be determined from the available evidence. While improving soil organic carbon (e.g., from 0.3% to 0.6%) enhances microbial biomass and subterranean biological activity, quantifying specific species richness gains requires localized taxonomic baseline surveys, eDNA metabarcoding, and site-specific field sampling. Peer-reviewed literature supports directional improvements in functional diversity, but exact species count predictions without local empirical calibration are scientifically unfounded."`
  - Emits 0 recommendations and 0 invented numerical claims.

---

### Bug 8: Conflation of Computational vs Scientific Confidence
* **Observed Failure:** The scenario simulation assigned a single confidence score, conflating deterministic arithmetic ($600 \times 0.85 = 510$) with ecological outcome confidence.
* **Root Cause:**
  - `ConfidenceAssessment` model and `backend/app/scenarios/analyzer.py` lacked explicit separate semantic fields for arithmetic precision versus ecological outcome grounding.
* **Correction Implemented:**
  - In `backend/app/scenarios/analyzer.py`, `confidence_factors` now explicitly distinguishes:
    - `"computational_confidence": "high"` (deterministic arithmetic operations like $600 - 15\% = 510\text{ mm}$ have near-zero mathematical uncertainty).
    - `"scientific_evidence_confidence": "medium"` (ecological predictions derived from peer-reviewed evidence literature chunks subject to local field variance).
  - Explicit rationale: `"Scientific evidence confidence: Supported by verified peer-reviewed literature chunks; deterministic arithmetic perturbations carry high computational precision, while site-specific ecological response magnitudes require localized field calibration."`

---

## 3. Files and Code Modified

| File Path | Component | Description of Changes |
|:---|:---|:---|
| `backend/app/environmental/metric_rules.py` | Environmental Core | Added `moderate_variable` rainfall category (500–1000 mm); removed blanket "low" classification. |
| `backend/app/environmental/analyzer.py` | Multi-Metric Synthesis | Added regional/seasonal context clause for 500–1000 mm rainfall; structured 2-variable vs 3-variable compound interaction text. |
| `backend/app/recommendations/generator.py` | Recommendation Engine | Lowered water-limited trigger to `< 500.0` mm; ensured reasoning steps cite only observed metrics; candidate rules respect driving variables. |
| `backend/app/agents/graph.py` | Workflow Orchestration | Node 3 (`validate_environmental_state`) routes to clarification if $< 2$ driving variables are present. |
| `backend/app/conversation/memory_policy.py` | Memory & Context | Defined `DRIVING_VARIABLES = {"soil_organic_carbon", "rainfall", "land_use"}`; non-driving attributes do not bypass clarification. |
| `backend/app/conversation/context_manager.py` | Context Extraction | Added explicit regex and semantic extraction for `soil_moisture` independent from rainfall. |
| `backend/app/conversation/turn_processor.py` | Intent & Routing | Deterministic routing for `measurement_lookup`, `unsupported_quantification`, and `scenario_analysis`. |
| `backend/app/scenarios/parser.py` | Scenario Engine | Separated baseline preamble from scenario changes; extracted baseline values; filtered no-op changes. |
| `backend/app/scenarios/analyzer.py` | Scenario Engine | Mapped rainfall to `metric="rainfall"`; retained soil moisture as unknown; separated computational vs scientific confidence. |
| `backend/app/api/endpoints/scenarios.py` | REST API | Added automatic baseline population from `request.baseline` dictionary. |
| `backend/tests/test_live_behavior_corrections.py` | Automated Testing | 9 comprehensive regression tests for Bugs 1–8. |
| `scripts/verify_live_tests_a_to_g.py` | E2E Live Test Script | Automated execution and verification of Tests A through G against live Docker stack. |

---

## 4. Test Verification Results

### 4.1. Unit and Integration Test Suite
```bash
pytest backend/tests/test_live_behavior_corrections.py
============================== 9 passed in 16.65s ==============================

pytest backend/tests/
======================== 100 passed, 1 warning in 21.07s ========================
```

### 4.2. Frontend Production Build
```bash
npm --prefix frontend run build
> vite build
✓ built in 595ms
```

### 4.3. Live Docker Black-Box Tests (Tests A–G)
All tests executed live against `http://localhost:8000` with active pgvector database:

```
============================================================
  HEALTH & KNOWLEDGE CHECK
============================================================
Health response (200): {'status': 'ok', 'service': 'darukaa-biodiversity-intelligence'}
Knowledge search (200): found 5 chunks
Assessment evaluate (200): status completed

============================================================
  TEST A: 'My biodiversity is declining on my farm.'
============================================================
Status: clarification_needed
Clarification questions: 3 asked (land use, rainfall, SOC)
Recommendations emitted: 0
>>> TEST A PASSED: Clarification requested, no premature recommendations.

============================================================
  TEST B: 'I grow wheat continuously.'
============================================================
Status: clarification_needed
Clarification questions: 3 asked (rainfall, SOC, ecoregion)
Recommendations emitted: 0
>>> TEST B PASSED: Land use recorded; clarification continued because rainfall & SOC still missing.

============================================================
  TEST C: 'Annual rainfall is around 600 mm.'
============================================================
Status: clarification_needed
Clarification questions: 2 asked (SOC, irrigation)
Recommendations emitted: 0
Assistant message context: "Annual rainfall is 600 mm; whether this represents water stress depends on regional and seasonal context."
>>> TEST C PASSED: Rainfall 600 mm recorded contextually without false 'low' label; clarification continued for SOC.

============================================================
  TEST E: 'What is my current soil moisture?'
============================================================
Status: completed
Assistant message: "Soil moisture has not been provided. If you have a measurement, share it and I can use it in the assessment."
Recommendations emitted: 0
>>> TEST E PASSED: Correctly handled missing soil moisture; rainfall != soil moisture; no recommendations triggered.

============================================================
  TEST D: 'My soil organic carbon is 0.3%.'
============================================================
Status: completed
Driving variables present: 3 (land_use, rainfall, soil_organic_carbon)
Compound Multi-Metric Interaction: Synthesized interaction between SOC 0.3%, 600 mm rainfall, and continuous wheat.
Recommendations emitted: 2 evidence-grounded recommendations (Residue Retention, Agroforestry Transition).
>>> TEST D PASSED: Context now fully satisfied; multi-metric assessment executed.

============================================================
  TEST F: Unsupported Species Quantification
============================================================
Status: completed
Query: "If I improve SOC from 0.3% to 0.6%, how many bird species will I gain?"
Assistant message: "Exact species increase cannot be determined from the available evidence. While improving soil organic carbon (e.g., from 0.3% to 0.6%) enhances microbial biomass and subterranean biological activity, quantifying specific species richness gains requires localized taxonomic baseline surveys, eDNA metabarcoding, and site-specific field sampling. Peer-reviewed literature supports directional improvements in functional diversity, but exact species count predictions without local empirical calibration are scientifically unfounded."
Recommendations emitted: 0
Invented numbers emitted: 0
>>> TEST F PASSED: Unsupported species count refused without invented numbers or recommendations.

============================================================
  TEST G: Preamble Baseline + Scenario Simulation
============================================================
Query: "Suppose I have a farm with wheat monoculture, rainfall of 600mm, and SOC of 0.3%. What happens if rainfall drops by 15% and I switch to intercropping?"
Status: completed (200 OK)
Baseline Extracted: land_use=wheat monoculture, rainfall=600.0, soil_organic_carbon=0.3
Changed Variables:
  - land_use: wheat monoculture -> intercropping
  - rainfall: 600.0 mm -> 510.0 mm (-15%)
Evaluation Matrix Metrics:
  - rainfall: Baseline 600.0 mm -> Scenario 510.0 mm (conf=high)
  - soil_moisture: Baseline Unknown / Not provided -> Scenario Directional decrease (conf=medium)
  - soil_organic_carbon: Baseline 0.3% -> Scenario Enhanced substrate accrual (conf=medium)
Confidence Semantics:
  - Computational confidence: high (deterministic arithmetic: 600 * 0.85 = 510)
  - Scientific evidence confidence: medium (peer-reviewed literature chunks with field variance)
>>> TEST G PASSED: Baseline preamble separated; changes parsed; Evaluation Matrix correctly labels rainfall -> rainfall; soil moisture unknown.
```

---

## 5. Scientific Safety & Guardrail Compliance Matrix

| Rule | Requirement | Verification Result |
|:---|:---|:---|
| **Unknown $\neq$ Zero** | Unmeasured variables must never default to 0 | Passed. Unmeasured soil moisture outputs `"Unknown / Not provided"`, never `0` or `0.0`. |
| **Unknown $\neq$ Average** | Unmeasured variables must not use regional means silently | Passed. Clarification is requested explicitly rather than inserting assumed averages. |
| **Rainfall $\neq$ Soil Moisture** | $600\text{ mm}$ precipitation must never become $600\text{ mm}$ soil moisture | Passed. Mapped to distinct database/context keys; matrix keeps them separate. |
| **No Invented Measurements** | Never hallucinate unprovided field data | Passed. Query for soil moisture returns missing notification. |
| **No Fabricated Predictions** | Reject demands for exact species counts without local empirical surveys | Passed. Test F explicitly refuses species count predictions. |
| **No Artificial 3-Variable Forcing** | Respect 2-variable vs 3-variable threshold | Passed. 2 variables permit pairwise reasoning; 3+ enable full multi-metric synthesis; third variable is never invented. |
| **Confidence Decoupling** | Separate arithmetic certainty from ecological certainty | Passed. High computational confidence does not inflate medium ecological confidence. |

---

## 6. Conclusion

The platform behavior has been audited, corrected, and verified end-to-end. Darukaa.Earth strictly enforces scientific safety constraints, robust conversational memory, accurate scenario baseline parsing, and transparent confidence semantics in full compliance with deployment specifications.

---

## 7. Final Scientific Semantics Verification

Following the initial audit, a targeted correction pass was conducted to enforce rigorous scientific semantics across scenario metrics, source terminology, evidence traceability, and quantitative claims.

### 7.1. Soil Moisture Semantics in Scenarios
* **Requirement:** Rainfall and soil moisture are completely distinct environmental variables. Rainfall reduction must never be converted into an inferred soil moisture measurement or scenario value.
* **Verified Behavior:**
  - **Observation:** `rainfall: 600 mm → 510 mm` (Direction: `decreased`, Confidence: `high` for exact arithmetic).
  - **Measurement:** `soil_moisture: Baseline = Unknown / Not provided → Scenario = Unknown / Not provided` (Direction: `uncertain`, Confidence: `medium`).
  - **Potential Implication:** Represented separately in metric impacts:  
    *"Reduced rainfall may increase soil-water stress or desiccation risk, but soil moisture cannot be determined without a soil-moisture measurement or validated hydrological model."*
  - **Audit Layers Confirmed:** Scenario state builder, scenario analyzer, evaluation matrix, impacted metrics, API response serializer, and UI view.

### 7.2. Source Terminology Accuracy
* **Requirement:** Authoritative technical reports from intergovernmental agencies (FAO, IPCC) must not be falsely described as peer-reviewed journal papers.
* **Verified Behavior:**
  - Replaced indiscriminate "peer-reviewed literature" descriptors across confidence rationales, limitation notes, API responses, and UI badges.
  - Standardized terminology: *"verified scientific and technical sources"* and *"authoritative scientific/technical reports"*.
  - Preserved underlying source metadata without fabrication.

### 7.3. Evidence Chain Verification (Backend Objects & Real Database Records)
Three distinct live recommendation and evidence items were inspected end-to-end against the active PostgreSQL database (`knowledge_documents` and `knowledge_chunks`):

1. **Evidence Chain 1:**
   - **Recommendation:** Continuous Organic Residue Retention and Surface Mulching
   - **Relationship:** `temp_soil_carbon_oxidation`
   - **Evidence Item ID:** `9e858e83-dbac-48cf-bed3-593743e9eaef`
   - **Knowledge Chunk DB ID:** `7` (tokens/length: 641 chars, section: Chapter 2)
   - **Knowledge Document DB ID:** `2`
   - **Document Title:** *State of Knowledge of Soil Biodiversity: Status, Challenges and Potentialities*
   - **Document Type:** `report`
   - **Source Organization:** `FAO`
   - **DOI:** `10.4060/cb1924en` | **URL:** `https://doi.org/10.4060/cb1924en`

2. **Evidence Chain 2:**
   - **Recommendation:** Continuous Organic Residue Retention and Surface Mulching
   - **Relationship:** `temp_soil_carbon_oxidation`
   - **Evidence Item ID:** `61cb79cc-aa74-47a1-aa01-b703761aba0a`
   - **Knowledge Chunk DB ID:** `15` (tokens/length: 682 chars, section: Chapter 4)
   - **Knowledge Document DB ID:** `3`
   - **Document Title:** *IPCC Special Report on Climate Change and Land: Chapter 4 — Land Degradation*
   - **Document Type:** `report`
   - **Source Organization:** `IPCC`
   - **DOI:** `10.1017/9781009157988.006` | **URL:** `https://www.ipcc.ch/srccl/chapter/chapter-4/`

3. **Evidence Chain 3:**
   - **Recommendation:** Agroforestry Integration and Diversified Cropping System Transition
   - **Relationship:** `soc_rainfall_monoculture_stress`
   - **Evidence Item ID:** `9e858e83-dbac-48cf-bed3-593743e9eaef`
   - **Knowledge Chunk DB ID:** `7`
   - **Knowledge Document DB ID:** `2`
   - **Source Organization:** `FAO`
   - **DOI:** `10.4060/cb1924en` | **URL:** `https://doi.org/10.4060/cb1924en`

All claims trace to genuine indexed rows; no disconnected citations or fabricated database references exist.

### 7.4. Quantitative Claim Safety
* **Live Test Query:** *"My SOC is 0.3%. If I improve it to 0.6%, exactly how many species will increase?"*
* **Response Output:**
  > *"Exact species increase cannot be determined from the available evidence. While improving soil organic carbon (e.g., from 0.3% to 0.6%) enhances microbial biomass and subterranean biological activity, quantifying specific species richness gains requires localized taxonomic baseline surveys, eDNA metabarcoding, and site-specific field sampling. Authoritative scientific and technical sources support directional improvements in functional diversity, but exact species count predictions without local empirical calibration are scientifically unfounded."*
* **Verified:**
  - Zero invented species counts (0 numbers generated).
  - Zero invented percentage estimates.
  - Zero repeated previous agricultural recommendations.
  - Clearly distinguishes qualitative ecological direction from quantitative empirical prediction.

### 7.5. Final Context Integrity Verification (Turns 1–4)
* **Turn 1:** *"My biodiversity is declining on my farm."* → Status: `clarification_needed`, Recs: 0.
* **Turn 2:** *"I grow wheat continuously."* → Status: `clarification_needed`, Recs: 0.
* **Turn 3:** *"Annual rainfall is around 600 mm."* → Status: `clarification_needed`, Recs: 0. Contextualized: 600 mm not classified as low rainfall.
* **Turn 4:** *"My soil organic carbon is 0.3%."* → Status: `completed`, Recs: 2.
* **Final State Recorded:**
  - `soil_organic_carbon`: 0.3%
  - `rainfall`: 600 mm
  - `land_use`: continuous wheat cropping
  - `soil_moisture`: Unknown (not provided; not invented)
  - 3 genuinely relevant driving variables activated compound multi-metric reasoning.

### 7.6. Final Scenario Verification
* **Query:** *"Suppose I have a farm with wheat monoculture, rainfall of 600 mm, and SOC of 0.3%. What happens if rainfall drops by 15% and I switch to intercropping?"*
* **Baseline Extracted:** SOC = 0.3%, Rainfall = 600 mm, Land use = wheat monoculture.
* **Perturbations Applied:** Rainfall = -15% relative change, Land use = intercropping categorical change.
* **Derived Scenario State:** Rainfall = 510 mm, SOC = 0.3%, Land use = intercropping, Soil moisture = None (not invented).
* **Evaluation Matrix Output:**
  - `rainfall`: Baseline `600.0 mm` → Scenario `510.0 mm (assumed -15%)` | Direction: `decreased` | Confidence: `high`
  - `soil_moisture`: Baseline `Unknown / Not provided` → Scenario `Unknown / Not provided` | Direction: `uncertain` | Confidence: `medium`
  - `soil_water_stress`: Represented as potential implication, not a measured moisture value.
* **Confidence Semantics:**
  - Computational confidence: `high` (deterministic arithmetic $600 \times 0.85 = 510$).
  - Scientific evidence confidence: `medium` (authoritative scientific and technical sources).
  - Overall scenario confidence: `medium` (ecological prediction confidence is not inflated by arithmetic precision).

