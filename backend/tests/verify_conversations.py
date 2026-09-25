"""Script to run the exact manual verification conversations from Section 13.
"""
from app.conversation.schemas import ChatRequest
from app.conversation.turn_processor import TurnProcessor
from app.conversation.context_manager import EnvironmentalContextManager

def run_conversation_1():
    print("=" * 60)
    print("CONVERSATION 1: Targeted Clarification")
    print("=" * 60)
    conv_id = "manual_conv_1"
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_id, None)

    req = ChatRequest(conversation_id=conv_id, message="My farmland has poor biodiversity.")
    resp = TurnProcessor.process_turn(req)
    print(f"Status: {resp.status}")
    print(f"Validation Error: {resp.validation_error}")
    print(f"Message:\n{resp.message}")
    print(f"Clarification Questions:\n{resp.clarification_questions}")
    assert resp.status == "clarification_needed"
    assert resp.clarification_questions and len(resp.clarification_questions) > 0
    print("[PASS] Conversation 1 passed targeted clarification.")

def run_conversation_2():
    print("\n" + "=" * 60)
    print("CONVERSATION 2: Wheat Farm Context")
    print("=" * 60)
    conv_id = "manual_conv_2"
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_id, None)

    req = ChatRequest(conversation_id=conv_id, message="I grow wheat. SOC is 0.3% and rainfall is 600 mm.")
    resp = TurnProcessor.process_turn(req)
    print(f"Status: {resp.status}")
    print(f"Validation Error: {resp.validation_error}")
    print(f"Message:\n{resp.message}")
    ctx = EnvironmentalContextManager.get_or_create_context(conv_id)
    vars_found = {k: v.value for k, v in ctx.variables.items()}
    print(f"Context variables: {vars_found}")
    print(f"Clarification Questions:\n{resp.clarification_questions}")

    assert "crop" in ctx.variables and ctx.variables["crop"].value == "wheat"
    assert "soil_organic_carbon" in ctx.variables and ctx.variables["soil_organic_carbon"].value == 0.3
    assert "rainfall" in ctx.variables and ctx.variables["rainfall"].value == 600.0
    if resp.clarification_questions:
        for q in resp.clarification_questions:
            assert "crop" not in q.lower()
            assert "land use" not in q.lower()
    print("[PASS] Conversation 2 recognized wheat, SOC, rainfall without repeated crop questions.")

def run_conversation_3():
    print("\n" + "=" * 60)
    print("CONVERSATION 3: Invalid pH followed by Corrected pH")
    print("=" * 60)
    conv_id = "manual_conv_3"
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_id, None)

    # Turn 1
    req1 = ChatRequest(conversation_id=conv_id, message="My soil pH is 15.5.")
    resp1 = TurnProcessor.process_turn(req1)
    print(f"Turn 1 Status: {resp1.status}")
    print(f"Turn 1 Validation Error: {resp1.validation_error}")
    print(f"Turn 1 Message:\n{resp1.message}")
    print(f"Turn 1 Active Context:\n{resp1.environmental_context}")
    print(f"Turn 1 Detected Updates:\n{resp1.detected_updates}")

    assert resp1.validation_error is True
    assert "Soil pH must be between 0 and 14" in resp1.message
    assert "15.5" in resp1.message
    assert "Value error" not in resp1.message
    ctx1 = EnvironmentalContextManager.get_or_create_context(conv_id)
    assert "soil_ph" not in ctx1.variables or ctx1.variables["soil_ph"].value != 15.5
    assert len(resp1.detected_updates or []) == 0

    # Turn 2
    req2 = ChatRequest(conversation_id=conv_id, message="Actually my pH is 12.5.")
    resp2 = TurnProcessor.process_turn(req2)
    print(f"\nTurn 2 Status: {resp2.status}")
    print(f"Turn 2 Validation Error: {resp2.validation_error}")
    print(f"Turn 2 Message:\n{resp2.message}")
    ctx2 = EnvironmentalContextManager.get_or_create_context(conv_id)
    print(f"Turn 2 Active soil_ph: {ctx2.variables.get('soil_ph')}")
    print(f"Turn 2 Detected Updates: {resp2.detected_updates}")

    assert ctx2.variables["soil_ph"].value == 12.5
    # Absolutely NO 15.5 -> 12.5
    for upd in (resp2.detected_updates or []):
        assert upd.old_value != 15.5
        assert upd.new_value != 15.5
    print("[PASS] Conversation 3 passed: 15.5 never entered memory, 12.5 recorded without 15.5 -> 12.5 transition.")

def run_conversation_4():
    print("\n" + "=" * 60)
    print("CONVERSATION 4: Acidic pH 5.5 vs Alkaline pH 12.5 Comparison")
    print("=" * 60)

    # Run A: pH 5.5 + SOC 0.3%
    conv_a = "manual_conv_4a"
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_a, None)
    req_a = ChatRequest(conversation_id=conv_a, message="My soil pH is 5.5 and SOC is 0.3% on my wheat farm with 600 mm rainfall.")
    resp_a = TurnProcessor.process_turn(req_a)

    # Run B: pH 12.5 + SOC 0.3%
    conv_b = "manual_conv_4b"
    EnvironmentalContextManager._MEMORY_STORE.pop(conv_b, None)
    req_b = ChatRequest(conversation_id=conv_b, message="My soil pH is 12.5 and SOC is 0.3% on my wheat farm with 600 mm rainfall.")
    resp_b = TurnProcessor.process_turn(req_b)

    print(f"resp_a status: {resp_a.status}")
    inner_a = (resp_a.assessment or {}).get("assessment", resp_a.assessment or {})
    inner_b = (resp_b.assessment or {}).get("assessment", resp_b.assessment or {})

    rels_a = [r.get("relationship_id") for r in (inner_a.get("key_relationships") or inner_a.get("active_relationships", []))]
    rels_b = [r.get("relationship_id") for r in (inner_b.get("key_relationships") or inner_b.get("active_relationships", []))]

    print(f"pH 5.5 active relationships: {rels_a}")
    print(f"pH 12.5 active relationships: {rels_b}")

    # Verify pH 5.5 activates acidic stress relationship
    assert "ph_microbial_structure" in rels_a
    # Verify pH 12.5 does NOT activate ph_microbial_structure (acidification relationship)
    assert "ph_microbial_structure" not in rels_b

    # Verify honest limitations in pH 12.5
    recs_b = (resp_b.assessment or {}).get("recommendations", [])
    if recs_b:
        limitations_b = " ".join(" ".join(r.get("limitations", [])) for r in recs_b)
        print(f"pH 12.5 recommendations limitations:\n{limitations_b}")
        assert "alkaline" in limitations_b.lower() or "corpus" in limitations_b.lower()

    print("[PASS] Conversation 4 passed: pH 5.5 acidic relationship activated correctly, pH 12.5 does not fake relationship and honestly acknowledges corpus limitations.")

if __name__ == "__main__":
    run_conversation_1()
    run_conversation_2()
    run_conversation_3()
    run_conversation_4()
    print("\nALL 4 MANUAL VERIFICATION SCENARIOS COMPLETED SUCCESSFULLY!")
