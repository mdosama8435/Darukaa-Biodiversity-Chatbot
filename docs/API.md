# Darukaa.Earth — API Reference

Interactive OpenAPI documentation is hosted directly on the running backend at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) (or [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs))
- **OpenAPI JSON**: [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)

---

## 1. System Health

### `GET /health` or `GET /api/v1/health`
Verifies backend service availability.

**Response (HTTP 200)**:
```json
{
  "status": "ok",
  "service": "darukaa-biodiversity-intelligence"
}
```

---

## 2. Conversational Environmental Intelligence

### `POST /api/v1/chat`
Maintains conversational environmental context across multiple dialogue turns, extracts variables, detects overrides, triggers clarifications, and produces evidence-grounded recommendations.

**Request Schema**:
```json
{
  "conversation_id": "session_123456",
  "message": "My soil organic carbon is 0.3%."
}
```

**Response Schema (Sample)**:
```json
{
  "conversation_id": "session_123456",
  "turn_id": 4,
  "role": "assistant",
  "message": "Based on your reported soil organic carbon (0.3%), annual rainfall (600 mm), and continuous wheat cropping...",
  "status": "completed",
  "clarification_questions": [],
  "environmental_context": {
    "land_use": {
      "value": "wheat continuous cropping",
      "source": "user_statement",
      "turn_id": 2,
      "status": "provided"
    },
    "rainfall": {
      "value": 600.0,
      "unit": "mm",
      "source": "user_statement",
      "turn_id": 3,
      "status": "provided"
    },
    "soil_organic_carbon": {
      "value": 0.3,
      "unit": "%",
      "source": "user_statement",
      "turn_id": 4,
      "status": "provided"
    }
  },
  "detected_updates": [],
  "confidence": "medium"
}
```

---

## 3. What-If Scenario Analysis

### `POST /api/v1/scenarios/analyze`
Evaluates hypothetical management or climatic changes relative to a baseline state.

**Request Schema**:
```json
{
  "conversation_id": "session_123456",
  "query": "What if rainfall decreases by 15% and we transition from wheat monoculture to intercropping?",
  "baseline": {
    "soil_organic_carbon": 0.3,
    "rainfall": 600.0,
    "land_use": "wheat monoculture"
  },
  "changes": [
    {
      "variable": "rainfall",
      "value": -15,
      "unit": "percent",
      "status": "assumed_scenario"
    },
    {
      "variable": "land_use",
      "value": "intercropping",
      "status": "assumed_scenario"
    }
  ]
}
```

**Response Schema (Sample)**:
```json
{
  "status": "completed",
  "comparison": {
    "baseline_summary": {
      "soil_organic_carbon": 0.3,
      "rainfall": 600.0,
      "land_use": "wheat monoculture"
    },
    "scenario_summary": {
      "soil_organic_carbon": 0.3,
      "rainfall": 510.0,
      "land_use": "intercropping"
    },
    "changed_variables": [
      {
        "variable": "rainfall",
        "change_type": "relative_change",
        "baseline_value": 600.0,
        "scenario_value": 510.0
      },
      {
        "variable": "land_use",
        "change_type": "categorical_change",
        "baseline_value": "wheat monoculture",
        "scenario_value": "intercropping"
      }
    ],
    "evaluation_matrix": [
      {
        "metric": "soil_organic_carbon",
        "baseline": "0.3%",
        "scenario": "Enhanced substrate accrual",
        "direction": "increased",
        "confidence": "medium",
        "limitations": "Long-term organic carbon retention is constrained by soil texture and temperature oxidation rates."
      },
      {
        "metric": "soil_moisture",
        "baseline": "600.0 mm",
        "scenario": "510.0 mm (assumed -15%)",
        "direction": "decreased",
        "confidence": "high",
        "limitations": "Soil aggregate stability and vegetative mulch strongly influence hydraulic retention."
      }
    ],
    "synergies": [
      {
        "rationale": "Crop diversification simultaneously supplies above-ground habitat heterogeneity and below-ground labile organic carbon inputs..."
      }
    ],
    "tradeoffs": [],
    "multi_metric_grounding": true,
    "multi_metric_coverage": "compound (3 variables: soil_organic_carbon, rainfall, land_use)",
    "confidence": "high"
  }
}
```

---

## 4. Structured Environmental Assessment

### `POST /api/v1/assessment`
Direct parameter-level assessment executing the 12-node LangGraph pipeline.

**Request Schema**:
```json
{
  "soil_ph": 6.5,
  "soil_organic_carbon": 0.3,
  "soil_moisture": 18.0,
  "temperature": 26.5,
  "rainfall": 600.0,
  "land_use": "wheat monoculture",
  "land_cover": "cropland",
  "species_richness": 10,
  "habitat_diversity": "low",
  "region": "semi-arid"
}
```

**Response Schema (Sample)**:
```json
{
  "status": "completed",
  "assessment": {
    "environmental_state": {
      "soil_ph": 6.5,
      "soil_organic_carbon": 0.3,
      "rainfall": 600.0,
      "land_use": "wheat monoculture"
    },
    "key_relationships": [
      { "relationship_id": "soc_rainfall_monoculture_stress" }
    ],
    "compound_synthesis": "COMPOUND MULTI-METRIC INTERACTION: Observed depleted soil carbon (0.3) conjoined with low precipitation (600.0)...",
    "data_completeness": 0.833
  },
  "recommendations": [
    {
      "action": "Agroforestry Integration and Diversified Cropping System Transition",
      "why": [
        "Continuous monoculture depletes soil organic carbon stocks and destroys vertical ecological niches.",
        "Perennial woody root systems enhance hydraulic conductivity, facilitating water infiltration into subsoil horizons."
      ],
      "impacted_metrics": ["soil_organic_carbon", "species_richness", "habitat_diversity", "soil_moisture"],
      "time_horizon": {
        "short_term": "0-1 years: Establishment of drought-adapted tree lines...",
        "medium_term": "1-3 years: Fine-root biomass accumulation...",
        "long_term": "3-7+ years: Stabilized macro-aggregate soil carbon..."
      },
      "confidence": "medium",
      "limitations": [
        "Species selection requires local agronomic and ecological validation."
      ]
    }
  ],
  "confidence": "medium"
}
```

---

## 5. Scientific Knowledge Vector Search

### `POST /api/v1/knowledge/search`
Direct vector similarity search against PostgreSQL 16 + pgvector knowledge chunks.

**Request Schema**:
```json
{
  "query": "soil organic carbon biodiversity",
  "top_k": 3,
  "min_similarity": 0.25
}
```

**Response Schema (Sample)**:
```json
{
  "query": "soil organic carbon biodiversity",
  "results_count": 3,
  "results": [
    {
      "chunk_id": 6,
      "document_id": 2,
      "title": "State of Knowledge of Soil Biodiversity: Status, Challenges and Potentialities (Report Excerpt)",
      "source": "FAO",
      "similarity": 0.8194,
      "doi": "10.4060/cb1924en",
      "url": "https://doi.org/10.4060/cb1924en",
      "variables": ["soil_organic_carbon"],
      "topics": ["biodiversity", "ecosystem", "soil"],
      "content": "Soil biodiversity encompasses the variety of living organisms in the soil, ranging from microscopic bacteria and fungi..."
    }
  ]
}
```
