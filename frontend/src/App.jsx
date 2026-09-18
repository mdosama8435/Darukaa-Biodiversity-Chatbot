import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import ContextPanel from './components/ContextPanel';
import ScenarioView from './components/ScenarioView';
import AssessmentView from './components/AssessmentView';
import EvidenceView from './components/EvidenceView';
import SystemView from './components/SystemView';
import {
  getHealth,
  sendChatMessage,
  resetConversation,
  deleteConversation,
  analyzeScenario,
  runAssessment,
} from './services/api';
import {
  loadSavedConversations,
  saveAllConversations,
  getStoredActiveConversationId,
  setStoredActiveConversationId,
  createNewConversationRecord,
  deriveConversationTitle,
} from './services/conversationStore';

export default function App() {
  // Navigation State (Chat is default per Step 3 & 19)
  const [activeTab, setActiveTab] = useState('chat');

  // Dynamic API Health State
  const [health, setHealth] = useState(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);

  // UI Drawer & Responsive State
  const [isContextOpen, setIsContextOpen] = useState(true);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Persistent Conversation Sessions
  const [conversations, setConversations] = useState(() => {
    const loaded = loadSavedConversations();
    if (loaded.length > 0) return loaded;
    const initial = createNewConversationRecord();
    saveAllConversations([initial]);
    return [initial];
  });

  const [activeConversationId, setActiveConversationId] = useState(() => {
    const storedId = getStoredActiveConversationId();
    const loaded = loadSavedConversations();
    if (storedId && loaded.some((c) => c.id === storedId)) {
      return storedId;
    }
    return loaded.length > 0 ? loaded[0].id : null;
  });

  // Active conversation object
  const activeConversation =
    conversations.find((c) => c.id === activeConversationId) ||
    conversations[0] ||
    createNewConversationRecord();

  // Chat Execution State
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);

  // Scenario Analysis State
  const [scenarioResult, setScenarioResult] = useState(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenarioError, setScenarioError] = useState(null);

  // Direct Assessment State
  const [assessmentResult, setAssessmentResult] = useState(null);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState(null);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    if (conversations.length > 0) {
      saveAllConversations(conversations);
    }
  }, [conversations]);

  // Keep active conversation ID synced in storage
  useEffect(() => {
    if (activeConversationId) {
      setStoredActiveConversationId(activeConversationId);
    }
  }, [activeConversationId]);

  // Live Health Verification
  const verifyBackendHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    try {
      const data = await getHealth();
      setHealth(data);
    } catch {
      setHealth({ status: 'offline' });
    } finally {
      setIsCheckingHealth(false);
    }
  }, []);

  useEffect(() => {
    verifyBackendHealth();
    const interval = setInterval(verifyBackendHealth, 30000);
    return () => clearInterval(interval);
  }, [verifyBackendHealth]);

  // Create a brand new conversation
  const handleNewConversation = () => {
    const newConv = createNewConversationRecord();
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
    setChatError(null);
    setChatLoading(false);
  };

  // Select an existing conversation
  const handleSelectConversation = (id) => {
    if (id === activeConversationId) return;
    setActiveConversationId(id);
    setChatError(null);
  };

  // Delete a conversation
  const handleDeleteConversation = async (id) => {
    try {
      await deleteConversation(id);
    } catch {
      // Best-effort backend cleanup
    }

    setConversations((prev) => {
      const updated = prev.filter((c) => c.id !== id);
      if (updated.length === 0) {
        const fresh = createNewConversationRecord();
        setActiveConversationId(fresh.id);
        return [fresh];
      }
      if (activeConversationId === id) {
        setActiveConversationId(updated[0].id);
      }
      return updated;
    });
  };

  // Conversational Message Handler
  const handleSendMessage = async (text) => {
    if (!text || !text.trim() || chatLoading) return;
    const query = text.trim();

    const currentTurn = (activeConversation.messages?.length || 0) + 1;
    const userMsg = {
      role: 'user',
      content: query,
      turn_id: currentTurn,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    // Calculate updated title if needed
    const currentTitle = activeConversation.title;
    const updatedTitle =
      !currentTitle || currentTitle === 'New Conversation'
        ? deriveConversationTitle(query)
        : currentTitle;

    // Optimistically update messages
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === activeConversation.id) {
          return {
            ...c,
            title: updatedTitle,
            updatedAt: new Date().toISOString(),
            messages: [...c.messages, userMsg],
          };
        }
        return c;
      })
    );

    setChatLoading(true);
    setChatError(null);

    try {
      const data = await sendChatMessage({
        conversationId: activeConversation.id,
        message: query,
      });

      const assistantMsg = {
        role: 'assistant',
        content: data.message,
        turn_id: data.turn_id,
        status: data.status,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        clarification_questions: data.clarification_questions || [],
        assessment: data.assessment,
        confidence: data.confidence,
      };

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === activeConversation.id) {
            return {
              ...c,
              updatedAt: new Date().toISOString(),
              messages: [...c.messages, assistantMsg],
              activeContext: data.environmental_context || c.activeContext || {},
              detectedUpdates: data.detected_updates || c.detectedUpdates || [],
              activeAssessment: data.assessment || c.activeAssessment || null,
              latestClarificationQuestions:
                data.clarification_questions || c.latestClarificationQuestions || [],
            };
          }
          return c;
        })
      );
    } catch (err) {
      setChatError(err.message || 'Error communicating with environmental intelligence service.');
    } finally {
      setChatLoading(false);
    }
  };

  // Run What-If Scenario
  const handleRunScenario = async (query, baseline) => {
    if (!query || !query.trim()) return;
    setScenarioLoading(true);
    setScenarioError(null);

    try {
      const data = await analyzeScenario({
        conversationId: activeConversation.id,
        query: query.trim(),
        baseline,
      });
      setScenarioResult(data);
    } catch (err) {
      setScenarioError(err.message || 'Scenario engine failed to analyze simulation.');
      setScenarioResult(null);
    } finally {
      setScenarioLoading(false);
    }
  };

  // Run Direct Parameter Assessment
  const handleRunAssessment = async (payload) => {
    setAssessmentLoading(true);
    setAssessmentError(null);

    try {
      const data = await runAssessment(payload);
      setAssessmentResult(data);
    } catch (err) {
      setAssessmentError(err.message || 'Direct assessment processing error.');
      setAssessmentResult(null);
    } finally {
      setAssessmentLoading(false);
    }
  };

  // Count active variables in current conversation
  const currentContextVarsCount = Object.values(activeConversation.activeContext || {}).filter(
    (prov) => prov && prov.value !== null && prov.value !== undefined
  ).length;

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 selection:bg-emerald-500/20 selection:text-emerald-300 font-sans overflow-hidden">
      {/* SIDEBAR (Desktop & Mobile Drawer) */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        conversations={conversations}
        activeConversationId={activeConversation.id}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onSendDemoTurn={handleSendMessage}
        chatLoading={chatLoading}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* MAIN WORKSPACE */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* COMPACT TOP BAR */}
        <Header
          health={health}
          isCheckingHealth={isCheckingHealth}
          onRefreshHealth={verifyBackendHealth}
          contextCount={currentContextVarsCount}
          isContextOpen={isContextOpen}
          onToggleContext={() => setIsContextOpen(!isContextOpen)}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen(true)}
        />

        {/* WORKSPACE CONTENT AREA */}
        <div className="flex-1 flex min-h-0 overflow-hidden relative">
          {/* Active View Container */}
          <main className="flex-1 flex flex-col min-w-0 overflow-y-auto px-3 sm:px-6 py-4">
            {activeTab === 'chat' && (
              <ChatView
                chatMessages={activeConversation.messages || []}
                chatLoading={chatLoading}
                chatError={chatError}
                activeContext={activeConversation.activeContext || {}}
                activeAssessment={activeConversation.activeAssessment}
                latestClarificationQuestions={activeConversation.latestClarificationQuestions || []}
                onSendMessage={handleSendMessage}
                onViewEvidence={() => setActiveTab('evidence')}
                onRetry={() => {
                  const lastUser = [...(activeConversation.messages || [])]
                    .reverse()
                    .find((m) => m.role === 'user');
                  if (lastUser) handleSendMessage(lastUser.content);
                }}
              />
            )}

            {activeTab === 'scenarios' && (
              <ScenarioView
                activeContext={activeConversation.activeContext || {}}
                scenarioResult={scenarioResult}
                scenarioLoading={scenarioLoading}
                scenarioError={scenarioError}
                onRunScenario={handleRunScenario}
              />
            )}

            {activeTab === 'assessment' && (
              <AssessmentView
                onRunAssessment={handleRunAssessment}
                loading={assessmentLoading}
                error={assessmentError}
                result={assessmentResult}
              />
            )}

            {activeTab === 'evidence' && <EvidenceView />}

            {activeTab === 'system' && (
              <SystemView
                healthStatus={health}
                onRefreshHealth={verifyBackendHealth}
              />
            )}
          </main>

          {/* SECONDARY ENVIRONMENTAL CONTEXT PANEL (Drawer / Collapsible) */}
          {activeTab === 'chat' && isContextOpen && (
            <aside className="w-80 border-l border-slate-800/80 bg-slate-900/60 p-3 shrink-0 hidden lg:flex flex-col h-full animate-fadeIn">
              <ContextPanel
                activeContext={activeConversation.activeContext || {}}
                detectedUpdates={activeConversation.detectedUpdates || []}
                onClose={() => setIsContextOpen(false)}
              />
            </aside>
          )}
        </div>

        {/* COMPACT FOOTER */}
        <footer className="border-t border-slate-800/60 bg-slate-950/80 py-2.5 px-6 text-center text-[11px] font-mono text-slate-500 shrink-0">
          Darukaa.Earth • AI Biodiversity Intelligence • Authoritative Scientific Sources
        </footer>
      </div>
    </div>
  );
}
