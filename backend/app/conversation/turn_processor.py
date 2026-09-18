import re
import uuid
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.conversation.schemas import (
    MetricStatus,
    ChatRequest,
    ChatResponse,
    EnvironmentalContextModel,
)
from app.conversation.context_manager import EnvironmentalContextManager
from app.conversation.clarification import ClarificationEngine
from app.conversation.memory_policy import MemoryPolicy
from app.agents.graph import app_graph
from app.agents.state import EnvironmentalState

logger = logging.getLogger(__name__)


class TurnProcessor:
    """Orchestrates single-turn dialogue processing, context updates, and Phase 3 invocation."""

    @classmethod
    def process_turn(
        cls,
        request: ChatRequest,
        db_session: Optional[Any] = None,
    ) -> ChatResponse:
        """Processes a single conversational turn through memory merging and assessment pipeline."""
        # 1. Resolve or generate conversation ID
        conv_id = request.conversation_id or str(uuid.uuid4())
        context = EnvironmentalContextManager.get_or_create_context(conv_id)

        # Derive turn_id based on number of previous interactions
        current_turn = len(context.detected_updates) + context.clarification_depth + 1
        user_text = request.message.strip()
        user_lower = user_text.lower()

        # ---------------------------------------------------------------------
        # Phase 5: Hypothetical What-If Scenario Detection
        # Baseline context is preserved immutably (Scenario != Real-World Update)
        # ---------------------------------------------------------------------
        # ---------------------------------------------------------------------
        # Intent 0: Context Overview / Stored Farm Information (Step 13)
        # e.g., "What information do you have about my farm?", "What do you know about my farm?"
        # Must answer from active stored context without generating recommendations.
        # ---------------------------------------------------------------------
        is_context_overview_query = bool(
            re.search(r"\b(?:what (?:information|data|metrics|context) do you have|what do you know|show (?:my )?data|show (?:my )?information|current stored context)\b", user_lower)
            or ("about my farm" in user_lower and any(w in user_lower for w in ["what", "information", "know", "data", "have"]))
            or ("about my land" in user_lower and any(w in user_lower for w in ["what", "information", "know", "data", "have"]))
        )
        if is_context_overview_query and not any(k in user_lower for k in ["what if", "suppose", "compare"]):
            provided_items = []
            for k, prov in context.variables.items():
                if prov.value is not None and prov.status != MetricStatus.UNKNOWN:
                    label = k.replace("_", " ").title()
                    unit_str = f" {prov.unit}" if prov.unit else ""
                    provided_items.append(f"• {label}: {prov.value}{unit_str}")

            if provided_items:
                msg = (
                    "Here is the verified environmental information currently recorded for your farm:\n\n"
                    + "\n".join(provided_items)
                    + "\n\nAll other environmental variables remain unmeasured or not provided."
                )
            else:
                msg = "No environmental measurements have been recorded yet for your farm. You can share measurements such as soil organic carbon, rainfall, or land use."

            return ChatResponse(
                conversation_id=conv_id,
                turn_id=current_turn,
                role="assistant",
                message=msg,
                status="completed",
                environmental_context=cls._format_context_summary(context),
                detected_updates=[],
                confidence="high" if provided_items else "insufficient",
            )

        # ---------------------------------------------------------------------
        # Intent 1: Measurement Lookup / Missing Measurement (Bug 2 / Bug 6)
        # e.g., "What is my current soil moisture?", "What is my SOC?"
        # Measurement queries must not trigger recommendation generation or reuse old recommendations.
        # ---------------------------------------------------------------------
        is_measurement_query = bool(
            re.search(r"\b(?:what is|what's|tell me|check|do i have|how much)\s+(?:my\s+)?(?:current\s+)?(soil moisture|moisture|soc|soil organic carbon|rainfall|precipitation|soil ph|ph|land use)\b", user_lower)
            or ("soil moisture" in user_lower and any(w in user_lower for w in ["what", "current", "have", "?"]))
        )
        if is_measurement_query and not any(k in user_lower for k in ["what if", "suppose", "compare"]):
            # Check specifically for soil moisture query (Bug 2 / Condition 3: Rainfall != Soil Moisture)
            if "moisture" in user_lower:
                moist_prov = context.variables.get("soil_moisture")
                if moist_prov and moist_prov.value is not None and moist_prov.status != MetricStatus.UNKNOWN:
                    msg = f"Your current soil moisture is {moist_prov.value}{moist_prov.unit or '%' }."
                else:
                    # Bug 2: Exact required response if soil moisture is not present
                    msg = "Soil moisture has not been provided. If you have a measurement, share it and I can use it in the assessment."

                return ChatResponse(
                    conversation_id=conv_id,
                    turn_id=current_turn,
                    role="assistant",
                    message=msg,
                    status="completed",
                    environmental_context=cls._format_context_summary(context),
                    detected_updates=[],
                    confidence="insufficient",
                )

            # Other variable lookups
            for var_key, var_label in [
                ("soil_organic_carbon", "Soil Organic Carbon"),
                ("rainfall", "Annual rainfall"),
                ("soil_ph", "Soil pH"),
                ("land_use", "Land use"),
            ]:
                if var_key in user_lower or (var_key == "soil_organic_carbon" and "soc" in user_lower):
                    prov = context.variables.get(var_key)
                    if prov and prov.value is not None and prov.status != MetricStatus.UNKNOWN:
                        msg = f"Your current {var_label} is {prov.value}{prov.unit or ''}."
                    else:
                        msg = f"{var_label} has not been provided. If you have a measurement, share it and I can use it in the assessment."

                    return ChatResponse(
                        conversation_id=conv_id,
                        turn_id=current_turn,
                        role="assistant",
                        message=msg,
                        status="completed",
                        environmental_context=cls._format_context_summary(context),
                        detected_updates=[],
                        confidence="insufficient",
                    )

        # ---------------------------------------------------------------------
        # Intent 2: Unsupported Quantitative Question (Bug 7 / Bug 6)
        # e.g., "Tell me exactly how many species will increase if I improve SOC to 0.6%."
        # Must refuse exact quantification, explain needed empirical studies, and NOT repeat recommendations.
        # ---------------------------------------------------------------------
        is_species_quant = bool(
            re.search(r"\b(?:exact|precise)\s+(?:number|count|increase)\s+of\s+(?:species|taxa|organisms|earthworms|insects|birds|pollinators|plants)\b", user_lower)
            or re.search(r"(?:tell me |calculate |predict |give me |what is |what's )?(?:the )?(?:exact )?(?:how many|how much)\s+(?:species|taxa|organisms|earthworms|insects)\s+(?:that )?(?:will|would|can)?\s*(?:increase|grow|improve|appear|be added)", user_lower)
            or "how many species will increase" in user_lower
            or "exactly how many species" in user_lower
            or "exact number of species" in user_lower
            or "exact number of earthworms" in user_lower
        )
        if is_species_quant:
            # Extract any newly stated variables (e.g. SOC = 0.3%)
            extracted_vars, _, _ = EnvironmentalContextManager.extract_from_message(
                text=user_text,
                turn_id=current_turn,
                active_context=context,
            )
            updates = []
            if extracted_vars:
                context, updates = EnvironmentalContextManager.merge_context(
                    current_context=context,
                    new_variables=extracted_vars,
                    turn_id=current_turn,
                )

            msg = (
                "Exact species increase cannot be determined from the available evidence.\n\n"
                "While improving soil organic carbon (e.g., from 0.3% to 0.6%) enhances microbial biomass and subterranean biological activity, "
                "quantifying specific species richness gains requires localized taxonomic baseline surveys, eDNA metabarcoding, and site-specific field sampling. "
                "Authoritative scientific and technical sources support directional improvements in functional diversity, but exact species count predictions without local empirical calibration are scientifically unfounded."
            )
            return ChatResponse(
                conversation_id=conv_id,
                turn_id=current_turn,
                role="assistant",
                message=msg,
                status="completed",
                environmental_context=cls._format_context_summary(context),
                detected_updates=[u.model_dump() for u in updates],
                confidence="insufficient",
            )

        # ---------------------------------------------------------------------
        # Phase 5: Hypothetical What-If Scenario Detection (Bug 3)
        # Baseline context is preserved immutably (Scenario != Real-World Update)
        # ---------------------------------------------------------------------
        is_what_if = any(k in user_lower for k in [
            "what if", "suppose", "what happens if", "compare my",
            "assume rainfall", "assume soc", "assume temperature", "assume intercropping"
        ])
        if is_what_if:
            from app.scenarios.parser import ScenarioParser
            from app.scenarios.validator import ScenarioValidator
            from app.scenarios.state_builder import ScenarioStateBuilder
            from app.scenarios.analyzer import ScenarioAnalysisEngine

            # Preamble baseline extraction (Bug 3)
            preamble, _ = ScenarioParser.split_preamble_and_scenario(user_text)
            if preamble:
                preamble_vars = ScenarioParser.extract_baseline_declarations(preamble)
                if preamble_vars:
                    from app.conversation.schemas import VariableProvenance
                    now_iso = datetime.now(timezone.utc).isoformat()
                    new_provs = {}
                    for k, v in preamble_vars.items():
                        new_provs[k] = VariableProvenance(
                            variable=k,
                            value=v,
                            unit="%" if k in ("soil_organic_carbon", "soil_moisture") else ("mm" if k == "rainfall" else None),
                            source="user_statement",
                            turn_id=current_turn,
                            timestamp=now_iso,
                            status=MetricStatus.PROVIDED,
                        )
                    context, _ = EnvironmentalContextManager.merge_context(context, new_provs, current_turn)

            flat_env = EnvironmentalContextManager.get_flat_environmental_data(context)
            changes, needs_clarif, clarif_q = ScenarioParser.parse_query(user_text, flat_env)

            if needs_clarif:
                return ChatResponse(
                    conversation_id=conv_id,
                    turn_id=current_turn,
                    role="assistant",
                    message="\n".join(clarif_q),
                    status="clarification_needed",
                    clarification_questions=clarif_q,
                    environmental_context=cls._format_context_summary(context),
                    detected_updates=[],
                )

            is_valid, errs = ScenarioValidator.validate_changes(changes, flat_env)
            if not is_valid:
                return ChatResponse(
                    conversation_id=conv_id,
                    turn_id=current_turn,
                    role="assistant",
                    message=f"Scenario validation error: {'; '.join(errs)}",
                    status="error",
                    environmental_context=cls._format_context_summary(context),
                    detected_updates=[],
                )

            scen_state, assumptions = ScenarioStateBuilder.build_scenario_state(flat_env, changes)
            comparison = ScenarioAnalysisEngine.analyze_scenario(
                baseline=flat_env,
                scenario_state=scen_state,
                changes=changes,
                assumptions=assumptions,
                conversation_id=conv_id,
                db_session=db_session,
            )

            # Build conversational summary of scenario results
            summary_lines = [
                f"**What-If Scenario Analysis ({comparison.scenario_id}):**",
                f"• **Assumptions:** {', '.join(comparison.assumptions[:2])}",
                f"• **Multi-Metric Support:** {comparison.multi_metric_coverage}",
                "\n**Scenario Evaluation Matrix:**",
            ]
            for row in comparison.evaluation_matrix:
                summary_lines.append(f"- **{row.metric}**: {row.baseline} → {row.scenario} | Direction: *{row.direction.value}* (Confidence: {row.confidence.upper()})")

            if comparison.synergies:
                summary_lines.append("\n**Evidence-Grounded Synergies:**")
                for s in comparison.synergies:
                    summary_lines.append(f"• {s.rationale}")

            if comparison.tradeoffs:
                summary_lines.append("\n**Evidence-Grounded Trade-offs:**")
                for t in comparison.tradeoffs:
                    summary_lines.append(f"• {t.rationale}")
            elif comparison.tradeoff_summary:
                summary_lines.append(f"\n*(Trade-off Analysis: {comparison.tradeoff_summary})*")

            summary_lines.append(f"\n*(Baseline memory preserved: {', '.join(flat_env.keys())})*")

            return ChatResponse(
                conversation_id=conv_id,
                turn_id=current_turn,
                role="assistant",
                message="\n".join(summary_lines),
                status="completed",
                environmental_context=cls._format_context_summary(context),
                detected_updates=[],
                assessment={"scenario": comparison.model_dump()},
                confidence=comparison.confidence,
            )

        # ---------------------------------------------------------------------
        # Intent 3: Context Update / Clarification Response / Assessment
        # ---------------------------------------------------------------------
        # 2. Extract newly provided variables, explicit unknowns, and check ambiguous references
        extracted_vars, explicit_unknowns, ambiguity_q = EnvironmentalContextManager.extract_from_message(
            text=user_text,
            turn_id=current_turn,
            active_context=context,
        )

        # Handle Ambiguous Reference Resolution (Correction 3)
        if ambiguity_q:
            return ChatResponse(
                conversation_id=conv_id,
                turn_id=current_turn,
                role="assistant",
                message=ambiguity_q,
                status="clarification_needed",
                clarification_questions=[ambiguity_q],
                environmental_context=cls._format_context_summary(context),
                detected_updates=[],
            )

        # 3. Merge newly provided variables into persistent context
        context, updates = EnvironmentalContextManager.merge_context(
            current_context=context,
            new_variables=extracted_vars,
            turn_id=current_turn,
        )

        # 4. Consult Clarification Engine for topic-relevant missing variables
        candidate_questions = ClarificationEngine.generate_clarification_questions(
            user_message=user_text,
            active_context=context,
            max_questions=3,
        )

        # 5. Consult Memory Policy to decide whether to clarify or proceed to Phase 3
        should_clarify, policy_reason = MemoryPolicy.should_request_clarification(
            context=context,
            clarification_candidates=candidate_questions,
            max_depth=MemoryPolicy.DEFAULT_MAX_CLARIFICATION_DEPTH,
        )

        # Contextual note for rainfall (Condition 2 / Bug 5)
        # "Annual rainfall is 600 mm; whether this represents water stress depends on regional and seasonal context."
        contextual_rain_note = None
        if "rainfall" in extracted_vars and extracted_vars["rainfall"].value is not None:
            r_val = extracted_vars["rainfall"].value
            reg_prov = context.variables.get("region")
            reg_val = str(reg_prov.value if reg_prov and reg_prov.value else "").lower()
            is_arid = any(k in reg_val for k in ["arid", "semi-arid", "dryland"])
            try:
                r_num = float(r_val)
                if not is_arid and r_num >= 500.0:
                    clean_r = int(r_num) if r_num.is_integer() else r_num
                    contextual_rain_note = f"Annual rainfall is {clean_r} mm; whether this represents water stress depends on regional and seasonal context."
            except (ValueError, TypeError):
                pass

        # Case A: Clarification Needed
        if should_clarify and candidate_questions:
            context.clarification_depth += 1
            questions_list = [q.question for q in candidate_questions]

            # Formulate conversational assistant response explaining what is needed
            ack_prefix = ""
            if contextual_rain_note:
                ack_prefix = f"Recorded annual rainfall. {contextual_rain_note}\n\n"
            elif updates:
                update_items = [f"{u.variable.replace('_', ' ')} as {u.new_value}" for u in updates]
                ack_prefix = f"Recorded {', '.join(update_items)}.\n\n"
            elif "land_use" in extracted_vars and extracted_vars["land_use"].value is not None:
                ack_prefix = f"Recorded land use as {extracted_vars['land_use'].value}.\n\n"

            clarification_message = (
                f"{ack_prefix}To formulate a scientifically grounded multi-metric assessment for your land, I need a few additional details:\n\n"
                + "\n".join([f"• {q}" for q in questions_list])
            )

            return ChatResponse(
                conversation_id=conv_id,
                turn_id=current_turn,
                role="assistant",
                message=clarification_message,
                status="clarification_needed",
                clarification_questions=questions_list,
                environmental_context=cls._format_context_summary(context),
                detected_updates=[u.model_dump() for u in updates],
            )

        # Case B: Sufficient Information OR Clarification Depth Reached -> Invoke Phase 3
        # Flatten persistent context into typed variables (ignoring UNKNOWN / None)
        flat_env = EnvironmentalContextManager.get_flat_environmental_data(context)

        initial_state: EnvironmentalState = {
            "user_query": user_text,
            "conversation_history": [
                {"role": "user", "content": user_text, "turn_id": current_turn}
            ],
            "environmental_data": flat_env,
            "status": "ready",
        }

        # Invoke Phase 3 12-node reasoning pipeline
        try:
            final_state = app_graph.invoke(initial_state)
            phase3_response = final_state.get("final_response") or {}
        except Exception as exc:
            logger.error("Phase 3 pipeline failed during conversational turn: %s", exc, exc_info=True)
            return ChatResponse(
                conversation_id=conv_id,
                turn_id=current_turn,
                role="assistant",
                message=f"An error occurred during ecological analysis: {exc}",
                status="error",
                environmental_context=cls._format_context_summary(context),
            )

        p3_status = phase3_response.get("status", "completed")

        # Correction 1: If depth was reached but evidence is insufficient, Phase 3 validates this!
        if p3_status == "insufficient_evidence":
            assistant_text = (
                "Based on the available parameters, there is insufficient verified scientific evidence "
                "in the corpus to generate a confident, grounded recommendation without additional localized field data."
            )
            return ChatResponse(
                conversation_id=conv_id,
                turn_id=current_turn,
                role="assistant",
                message=assistant_text,
                status="insufficient_evidence",
                environmental_context=cls._format_context_summary(context),
                detected_updates=[u.model_dump() for u in updates],
                assessment=phase3_response.get("assessment"),
                confidence="insufficient",
            )

        # Synthesize conversational explanation of recommendations
        recs = phase3_response.get("recommendations") or []
        conf = phase3_response.get("confidence", "medium")
        compound = phase3_response.get("assessment", {}).get("compound_synthesis")

        message_parts = []
        if compound:
            message_parts.append(compound)

        if recs:
            message_parts.append("\n**Key Evidence-Grounded Recommendations:**")
            for i, r in enumerate(recs[:2], start=1):
                message_parts.append(f"{i}. **{r['action']}**")
                if r.get("why"):
                    message_parts.append(f"   • *Rationale:* {r['why'][0]}")
                if r.get("expected_effect", {}).get("description"):
                    message_parts.append(f"   • *Expected Impact:* {r['expected_effect']['description']}")

        if updates:
            update_notes = ", ".join([f"{u.variable}: {u.old_value} → {u.new_value}" for u in updates])
            message_parts.append(f"\n*(Updated in this turn: {update_notes})*")

        assistant_msg = "\n".join(message_parts) if message_parts else "Environmental assessment completed."

        return ChatResponse(
            conversation_id=conv_id,
            turn_id=current_turn,
            role="assistant",
            message=assistant_msg,
            status="completed",
            environmental_context=cls._format_context_summary(context),
            detected_updates=[u.model_dump() for u in updates],
            assessment=phase3_response,
            confidence=conf,
        )

    @classmethod
    def _format_context_summary(cls, context: EnvironmentalContextModel) -> Dict[str, Any]:
        """Formats the persistent context for API output and frontend display."""
        summary = {}
        for var_name, prov in context.variables.items():
            summary[var_name] = {
                "value": prov.value,
                "unit": prov.unit,
                "source": prov.source,
                "turn_id": prov.turn_id,
                "status": prov.status.value,
                "timestamp": prov.timestamp,
            }
        return summary
