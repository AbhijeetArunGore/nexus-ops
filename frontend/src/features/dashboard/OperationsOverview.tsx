import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Activity,
  Layers,
  ArrowUpRight,
  RefreshCw,
  Server
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { api } from '../../services/api';
import { IncidentSummary } from '../../types';
import { SeverityBadge } from '../../components/common/SeverityBadge';
import { ImpactBadge } from '../../components/common/ImpactBadge';

export const OperationsOverview: React.FC = () => {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.listIncidents();
      setIncidents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Compute stats
  const total = incidents.length;
  const critical = incidents.filter(i => i.severity === 'CRITICAL').length;
  const high = incidents.filter(i => i.severity === 'HIGH').length;
  const open = incidents.filter(i => i.status === 'OPEN' || i.status === 'INVESTIGATING').length;
  const resolved = incidents.filter(i => i.status === 'RESOLVED' || i.status === 'CLOSED').length;

  // Chart data: Error count by service
  const serviceErrorMap: Record<string, number> = {};
  incidents.forEach(inc => {
    inc.affected_services.forEach(svc => {
      serviceErrorMap[svc] = (serviceErrorMap[svc] || 0) + (inc.total_errors || 1);
    });
  });
  const chartData = Object.entries(serviceErrorMap).map(([service, errors]) => ({
    service,
    errors
  }));

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            Operations Command Center
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              SYNTHETIC TELEMETRY WORKSPACE
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Simulated fintech payment lifecycle telemetry, topology analysis, and deterministic incident intelligence.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-xs font-mono rounded bg-gray-800 text-gray-200 hover:bg-gray-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => navigate('/investigate')}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded bg-blue-600 text-white hover:bg-blue-500 transition shadow-lg shadow-blue-600/20"
          >
            New Ingestion
            <ArrowUpRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider">Total Incidents</span>
            <Layers className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-3xl font-extrabold text-white font-mono">{total}</div>
          <div className="text-[11px] text-gray-500 mt-1 font-mono">Analyzed datasets</div>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider">Active / Open</span>
            <Activity className="w-4 h-4 text-yellow-400" />
          </div>
          <div className="text-3xl font-extrabold text-yellow-400 font-mono">{open}</div>
          <div className="text-[11px] text-gray-500 mt-1 font-mono">Under investigation</div>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider">Critical Severity</span>
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-3xl font-extrabold text-red-400 font-mono">{critical}</div>
          <div className="text-[11px] text-red-400/80 mt-1 font-mono">Immediate triage</div>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider">High Severity</span>
            <AlertTriangle className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-3xl font-extrabold text-orange-400 font-mono">{high}</div>
          <div className="text-[11px] text-gray-500 mt-1 font-mono">Material degradation</div>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-gray-400 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider">Resolved</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 font-mono">{resolved}</div>
          <div className="text-[11px] text-emerald-400/80 mt-1 font-mono">Mitigated & verified</div>
        </div>
      </div>

      {/* Grid: Service Health & Telemetry Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Service Health Topology Matrix */}
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-wide text-white uppercase font-mono flex items-center gap-2">
              <Server className="w-4 h-4 text-blue-400" />
              Payment Service Mesh Status
            </h2>
            <span className="text-[11px] font-mono text-gray-500">Synthetic Topology</span>
          </div>
          <div className="space-y-3">
            {[
              { name: 'payment-api', tier: 'Tier 1 Core', ok: !incidents.some(i => (i.status === 'OPEN' || i.status === 'INVESTIGATING') && i.affected_services.includes('payment-api')) },
              { name: 'payment-orchestrator', tier: 'Tier 1 Core', ok: !incidents.some(i => (i.status === 'OPEN' || i.status === 'INVESTIGATING') && i.affected_services.includes('payment-orchestrator')) },
              { name: 'order-db', tier: 'Tier 1 Relational', ok: !incidents.some(i => (i.status === 'OPEN' || i.status === 'INVESTIGATING') && i.affected_services.includes('order-db')) },
              { name: 'bank-connector', tier: 'Tier 1 Gateway', ok: !incidents.some(i => (i.status === 'OPEN' || i.status === 'INVESTIGATING') && i.affected_services.includes('bank-connector')) },
              { name: 'webhook-dispatcher', tier: 'Tier 2 Async', ok: !incidents.some(i => (i.status === 'OPEN' || i.status === 'INVESTIGATING') && i.affected_services.includes('webhook-dispatcher')) },
              { name: 'settlement-engine', tier: 'Tier 3 Batch', ok: !incidents.some(i => (i.status === 'OPEN' || i.status === 'INVESTIGATING') && i.affected_services.includes('settlement-engine')) },
            ].map(svc => (
              <div key={svc.name} className="flex items-center justify-between p-3 rounded-lg bg-gray-900/60 border border-gray-800/80">
                <div>
                  <div className="font-mono text-xs font-semibold text-gray-200">{svc.name}</div>
                  <div className="text-[11px] text-gray-500">{svc.tier}</div>
                </div>
                <div className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                  svc.ok ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/50' : 'bg-red-950/80 text-red-400 border border-red-800/80 animate-pulse'
                }`}>
                  {svc.ok ? 'NO OPEN INCIDENT' : 'ACTIVE INCIDENT ALERT'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Telemetry Error Volume Chart */}
        <div className="lg:col-span-2 bg-[#111827] border border-gray-800 rounded-xl p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold tracking-wide text-white uppercase font-mono">
                Error Volume Distribution by Service
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">Aggregate error telemetry extracted from normalized event patterns.</p>
            </div>
          </div>
          <div className="h-64 w-full">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                  <XAxis dataKey="service" stroke="#6B7280" tick={{ fontSize: 11, fill: '#9CA3AF' }} interval={0} angle={-15} textAnchor="end" />
                  <YAxis stroke="#6B7280" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px' }}
                    itemStyle={{ color: '#F3F4F6', fontFamily: 'monospace' }}
                  />
                  <Bar dataKey="errors" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs font-mono text-gray-500">
                No error telemetry recorded yet. Ingest logs or launch a simulation from Payment Reliability Lab.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Active Incidents Table */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-gray-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-white tracking-wide uppercase font-mono">
              Active Incident Intelligence Feed
            </h2>
            <p className="text-xs text-gray-400">Classified using the 8-factor deterministic severity decision policy.</p>
          </div>
        </div>

        {incidents.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <Clock className="w-10 h-10 text-gray-600 mx-auto" />
            <p className="text-sm text-gray-400">No active incidents found.</p>
            <button
              onClick={() => navigate('/lab')}
              className="text-xs font-mono text-blue-400 hover:text-blue-300 underline"
            >
              Open Payment Reliability Lab to load synthetic Pine Labs scenarios
            </button>
          </div>
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
                  <th className="py-3 px-4">Affected Services</th>
                  <th className="py-3 px-4">Events</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 text-gray-300">
                {incidents.slice(0, 8).map(inc => (
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
                    <td className="py-3.5 px-4 font-mono text-gray-400">{inc.total_events}</td>
                    <td className="py-3.5 px-4 text-right">
                      <button className="text-blue-400 hover:text-blue-300 font-mono text-xs inline-flex items-center gap-1">
                        Investigate <ArrowUpRight className="w-3.5 h-3.5" />
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
