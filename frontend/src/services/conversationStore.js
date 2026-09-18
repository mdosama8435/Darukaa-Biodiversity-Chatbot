/**
 * Darukaa.Earth Client-Side Conversation Persistence & Synchronization Store
 * Guarantees persistent multi-session conversation history, message restore,
 * environmental context preservation, and seamless conversation switching
 * without state leakage.
 */

const STORAGE_KEY = 'darukaa_conversations_v2';
const ACTIVE_CONV_KEY = 'darukaa_active_conversation_id';

export function deriveConversationTitle(query, existingTitle = null) {
  if (existingTitle && existingTitle !== 'New Conversation' && !existingTitle.startsWith('Conversation')) {
    return existingTitle;
  }
  if (!query || typeof query !== 'string') return 'New Conversation';

  const lower = query.toLowerCase();
  if (lower.includes('biodiversity')) return 'Biodiversity Assessment';
  if (lower.includes('wheat')) return 'Wheat Farm Analysis';
  if (lower.includes('rainfall') || lower.includes('rain')) return 'Rainfall & Hydrology';
  if (lower.includes('soil organic carbon') || lower.includes('soc')) return 'Soil Carbon Evaluation';
  if (lower.includes('intercrop') || lower.includes('intercropping')) return 'Intercropping Scenario';
  if (lower.includes('maize')) return 'Crop Transition: Maize';
  if (lower.includes('ph')) return 'Soil pH & Acidity';
  if (lower.includes('drought')) return 'Drought Stress Analysis';

  // Fallback: clean snippet of first message
  const cleaned = query.replace(/[^\w\s]/gi, '').trim();
  const words = cleaned.split(/\s+/).slice(0, 4).join(' ');
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : 'Environmental Inquiry';
}

export function loadSavedConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.warn('Failed to parse saved conversations from storage:', err);
    return [];
  }
}

export function saveAllConversations(conversations) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch (err) {
    console.warn('Failed to save conversations to storage:', err);
  }
}

export function getStoredActiveConversationId() {
  try {
    return localStorage.getItem(ACTIVE_CONV_KEY);
  } catch {
    return null;
  }
}

export function setStoredActiveConversationId(id) {
  try {
    if (id) {
      localStorage.setItem(ACTIVE_CONV_KEY, id);
    } else {
      localStorage.removeItem(ACTIVE_CONV_KEY);
    }
  } catch {
    // Ignore storage errors
  }
}

export function createNewConversationRecord(customId = null) {
  const id = customId || `conv_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
  return {
    id,
    title: 'New Conversation',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    messages: [
      {
        role: 'assistant',
        content:
          'Welcome to Darukaa.Earth Environmental Intelligence. Describe your land, soil, climate, farming system, or biodiversity concern. Darukaa connects environmental variables with evidence from authoritative scientific sources.',
        turn_id: 0,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        status: 'success',
        clarification_questions: [],
      },
    ],
    activeContext: {},
    detectedUpdates: [],
    activeAssessment: null,
    latestClarificationQuestions: [],
  };
}

export function formatRelativeTime(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}
