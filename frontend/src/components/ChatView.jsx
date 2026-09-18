import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Sparkles,
  HelpCircle,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Layers,
  ShieldCheck,
  Clock,
  ArrowRight,
} from 'lucide-react';

export default function ChatView({
  chatMessages = [],
  chatLoading = false,
  chatError = null,
  activeContext = {},
  activeAssessment = null,
  latestClarificationQuestions = [],
  onSendMessage,
  onViewEvidence = null,
  onRetry = null,
}) {
  const [inputText, setInputText] = useState('');
  const [expandedAnalysis, setExpandedAnalysis] = useState({});
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to bottom of chat on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, chatLoading]);

  // Handle send message
  const handleSend = () => {
    if (!inputText.trim() || chatLoading) return;
    onSendMessage(inputText.trim());
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  // Keyboard navigation: Enter = send (without Shift), Shift+Enter = newline
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Handle textarea auto-resize
  const handleInputChange = (e) => {
    setInputText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  // Quick prompt chips for welcome state
  const welcomePrompts = [
    'My biodiversity is declining',
    'Analyze my wheat farm',
    'Rainfall has decreased in my region',
    'My soil organic carbon is 0.3%',
    'What if I switch to intercropping?',
  ];

  // Count active variables
  const providedVars = Object.keys(activeContext).filter(
    (k) => activeContext[k] && activeContext[k].value !== null && activeContext[k].value !== undefined
  );

  const hasMultipleVariables = providedVars.length >= 3;
  const isWelcomeState = chatMessages.length <= 1;

  const toggleAnalysis = (idx) => {
    setExpandedAnalysis((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto w-full">
      {/* Message Scroll Area */}
      <div className="flex-1 overflow-y-auto px-2 sm:px-4 py-4 space-y-5">
        {/* Welcome State when conversation has no user turns */}
        {isWelcomeState ? (
          <div className="py-8 sm:py-14 text-center max-w-2xl mx-auto space-y-6 animate-fadeIn">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-3xl mx-auto shadow-sm">
              🌱
            </div>

            <div className="space-y-2">
              <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Understand your environment
              </h2>
              <p className="text-sm text-slate-400 leading-relaxed max-w-lg mx-auto">
                Describe your land, soil, climate, farming system, or biodiversity concern.
                Darukaa connects environmental variables with evidence from authoritative scientific sources.
              </p>
            </div>

            {/* Interactive Prompt Chips */}
            <div className="pt-2 space-y-2">
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold">
                Try asking:
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {welcomePrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSendMessage(prompt)}
                    className="px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-emerald-300 border border-slate-800 hover:border-emerald-500/40 text-xs sm:text-[13px] font-medium transition-all shadow-xs text-left"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          chatMessages.map((msg, idx) => {
            const isUser = msg.role === 'user';
            const isClarification = msg.status === 'clarification_needed';
            const assessment = msg.assessment || (idx === chatMessages.length - 1 ? activeAssessment : null);
            const recommendations = assessment?.recommendations || [];
            const evidence = assessment?.evidence || [];
            const compoundSynthesis = assessment?.compound_synthesis;
            const activeRelationships = assessment?.active_relationships || [];

            return (
              <div
                key={idx}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1.5`}
              >
                {/* Sender Metadata */}
                <div className="text-[10px] font-mono text-slate-500 px-1 flex items-center space-x-1.5">
                  <span className="font-semibold text-slate-400">
                    {isUser ? 'You' : 'Darukaa AI'}
                  </span>
                  <span>•</span>
                  <span>{msg.timestamp || `Turn ${msg.turn_id}`}</span>
                </div>

                {/* Message Bubble */}
                <div
                  className={`rounded-2xl px-4 py-3 text-xs sm:text-[13.5px] leading-relaxed max-w-[92%] sm:max-w-[85%] ${
                    isUser
                      ? 'bg-emerald-600 text-white rounded-br-none shadow-xs font-sans'
                      : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none shadow-xs'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {/* Clarification Questions (Level 2) */}
                  {!isUser && msg.clarification_questions && msg.clarification_questions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
                      <div className="text-[11px] font-mono text-amber-400 font-semibold flex items-center space-x-1.5 uppercase">
                        <HelpCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <span>Clarification Needed:</span>
                      </div>
                      <div className="flex flex-col gap-1.5">
                        {msg.clarification_questions.map((q, qIdx) => (
                          <button
                            key={qIdx}
                            onClick={() => onSendMessage(q.split('(')[0].trim())}
                            className="text-left text-xs text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 px-3 py-2 rounded-lg border border-amber-500/20 transition-colors flex items-start space-x-2"
                          >
                            <span className="text-amber-400 font-bold">•</span>
                            <span>{q}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Multi-Metric Reasoning (Level 5 - Progressive Disclosure) */}
                  {!isUser && (compoundSynthesis || activeRelationships.length > 0) && (
                    <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2 font-sans">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-1.5 text-xs font-mono font-bold text-emerald-400 uppercase">
                          <Layers className="w-3.5 h-3.5" />
                          <span>Multi-Metric Analysis</span>
                        </div>
                        <button
                          onClick={() => toggleAnalysis(idx)}
                          className="text-[10px] font-mono text-slate-400 hover:text-slate-200 flex items-center space-x-1"
                        >
                          <span>{expandedAnalysis[idx] ? 'Hide details' : 'View analysis'}</span>
                          {expandedAnalysis[idx] ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : (
                            <ChevronDown className="w-3 h-3" />
                          )}
                        </button>
                      </div>

                      {/* Interaction Summary Flow */}
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1.5 text-xs font-mono">
                        <div className="flex items-center justify-between text-slate-300">
                          <span className="font-semibold text-emerald-300">
                            Soil Organic Carbon ↕ Rainfall ↕ Land Use
                          </span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                            Interaction Detected
                          </span>
                        </div>
                        {compoundSynthesis && (
                          <p className="text-[12px] font-serif text-slate-300 leading-relaxed pt-1">
                            {compoundSynthesis}
                          </p>
                        )}
                      </div>

                      {/* Expanded Analysis Details */}
                      {expandedAnalysis[idx] && (
                        <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-xs space-y-2 animate-fadeIn font-mono">
                          <div className="text-[11px] text-slate-400 font-semibold uppercase">
                            Active Relationships ({activeRelationships.length}):
                          </div>
                          {activeRelationships.map((rel, rIdx) => (
                            <div key={rIdx} className="p-2 rounded bg-slate-900 border border-slate-800 space-y-1">
                              <div className="font-bold text-slate-200">
                                {rel.name || rel.relationship_id}
                              </div>
                              <div className="text-slate-400 text-[11px] font-serif">
                                {rel.mechanism}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Recommendations (Level 4 - Progressive Disclosure) */}
                  {!isUser && recommendations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-3 font-sans">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-1.5 text-xs font-mono font-bold text-emerald-400 uppercase">
                          <ShieldCheck className="w-4 h-4" />
                          <span>Recommendation</span>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold uppercase">
                          Confidence: {msg.confidence || 'Medium'}
                        </span>
                      </div>

                      {recommendations.map((rec, rIdx) => (
                        <div
                          key={rIdx}
                          className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs"
                        >
                          <div className="font-bold text-slate-100 text-[13px]">
                            {rec.action}
                          </div>

                          {rec.why && rec.why.length > 0 && (
                            <div className="space-y-0.5">
                              <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold">
                                Why:
                              </span>
                              <p className="text-slate-300 font-serif text-xs leading-relaxed">
                                {rec.why[0]}
                              </p>
                            </div>
                          )}

                          {rec.impacted_metrics && rec.impacted_metrics.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5 pt-1">
                              <span className="text-[10px] font-mono text-slate-400">Impacted:</span>
                              {rec.impacted_metrics.map((m) => (
                                <span
                                  key={m}
                                  className="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-emerald-300"
                                >
                                  {m.replace(/_/g, ' ')}
                                </span>
                              ))}
                            </div>
                          )}

                          {rec.time_horizon && (
                            <div className="text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-800/60 flex items-center space-x-2">
                              <Clock className="w-3 h-3 text-slate-500" />
                              <span>Horizon:</span>
                              <span className="text-slate-300">
                                {rec.time_horizon.short_term ? 'Short-term' : 'Medium-term'}
                              </span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Compact Evidence References (Level 6) */}
                  {!isUser && evidence.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-slate-400">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-semibold text-slate-300">Evidence:</span>
                        {evidence.slice(0, 3).map((item, eIdx) => (
                          <span
                            key={eIdx}
                            className="px-1.5 py-0.2 rounded bg-slate-950 border border-slate-800 text-slate-300 text-[10px]"
                          >
                            {item.source_organization || item.source || 'Authoritative Source'}
                            {item.publication_year ? ` · ${item.publication_year}` : ''}
                          </span>
                        ))}
                      </div>

                      {onViewEvidence && (
                        <button
                          onClick={onViewEvidence}
                          className="text-emerald-400 hover:text-emerald-300 flex items-center space-x-1 transition-colors"
                        >
                          <span>View evidence</span>
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Polished Loading State (Step 23: Accurate, not fake progress) */}
        {chatLoading && (
          <div className="flex items-center space-x-2.5 p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono text-emerald-400 max-w-sm animate-fadeIn shadow-xs">
            <RefreshCw className="w-4 h-4 animate-spin shrink-0 text-emerald-400" />
            <span>Analyzing environmental context...</span>
          </div>
        )}

        {/* User-Friendly Error State (Step 24: No raw python stack traces) */}
        {chatError && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-start justify-between space-x-3 max-w-md animate-fadeIn">
            <div className="flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
              <div>
                <div className="font-semibold text-rose-200">Request Error</div>
                <div className="font-serif mt-0.5 text-[11px] text-rose-300/90">
                  {chatError.length > 120
                    ? 'Something went wrong while analyzing your environmental request. Please check connectivity or try again.'
                    : chatError}
                </div>
              </div>
            </div>
            {onRetry && (
              <button
                onClick={onRetry}
                className="px-2 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-mono shrink-0 transition-colors"
              >
                Try again
              </button>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Prominent Bottom Composer (Step 5) */}
      <div className="p-3 sm:p-4 border-t border-slate-800/80 bg-slate-950/90 backdrop-blur-md">
        <div className="relative flex items-end bg-slate-900 border border-slate-800 focus-within:border-emerald-500/50 rounded-2xl shadow-xs transition-colors p-1.5">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={chatLoading}
            placeholder="Tell me about your land or environmental concern..."
            className="flex-1 bg-transparent px-3 py-2 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none max-h-36 leading-relaxed disabled:opacity-50"
          />

          <button
            onClick={handleSend}
            disabled={chatLoading || !inputText.trim()}
            className="p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium transition-all shrink-0 ml-1 shadow-xs"
            aria-label="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        <div className="mt-1.5 px-2 flex items-center justify-between text-[10px] font-mono text-slate-500">
          <span>Press Enter to send, Shift+Enter for new line</span>
          {providedVars.length > 0 && (
            <span className="text-emerald-400">
              {providedVars.length} variables in context
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
