import React, { useState } from 'react';
import {
  MessageSquare,
  Sliders,
  Compass,
  FileText,
  Settings,
  Plus,
  Trash2,
  Sparkles,
  ChevronDown,
  ChevronRight,
  ArrowRight,
  Clock,
  X,
} from 'lucide-react';
import { formatRelativeTime } from '../services/conversationStore';

export default function Sidebar({
  activeTab,
  onSelectTab,
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onSendDemoTurn,
  chatLoading,
  isMobileOpen = false,
  onCloseMobile,
}) {
  const [isDemoOpen, setIsDemoOpen] = useState(false);

  const navItems = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'scenarios', label: 'Scenario Analysis', icon: Sliders, badge: 'What-If' },
    { id: 'assessment', label: 'Assessment', icon: Compass },
    { id: 'evidence', label: 'Scientific Evidence', icon: FileText },
    { id: 'system', label: 'System', icon: Settings },
  ];

  const demoTurns = [
    { num: 1, label: 'Biodiversity decline', query: 'My farm has declining biodiversity.' },
    { num: 2, label: 'Continuous wheat', query: 'I grow wheat continuously.' },
    { num: 3, label: 'Rainfall 600 mm', query: 'Annual rainfall is around 600 mm.' },
    { num: 4, label: 'SOC 0.3%', query: 'My soil organic carbon is 0.3%.' },
    { num: 5, label: 'Override: wheat → maize', query: 'Actually, I switched from wheat to maize this year.' },
  ];

  const sidebarContent = (
    <aside className="w-64 bg-slate-900/95 border-r border-slate-800/80 flex flex-col h-full shrink-0 select-none text-slate-300">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm shadow-xs">
            🌱
          </div>
          <div>
            <div className="font-bold text-sm tracking-tight text-white flex items-center space-x-1.5">
              <span>Darukaa.Earth</span>
            </div>
            <div className="text-[10px] font-mono text-emerald-400">
              Biodiversity Intelligence
            </div>
          </div>
        </div>

        {/* Mobile close button */}
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="p-1 rounded-md text-slate-400 hover:text-white md:hidden"
            aria-label="Close Sidebar"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* New Conversation Button */}
      <div className="p-3 border-b border-slate-800/60">
        <button
          onClick={() => {
            onNewConversation();
            if (activeTab !== 'chat') onSelectTab('chat');
            if (onCloseMobile) onCloseMobile();
          }}
          className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white text-xs font-medium transition-all shadow-xs"
        >
          <Plus className="w-4 h-4" />
          <span>New Conversation</span>
        </button>
      </div>

      {/* Scrollable Center: Recent Conversations */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Recent Conversations Section */}
        <div>
          <div className="px-2 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500 flex items-center justify-between">
            <span>Recent Conversations</span>
            <Clock className="w-3 h-3 text-slate-500" />
          </div>

          <div className="mt-1 space-y-0.5">
            {conversations.length === 0 ? (
              <div className="px-3 py-3 text-center text-xs text-slate-500 font-serif italic">
                No previous conversations yet.
              </div>
            ) : (
              conversations.map((conv) => {
                const isActive = conv.id === activeConversationId && activeTab === 'chat';
                const timeLabel = formatRelativeTime(conv.updatedAt || conv.createdAt);

                return (
                  <div
                    key={conv.id}
                    className={`group flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition-all cursor-pointer ${
                      isActive
                        ? 'bg-slate-800 text-white font-medium border border-slate-700/80 shadow-xs'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`}
                    onClick={() => {
                      onSelectConversation(conv.id);
                      if (activeTab !== 'chat') onSelectTab('chat');
                      if (onCloseMobile) onCloseMobile();
                    }}
                  >
                    <div className="truncate flex-1 mr-2">
                      <div className="truncate text-slate-200 group-hover:text-white">
                        {conv.title || 'Conversation'}
                      </div>
                      {timeLabel && (
                        <div className="text-[10px] font-mono text-slate-500">
                          {timeLabel}
                        </div>
                      )}
                    </div>

                    {/* Delete button (visible on hover or active) */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-700/80 text-slate-400 hover:text-rose-400 transition-opacity"
                      title="Delete conversation"
                      aria-label="Delete conversation"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Workspace Navigation Section */}
        <div>
          <div className="px-2 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500">
            Workspace
          </div>
          <div className="mt-1 space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onSelectTab(item.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold shadow-xs'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-500'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded font-semibold ${
                        isActive ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Collapsible Evaluator Demo Flow Footer */}
      <div className="border-t border-slate-800/80 bg-slate-950/60 p-2.5">
        <button
          onClick={() => setIsDemoOpen(!isDemoOpen)}
          className="w-full flex items-center justify-between px-2 py-1.5 rounded-md text-[11px] font-mono text-slate-400 hover:text-emerald-300 hover:bg-slate-800/50 transition-colors"
        >
          <div className="flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>Evaluator Demo Flow</span>
          </div>
          {isDemoOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>

        {isDemoOpen && (
          <div className="mt-1.5 space-y-1 pt-1 border-t border-slate-800/60 animate-fadeIn">
            {demoTurns.map((turn) => (
              <button
                key={turn.num}
                onClick={() => {
                  onSelectTab('chat');
                  onSendDemoTurn(turn.query);
                  if (onCloseMobile) onCloseMobile();
                }}
                disabled={chatLoading}
                className="w-full text-left px-2 py-1 rounded text-[10px] font-mono text-slate-400 hover:text-emerald-300 hover:bg-slate-800/70 transition-all flex items-center justify-between group disabled:opacity-50"
              >
                <div className="truncate">
                  <span className="text-emerald-400 font-bold mr-1">#{turn.num}</span>
                  <span>{turn.label}</span>
                </div>
                <ArrowRight className="w-3 h-3 text-slate-600 group-hover:text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-1" />
              </button>
            ))}
          </div>
        )}
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <div className="hidden md:flex h-screen sticky top-0 shrink-0">
        {sidebarContent}
      </div>

      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs md:hidden"
          onClick={onCloseMobile}
        >
          <div
            className="w-64 h-full bg-slate-900"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
