# Darukaa.Earth — Scientific Grounding & Evidence Methodology

## 1. Scientific Knowledge Sources

Darukaa.Earth grounds its environmental reasoning in an audited, peer-reviewed scientific corpus. The current production registry comprises two comprehensive institutional consensus assessments:

1. **Food and Agriculture Organization of the United Nations (FAO)**
   - **Title**: *State of Knowledge of Soil Biodiversity: Status, Challenges and Potentialities* (2020)
   - **DOI**: [10.4060/cb1924en](https://doi.org/10.4060/cb1924en)
   - **Focus**: Relationships between soil organic carbon (SOC) thresholds ($>2.0\%$ vs $<0.5\%$), subterranean fungal-to-bacterial biomass ratios, macrofauna diversity, and continuous monoculture degradation.

2. **Intergovernmental Panel on Climate Change (IPCC)**
   - **Title**: *Special Report on Climate Change and Land (SRCCL): Chapter 4 — Land Degradation* (2019)
   - **DOI**: [10.1017/9781009157988.006](https://doi.org/10.1017/9781009157988.006)
   - **Focus**: Compounding interactions between reduced precipitation, ambient temperature increases, thermal oxidation of soil organic matter, loss of root tensile strength, and multi-tier vegetative buffering.

### Source Exclusion Policy
To preserve scientific integrity, external sources with unverified regional applicability or publication mismatches are strictly excluded. Specifically, the previously tested Torralba agroforestry study is excluded from the active database registry due to geographic mismatch.

---

## 2. Chunking & Semantic Indexing

Scientific documents undergo structured, section-aware chunking:
- **Structural Integrity**: Document headers, sub-sections, and tables are preserved to prevent semantic fragmentation.
- **Controlled Vocabulary Tagging**: Each chunk is annotated with canonical environmental variables (`soil_organic_carbon`, `rainfall`, `soil_moisture`, `land_use`, `species_richness`) and ecological topics (`agriculture`, `climate`, `soil`, `biodiversity`).
- **Embeddings**: Generated using `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors with L2 normalization).
- **Storage**: Stored in PostgreSQL 16 using `pgvector 0.8.6` with cosine distance indexing (`<=>`).

---

## 3. Retrieval & Evidence Scoring Formula

Retrieval does not rely on naive single-string keyword searches. Queries are dynamically synthesized by `MultiDimensionalQueryBuilder` using active compound relationship variables.

Candidate chunks are evaluated through an auditable multi-factor scoring formula in `backend/app/evidence/scoring.py`:

$$\text{Score} = (0.40 \times \text{Semantic Similarity}) + (0.25 \times \text{Metadata Relevance}) + (0.20 \times \text{Relationship Match}) + (0.15 \times \text{Source Quality})$$

- **Relevance Threshold**: Chunks with $\text{Score} < 0.40$ are excluded.
- **Source Verification Gate**: Chunks lacking verified institutional DOIs or URLs are disqualified from supporting recommendations.

---

## 4. Guarded Relationship Activation

Causal relationships are codified declaratively in `backend/app/environmental/relationships.py`. A relationship cannot be triggered by arbitrary generative association. It activates **only** when all required variables are verified in the active environmental state:

```python
# Example: Compound Drought & Soil Degradation Stress
Relationship(
    relationship_id="soc_rainfall_monoculture_stress",
    mechanism="Water deficit impairs aggregate stability, suppressing subterranean microbial activity, compounded by lack of microclimatic buffering in monoculture.",
    variables=["soil_organic_carbon", "rainfall", "land_use"],
    required_variables=["soil_organic_carbon", "rainfall", "land_use"],  # Strictly guarded
)
```

If any required variable is missing, the relationship remains dormant.

---

## 5. Quantitative Claim Safeguards

A critical failure mode of generative AI in environmental science is the fabrication of numerical improvements (e.g., claiming a cover crop will increase species richness by exactly $28.4\%$).

Darukaa enforces a three-tier quantitative safeguard in `backend/app/recommendations/validator.py` and `backend/app/scenarios/analyzer.py`:
1. **Case A (Unsupported Numbers)**: If a recommendation or scenario output contains a numerical percentage or metric multiplier absent from the supporting scientific chunks, the statement is rejected.
2. **Case B (Associative Language Softening)**: Directional outcomes are framed using empirical associative language (e.g., *"Associated with enhanced root-zone moisture retention and subterranean fungal biomass"*) rather than uncalibrated causal certainty.
3. **Case C (Site-Specific Magnitude Safeguard)**: When site-specific empirical models are unavailable, the system explicitly reports:
   > *"Direction supported; site-specific magnitude cannot be estimated from available evidence without local soil testing."*

---

## 6. Unknown-Data Integrity Standards

- **Missing != Zero**: An unprovided variable (such as unmeasured soil organic carbon) is represented as `None` or `status: unknown`. It is **never** coerced to `0`, `0.0`, or a regional statistical average.
- **Qualitative Input Preservation**: Qualitative observations (*"The soil is dry"*) are tagged as `inferred` or `qualitative` and are never converted into synthetic numerical measurements.
- **Memory Boundary**: Previous assistant conversational assertions are never recycled into the knowledge base or treated as empirical evidence.

---

## 7. Confidence Scoring Architecture

Confidence is categorical (`HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`) and explainable. It reflects evidence density and input completeness:

- **HIGH**: $\ge 3$ active environmental variables provided, supported by multiple verified peer-reviewed chunks ($\text{relevance} \ge 0.65$), with verified relationship match.
- **MEDIUM**: Adequate baseline variables provided ($\ge 2$), supported by at least 1 verified chunk ($\text{relevance} \ge 0.50$).
- **LOW**: Sparse input data or weak semantic alignment with available literature.
- **INSUFFICIENT**: Critical decision variables missing or infrastructure retrieval offline.

Confidence never represents a statistical probability of absolute ecological truth; it quantifies empirical literature support.
