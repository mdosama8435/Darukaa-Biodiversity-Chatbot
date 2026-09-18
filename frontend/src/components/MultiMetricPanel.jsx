import React from 'react';
import { Layers, ArrowDown, ShieldCheck, AlertCircle, Cpu } from 'lucide-react';

export default function MultiMetricPanel({ assessment = null, scenarioComparison = null }) {
  // Can source from direct assessment or scenario comparison
  const activeRelationships = assessment?.active_relationships || scenarioComparison?.relationships || [];
  const compoundSynthesis = assessment?.compound_synthesis || assessment?.assessment?.compound_synthesis;
  const multiMetricCoverage = scenarioComparison?.multi_metric_coverage;
  const isGrounded = scenarioComparison ? scenarioComparison.multi_metric_grounding : activeRelationships.some((r) => r.is_multi_metric);

  // Identify compound multi-metric relationship
  const compoundRel = activeRelationships.find((r) => r.is_multi_metric || (r.variables_involved && r.variables_involved.length >= 3));

  if (!assessment && !scenarioComparison) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-400">
        <div className="flex items-center space-x-2 text-slate-400">
          <Layers className="w-4 h-4 text-slate-500" />
          <span className="font-bold uppercase tracking-wider">Multi-Metric Reasoning</span>
        </div>
        <p className="mt-2 text-slate-400 font-serif text-xs">
          Provide at least 3 environmental variables (e.g., SOC, Rainfall, Land Use) to activate compound ecological interaction reasoning.
        </p>
      </div>
    );
  }

  const variablesInvolved = compoundRel?.variables_involved || ['soil_organic_carbon', 'rainfall', 'land_use'];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-md bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
              Multi-Metric Reasoning
            </h2>
            <span className="text-[10px] text-slate-400 font-mono">
              Compound Environmental Stress Interaction
            </span>
          </div>
        </div>

        {/* Grounding Status Badges */}
        <div className="flex items-center space-x-2 text-[11px] font-mono">
          <div className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300">
            Variables: <strong className="text-emerald-400">{variablesInvolved.length}</strong>
          </div>
          <div
            className={`px-2.5 py-1 rounded border font-semibold flex items-center space-x-1.5 ${
              isGrounded
                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
            }`}
          >
            {isGrounded ? <ShieldCheck className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            <span>{isGrounded ? 'Evidence Supported' : 'Limited by Data'}</span>
          </div>
        </div>
      </div>

      {/* Visual Flow Diagram */}
      <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800/80">
        <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-2 font-semibold">
          Ecological Reasoning Chain:
        </div>
        <div className="flex flex-col items-center space-y-1 text-xs font-mono">
          {variablesInvolved.map((v, i) => (
            <React.Fragment key={v}>
              <div className="px-3 py-1.5 rounded-md bg-slate-900 border border-slate-700 text-slate-200 font-semibold text-center w-full sm:w-72 shadow-xs">
                {v.replace(/_/g, ' ').toUpperCase()}
              </div>
              <ArrowDown className="w-3.5 h-3.5 text-emerald-500/70" />
            </React.Fragment>
          ))}
          <div className="px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 font-semibold text-center w-full sm:w-72">
            COMBINED ENVIRONMENTAL STRESS
          </div>
          <ArrowDown className="w-3.5 h-3.5 text-emerald-500/70" />
          <div className="px-3 py-1.5 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-bold text-center w-full sm:w-72">
            BIODIVERSITY IMPLICATIONS
          </div>
        </div>
      </div>

      {/* Reasoning Synthesis / Mechanism */}
      <div className="space-y-1.5">
        <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold block">
          Auditable Scientific Synthesis:
        </span>
        {compoundSynthesis ? (
          <p className="text-xs sm:text-[13px] text-slate-300 font-serif leading-relaxed p-3 rounded-lg bg-slate-950/50 border border-slate-800/70">
            {compoundSynthesis}
          </p>
        ) : compoundRel?.mechanism ? (
          <p className="text-xs sm:text-[13px] text-slate-300 font-serif leading-relaxed p-3 rounded-lg bg-slate-950/50 border border-slate-800/70">
            {compoundRel.mechanism}
          </p>
        ) : (
          <p className="text-xs text-slate-400 font-serif italic p-3 rounded-lg bg-slate-950/50 border border-slate-800/70">
            Multi-metric grounding is limited by available environmental data.
          </p>
        )}
      </div>

      {/* Coverage metadata */}
      {multiMetricCoverage && (
        <div className="text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-800 flex items-center justify-between">
          <span>Coverage Scope:</span>
          <span className="text-slate-300">{multiMetricCoverage}</span>
        </div>
      )}
    </div>
  );
}
