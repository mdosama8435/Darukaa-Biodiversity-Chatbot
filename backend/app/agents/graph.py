"""LangGraph workflow definition for environmental intelligence processing.

Reordered 12-node pipeline (Correction 6):
START
  ↓
parse_input
  ↓
extract_environmental_state
  ↓
validate_environmental_state
  ↓ (conditional: if needs_clarification -> format_response -> END)
analyze_metric_relationships
  ↓
build_retrieval_queries
  ↓
retrieve_knowledge (pgvector - no silent fallback)
  ↓
map_evidence
  ↓
generate_candidates
  ↓
validate_recommendations
  ↓
calculate_confidence
  ↓
format_response
  ↓
END
"""

import logging
import re
from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph, START, END

from app.agents.state import EnvironmentalState
from app.models.environmental import EnvironmentalData
from app.environmental.analyzer import EnvironmentalRelationshipAnalyzer
from app.rag.query_builder import MultiDimensionalQueryBuilder
from app.rag.schemas import KnowledgeSearchRequest
from app.rag.retriever import KnowledgeRetriever
from app.evidence.mapper import EvidenceMapper
from app.evidence.validator import EvidenceValidator
from app.recommendations.generator import RecommendationGenerator
from app.recommendations.validator import RecommendationEvidenceValidator
from app.recommendations.ranking import rank_and_score_recommendations, calculate_explainable_confidence
from app.database.connection import SessionLocal

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Node 1: parse_input
# -----------------------------------------------------------------------------
def parse_input(state: EnvironmentalState) -> Dict[str, Any]:
    """Parses incoming query and initializes dialogue context."""
    query = state.get("user_query") or ""
    history = state.get("conversation_history") or []
    return {
        "user_query": query.strip(),
        "conversation_history": history,
        "status": "ready",
    }


# -----------------------------------------------------------------------------
# Node 2: extract_environmental_state (with Multi-Turn State Merging)
# -----------------------------------------------------------------------------
def _extract_from_text(text: str) -> Dict[str, Any]:
    """Deterministic regex extractor for environmental variables from natural language."""
    extracted: Dict[str, Any] = {}
    lower = text.lower()

    # Soil Organic Carbon
    soc_num = re.search(r"(?:soc|soil organic carbon)\s*(?:is|=|level is|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*%", lower)
    if soc_num:
        extracted["soil_organic_carbon"] = float(soc_num.group(1))
    elif "low soil organic carbon" in lower or "low soc" in lower or "depleted soc" in lower:
        extracted["soil_organic_carbon"] = 0.3  # heuristic indicator

    # Soil pH
    ph_match = re.search(r"\bph\s*(?:is|=|level is)?\s*([0-9]+(?:\.[0-9]+)?)\b", lower)
    if ph_match:
        extracted["soil_ph"] = float(ph_match.group(1))

    # Rainfall
    rain_mm = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:mm|millimeters)", lower)
    if rain_mm:
        extracted["rainfall"] = float(rain_mm.group(1))
    elif any(p in lower for p in ["low rainfall", "rainfall is low", "rainfall low", "precipitation deficit", "drought"]):
        extracted["rainfall"] = 400.0  # heuristic indicator for dryland

    # Land use
    if "wheat monoculture" in lower:
        extracted["land_use"] = "wheat monoculture"
        extracted["land_cover"] = "cropland"
    elif "monoculture" in lower:
        extracted["land_use"] = "monoculture"
    elif "wheat" in lower and ("continuous" in lower or "grow" in lower):
        extracted["land_use"] = "continuous wheat cropping"
        extracted["land_cover"] = "cropland"
    elif "agroforestry" in lower:
        extracted["land_use"] = "agroforestry"

    # Region
    if "semi-arid" in lower or "semi arid" in lower:
        if "bihar" in lower:
            extracted["region"] = "semi-arid Bihar"
        else:
            extracted["region"] = "semi-arid"
    elif "arid" in lower:
        extracted["region"] = "arid"

    # Habitat / Biodiversity indicators
    if "biodiversity has declined" in lower or "biodiversity is declining" in lower or "declined" in lower:
        extracted["habitat_diversity"] = "low"

    return extracted


def extract_environmental_state(state: EnvironmentalState) -> Dict[str, Any]:
    """Extracts and merges environmental variables across multi-turn dialogue (Correction 22)."""
    # 1. Start with prior turn state from conversation history if available
    merged: Dict[str, Any] = {}
    history = state.get("conversation_history") or []
    for turn in history:
        if isinstance(turn, dict) and "environmental_data" in turn:
            merged.update(turn["environmental_data"])

    # 2. Layer any explicitly provided structured payload
    provided_raw = state.get("environmental_data") or {}
    if isinstance(provided_raw, dict):
        merged.update(provided_raw)

    # 3. Layer variables extracted from text query
    user_query = state.get("user_query") or ""
    if user_query:
        extracted_text_vars = _extract_from_text(user_query)
        for k, v in extracted_text_vars.items():
            if merged.get(k) is None:  # query populates missing
                merged[k] = v

    # Instantiate model to guarantee typed validation
    env_instance = EnvironmentalData.from_flat_or_nested(merged)
    flat_data = env_instance.to_flat_dict()
    completeness = env_instance.completeness_score()

    return {
        "environmental_data": flat_data,
        "completeness_score": completeness,
    }


# -----------------------------------------------------------------------------
# Node 3: validate_environmental_state (Targeted Clarification Logic)
# -----------------------------------------------------------------------------
def validate_environmental_state(state: EnvironmentalState) -> Dict[str, Any]:
    """Validates parameters; detects whether critical metrics are missing for a grounded assessment."""
    flat_data = state.get("environmental_data") or {}
    env_instance = EnvironmentalData.from_flat_or_nested(flat_data)
    provided = env_instance.get_provided_fields()
    missing = env_instance.get_missing_fields()

    # Check driving decision variables (SOC, Rainfall, Land Use)
    driving_vars = ["soil_organic_carbon", "rainfall", "land_use"]
    provided_driving = [v for v in driving_vars if flat_data.get(v) is not None]

    # If fewer than 2 driving variables are present, cannot formulate grounded ecological reasoning (Bug 1 / Condition 1)
    if len(provided_driving) < 2:
        clarification_questions = []
        if flat_data.get("land_use") is None:
            clarification_questions.append(
                "What type of land use or cropping system do you currently have (e.g., continuous wheat monoculture, pasture)?"
            )
        if flat_data.get("rainfall") is None:
            clarification_questions.append(
                "What is your approximate annual rainfall or general water availability (e.g., mm/year)?"
            )
        if flat_data.get("soil_organic_carbon") is None:
            clarification_questions.append(
                "Do you know your soil organic carbon (SOC) level or general soil health status?"
            )
        if not clarification_questions:
            clarification_questions.append(
                "What region or climate zone is the farm situated in (e.g., semi-arid, temperate)?"
            )

        return {
            "missing_fields": missing,
            "status": "needs_clarification",
            "clarification_questions": clarification_questions,
        }

    return {
        "missing_fields": missing,
        "status": "ready",
    }


def route_after_validation(state: EnvironmentalState) -> str:
    """Conditional edge router: routes to clarification formatting if info is insufficient."""
    if state.get("status") == "needs_clarification":
        return "format_response"
    return "analyze_metric_relationships"


# -----------------------------------------------------------------------------
# Node 4: analyze_metric_relationships (Precedes Query Construction - Correction 6)
# -----------------------------------------------------------------------------
def analyze_metric_relationships(state: EnvironmentalState) -> Dict[str, Any]:
    """Executes multi-metric relationship analysis discovering active compound interactions (>= 3 variables)."""
    env_data = state.get("environmental_data") or {}
    analyzer = EnvironmentalRelationshipAnalyzer()
    active_rels, classifications, summary = analyzer.analyze(env_data)

    return {
        "metric_relationships": [r.model_dump() for r in active_rels],
        "metric_classifications": [c.model_dump() for c in classifications],
        "compound_synthesis": summary.get("compound_synthesis"),
    }


# -----------------------------------------------------------------------------
# Node 5: build_retrieval_queries
# -----------------------------------------------------------------------------
def build_retrieval_queries(state: EnvironmentalState) -> Dict[str, Any]:
    """Synthesizes targeted multi-variable scientific search queries."""
    env_data = state.get("environmental_data") or {}
    raw_rels = state.get("metric_relationships") or []
    from app.environmental.schemas import ActiveRelationship
    active_rels = [ActiveRelationship(**r) for r in raw_rels]

    queries = MultiDimensionalQueryBuilder.build_queries(
        environmental_data=env_data,
        active_relationships=active_rels,
        max_queries=5,
    )
    return {"retrieval_queries": queries}


# -----------------------------------------------------------------------------
# Node 6: retrieve_knowledge (PostgreSQL + pgvector - Zero Silent Fallback)
# -----------------------------------------------------------------------------
def retrieve_knowledge(state: EnvironmentalState) -> Dict[str, Any]:
    """Queries PostgreSQL + pgvector. Fails explicitly if infrastructure is offline (Correction 1)."""
    queries = state.get("retrieval_queries") or []
    all_chunks: List[Dict[str, Any]] = []

    try:
        db = SessionLocal()
        retriever = KnowledgeRetriever()
        for q in queries:
            req = KnowledgeSearchRequest(query=q, top_k=3, min_similarity=0.30)
            res = retriever.search(db=db, request=req)
            for item in res.results:
                all_chunks.append(item.model_dump())
        db.close()
    except Exception as exc:
        err_msg = f"PostgreSQL/pgvector retrieval failed: {exc}"
        logger.error(err_msg)
        # Explicit infrastructure error per Correction 1
        return {
            "status": "error",
            "error": err_msg,
            "retrieved_chunks": [],
        }

    return {
        "retrieved_chunks": all_chunks,
    }


# -----------------------------------------------------------------------------
# Node 7: map_evidence
# -----------------------------------------------------------------------------
def map_evidence(state: EnvironmentalState) -> Dict[str, Any]:
    """Maps retrieved knowledge chunks to active relationships with source verification."""
    if state.get("status") == "error":
        return {}

    chunks = state.get("retrieved_chunks") or []
    raw_rels = state.get("metric_relationships") or []
    from app.environmental.schemas import ActiveRelationship
    active_rels = [ActiveRelationship(**r) for r in raw_rels]

    env_data = state.get("environmental_data") or {}
    env_inst = EnvironmentalData.from_flat_or_nested(env_data)
    observed_vars = list(env_inst.get_provided_fields().keys())

    evidence_items = EvidenceMapper.map_chunks_to_evidence(
        retrieved_chunks=chunks,
        active_relationships=active_rels,
        observed_variables=observed_vars,
    )

    # Validate evidence sufficiency
    is_sufficient, msgs, qualified = EvidenceValidator.validate_evidence(
        evidence_items=evidence_items,
        min_relevance=0.40,
        min_evidence_count=1,
    )

    return {
        "evidence": [e.model_dump() for e in evidence_items],
        "status": "ready" if is_sufficient else "insufficient_evidence",
    }


# -----------------------------------------------------------------------------
# Node 8: generate_candidates
# -----------------------------------------------------------------------------
def generate_candidates(state: EnvironmentalState) -> Dict[str, Any]:
    """Generates constraint-aware intervention candidates without universal species hardcoding."""
    if state.get("status") in ["error", "insufficient_evidence"]:
        return {"candidate_recommendations": []}

    env_data = state.get("environmental_data") or {}
    from app.environmental.schemas import ActiveRelationship, MetricClassification
    from app.evidence.schemas import EvidenceItem

    active_rels = [ActiveRelationship(**r) for r in (state.get("metric_relationships") or [])]
    classifications = [MetricClassification(**c) for c in (state.get("metric_classifications") or [])]
    evidence_items = [EvidenceItem(**e) for e in (state.get("evidence") or [])]

    candidates = RecommendationGenerator.generate_candidates(
        environmental_data=env_data,
        active_relationships=active_rels,
        evidence_items=evidence_items,
        classifications=classifications,
    )

    return {
        "candidate_recommendations": [c.model_dump() for c in candidates],
    }


# -----------------------------------------------------------------------------
# Node 9: validate_recommendations (Generic Claim Guard & Softening)
# -----------------------------------------------------------------------------
def validate_recommendations(state: EnvironmentalState) -> Dict[str, Any]:
    """Enforces generic quantitative claim verification and associative language."""
    if state.get("status") in ["error", "insufficient_evidence"]:
        return {"validated_recommendations": []}

    from app.recommendations.schemas import RecommendationItem
    from app.evidence.schemas import EvidenceItem

    candidates = [RecommendationItem(**c) for c in (state.get("candidate_recommendations") or [])]
    evidence_items = [EvidenceItem(**e) for e in (state.get("evidence") or [])]

    validated: List[Dict[str, Any]] = []
    for cand in candidates:
        val_item = RecommendationEvidenceValidator.validate_recommendation(
            candidate=cand,
            all_evidence=evidence_items,
        )
        validated.append(val_item.model_dump())

    return {
        "validated_recommendations": validated,
    }


# -----------------------------------------------------------------------------
# Node 10: calculate_confidence
# -----------------------------------------------------------------------------
def calculate_confidence(state: EnvironmentalState) -> Dict[str, Any]:
    """Derives categorical confidence and exposes measurable driving factors."""
    if state.get("status") in ["error", "insufficient_evidence"]:
        return {
            "confidence": "insufficient",
            "confidence_factors": {
                "input_completeness": state.get("completeness_score", 0.0),
                "evidence_quality": 0.0,
                "supporting_chunks": 0,
                "rationale": "Execution halted due to infrastructure error or insufficient evidence.",
            },
        }

    from app.recommendations.schemas import RecommendationItem
    from app.evidence.schemas import EvidenceItem

    validated_recs = [RecommendationItem(**r) for r in (state.get("validated_recommendations") or [])]
    evidence_items = [EvidenceItem(**e) for e in (state.get("evidence") or [])]
    completeness = float(state.get("completeness_score") or 0.0)

    ranked_recs = rank_and_score_recommendations(
        recommendations=validated_recs,
        completeness_score=completeness,
        all_evidence=evidence_items,
    )

    # Derive overall confidence from the top recommendation or general evidence
    overall_conf = ranked_recs[0].confidence if ranked_recs else "insufficient"
    overall_factors = ranked_recs[0].confidence_factors if ranked_recs else {}

    return {
        "validated_recommendations": [r.model_dump() for r in ranked_recs],
        "confidence": overall_conf,
        "confidence_factors": overall_factors,
    }


# -----------------------------------------------------------------------------
# Node 11: execute_scenario_simulation (Phase 5 Scenario Analysis Engine)
# -----------------------------------------------------------------------------
def execute_scenario_simulation(state: EnvironmentalState) -> Dict[str, Any]:
    """Executes evidence-grounded what-if scenario comparative analysis."""
    from app.scenarios.parser import ScenarioParser
    from app.scenarios.validator import ScenarioValidator
    from app.scenarios.state_builder import ScenarioStateBuilder
    from app.scenarios.analyzer import ScenarioAnalysisEngine
    from app.scenarios.schemas import ScenarioChange

    query = state.get("user_query") or state.get("scenario_query") or ""
    baseline = state.get("environmental_data") or {}

    raw_changes = state.get("scenario_changes")
    if raw_changes:
        changes = [ScenarioChange(**c) if isinstance(c, dict) else c for c in raw_changes]
        clarification_needed, questions = False, []
    else:
        changes, clarification_needed, questions = ScenarioParser.parse_query(query, baseline)

    if clarification_needed:
        return {
            "status": "needs_clarification",
            "clarification_questions": questions,
        }

    is_valid, errs = ScenarioValidator.validate_changes(changes, baseline)
    if not is_valid:
        return {
            "status": "error",
            "error": "; ".join(errs),
        }

    scen_state, assumptions = ScenarioStateBuilder.build_scenario_state(baseline, changes)
    comparison = ScenarioAnalysisEngine.analyze_scenario(
        baseline=baseline,
        scenario_state=scen_state,
        changes=changes,
        assumptions=assumptions,
    )

    return {
        "status": "completed",
        "scenario_comparison": comparison.model_dump(),
        "final_response": {
            "status": "completed",
            "scenario": comparison.model_dump(),
        },
    }


def route_after_input(state: EnvironmentalState) -> str:
    """Routes to scenario analysis if what-if simulation is requested, otherwise proceeds to assessment."""
    if state.get("is_scenario"):
        return "execute_scenario_simulation"
    q = (state.get("user_query") or "").lower()
    if any(k in q for k in ["what if", "suppose", "assume rainfall", "assume soc", "assume temperature"]):
        return "execute_scenario_simulation"
    return "extract_environmental_state"


# -----------------------------------------------------------------------------
# Node 12: format_response
# -----------------------------------------------------------------------------
def format_response(state: EnvironmentalState) -> Dict[str, Any]:
    """Builds the final machine-readable response payload."""
    status = state.get("status") or "ready"

    # Case 0: Scenario Simulation Completed
    if state.get("scenario_comparison"):
        return {
            "final_response": {
                "status": "completed",
                "scenario": state.get("scenario_comparison"),
            }
        }

    # Case A: Needs Clarification
    if status == "needs_clarification":
        return {
            "final_response": {
                "status": "needs_clarification",
                "questions": state.get("clarification_questions") or [],
                "missing_fields": state.get("missing_fields") or [],
                "data_completeness": round(float(state.get("completeness_score") or 0.0), 3),
            }
        }

    # Case B: Error
    if status == "error":
        return {
            "final_response": {
                "status": "error",
                "error": state.get("error") or "Unknown infrastructure error.",
                "confidence": "insufficient",
            }
        }

    # Case C: Insufficient Evidence
    if status == "insufficient_evidence":
        return {
            "final_response": {
                "status": "insufficient_evidence",
                "message": "Insufficient evidence to make a confident recommendation.",
                "confidence": "insufficient",
                "assessment": {
                    "environmental_state": state.get("environmental_data") or {},
                    "key_relationships": state.get("metric_relationships") or [],
                    "data_completeness": round(float(state.get("completeness_score") or 0.0), 3),
                },
                "recommendations": [],
                "evidence_summary": [],
            }
        }

    # Case D: Complete Structured Assessment
    env_data = state.get("environmental_data") or {}
    env_inst = EnvironmentalData.from_flat_or_nested(env_data)

    limitations = [
        "Species selection requires local agronomic, edaphic, and climatic field verification.",
        "Recommendations are based on reported scientific syntheses and context-dependent heuristics.",
    ]

    response_payload = {
        "status": "completed",
        "assessment": {
            "environmental_state": env_inst.get_provided_fields(),
            "key_relationships": state.get("metric_relationships") or [],
            "compound_synthesis": state.get("compound_synthesis"),
            "data_completeness": round(float(state.get("completeness_score") or 0.0), 3),
        },
        "recommendations": state.get("validated_recommendations") or [],
        "evidence_summary": state.get("evidence") or [],
        "confidence": state.get("confidence") or "medium",
        "confidence_factors": state.get("confidence_factors") or {},
        "limitations": limitations,
    }

    return {
        "final_response": response_payload,
    }


# -----------------------------------------------------------------------------
# Graph Builder
# -----------------------------------------------------------------------------
def build_graph() -> Any:
    """Compiles the Environmental Intelligence Reasoning & Scenario Analysis Graph."""
    workflow = StateGraph(EnvironmentalState)

    # Register all nodes
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("execute_scenario_simulation", execute_scenario_simulation)
    workflow.add_node("extract_environmental_state", extract_environmental_state)
    workflow.add_node("validate_environmental_state", validate_environmental_state)
    workflow.add_node("analyze_metric_relationships", analyze_metric_relationships)
    workflow.add_node("build_retrieval_queries", build_retrieval_queries)
    workflow.add_node("retrieve_knowledge", retrieve_knowledge)
    workflow.add_node("map_evidence", map_evidence)
    workflow.add_node("generate_candidates", generate_candidates)
    workflow.add_node("validate_recommendations", validate_recommendations)
    workflow.add_node("calculate_confidence", calculate_confidence)
    workflow.add_node("format_response", format_response)

    # Define edges
    workflow.add_edge(START, "parse_input")

    # Conditional branch after parse_input (Scenario vs Assessment)
    workflow.add_conditional_edges(
        "parse_input",
        route_after_input,
        {
            "execute_scenario_simulation": "execute_scenario_simulation",
            "extract_environmental_state": "extract_environmental_state",
        },
    )

    workflow.add_edge("execute_scenario_simulation", "format_response")
    workflow.add_edge("extract_environmental_state", "validate_environmental_state")

    # Conditional branch after validation
    workflow.add_conditional_edges(
        "validate_environmental_state",
        route_after_validation,
        {
            "format_response": "format_response",
            "analyze_metric_relationships": "analyze_metric_relationships",
        },
    )

    workflow.add_edge("analyze_metric_relationships", "build_retrieval_queries")
    workflow.add_edge("build_retrieval_queries", "retrieve_knowledge")
    workflow.add_edge("retrieve_knowledge", "map_evidence")
    workflow.add_edge("map_evidence", "generate_candidates")
    workflow.add_edge("generate_candidates", "validate_recommendations")
    workflow.add_edge("validate_recommendations", "calculate_confidence")
    workflow.add_edge("calculate_confidence", "format_response")
    workflow.add_edge("format_response", END)

    return workflow.compile()


app_graph = build_graph()

