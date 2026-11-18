import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, CheckCircle2, AlertCircle, ArrowUpRight } from 'lucide-react';
import { api } from '../../services/api';
import { IncidentSummary } from '../../types';
import { SeverityBadge } from '../../components/common/SeverityBadge';

export const IncidentLearningHub: React.FC = () => {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listIncidents().then(data => {
      setIncidents(data);
      setLoading(false);
    });
  }, []);

  const verified = incidents.filter(i => i.status === 'RESOLVED' || i.status === 'CLOSED');
  const pending = incidents.filter(i => i.status === 'OPEN' || i.status === 'INVESTIGATING');

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
          Incident Learning & Knowledge Feedback Hub
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">
            HUMAN-IN-THE-LOOP
          </span>
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Store human-verified resolutions, evaluate AI diagnostic accuracy, and prevent unverified AI outputs from polluting organizational knowledge.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="text-xs font-mono text-gray-400 uppercase">Total Incidents Ingested</div>
          <div className="text-2xl font-mono font-bold text-white mt-1">{incidents.length}</div>
        </div>
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="text-xs font-mono text-emerald-400 uppercase">Human Reviewed & Closed</div>
          <div className="text-2xl font-mono font-bold text-emerald-400 mt-1">{verified.length}</div>
        </div>
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="text-xs font-mono text-yellow-400 uppercase">Pending Review / Triage</div>
          <div className="text-2xl font-mono font-bold text-yellow-400 mt-1">{pending.length}</div>
        </div>
      </div>

      {/* Incident List for Verification */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h3 className="text-xs font-mono uppercase text-white font-bold tracking-wider">
            Incidents Pending Post-Incident Review
          </h3>
        </div>

        {incidents.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-gray-500">No incidents to review.</div>
        ) : (
          <div className="divide-y divide-gray-800/60">
            {incidents.map(inc => (
              <div
                key={inc.id}
                onClick={() => navigate(`/incidents/${inc.id}`)}
                className="p-4 flex items-center justify-between hover:bg-gray-800/40 cursor-pointer transition"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-blue-400">{inc.incident_number}</span>
                    <SeverityBadge severity={inc.severity} size="sm" />
                    <span className="font-mono text-[10px] text-gray-400 bg-gray-900 px-2 py-0.5 rounded">
                      {inc.status}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-white">{inc.title}</h4>
                </div>

                <button className="text-xs font-mono text-blue-400 hover:text-blue-300 flex items-center gap-1">
                  Audit Findings <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
