"""API route tests for multi-turn conversational chat (/api/v1/chat)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestChatEndpoints:
    """Tests for conversational chat API."""

    def test_turn_1_triggers_targeted_clarification(self):
        """Turn 1 with vague inquiry triggers clarification questions."""
        payload = {
            "conversation_id": "test_conv_api_1",
            "message": "My biodiversity has been declining.",
        }
        res = client.post("/api/v1/chat", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["conversation_id"] == "test_conv_api_1"
        assert data["status"] == "clarification_needed"
        assert len(data["clarification_questions"]) >= 1
        assert "land use" in data["message"].lower() or "rainfall" in data["message"].lower()

    def test_conversations_listing_and_context_inspection(self):
        """Tests GET /conversations and GET /conversations/{id}."""
        # Create a conversation with state
        payload = {
            "conversation_id": "test_conv_inspect",
            "message": "Rainfall is 600 mm and land use is wheat monoculture.",
        }
        client.post("/api/v1/chat", json=payload)

        # 1. List conversations
        list_res = client.get("/api/v1/chat/conversations")
        assert list_res.status_code == 200
        sessions = list_res.json()
        assert any(s["conversation_id"] == "test_conv_inspect" for s in sessions)

        # 2. Get specific conversation context
        ctx_res = client.get("/api/v1/chat/conversations/test_conv_inspect")
        assert ctx_res.status_code == 200
        ctx_data = ctx_res.json()
        assert ctx_data["conversation_id"] == "test_conv_inspect"
        env_ctx = ctx_data["environmental_context"]
        assert "rainfall" in env_ctx
        assert env_ctx["rainfall"]["value"] == 600.0

        # 3. Delete conversation session
        del_res = client.delete("/api/v1/chat/conversations/test_conv_inspect")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"
