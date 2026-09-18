import React from 'react';
import { Sprout, RefreshCw, PanelRightOpen, PanelRightClose, Menu } from 'lucide-react';

export default function Header({
  health,
  isCheckingHealth,
  onRefreshHealth,
  contextCount = 0,
  isContextOpen,
  onToggleContext,
  onToggleMobileSidebar,
}) {
  const isConnected = health && health.status === 'ok';

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-30 px-4 sm:px-6 py-2.5 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        {/* Mobile menu toggle */}
        <button
          onClick={onToggleMobileSidebar}
          className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 md:hidden transition-colors"
          aria-label="Toggle Navigation Menu"
        >
          <Menu className="w-4 h-4" />
        </button>

        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-xs">
            <Sprout className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-sm font-bold text-slate-100 tracking-tight">
                Darukaa.Earth
              </h1>
              <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                Environmental AI
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Evidence-grounded multi-metric ecological intelligence
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2 sm:space-x-3">
        {/* Environmental Context Drawer Toggle (Secondary disclosure) */}
        <button
          onClick={onToggleContext}
          className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono transition-all border ${
            isContextOpen
              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
              : 'bg-slate-900 text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white'
          }`}
          title="Toggle Environmental Context Panel"
          aria-label="Toggle Environmental Context Panel"
        >
          {isContextOpen ? (
            <PanelRightClose className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <PanelRightOpen className="w-3.5 h-3.5 text-slate-400" />
          )}
          <span className="hidden sm:inline">Context</span>
          {contextCount > 0 && (
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 font-bold">
              {contextCount}
            </span>
          )}
        </button>

        {/* Backend Connectivity Status */}
        <div className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected
                ? 'bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.4)]'
                : 'bg-rose-500'
            }`}
          />
          <span className={`hidden sm:inline ${isConnected ? 'text-emerald-300' : 'text-rose-400 font-medium'}`}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        {/* Ping / Refresh Status */}
        <button
          onClick={onRefreshHealth}
          disabled={isCheckingHealth}
          className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
          title="Verify API Connectivity"
          aria-label="Refresh backend health"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isCheckingHealth ? 'animate-spin text-emerald-400' : ''}`} />
        </button>
      </div>
    </header>
  );
}
