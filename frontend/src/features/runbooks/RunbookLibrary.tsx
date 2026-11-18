import React, { useState, useEffect } from 'react';
import { BookOpen, Search, ShieldCheck, ChevronRight, ChevronDown } from 'lucide-react';
import { api } from '../../services/api';
import { Runbook } from '../../types';

export const RunbookLibrary: React.FC = () => {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>('RB-PAY-001');

  useEffect(() => {
    setLoading(true);
    api.listRunbooks(query || undefined).then(data => {
      setRunbooks(data);
      setLoading(false);
    });
  }, [query]);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
          SRE Runbook & Operational Procedures Library
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            {runbooks.length} PROCEDURES
          </span>
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Standardized troubleshooting procedures and verification steps for payment gateway failure modes.
        </p>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 text-gray-500 absolute left-4 top-3.5" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search runbooks by symptom, service, category, or keyword..."
          className="w-full pl-11 pr-4 py-3 bg-[#111827] border border-gray-800 rounded-xl text-xs font-mono text-gray-200 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Runbook List */}
      <div className="space-y-4">
        {loading ? (
          <div className="p-12 text-center text-xs font-mono text-gray-500">Searching runbooks...</div>
        ) : runbooks.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-gray-500">No matching runbooks found.</div>
        ) : (
          runbooks.map(rb => {
            const isExpanded = expandedId === rb.id;
            return (
              <div
                key={rb.id}
                className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden transition"
              >
                <div
                  onClick={() => setExpandedId(isExpanded ? null : rb.id)}
                  className="p-5 flex items-center justify-between cursor-pointer hover:bg-gray-900/60 transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-blue-400">{rb.id}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-300">
                        {rb.category}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-900/40">
                        {rb.provenance}
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-white">{rb.title}</h3>
                  </div>
                  {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                </div>

                {isExpanded && (
                  <div className="p-5 pt-0 border-t border-gray-800/80 space-y-4 text-xs font-mono">
                    <div className="space-y-1.5 pt-3">
                      <div className="text-[10px] uppercase text-gray-500 font-bold">Applicable Services:</div>
                      <div className="flex flex-wrap gap-1">
                        {rb.applicable_services.map(s => (
                          <span key={s} className="px-2 py-0.5 rounded bg-gray-900 text-gray-300 border border-gray-800">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <div className="text-[10px] uppercase text-gray-500 font-bold">Observable Symptoms:</div>
                      <ul className="space-y-1 text-gray-300">
                        {rb.symptoms.map((sym, i) => (
                          <li key={i}>• {sym}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="space-y-1.5">
                      <div className="text-[10px] uppercase text-blue-400 font-bold">Step-by-Step Investigation:</div>
                      <div className="p-3.5 rounded-lg bg-gray-950 border border-gray-800 space-y-1.5 text-gray-300 leading-relaxed">
                        {rb.investigation_steps.map((step, i) => (
                          <div key={i}>{step}</div>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                      <div className="p-3 rounded bg-red-950/20 border border-red-800/40 space-y-1">
                        <span className="text-[10px] uppercase text-red-400 font-bold">Escalation Trigger:</span>
                        <p className="text-gray-300 text-[11px]">{rb.escalation_conditions}</p>
                      </div>

                      <div className="p-3 rounded bg-emerald-950/20 border border-emerald-800/40 space-y-1">
                        <span className="text-[10px] uppercase text-emerald-400 font-bold">Recovery Verification:</span>
                        <p className="text-gray-300 text-[11px]">{rb.recovery_verification}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
