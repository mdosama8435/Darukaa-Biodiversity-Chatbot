"""Live verification script running Tests A through G against the live Docker backend on http://localhost:8000."""

import json
import uuid
import requests

BASE_URL = "http://localhost:8000/api/v1"

def print_separator(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def main():
    print_separator("HEALTH & KNOWLEDGE CHECK")
    # Health check
    res = requests.get(f"{BASE_URL}/health")
    print(f"Health response ({res.status_code}): {res.json()}")
    assert res.status_code == 200

    # Knowledge search
    search_payload = {"query": "intercropping biodiversity soil organic carbon", "limit": 3}
    search_res = requests.post(f"{BASE_URL}/knowledge/search", json=search_payload)
    print(f"Knowledge search ({search_res.status_code}): found {len(search_res.json().get('results', []))} chunks")
    assert search_res.status_code == 200

    # Assessment endpoint check
    assess_payload = {
        "region": "semi-arid",
        "soil_organic_carbon": 0.3,
        "rainfall": 600.0,
        "land_use": "continuous wheat cropping",
    }
    assess_res = requests.post(f"{BASE_URL}/assessment", json=assess_payload)
    print(f"Assessment evaluate ({assess_res.status_code}): status {assess_res.json().get('status')}")
    assert assess_res.status_code == 200

    # =========================================================================
    # MULTI-TURN CONVERSATION: TESTS A, B, C, D, E
    # =========================================================================
    conv_id = f"live_test_session_{uuid.uuid4().hex[:8]}"
    print_separator(f"CONVERSATION SESSION: {conv_id}")

    # TEST A: "My biodiversity is declining on my farm."
    print_separator("TEST A: 'My biodiversity is declining on my farm.'")
    res_a = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "My biodiversity is declining on my farm."})
    data_a = res_a.json()
    print(f"Status: {data_a.get('status')}")
    print(f"Clarification questions count: {len(data_a.get('clarification_questions') or [])}")
    print(f"Assistant Message:\n{data_a.get('message')}")
    assert data_a.get("status") == "clarification_needed"
    assert data_a.get("clarification_questions") is not None
    assert "Agroforestry" not in data_a.get("message", "")
    print(">>> TEST A PASSED: Clarification requested, no premature recommendations.")

    # TEST B: "I grow wheat continuously."
    print_separator("TEST B: 'I grow wheat continuously.'")
    res_b = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "I grow wheat continuously."})
    data_b = res_b.json()
    print(f"Status: {data_b.get('status')}")
    print(f"Clarification questions count: {len(data_b.get('clarification_questions') or [])}")
    print(f"Assistant Message:\n{data_b.get('message')}")
    assert data_b.get("status") == "clarification_needed"
    assert "Agroforestry" not in data_b.get("message", "")
    assert data_b.get("assessment") is None or "recommendations" not in data_b.get("assessment", {})
    print(">>> TEST B PASSED: Land use recorded; clarification continued because rainfall & SOC still missing.")

    # TEST C: "Annual rainfall is around 600 mm."
    print_separator("TEST C: 'Annual rainfall is around 600 mm.'")
    res_c = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "Annual rainfall is around 600 mm."})
    data_c = res_c.json()
    print(f"Status: {data_c.get('status')}")
    print(f"Clarification questions count: {len(data_c.get('clarification_questions') or [])}")
    print(f"Assistant Message:\n{data_c.get('message')}")
    assert data_c.get("status") == "clarification_needed"
    # Verify no false "low rainfall" classification without context
    assert "low precipitation (600" not in data_c.get("message", "")
    assert "whether this represents water stress depends on regional and seasonal context" in data_c.get("message", "")
    print(">>> TEST C PASSED: Rainfall 600 mm recorded contextually without false 'low' label; clarification continued for SOC.")

    # TEST E (Can be queried before or after SOC): "What is my current soil moisture?"
    print_separator("TEST E: 'What is my current soil moisture?'")
    res_e = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "What is my current soil moisture?"})
    data_e = res_e.json()
    print(f"Status: {data_e.get('status')}")
    print(f"Assistant Message:\n{data_e.get('message')}")
    assert data_e.get("status") == "completed"
    assert "Soil moisture has not been provided" in data_e.get("message", "")
    assert "600" not in data_e.get("message", ""), "Rainfall 600 mm must NEVER be mapped to soil moisture!"
    assert data_e.get("assessment") is None, "Measurement lookup must NOT trigger recommendations!"
    print(">>> TEST E PASSED: Correctly handled missing soil moisture; rainfall != soil moisture; no recommendations triggered.")

    # TEST D: "My soil organic carbon is 0.3%."
    print_separator("TEST D: 'My soil organic carbon is 0.3%.'")
    res_d = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id, "message": "My soil organic carbon is 0.3%."})
    data_d = res_d.json()
    print(f"Status: {data_d.get('status')}")
    print(f"Assistant Message:\n{data_d.get('message')}")
    assert data_d.get("status") == "completed"
    assert data_d.get("assessment") is not None
    assert "Key Evidence-Grounded Recommendations" in data_d.get("message", "")
    assert "COMPOUND MULTI-METRIC INTERACTION" in data_d.get("message", "")
    print(">>> TEST D PASSED: Context now fully satisfied (Land Use + Rainfall + SOC); multi-metric assessment executed.")

    # =========================================================================
    # TEST F: Unsupported Species Quantification
    # =========================================================================
    print_separator("TEST F: Unsupported Species Quantification")
    conv_id_f = f"live_test_session_f_{uuid.uuid4().hex[:8]}"
    msg_f = "My soil organic carbon is 0.3%. Tell me exactly how many species will increase if I improve it to 0.6%."
    res_f = requests.post(f"{BASE_URL}/chat", json={"conversation_id": conv_id_f, "message": msg_f})
    data_f = res_f.json()
    print(f"Status: {data_f.get('status')}")
    print(f"Assistant Message:\n{data_f.get('message')}")
    assert data_f.get("status") == "completed"
    assert "Exact species increase cannot be determined from the available evidence" in data_f.get("message", "")
    assert "eDNA metabarcoding" in data_f.get("message", "") or "taxonomic baseline" in data_f.get("message", "")
    assert "recommendations" not in (data_f.get("assessment") or {}), "Must not silently replace with old recommendations!"
    print(">>> TEST F PASSED: Unsupported species count refused without invented numbers or recommendations.")

    # =========================================================================
    # TEST G: Scenario Baseline Preamble + What-If Simulation
    # =========================================================================
    print_separator("TEST G: Preamble Baseline + Scenario Simulation")
    query_g = (
        "SOC = 0.3%\n"
        "Rainfall = 600 mm\n"
        "Land use = wheat monoculture\n\n"
        "What if rainfall decreases by 15% and I switch from wheat monoculture to intercropping?"
    )

    # 1. Test via /api/v1/scenarios/analyze
    scen_res = requests.post(f"{BASE_URL}/scenarios/analyze", json={"query": query_g})
    print(f"Scenario API Response ({scen_res.status_code}):")
    assert scen_res.status_code == 200, f"Failed with {scen_res.text}"
    scen_data = scen_res.json()
    comparison = scen_data.get("comparison", {})
    assert comparison, "Comparison must not be empty"

    print(f"Scenario ID: {comparison.get('scenario_id')}")
    print(f"Confidence: {comparison.get('confidence')}")
    print(f"Confidence factors: {json.dumps(comparison.get('confidence_factors'), indent=2)}")

    print("\nResolved Changed Variables:")
    for ch in comparison.get("changed_variables", []):
        print(f"  - {ch.get('variable')}: baseline={ch.get('baseline_value')}, scenario={ch.get('scenario_value')}, type={ch.get('change_type')}")

    print("\nEvaluation Matrix:")
    matrix_by_metric = {}
    for row in comparison.get("evaluation_matrix", []):
        matrix_by_metric[row.get("metric")] = row
        print(f"  - {row.get('metric')}: baseline={row.get('baseline')} -> scenario={row.get('scenario')} | conf={row.get('confidence')}")

    # Assertions for TEST G:
    # 1. Baseline has SOC 0.3%, Rainfall 600 mm, Land use wheat monoculture
    base_summary = comparison.get("baseline_summary", {})
    assert base_summary.get("soil_organic_carbon") == 0.3
    assert base_summary.get("rainfall") == 600.0
    assert "wheat monoculture" in str(base_summary.get("land_use")).lower()

    # 2. Changes ONLY contain rainfall (-15%) and land_use (intercropping)
    changed_vars = [c.get("variable") for c in comparison.get("changed_variables", [])]
    assert "soil_organic_carbon" not in changed_vars, "SOC must NOT be in changed_variables!"
    assert "rainfall" in changed_vars
    assert "land_use" in changed_vars

    # 3. Rainfall in evaluation matrix is labeled as RAINFALL
    assert "rainfall" in matrix_by_metric, "Evaluation matrix must contain 'rainfall'!"
    rain_row = matrix_by_metric["rainfall"]
    assert "600" in str(rain_row.get("baseline")) and "mm" in str(rain_row.get("baseline"))
    assert "510" in str(rain_row.get("scenario")) and "mm" in str(rain_row.get("scenario"))

    # 4. Soil moisture is NOT labeled as 600 mm or 510 mm!
    if "soil_moisture" in matrix_by_metric:
        moist_row = matrix_by_metric["soil_moisture"]
        assert "600 mm" not in str(moist_row.get("baseline")), "Soil moisture must not be 600 mm!"
        assert "510 mm" not in str(moist_row.get("scenario")), "Soil moisture must not be 510 mm!"
        assert "Unknown" in str(moist_row.get("baseline")) or "Not provided" in str(moist_row.get("baseline"))
        assert "Unknown" in str(moist_row.get("scenario")) or "Not provided" in str(moist_row.get("scenario"))
        assert moist_row.get("direction") == "uncertain"

    # 5. Also test via /api/v1/chat endpoint with query_g
    chat_scen_res = requests.post(f"{BASE_URL}/chat", json={"message": query_g})
    assert chat_scen_res.status_code == 200
    chat_scen_data = chat_scen_res.json()
    chat_msg = chat_scen_data.get("message", "").lower()
    assert "rainfall" in chat_msg and "600" in chat_msg and "510" in chat_msg
    assert "soil_moisture: 600" not in chat_msg
    print(">>> TEST G PASSED: Baseline preamble separated; changes parsed; Evaluation Matrix correctly labels rainfall -> rainfall; soil moisture unknown.")

    print_separator("ALL LIVE TESTS A THROUGH G PASSED WITH FULL DATA INTEGRITY!")

if __name__ == "__main__":
    main()
