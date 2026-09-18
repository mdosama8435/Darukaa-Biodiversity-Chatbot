import React, { useState } from 'react';
import {
  Database,
  History,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Sprout,
  CloudRain,
  Trees,
  Bug,
  Factory,
  X,
} from 'lucide-react';

export default function ContextPanel({
  activeContext = {},
  detectedUpdates = [],
  onClose = null,
}) {
  const [expandedCategories, setExpandedCategories] = useState({
    soil: true,
    climate: true,
    land: true,
    biodiversity: false,
    human_impact: false,
  });

  const toggleCategory = (cat) => {
    setExpandedCategories((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  const categories = [
    {
      id: 'soil',
      name: 'Soil Health',
      icon: Sprout,
      metrics: [
        { key: 'soil_organic_carbon', label: 'Soil Organic Carbon', defaultUnit: '%' },
        { key: 'soil_ph', label: 'Soil pH', defaultUnit: '' },
        { key: 'soil_moisture', label: 'Soil Moisture', defaultUnit: '%' },
      ],
    },
    {
      id: 'climate',
      name: 'Climate & Water',
      icon: CloudRain,
      metrics: [
        { key: 'rainfall', label: 'Annual Rainfall', defaultUnit: 'mm' },
        { key: 'temperature', label: 'Mean Temperature', defaultUnit: '°C' },
      ],
    },
    {
      id: 'land',
      name: 'Land & Farming System',
      icon: Trees,
      metrics: [
        { key: 'land_use', label: 'Land Use / Cropping', defaultUnit: '' },
        { key: 'land_cover', label: 'Land Cover', defaultUnit: '' },
      ],
    },
    {
      id: 'biodiversity',
      name: 'Biodiversity',
      icon: Bug,
      metrics: [
        { key: 'species_richness', label: 'Species Richness', defaultUnit: 'taxa' },
        { key: 'habitat_diversity', label: 'Habitat Diversity', defaultUnit: '' },
      ],
    },
    {
      id: 'human_impact',
      name: 'Human Impact',
      icon: Factory,
      metrics: [
        { key: 'pollution', label: 'Pollution Index', defaultUnit: '' },
        { key: 'deforestation', label: 'Deforestation Rate', defaultUnit: '%' },
      ],
    },
  ];

  // Count provided variables
  const providedCount = Object.values(activeContext).filter(
    (prov) => prov && prov.value !== null && prov.value !== undefined
  ).length;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl flex flex-col h-full overflow-hidden shadow-sm select-none">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Database className="w-4 h-4 text-emerald-400" />
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Environmental Context
          </h2>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
            {providedCount} {providedCount === 1 ? 'variable' : 'variables'} provided
          </span>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
              aria-label="Close Context Panel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* State Value Overrides Alert */}
      {detectedUpdates.length > 0 && (
        <div className="p-3 mx-3 mt-3 rounded-lg bg-amber-500/10 border border-amber-500/25 text-xs font-mono space-y-1">
          <div className="font-bold text-amber-400 flex items-center space-x-1.5 text-[11px]">
            <History className="w-3.5 h-3.5" />
            <span>State Value Override Detected:</span>
          </div>
          {detectedUpdates.map((u, i) => (
            <div key={i} className="text-[11px] text-amber-200 pl-5">
              • <span className="font-semibold text-slate-300">{u.variable}</span>:{' '}
              <span className="line-through text-slate-400">{String(u.old_value)}</span> →{' '}
              <span className="font-bold text-emerald-300">{String(u.new_value)}</span>{' '}
              <span className="text-slate-400 text-[10px]">
                {u.turn_id ? `(Turn ${u.turn_id})` : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Scrollable Categories List */}
      <div className="p-3 space-y-3 overflow-y-auto flex-1">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const isExpanded = expandedCategories[cat.id];
          const hasProvidedInCat = cat.metrics.some((m) => {
            const p = activeContext[m.key];
            return p && p.value !== null && p.value !== undefined;
          });

          return (
            <div
              key={cat.id}
              className="rounded-lg border border-slate-800/80 bg-slate-950/40 overflow-hidden"
            >
              {/* Category Accordion Header */}
              <button
                onClick={() => toggleCategory(cat.id)}
                className="w-full px-3 py-2 flex items-center justify-between text-xs font-medium text-slate-300 hover:bg-slate-800/40 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <Icon className={`w-3.5 h-3.5 ${hasProvidedInCat ? 'text-emerald-400' : 'text-slate-500'}`} />
                  <span className="font-semibold text-[11px] uppercase tracking-wider font-mono">
                    {cat.name}
                  </span>
                </div>
                <div className="flex items-center space-x-1.5 text-slate-500">
                  {hasProvidedInCat && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  )}
                  {isExpanded ? (
                    <ChevronUp className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </div>
              </button>

              {/* Category Metrics List */}
              {isExpanded && (
                <div className="p-2.5 pt-1 space-y-1.5 border-t border-slate-800/40">
                  {cat.metrics.map((metric) => {
                    const prov = activeContext[metric.key];
                    const isProvided = prov && prov.value !== null && prov.value !== undefined;
                    const isUnknown = prov && prov.status === 'unknown';
                    const isInferred = prov && prov.status === 'inferred';
                    const isUpdated = prov && prov.status === 'updated';

                    const unit = prov?.unit || metric.defaultUnit;

                    return (
                      <div
                        key={metric.key}
                        className={`p-2 rounded-md border text-xs transition-colors ${
                          isProvided
                            ? 'bg-slate-900 border-slate-700/80'
                            : 'bg-slate-950/30 border-slate-800/40 opacity-70'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-300 font-medium">
                            {metric.label}
                          </span>
                          {isProvided ? (
                            <span
                              className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold uppercase ${
                                isUpdated
                                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                  : isInferred
                                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                                  : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              }`}
                            >
                              {isUpdated ? 'Updated' : isInferred ? 'Inferred' : 'Provided'}
                            </span>
                          ) : (
                            <span className="text-[10px] font-serif italic text-slate-500">
                              {isUnknown ? 'Unknown' : 'Not provided'}
                            </span>
                          )}
                        </div>

                        {/* Value & Provenance */}
                        {isProvided ? (
                          <div className="mt-1">
                            <div className="text-sm font-semibold text-white tracking-tight">
                              {String(prov.value)}
                              {unit ? ` ${unit}` : ''}
                            </div>
                            <div className="mt-1 text-[10px] font-mono text-slate-400 flex items-center space-x-1.5">
                              <span>
                                {prov.source === 'user_statement'
                                  ? 'User provided'
                                  : prov.source || 'User provided'}
                              </span>
                              {prov.turn_id !== undefined && (
                                <>
                                  <span>•</span>
                                  <span>Turn {prov.turn_id}</span>
                                </>
                              )}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
