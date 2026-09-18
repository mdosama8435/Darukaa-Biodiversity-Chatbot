import React, { useState } from 'react';
import { FileText, ExternalLink, ChevronDown, ChevronUp, ShieldCheck, Tag } from 'lucide-react';

export default function EvidencePanel({ evidence = [] }) {
  const [expandedItems, setExpandedItems] = useState({});

  const toggleExpand = (id) => {
    setExpandedItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (!evidence || evidence.length === 0) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-400">
        <div className="flex items-center space-x-2 text-slate-400">
          <FileText className="w-4 h-4 text-slate-500" />
          <span className="font-bold uppercase tracking-wider">Scientific Evidence</span>
        </div>
        <p className="mt-2 text-slate-400 font-serif text-xs">
          No retrieval evidence loaded yet. Environmental reasoning will pull verified scientific and technical evidence chunks from PostgreSQL/pgvector.
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
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
              Scientific Evidence
            </h2>
            <span className="text-[10px] text-slate-400 font-mono">
              Retrieved from PostgreSQL / pgvector Corpus
            </span>
          </div>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-emerald-400">
          {evidence.length} Chunks Grounded
        </span>
      </div>

      {/* Evidence Cards List */}
      <div className="space-y-3">
        {evidence.map((item, idx) => {
          const itemId = item.chunk_id || `ev_${idx}`;
          const isExpanded = !!expandedItems[itemId];
          const doi = item.doi;
          const url = item.url || (doi ? `https://doi.org/${doi}` : null);
          const score = item.relevance_score !== undefined ? item.relevance_score : item.similarity;

          return (
            <div
              key={itemId}
              className="rounded-lg bg-slate-950 border border-slate-800/90 overflow-hidden text-xs transition-colors hover:border-slate-700"
            >
              {/* Summary Bar */}
              <div
                onClick={() => toggleExpand(itemId)}
                className="p-3.5 flex items-start justify-between cursor-pointer select-none space-x-3"
              >
                <div className="space-y-1 flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-emerald-400 text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                      {item.source_organization || item.source || 'Verified Source'}
                    </span>
                    {item.publication_year && (
                      <span className="text-[10px] font-mono text-slate-400">
                        ({item.publication_year})
                      </span>
                    )}
                    {item.chunk_id && (
                      <span className="text-[10px] font-mono text-slate-400">
                        • Chunk #{item.chunk_id}
                      </span>
                    )}
                    {score !== undefined && (
                      <span className="text-[10px] font-mono text-slate-400">
                        • Rel: {(Number(score) * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <h3 className="font-semibold text-slate-200 text-xs sm:text-[13px] leading-snug">
                    {item.source_title || item.title || 'Scientific Environmental Report'}
                  </h3>
                </div>

                <div className="flex items-center space-x-2 shrink-0 pt-0.5">
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </div>

              {/* Passage Preview (Concise) */}
              <div className="px-3.5 pb-3">
                <p className="text-slate-300 font-serif italic text-xs leading-relaxed line-clamp-2">
                  "{item.claim || item.content || 'Evidence grounding established.'}"
                </p>
              </div>

              {/* Collapsible Details */}
              {isExpanded && (
                <div className="px-3.5 pb-3.5 pt-2 border-t border-slate-900 bg-slate-900/40 space-y-2.5">
                  {/* Full Text Passage */}
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block">
                      Full Evidence Passage:
                    </span>
                    <p className="text-slate-200 font-serif text-xs sm:text-[13px] leading-relaxed p-2.5 rounded bg-slate-950 border border-slate-800">
                      {item.content || item.claim}
                    </p>
                  </div>

                  {/* Variables and Topics */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                    {item.matched_variables?.map((v) => (
                      <span key={v} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        var: {v}
                      </span>
                    ))}
                    {item.matched_topics?.map((t) => (
                      <span key={t} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        topic: {t}
                      </span>
                    ))}
                  </div>

                  {/* External Source Citation & DOI Link */}
                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
                    <div className="text-slate-400 text-[11px] truncate mr-2">
                      {doi && <span>DOI: {doi}</span>}
                      {item.section && <span className="ml-2">• {item.section}</span>}
                    </div>

                    {url && (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1 text-emerald-400 hover:text-emerald-300 font-medium shrink-0"
                      >
                        <span>View Source</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
