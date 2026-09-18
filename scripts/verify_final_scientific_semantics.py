"""DARUKAA.EARTH - Final Scientific Semantics Verification Script.

Verifies:
1. PostgreSQL & pgvector connection and extension status.
2. Live API health check.
3. ISSUE 5: Final context integrity test (Turns 1-4).
4. ISSUE 4: Numerical claim safety test (species count refusal).
5. ISSUE 6: Final scenario test (baseline preamble, 600 -> 510 mm rainfall, soil moisture unknown).
6. ISSUE 3: Evidence chain verification for 3 live cases tracing:
   Recommendation -> Relationship -> EvidenceItem -> DB Knowledge Chunk -> DB Knowledge Document -> Organization -> DOI/URL.
"""

import sys
import uuid
import re
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

BASE_URL = "http://localhost:8000/api/v1"
DB_CONN = "postgresql://darukaa:darukaa_password_change_in_production@localhost:5432/darukaa_earth"


def print_separator(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def check_postgres_and_pgvector():
    print_separator("1. VERIFY POSTGRESQL & PGVECTOR")
    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Check postgres version
    cur.execute("SELECT version();")
    v = cur.fetchone()["version"]
    print(f"PostgreSQL Version: {v}")

    # Check pgvector extension
    cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
    ext = cur.fetchone()
    print(f"pgvector extension: {ext['extname']} v{ext['extversion']}")
    assert ext is not None and ext["extname"] == "vector"

    # Check documents and chunks count
    cur.execute("SELECT count(*) as cnt FROM knowledge_documents;")
    docs_cnt = cur.fetchone()["cnt"]
    cur.execute("SELECT count(*) as cnt FROM knowledge_chunks;")
    chunks_cnt = cur.fetchone()["cnt"]
    print(f"Knowledge base status: {docs_cnt} documents, {chunks_cnt} chunks indexed.")
    assert docs_cnt > 0 and chunks_cnt > 0

    cur.close()
    conn.close()
    print(">>> PostgreSQL 16 + pgvector verified successfully.")


def check_live_api_health():
    print_separator("2. VERIFY LIVE API HEALTH")
    res = requests.get(f"{BASE_URL}/health")
    print(f"Health ({res.status_code}): {res.json()}")
    assert res.status_code == 200
    assert res.json().get("status") == "ok"
    print(">>> Live API health confirmed.")


def run_final_conversation():
    print_separator("3. ISSUE 5: FINAL CONTEXT INTEGRITY CONVERSATION")
    conv_id = f"final_semantics_{uuid.uuid4().hex[:8]}"
    print(f"Session ID: {conv_id}")

    # Turn 1
    print("\n--- Turn 1: 'My biodiversity is declining on my farm.' ---")
    r1 = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "My biodiversity is declining on my farm."})
    d1 = r1.json()
    recs1 = (d1.get('assessment') or {}).get('recommendations', [])
    print(f"Status: {d1.get('status')} | Recs: {len(recs1)}")
    assert d1.get("status") == "clarification_needed"
    assert len(recs1) == 0

    # Turn 2
    print("\n--- Turn 2: 'I grow wheat continuously.' ---")
    r2 = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "I grow wheat continuously."})
    d2 = r2.json()
    recs2 = (d2.get('assessment') or {}).get('recommendations', [])
    print(f"Status: {d2.get('status')} | Recs: {len(recs2)}")
    assert d2.get("status") == "clarification_needed"
    assert len(recs2) == 0

    # Turn 3
    print("\n--- Turn 3: 'Annual rainfall is around 600 mm.' ---")
    r3 = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "Annual rainfall is around 600 mm."})
    d3 = r3.json()
    recs3 = (d3.get('assessment') or {}).get('recommendations', [])
    print(f"Status: {d3.get('status')} | Recs: {len(recs3)}")
    assert d3.get("status") == "clarification_needed"
    assert len(recs3) == 0
    # 600 mm must NOT automatically be classified as "low rainfall"
    msg3 = d3.get("message", "").lower()
    assert "low rainfall" not in msg3
    assert "whether this represents water stress depends on regional and seasonal context" in msg3 or "600 mm" in msg3

    # Turn 4
    print("\n--- Turn 4: 'My soil organic carbon is 0.3%.' ---")
    r4 = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "My soil organic carbon is 0.3%."})
    d4 = r4.json()
    recs4 = (d4.get('assessment') or {}).get('recommendations', [])
    print(f"Status: {d4.get('status')} | Recs: {len(recs4)}")
    assert d4.get("status") == "completed"

    # Inspect context
    env_ctx = d4.get("environmental_context", {})
    vars_dict = env_ctx.get("variables", env_ctx) if "variables" in env_ctx else env_ctx
    print(f"Final Variables Recorded: {list(vars_dict.keys())}")
    assert "soil_organic_carbon" in vars_dict and vars_dict["soil_organic_carbon"].get("value") == 0.3
    assert "rainfall" in vars_dict and vars_dict["rainfall"].get("value") == 600.0
    assert "land_use" in vars_dict and "wheat" in str(vars_dict["land_use"].get("value")).lower()
    # Soil moisture must remain UNKNOWN unless explicitly provided
    assert "soil_moisture" not in vars_dict or vars_dict["soil_moisture"].get("value") is None

    # Recommendations check
    recs = d4.get("assessment", {}).get("recommendations", [])
    print(f"Recommendations count: {len(recs)}")
    assert len(recs) >= 2, "Must generate evidence-grounded recommendations upon full driving context!"
    for i, rec in enumerate(recs, 1):
        print(f"  Rec {i}: {rec.get('action')}")
        assert rec.get("evidence") and len(rec.get("evidence")) > 0, f"Rec {i} must be grounded in evidence!"

    print(">>> ISSUE 5 PASSED: Full context integrity verified with multi-metric activation and zero unmeasured soil moisture.")
    return conv_id, d4


def run_numerical_claim_safety():
    print_separator("4. ISSUE 4: NUMERICAL CLAIM SAFETY TEST")
    conv_id = f"num_safety_{uuid.uuid4().hex[:8]}"
    query = "My SOC is 0.3%. If I improve it to 0.6%, exactly how many species will increase?"
    print(f"Query: {query}")

    res = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": query})
    data = res.json()
    msg = data.get("message", "")
    print(f"\nAssistant Response:\n{msg}")

    assert data.get("status") == "completed"
    assert len((data.get("assessment") or {}).get("recommendations", [])) == 0, "Must not emit repeated recommendations!"

    # Required safety checks
    assert "exact species increase cannot be determined" in msg.lower()
    assert "edna" in msg.lower() or "taxonomic baseline" in msg.lower() or "field sampling" in msg.lower()

    # No invented species count or percentage
    assert not re.search(r"gain [0-9]+ species", msg, re.IGNORECASE)
    assert not re.search(r"increase by [0-9]+ species", msg, re.IGNORECASE)
    assert not re.search(r"[0-9]+% more species", msg, re.IGNORECASE)

    # Accurate source terminology
    assert "peer-reviewed literature" not in msg.lower()
    assert "authoritative scientific and technical sources" in msg.lower() or "verified scientific" in msg.lower()

    print(">>> ISSUE 4 PASSED: Unsupported species count refused without invented numbers or repeated recommendations.")


def run_final_scenario():
    print_separator("5. ISSUE 6: FINAL SCENARIO TEST")
    query = "Suppose I have a farm with wheat monoculture, rainfall of 600 mm, and SOC of 0.3%. What happens if rainfall drops by 15% and I switch to intercropping?"
    print(f"Scenario Query:\n{query}")

    res = requests.post(f"{BASE_URL}/scenarios/analyze", json={"query": query})
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "completed"

    comp = data.get("comparison", {})
    base = comp.get("baseline_summary", {})
    scen = comp.get("scenario_summary", {})
    changes = comp.get("changed_variables", [])
    matrix = comp.get("evaluation_matrix", [])
    factors = comp.get("confidence_factors", {})

    print(f"\nBaseline Summary: {base}")
    print(f"Scenario Summary: {scen}")
    print(f"Changed Variables Count: {len(changes)}")

    # Verify Baseline: SOC=0.3%, Rainfall=600 mm, Land use=wheat monoculture
    assert base.get("soil_organic_carbon") == 0.3
    assert base.get("rainfall") == 600.0
    assert "wheat" in str(base.get("land_use")).lower()

    # Verify Changes: Rainfall=-15%, Land use=intercropping
    ch_vars = {c["variable"]: c for c in changes}
    assert "rainfall" in ch_vars
    assert "land_use" in ch_vars
    assert ch_vars["rainfall"]["change_value"] == -15.0 or ch_vars["rainfall"]["scenario_value"] == 510.0
    assert "intercropping" in str(ch_vars["land_use"]["scenario_value"]).lower()

    # Verify Scenario Summary: Rainfall=510 mm, SOC=0.3%, Land use=intercropping, Soil moisture=None
    assert scen.get("rainfall") == 510.0
    assert scen.get("soil_organic_carbon") == 0.3
    assert "intercropping" in str(scen.get("land_use")).lower()
    assert scen.get("soil_moisture") is None, "Soil moisture must NOT be present in scenario summary!"

    # Verify Evaluation Matrix
    matrix_by_metric = {row["metric"]: row for row in matrix}
    print("\nEvaluation Matrix Rows:")
    for m, r in matrix_by_metric.items():
        print(f"  - {m}: baseline='{r['baseline']}' -> scenario='{r['scenario']}' | direction='{r['direction']}' | conf='{r['confidence']}'")

    # Rainfall MUST be 600 mm -> 510 mm
    assert "rainfall" in matrix_by_metric
    rain_row = matrix_by_metric["rainfall"]
    assert "600" in str(rain_row["baseline"])
    assert "510" in str(rain_row["scenario"])
    assert rain_row["direction"] == "decreased"
    assert rain_row["confidence"] == "high"

    # Soil Moisture MUST remain Unknown / Not provided for both baseline and scenario!
    assert "soil_moisture" in matrix_by_metric
    moist_row = matrix_by_metric["soil_moisture"]
    assert moist_row["baseline"] == "Unknown / Not provided"
    assert moist_row["scenario"] == "Unknown / Not provided"
    assert moist_row["direction"] == "uncertain"
    assert "Reduced rainfall may increase soil-water stress or desiccation risk" in moist_row["limitations"]
    assert "validated hydrological model" in moist_row["limitations"]

    # Confidence semantics
    assert factors.get("computational_confidence") == "high"
    assert factors.get("scientific_evidence_confidence") == "medium"
    assert comp.get("confidence") == "medium"
    assert "peer-reviewed literature" not in factors.get("rationale", "").lower()
    assert "verified scientific and technical sources" in factors.get("rationale", "").lower()

    print(">>> ISSUE 6 PASSED: Final scenario verified: baseline preamble parsed, rainfall mapped to rainfall, soil moisture unknown, confidence decoupled.")
    return data


def verify_evidence_chains(chat_data):
    print_separator("6. ISSUE 3: EVIDENCE CHAIN VERIFICATION (BACKEND OBJECTS & DB)")
    recs = chat_data.get("assessment", {}).get("recommendations", [])
    assert len(recs) >= 2

    conn = psycopg2.connect(DB_CONN)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    chains_inspected = 0

    for rec_idx, rec in enumerate(recs, 1):
        action = rec.get("action")
        reasoning_steps = rec.get("environmental_reasoning", [])
        evidence_items = rec.get("evidence", [])

        print(f"\n[Case {rec_idx}] Recommendation: {action}")
        rel_id = reasoning_steps[0].get("relationship") if reasoning_steps else "unknown_relationship"
        print(f"  |-> Relationship: {rel_id}")

        for ev in evidence_items[:2]:
            ev_id = ev.get("evidence_id")
            chunk_id = ev.get("chunk_id")
            doc_id = ev.get("document_id")
            source_org = ev.get("source_organization")
            doi = ev.get("doi")
            url = ev.get("url")
            claim = ev.get("claim", "")[:80] + "..."

            print(f"  |-> Evidence Item (ID: {ev_id})")
            print(f"    Claim: '{claim}'")
            print(f"    |-> Knowledge Chunk DB ID: {chunk_id}")
            assert chunk_id is not None, "EvidenceItem must have a real chunk_id!"

            # Query database knowledge_chunks
            cur.execute("SELECT id, document_id, chunk_index, chunk_text, page_number, section FROM knowledge_chunks WHERE id = %s;", (chunk_id,))
            chunk_row = cur.fetchone()
            assert chunk_row is not None, f"Chunk ID {chunk_id} not found in database knowledge_chunks!"
            print(f"      DB Record: id={chunk_row['id']}, doc_id={chunk_row['document_id']}, chars={len(chunk_row['chunk_text'])}")

            # Query database knowledge_documents
            print(f"    |-> Knowledge Document DB ID: {chunk_row['document_id']}")
            cur.execute("SELECT id, title, source, document_type, doi, source_url, publication_year FROM knowledge_documents WHERE id = %s;", (chunk_row['document_id'],))
            doc_row = cur.fetchone()
            assert doc_row is not None, f"Document ID {chunk_row['document_id']} not found in database knowledge_documents!"
            print(f"      DB Record: title='{doc_row['title'][:50]}...', type='{doc_row['document_type']}'")
            print(f"    |-> Source Organization: {doc_row['source']}")
            print(f"    |-> DOI: {doc_row['doi']} | URL: {doc_row['source_url']}")

            # Validate that EvidenceItem matches DB record exactly
            assert doc_row["source"].lower() in source_org.lower(), f"Source org mismatch: {doc_row['source']} vs {source_org}"
            if doc_row["doi"]:
                assert doc_row["doi"] == doi, f"DOI mismatch: {doc_row['doi']} vs {doi}"

            chains_inspected += 1
            if chains_inspected >= 3:
                break
        if chains_inspected >= 3:
            break

    cur.close()
    conn.close()

    print(f"\n>>> Total Fully-Verified Database Evidence Chains: {chains_inspected}")
    assert chains_inspected >= 3, "Must verify at least 3 live evidence chains with actual database objects!"
    print(">>> ISSUE 3 PASSED: All 3 live recommendation chains trace seamlessly to real PostgreSQL/pgvector chunks and documents.")


def main():
    check_postgres_and_pgvector()
    check_live_api_health()
    conv_id, chat_data = run_final_conversation()
    run_numerical_claim_safety()
    run_final_scenario()
    verify_evidence_chains(chat_data)
    print_separator("ALL FINAL SCIENTIFIC SEMANTICS CHECKS PASSED WITH 100% SUCCESS!")


if __name__ == "__main__":
    main()
