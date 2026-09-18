import React, { useState } from 'react';
import {
  Sliders,
  GitCompare,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Sparkles,
  AlertCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  FileText,
} from 'lucide-react';

export default function ScenarioView({
  activeContext = {},
  scenarioResult = null,
  scenarioLoading = false,
  scenarioError = null,
  onRunScenario,
}) {
  const [queryInput, setQueryInput] = useState(
    'What if rainfall decreases by 15% and we transition from wheat monoculture to intercropping?'
  );

  // Baseline extraction from active context or verified benchmark defaults
  const resolvedBaseline = {
    soil_organic_carbon: activeContext?.soil_organic_carbon?.value ?? 0.3,
    rainfall: activeContext?.rainfall?.value ?? 600.0,
    land_use: activeContext?.land_use?.value ?? 'wheat monoculture',
  };

  const presetScenarios = [
    {
      title: 'Rainfall -15% & Intercropping',
      query: 'What if rainfall decreases by 15% and we transition from wheat monoculture to intercropping?',
    },
    {
      title: 'Drought Stress (-15% Rainfall)',
      query: 'What if rainfall decreases by 15%?',
    },
    {
      title: 'Crop Transition (Intercropping)',
      query: 'What if we transition from wheat monoculture to intercropping?',
    },
    {
      title: 'SOC Enhancement (0.3% → 0.8%)',
      query: 'What if soil organic carbon increases from 0.3% to 0.8%?',
    },
  ];

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!queryInput.trim() || scenarioLoading) return;
    onRunScenario(queryInput, resolvedBaseline);
  };

  const comparison = scenarioResult?.comparison;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner (Step 15) */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-1.5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">
                What if I change something?
              </h1>
              <p className="text-xs text-slate-400">
                Explore hypothetical climate and management interventions evaluated against scientific evidence.
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-teal-300 border border-slate-700">
            Scenario Engine
          </span>
        </div>
      </div>

      {/* Preset Scenario Shortcuts */}
      <div className="space-y-2">
        <span className="text-xs font-mono text-slate-400 block font-semibold">
          Suggested Scenarios:
        </span>
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          {presetScenarios.map((scen, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQueryInput(scen.query);
                onRunScenario(scen.query, resolvedBaseline);
              }}
              disabled={scenarioLoading}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-teal-300 border border-slate-800 hover:border-teal-500/40 transition-colors disabled:opacity-50"
            >
              {scen.title}
            </button>
          ))}
        </div>
      </div>

      {/* Baseline & Scenario Input */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
        {/* BASELINE CARD */}
        <div className="md:col-span-4 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
              Baseline State
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              Inherited Context
            </span>
          </div>

          <div className="space-y-2 font-mono text-xs">
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex justify-between items-center">
              <span className="text-slate-400">Soil Organic Carbon (SOC):</span>
              <span className="font-bold text-white">{resolvedBaseline.soil_organic_carbon}%</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex justify-between items-center">
              <span className="text-slate-400">Annual Rainfall:</span>
              <span className="font-bold text-white">{resolvedBaseline.rainfall} mm</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 flex justify-between items-center">
              <span className="text-slate-400">Land Use:</span>
              <span className="font-bold text-white capitalize">{resolvedBaseline.land_use}</span>
            </div>
          </div>
        </div>

        {/* SCENARIO INQUIRY */}
        <div className="md:col-span-8 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
              Hypothetical Change
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/15 text-teal-300 border border-teal-500/30">
              Simulation Query
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="e.g. What if rainfall decreases by 15% and we transition to intercropping?"
                className="flex-1 px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-teal-500/50 font-mono"
              />
              <button
                type="submit"
                disabled={scenarioLoading || !queryInput.trim()}
                className="px-4 py-2.5 bg-teal-600 hover:bg-teal-500 disabled:bg-slate-800 text-white font-medium text-xs sm:text-sm rounded-lg transition-colors flex items-center justify-center space-x-2 shrink-0 shadow-xs"
              >
                {scenarioLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <span>Simulate Scenario</span>
                )}
              </button>
            </div>
          </form>

          {scenarioError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs font-mono text-rose-300">
              {scenarioError}
            </div>
          )}

          {scenarioResult?.clarification_questions?.length > 0 && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs space-y-1.5">
              <div className="flex items-center space-x-1.5 text-amber-400 font-mono font-bold text-[11px] uppercase">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Clarification Needed:</span>
              </div>
              {scenarioResult.clarification_questions.map((q, qIdx) => (
                <p key={qIdx} className="text-slate-200 font-serif text-xs">
                  {q}
                </p>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* RESULTS DISPLAY */}
      {comparison && (
        <div className="space-y-5 animate-fadeIn">
          {/* Changed Variables Before/After Grid */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                Resolved Scenario Transitions
              </span>
              <div className="flex items-center space-x-2 text-xs font-mono">
                <span className="text-slate-400">Confidence:</span>
                <span className="px-2 py-0.5 rounded font-bold uppercase bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  {comparison.confidence}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {comparison.changed_variables?.map((ch, idx) => {
                const isRelative = ch.change_type === 'relative_change' || ch.unit === 'percent';
                const isCategorical = ch.change_type === 'land_use_change' || typeof ch.scenario_value === 'string';

                return (
                  <div
                    key={idx}
                    className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2 font-mono text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-200 uppercase text-[11px]">
                        {ch.variable.replace(/_/g, ' ')}
                      </span>
                      <span
                        className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold ${
                          isRelative
                            ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30'
                            : 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
                        }`}
                      >
                        {isRelative ? 'Relative Change' : isCategorical ? 'Categorical Change' : 'Direct Value'}
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-2 rounded bg-slate-900/80 border border-slate-800/80">
                      <div>
                        <span className="text-[10px] text-slate-400 block">Baseline</span>
                        <span className="text-xs font-semibold text-slate-300">
                          {ch.baseline_value !== null && ch.baseline_value !== undefined
                            ? `${ch.baseline_value}${ch.unit && ch.unit !== 'percent' ? ` ${ch.unit}` : ''}`
                            : 'Unknown'}
                        </span>
                      </div>
                      <span className="text-teal-400 font-bold text-sm">→</span>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 block">Scenario</span>
                        <span className="text-sm font-bold text-emerald-400">
                          {ch.scenario_value !== null && ch.scenario_value !== undefined
                            ? `${ch.scenario_value}${ch.unit && ch.unit !== 'percent' ? ` ${ch.unit}` : ''}`
                            : ch.change_value !== null
                            ? `${ch.change_value}%`
                            : 'Unknown'}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {comparison.assumptions && comparison.assumptions.length > 0 && (
              <div className="pt-2 flex flex-wrap items-center gap-1.5 text-xs font-mono">
                <span className="text-slate-400 font-semibold">Assumptions:</span>
                {comparison.assumptions.map((a, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300 text-[11px]">
                    • {a}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Evaluation Matrix */}
          {comparison.evaluation_matrix && comparison.evaluation_matrix.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <GitCompare className="w-4 h-4 text-teal-400" />
                  <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                    Evaluation Matrix
                  </h3>
                </div>
              </div>

              <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
                <table className="w-full text-left text-xs border-collapse font-mono">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-900/90 text-slate-400 text-[11px] uppercase">
                      <th className="p-3">Metric</th>
                      <th className="p-3">Baseline</th>
                      <th className="p-3">Scenario</th>
                      <th className="p-3">Direction</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">Limitations</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/70">
                    {comparison.evaluation_matrix.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                        <td className="p-3 font-semibold text-slate-200 capitalize">
                          {row.metric.replace(/_/g, ' ')}
                        </td>
                        <td className="p-3 text-slate-400">{String(row.baseline)}</td>
                        <td className="p-3 text-teal-300 font-semibold">{String(row.scenario)}</td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold inline-flex items-center gap-1 ${
                              row.direction === 'increased'
                                ? 'bg-emerald-500/15 text-emerald-300'
                                : row.direction === 'decreased'
                                ? 'bg-amber-500/15 text-amber-300'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {row.direction === 'increased' ? (
                              <TrendingUp className="w-3 h-3" />
                            ) : row.direction === 'decreased' ? (
                              <TrendingDown className="w-3 h-3" />
                            ) : (
                              <Minus className="w-3 h-3" />
                            )}
                            <span>{row.direction}</span>
                          </span>
                        </td>
                        <td className="p-3 uppercase text-slate-300">{row.confidence}</td>
                        <td className="p-3 font-serif text-[11px] text-slate-400 max-w-sm">
                          {row.limitations || 'Direction supported by scientific literature.'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Synergies & Trade-offs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2.5">
              <div className="flex items-center space-x-1.5 text-xs font-mono font-bold uppercase tracking-wider text-emerald-400 border-b border-slate-800 pb-2">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Synergies</span>
              </div>
              {comparison.synergies && comparison.synergies.length > 0 ? (
                <div className="space-y-2">
                  {comparison.synergies.map((s, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-serif text-slate-300 leading-relaxed">
                      • {s.rationale}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs font-serif text-slate-400 italic p-2">
                  No evidence-supported synergy identified for this specific delta.
                </p>
              )}
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2.5">
              <div className="flex items-center space-x-1.5 text-xs font-mono font-bold uppercase tracking-wider text-amber-400 border-b border-slate-800 pb-2">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Trade-Offs</span>
              </div>
              {comparison.tradeoffs && comparison.tradeoffs.length > 0 ? (
                <div className="space-y-2">
                  {comparison.tradeoffs.map((t, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-serif text-slate-300 leading-relaxed">
                      • {t.rationale}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs font-serif text-slate-400 italic p-2">
                  {comparison.tradeoff_summary || 'No evidence-supported trade-off identified.'}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
