/**
 * Darukaa.Earth API Client
 * Strictly interfaces with backend endpoints:
 * - POST /api/v1/chat
 * - POST /api/v1/scenarios/analyze
 * - POST /api/v1/assessment
 * - POST /api/v1/knowledge/search
 * - GET  /api/v1/health
 * 
 * Never hardcodes or fabricates scientific data.
 */

const API_BASE = '/api/v1';

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
    if (!res.ok) {
      return { status: 'offline', error: `HTTP ${res.status}: ${res.statusText}` };
    }
    const data = await res.json();
    return { status: 'ok', data };
  } catch (err) {
    return { status: 'offline', error: err.message || 'Network unreachable' };
  }
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
  if (!res.ok) {
    throw new Error(`Health check failed (HTTP ${res.status})`);
  }
  return await res.json();
}

export async function sendChatMessage({ conversationId, message, userId = null }) {
  const payload = {
    conversation_id: conversationId,
    message: message.trim(),
  };
  if (userId) payload.user_id = userId;

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `Chat service error (HTTP ${res.status})`);
  }
  return data;
}

export async function resetConversation(conversationId) {
  try {
    const res = await fetch(`${API_BASE}/chat/conversations/${encodeURIComponent(conversationId)}`, {
      method: 'DELETE',
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function deleteConversation(conversationId) {
  const res = await fetch(`${API_BASE}/chat/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE',
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Failed to delete conversation (HTTP ${res.status})`);
  }
  return data;
}

export async function listConversations(userId = null) {
  const url = userId ? `${API_BASE}/chat/conversations?user_id=${encodeURIComponent(userId)}` : `${API_BASE}/chat/conversations`;
  const res = await fetch(url, { method: 'GET' });
  if (!res.ok) {
    throw new Error(`Failed to list conversations (HTTP ${res.status})`);
  }
  return await res.json();
}

export async function getConversationContext(conversationId) {
  const res = await fetch(`${API_BASE}/chat/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'GET',
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch conversation context (HTTP ${res.status})`);
  }
  return await res.json();
}

export async function analyzeScenario({ conversationId, query, baseline, changes = [], assumptions = [] }) {
  const payload = {};
  if (conversationId) payload.conversation_id = conversationId;
  if (query) payload.query = query.trim();
  if (baseline && Object.keys(baseline).length > 0) payload.baseline = baseline;
  if (changes && changes.length > 0) payload.changes = changes;
  if (assumptions && assumptions.length > 0) payload.assumptions = assumptions;

  const res = await fetch(`${API_BASE}/scenarios/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `Scenario engine error (HTTP ${res.status})`);
  }
  return data;
}

export async function runAssessment(payload) {
  const res = await fetch(`${API_BASE}/assessment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `Assessment engine error (HTTP ${res.status})`);
  }
  return data;
}

export async function searchKnowledge({ query, top_k = 5, min_similarity = 0.25 }) {
  const res = await fetch(`${API_BASE}/knowledge/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query.trim(),
      top_k,
      min_similarity,
    }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `Knowledge search error (HTTP ${res.status})`);
  }
  return data;
}
