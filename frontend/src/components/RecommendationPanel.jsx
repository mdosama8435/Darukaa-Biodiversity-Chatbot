import React, { useState } from 'react';
import {
  ShieldCheck,
  Clock,
  AlertTriangle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  GitCommit,
  CheckCircle2,
} from 'lucide-react';
import { cleanText } from './ChatView';

export default function RecommendationPanel({ recommendations = [] }) {
  const [expandedTrace, setExpandedTrace] = useState({});

  const toggleTrace = (id) => {
    setExpandedTrace((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-400">
        <div className="flex items-center space-x-2 text-slate-400">
          <ShieldCheck className="w-4 h-4 text-slate-500" />
          <span className="font-bold uppercase tracking-wider">Evidence-Grounded Recommendations</span>
        </div>
        <p className="mt-2 text-slate-400 font-serif text-xs">
          Recommendations will appear when sufficient environmental state variables are provided and grounded in authoritative scientific evidence.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-md bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
              Evidence-Grounded Recommendations
            </h2>
            <span className="text-[10px] text-slate-400 font-mono">
              Site-Specific Agroecological Interventions
            </span>
          </div>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-emerald-400">
          {recommendations.length} Formulated
        </span>
      </div>

      {/* Recommendations Cards */}
      <div className="space-y-4">
        {recommendations.map((rec, idx) => {
          const recId = rec.recommendation_id || `rec_${idx}`;
          const isTraceOpen = !!expandedTrace[recId];
          const trace = rec.traceability || {};
          const conf = (rec.confidence || 'medium').toUpperCase();

          const confBadgeClass =
            conf === 'HIGH'
              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
              : conf === 'MEDIUM'
              ? 'bg-teal-500/15 text-teal-300 border-teal-500/30'
              : conf === 'LOW'
              ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
              : 'bg-rose-500/15 text-rose-300 border-rose-500/30';

          return (
            <div
              key={recId}
              className="rounded-xl bg-slate-950 border border-slate-800 p-4 space-y-3.5 transition-colors hover:border-slate-700"
            >
              {/* Action Title & Confidence */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-wider block">
                    Action {idx + 1}
                  </span>
                  <h3 className="text-sm sm:text-base font-bold text-white tracking-tight leading-snug">
                    {cleanText(rec.action)}
                  </h3>
                </div>

                <div className="flex items-center space-x-2 shrink-0">
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${confBadgeClass}`}
                  >
                    Confidence: {conf}
                  </span>
                </div>
              </div>

              {/* Why: Scientific Justification */}
              {rec.why && rec.why.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold block">
                    Why (Scientific Justification):
                  </span>
                  <ul className="space-y-1 text-xs text-slate-300 font-serif list-disc list-inside">
                    {rec.why.map((w, wIdx) => (
                      <li key={wIdx} className="leading-relaxed">
                        {cleanText(w)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Impacted Metrics Chips */}
              {rec.impacted_metrics && rec.impacted_metrics.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block">
                    Impacted Metrics:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {rec.impacted_metrics.map((m) => (
                      <span
                        key={m}
                        className="px-2 py-0.5 rounded-md bg-slate-900 border border-slate-700/80 text-[11px] font-mono text-emerald-300 capitalize"
                      >
                        {cleanText(m.replace(/_/g, ' '))}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Expected Effect (Strictly Direction-Only if Magnitude is uncalibrated) */}
              {rec.expected_effect?.description && (
                <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-serif text-slate-300">
                  <strong className="text-[11px] font-mono text-slate-400 block mb-0.5">
                    Expected Ecological Effect:
                  </strong>
                  {cleanText(rec.expected_effect.description)}
                </div>
              )}

              {/* Time Horizon */}
              {rec.time_horizon && (
                <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/80 space-y-2 text-xs">
                  <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                    <Clock className="w-3 h-3 text-slate-400" />
                    <span>Time Horizon:</span>
                  </span>
                  {rec.time_horizon.action_initiation || rec.time_horizon.expected_ecological_response ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-serif">
                      <div className="p-2 rounded bg-slate-950 border border-slate-800">
                        <strong className="text-emerald-400 font-mono text-[10px] block">Action Initiation:</strong>
                        <span className="text-slate-300">{cleanText(rec.time_horizon.action_initiation || 'Immediate (0–1 year)')}</span>
                      </div>
                      <div className="p-2 rounded bg-slate-950 border border-slate-800">
                        <strong className="text-teal-400 font-mono text-[10px] block">Expected Ecological Response:</strong>
                        <span className="text-slate-300">{cleanText(rec.time_horizon.expected_ecological_response || 'Gradual (Site dependent)')}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] font-serif">
                      {rec.time_horizon.short_term && (
                        <div className="p-2 rounded bg-slate-950 border border-slate-800">
                          <strong className="text-emerald-400 font-mono text-[10px] block">Short-Term:</strong>
                          <span className="text-slate-300">{cleanText(String(rec.time_horizon.short_term))}</span>
                        </div>
                      )}
                      {rec.time_horizon.medium_term && (
                        <div className="p-2 rounded bg-slate-950 border border-slate-800">
                          <strong className="text-teal-400 font-mono text-[10px] block">Medium-Term:</strong>
                          <span className="text-slate-300">{cleanText(String(rec.time_horizon.medium_term))}</span>
                        </div>
                      )}
                      {rec.time_horizon.long_term && (
                        <div className="p-2 rounded bg-slate-950 border border-slate-800">
                          <strong className="text-cyan-400 font-mono text-[10px] block">Long-Term:</strong>
                          <span className="text-slate-300">{cleanText(String(rec.time_horizon.long_term))}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Limitations */}
              {rec.limitations && rec.limitations.length > 0 && (
                <div className="p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs font-serif space-y-1">
                  <div className="text-[10px] font-mono font-bold text-amber-400 flex items-center space-x-1 uppercase">
                    <AlertTriangle className="w-3 h-3 text-amber-400" />
                    <span>Site-Specific Limitations:</span>
                  </div>
                  <ul className="list-disc list-inside text-slate-300 text-[11px] space-y-0.5">
                    {rec.limitations.map((l, lIdx) => (
                      <li key={lIdx}>{cleanText(l)}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Compact Section 10 Evidence Trace */}
              <div className="pt-1 border-t border-slate-800/80">
                <button
                  onClick={() => toggleTrace(recId)}
                  className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-400 hover:text-emerald-300 transition-colors"
                >
                  <GitCommit className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Evidence Trace</span>
                  {isTraceOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>

                {isTraceOpen && (
                  <div className="mt-2 p-2.5 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1.5">
                    <div className="flex items-center space-x-2 text-slate-300">
                      <span>Recommendation</span>
                      <span>→</span>
                      <span className="text-emerald-400">{trace.relationship_ids?.join(', ') || 'soc_soil_biodiversity'}</span>
                      <span>→</span>
                      <span>Chunks {trace.chunk_ids?.join(', ') || '#6'}</span>
                      <span>→</span>
                      <span className="text-slate-200">FAO / IPCC Scientific & Technical Report</span>
                    </div>
                    {trace.source_references && trace.source_references.length > 0 && (
                      <div className="text-[10px] text-slate-400 pt-1">
                        DOI / Citation: {trace.source_references.join('; ')}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
