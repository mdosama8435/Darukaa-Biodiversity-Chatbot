import React, { useState, useEffect } from 'react';
import { FileText, ExternalLink, Search, RefreshCw, Database, Tag, ShieldCheck } from 'lucide-react';
import { searchKnowledge } from '../services/api';

export default function EvidenceView() {
  const [query, setQuery] = useState('soil organic carbon biodiversity');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  const benchmarkQueries = [
    'soil organic carbon biodiversity',
    'rainfall soil moisture biodiversity',
    'land use habitat fragmentation biodiversity',
    'intercropping soil carbon biodiversity',
  ];

  const handleSearch = async (qToRun) => {
    const activeQuery = qToRun || query;
    if (!activeQuery.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await searchKnowledge({ query: activeQuery.trim(), top_k: 6 });
      setResults(data);
    } catch (err) {
      setError(err.message);
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleSearch('soil organic carbon biodiversity');
  }, []);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner (Step 14) */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-1.5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">
                Scientific Evidence Repository
              </h1>
              <p className="text-xs text-slate-400">
                Authoritative scientific evidence from FAO, IPCC, and ecological sources retrieved via pgvector.
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            PostgreSQL 16 + pgvector
          </span>
        </div>
      </div>

      {/* Query Suggestions */}
      <div className="space-y-2">
        <span className="text-xs font-mono text-slate-400 block font-semibold">
          Explore Key Ecological Topics:
        </span>
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          {benchmarkQueries.map((bQuery, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(bQuery);
                handleSearch(bQuery);
              }}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-emerald-300 border border-slate-800 hover:border-emerald-500/40 transition-colors disabled:opacity-50"
            >
              {bQuery}
            </button>
          ))}
        </div>
      </div>

      {/* Search Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSearch();
        }}
        className="flex gap-2"
      >
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search scientific corpus (e.g. intercropping soil carbon biodiversity)..."
            className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 font-mono"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-medium text-xs sm:text-sm rounded-lg transition-colors flex items-center space-x-2 shrink-0 shadow-xs"
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <span>Search Evidence</span>}
        </button>
      </form>

      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs font-mono text-rose-300">
          {error}
        </div>
      )}

      {/* Results List */}
      {results && (
        <div className="space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>
              Retrieved <strong>{results.results_count}</strong> qualified chunks for query:{' '}
              <span className="text-emerald-400 font-semibold">"{results.query}"</span>
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3.5">
            {results.results?.map((res, idx) => {
              const doi = res.doi;
              const url = res.url || (doi ? `https://doi.org/${doi}` : null);
              const simPercent = (res.similarity * 100).toFixed(1);

              return (
                <div
                  key={idx}
                  className="rounded-xl bg-slate-900 border border-slate-800 p-4 space-y-3 transition-colors hover:border-slate-700"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        {res.source}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        {res.document_title || res.title}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 text-xs font-mono">
                      <span className="text-slate-400">Similarity:</span>
                      <span className="text-emerald-400 font-semibold">{simPercent}%</span>
                    </div>
                  </div>

                  {/* Excerpt */}
                  <p className="text-xs sm:text-[13px] text-slate-200 font-serif leading-relaxed">
                    "{res.content || res.claim}"
                  </p>

                  {/* Topics and Variables */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono">
                    {res.matched_variables?.map((v) => (
                      <span key={v} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300">
                        var: {v}
                      </span>
                    ))}
                    {res.matched_topics?.map((t) => (
                      <span key={t} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400">
                        topic: {t}
                      </span>
                    ))}
                  </div>

                  {/* Citation and Link */}
                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs font-mono">
                    <div className="text-slate-400 text-[11px] truncate mr-2">
                      {doi && <span>DOI: {doi}</span>}
                      {res.section && <span className="ml-2">• {res.section}</span>}
                    </div>

                    {url && (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center space-x-1 text-emerald-400 hover:text-emerald-300 transition-colors shrink-0"
                      >
                        <span>View Source</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
