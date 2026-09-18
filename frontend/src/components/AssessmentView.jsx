import React, { useState } from 'react';
import {
  Compass,
  RefreshCw,
  Layers,
  ShieldCheck,
  AlertCircle,
  FileText,
  Clock,
  Sparkles,
} from 'lucide-react';
import MultiMetricPanel from './MultiMetricPanel';
import RecommendationPanel from './RecommendationPanel';
import EvidencePanel from './EvidencePanel';

export default function AssessmentView({ onRunAssessment, loading, error, result }) {
  // Clean initial state - do not auto-fill missing values (Step 16)
  const [formData, setFormData] = useState({
    soil_organic_carbon: '',
    soil_ph: '',
    soil_moisture: '',
    rainfall: '',
    temperature: '',
    land_use: '',
    land_cover: '',
    species_richness: '',
    habitat_diversity: '',
    pollution: '',
    deforestation: '',
    region: '',
    latitude: '',
    longitude: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Construct structured payload, omitting unprovided fields
    const payload = {
      soil: {},
      climate: {},
      land: {},
      biodiversity: {},
      human_impact: {},
      location: {},
    };

    if (formData.soil_organic_carbon !== '') payload.soil.soil_organic_carbon = parseFloat(formData.soil_organic_carbon);
    if (formData.soil_ph !== '') payload.soil.soil_ph = parseFloat(formData.soil_ph);
    if (formData.soil_moisture !== '') payload.soil.soil_moisture = parseFloat(formData.soil_moisture);

    if (formData.rainfall !== '') payload.climate.rainfall = parseFloat(formData.rainfall);
    if (formData.temperature !== '') payload.climate.temperature = parseFloat(formData.temperature);

    if (formData.land_use.trim() !== '') payload.land.land_use = formData.land_use.trim();
    if (formData.land_cover.trim() !== '') payload.land.land_cover = formData.land_cover.trim();

    if (formData.species_richness !== '') payload.biodiversity.species_richness = parseInt(formData.species_richness, 10);
    if (formData.habitat_diversity.trim() !== '') payload.biodiversity.habitat_diversity = formData.habitat_diversity.trim();

    if (formData.pollution.trim() !== '') payload.human_impact.pollution = formData.pollution.trim();
    if (formData.deforestation.trim() !== '') payload.human_impact.deforestation = formData.deforestation.trim();

    if (formData.region.trim() !== '') payload.location.region = formData.region.trim();
    if (formData.latitude !== '') payload.location.latitude = parseFloat(formData.latitude);
    if (formData.longitude !== '') payload.location.longitude = parseFloat(formData.longitude);

    onRunAssessment(payload);
  };

  const handleLoadBenchmark = () => {
    setFormData({
      soil_organic_carbon: '0.3',
      soil_ph: '6.8',
      soil_moisture: '16.5',
      rainfall: '600.0',
      temperature: '28.0',
      land_use: 'wheat monoculture',
      land_cover: 'cropland',
      species_richness: '8',
      habitat_diversity: 'low',
      pollution: 'none',
      deforestation: 'none',
      region: 'semi-arid',
      latitude: '25.6',
      longitude: '85.1',
    });
  };

  const handleClear = () => {
    setFormData({
      soil_organic_carbon: '',
      soil_ph: '',
      soil_moisture: '',
      rainfall: '',
      temperature: '',
      land_use: '',
      land_cover: '',
      species_richness: '',
      habitat_diversity: '',
      pollution: '',
      deforestation: '',
      region: '',
      latitude: '',
      longitude: '',
    });
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header Banner (Step 16) */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-1.5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">
                Structured Environmental Assessment
              </h1>
              <p className="text-xs text-slate-400">
                Direct parameter input across 6 ecological dimensions. All fields are optional.
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            Assessment Engine
          </span>
        </div>
      </div>

      {/* Form Container */}
      <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
            Environmental Parameter Matrix
          </span>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleClear}
              className="text-xs font-mono text-slate-400 hover:text-slate-200 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 transition-colors"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={handleLoadBenchmark}
              className="text-xs font-mono text-emerald-400 hover:text-emerald-300 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 hover:border-emerald-500/30 transition-colors"
            >
              Load Benchmark Values
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* 1. SOIL */}
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider">
                1. Soil
              </span>
              <span className="text-[9px] font-mono text-slate-500">Optional</span>
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Soil Organic Carbon (%):
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                name="soil_organic_carbon"
                value={formData.soil_organic_carbon}
                onChange={handleChange}
                placeholder="e.g. 0.3"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Soil pH:
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="14"
                name="soil_ph"
                value={formData.soil_ph}
                onChange={handleChange}
                placeholder="e.g. 6.8"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Soil Moisture (%):
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                name="soil_moisture"
                value={formData.soil_moisture}
                onChange={handleChange}
                placeholder="e.g. 16.5"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
          </div>

          {/* 2. CLIMATE */}
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-teal-400 uppercase tracking-wider">
                2. Climate
              </span>
              <span className="text-[9px] font-mono text-slate-500">Optional</span>
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Annual Rainfall (mm):
              </label>
              <input
                type="number"
                step="1"
                min="0"
                name="rainfall"
                value={formData.rainfall}
                onChange={handleChange}
                placeholder="e.g. 600"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Mean Temperature (°C):
              </label>
              <input
                type="number"
                step="0.1"
                name="temperature"
                value={formData.temperature}
                onChange={handleChange}
                placeholder="e.g. 28.0"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
          </div>

          {/* 3. LAND */}
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                3. Land
              </span>
              <span className="text-[9px] font-mono text-slate-500">Optional</span>
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Land Use:
              </label>
              <input
                type="text"
                name="land_use"
                value={formData.land_use}
                onChange={handleChange}
                placeholder="e.g. wheat monoculture"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Land Cover:
              </label>
              <input
                type="text"
                name="land_cover"
                value={formData.land_cover}
                onChange={handleChange}
                placeholder="e.g. cropland"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
          </div>

          {/* 4. BIODIVERSITY */}
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider">
                4. Biodiversity
              </span>
              <span className="text-[9px] font-mono text-slate-500">Optional</span>
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Species Richness (Count):
              </label>
              <input
                type="number"
                min="0"
                name="species_richness"
                value={formData.species_richness}
                onChange={handleChange}
                placeholder="e.g. 8"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Habitat Diversity:
              </label>
              <input
                type="text"
                name="habitat_diversity"
                value={formData.habitat_diversity}
                onChange={handleChange}
                placeholder="e.g. low"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
          </div>

          {/* 5. HUMAN IMPACT */}
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-amber-400 uppercase tracking-wider">
                5. Human Impact
              </span>
              <span className="text-[9px] font-mono text-slate-500">Optional</span>
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Pollution Status:
              </label>
              <input
                type="text"
                name="pollution"
                value={formData.pollution}
                onChange={handleChange}
                placeholder="e.g. none, agricultural runoff"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Deforestation Status:
              </label>
              <input
                type="text"
                name="deforestation"
                value={formData.deforestation}
                onChange={handleChange}
                placeholder="e.g. none, fragmented"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
          </div>

          {/* 6. SPATIAL / OPTIONAL */}
          <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-purple-400 uppercase tracking-wider">
                6. Spatial / Optional
              </span>
              <span className="text-[9px] font-mono text-slate-500">Optional</span>
            </div>
            <div>
              <label className="text-[11px] font-mono text-slate-400 block mb-1">
                Region / Biome:
              </label>
              <input
                type="text"
                name="region"
                value={formData.region}
                onChange={handleChange}
                placeholder="e.g. semi-arid"
                className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Latitude:</label>
                <input
                  type="number"
                  step="0.0001"
                  name="latitude"
                  value={formData.latitude}
                  onChange={handleChange}
                  placeholder="25.6"
                  className="w-full px-2 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
                />
              </div>
              <div>
                <label className="text-[11px] font-mono text-slate-400 block mb-1">Longitude:</label>
                <input
                  type="number"
                  step="0.0001"
                  name="longitude"
                  value={formData.longitude}
                  onChange={handleChange}
                  placeholder="85.1"
                  className="w-full px-2 py-1.5 rounded bg-slate-900 border border-slate-800 text-xs text-white font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/50"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Submit Button (Step 16: 'Analyze Environment') */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 disabled:bg-slate-800 text-white font-medium text-xs sm:text-sm rounded-lg transition-colors flex items-center space-x-2 shadow-xs"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Analyzing Environment...</span>
              </>
            ) : (
              <span>Analyze Environment</span>
            )}
          </button>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs font-mono text-rose-300">
            {error}
          </div>
        )}
      </form>

      {/* Assessment Results */}
      {result && (
        <div className="space-y-6 animate-fadeIn">
          <MultiMetricPanel assessment={result} />
          <RecommendationPanel recommendations={result.recommendations || []} />
          <EvidencePanel evidence={result.evidence || []} />
        </div>
      )}
    </div>
  );
}
