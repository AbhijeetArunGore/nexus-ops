import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Filter, ArrowUpRight, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';
import { IncidentSummary } from '../../types';
import { SeverityBadge } from '../../components/common/SeverityBadge';
import { ImpactBadge } from '../../components/common/ImpactBadge';

export const IncidentList: React.FC = () => {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [serviceFilter, setServiceFilter] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.listIncidents({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        service: serviceFilter || undefined
      });
      setIncidents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [severityFilter, statusFilter, serviceFilter]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            Incident Management Hub
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">
              {incidents.length} INCIDENTS
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Browse, filter, and audit all captured payment reliability incidents.
          </p>
        </div>

        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3 py-2 text-xs font-mono rounded bg-gray-800 text-gray-200 hover:bg-gray-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
          <Filter className="w-3.5 h-3.5 text-blue-400" />
          <span>FILTERS:</span>
        </div>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-gray-900 border border-gray-800 text-xs font-mono text-gray-300 rounded px-3 py-1.5 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-gray-900 border border-gray-800 text-xs font-mono text-gray-300 rounded px-3 py-1.5 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="OPEN">OPEN</option>
          <option value="INVESTIGATING">INVESTIGATING</option>
          <option value="MITIGATED">MITIGATED</option>
          <option value="RESOLVED">RESOLVED</option>
          <option value="CLOSED">CLOSED</option>
        </select>

        <input
          type="text"
          value={serviceFilter}
          onChange={(e) => setServiceFilter(e.target.value)}
          placeholder="Filter by service name (e.g. payment-api)..."
          className="bg-gray-900 border border-gray-800 text-xs font-mono text-gray-300 rounded px-3 py-1.5 focus:outline-none focus:border-blue-500 w-64"
        />

        {(severityFilter || statusFilter || serviceFilter) && (
          <button
            onClick={() => { setSeverityFilter(''); setStatusFilter(''); setServiceFilter(''); }}
            className="text-xs font-mono text-gray-400 hover:text-gray-200 underline"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Incidents Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs font-mono text-gray-500">Loading incidents...</div>
        ) : incidents.length === 0 ? (
          <div className="p-12 text-center text-xs font-mono text-gray-500">No matching incidents found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-900/60 text-gray-400 font-mono uppercase text-[11px] border-b border-gray-800">
                <tr>
                  <th className="py-3 px-4">Incident ID</th>
                  <th className="py-3 px-4">Title</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Impact</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Services</th>
                  <th className="py-3 px-4">Detected</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 text-gray-300">
                {incidents.map(inc => (
                  <tr
                    key={inc.id}
                    onClick={() => navigate(`/incidents/${inc.id}`)}
                    className="hover:bg-gray-800/40 cursor-pointer transition"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-400">{inc.incident_number}</td>
                    <td className="py-3.5 px-4 font-medium text-white max-w-xs truncate">{inc.title}</td>
                    <td className="py-3.5 px-4"><SeverityBadge severity={inc.severity} size="sm" /></td>
                    <td className="py-3.5 px-4"><ImpactBadge impact={inc.customer_impact} /></td>
                    <td className="py-3.5 px-4">
                      <span className="font-mono text-[11px] uppercase text-gray-400 bg-gray-800/80 px-2 py-0.5 rounded">
                        {inc.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1">
                        {inc.affected_services.slice(0, 2).map(s => (
                          <span key={s} className="px-1.5 py-0.5 rounded bg-gray-800 text-[10px] font-mono text-gray-300">
                            {s}
                          </span>
                        ))}
                        {inc.affected_services.length > 2 && (
                          <span className="text-[10px] text-gray-500 font-mono">+{inc.affected_services.length - 2}</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-gray-400">
                      {new Date(inc.created_at).toISOString().slice(0, 16).replace('T', ' ')}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button className="text-blue-400 hover:text-blue-300 font-mono text-xs inline-flex items-center gap-1">
                        Open Workspace <ArrowUpRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
