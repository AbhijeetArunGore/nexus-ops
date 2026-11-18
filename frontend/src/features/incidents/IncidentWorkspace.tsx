import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  AlertTriangle, CheckCircle2, Clock, Activity, FileText,
  Network, GitCommit, ShieldAlert, Cpu, Sparkles, BookOpen,
  MessageSquare, History, FileDown, RefreshCw, Send, Check, AlertCircle, Eye
} from 'lucide-react';
import { api } from '../../services/api';
import { IncidentDetail, TimelineResponse, BlastRadiusResponse, EvidenceGraphResponse, WhatAmIMissingResponse, TelemetryGapItem } from '../../types';
import { SeverityBadge } from '../../components/common/SeverityBadge';
import { ImpactBadge } from '../../components/common/ImpactBadge';

export const IncidentWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [loading, setLoading] = useState<boolean>(true);
  const [statusUpdating, setStatusUpdating] = useState<boolean>(false);

  // Tab specific data
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [blastRadius, setBlastRadius] = useState<BlastRadiusResponse | null>(null);
  const [evidenceGraph, setEvidenceGraph] = useState<EvidenceGraphResponse | null>(null);
  const [whatMissing, setWhatMissing] = useState<WhatAmIMissingResponse | null>(null);
  const [telemetryGaps, setTelemetryGaps] = useState<TelemetryGapItem[]>([]);
  const [postmortem, setPostmortem] = useState<any | null>(null);

  // AI & Copilot states
  const [copilotQuery, setCopilotQuery] = useState('');
  const [copilotMode, setCopilotMode] = useState<'LEARNING' | 'ENGINEERING'>('ENGINEERING');
  const [copilotHistory, setCopilotHistory] = useState<Array<{ sender: 'user' | 'bot'; text: string; details?: string; actions?: string[] }>>([]);
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [investigating, setInvestigating] = useState(false);

  // Export states
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<'markdown' | 'json' | 'slack'>('markdown');
  const [exportContent, setExportContent] = useState<string>('');
  const [copySuccess, setCopySuccess] = useState(false);

  // Audit / Feedback states
  const [verifiedCause, setVerifiedCause] = useState('');
  const [accuracy, setAccuracy] = useState<'VERIFIED' | 'PARTIAL' | 'REJECTED'>('VERIFIED');
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);

  const handleExport = async (format: 'markdown' | 'json' | 'slack') => {
    if (!id) return;
    setExportFormat(format);
    try {
      const res = await api.exportIncident(id, format);
      const text = format === 'json' ? JSON.stringify(res, null, 2) : res.content;
      setExportContent(text);
      setExportModalOpen(true);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCopyExport = () => {
    navigator.clipboard.writeText(exportContent);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  const handleDownloadExport = () => {
    const ext = exportFormat === 'json' ? 'json' : (exportFormat === 'slack' ? 'txt' : 'md');
    const blob = new Blob([exportContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${incident?.incident_number || 'incident'}_summary.${ext}`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const loadIncident = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.getIncident(id);
      setIncident(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncident();
  }, [id]);

  // Lazy load tab data
  useEffect(() => {
    if (!id) return;
    if (activeTab === 'timeline' && !timeline) {
      api.getTimeline(id).then(setTimeline);
    } else if (activeTab === 'blast-radius' && !blastRadius) {
      api.getBlastRadius(id).then(setBlastRadius);
    } else if (activeTab === 'evidence-graph' && !evidenceGraph) {
      api.getEvidenceGraph(id).then(setEvidenceGraph);
    } else if (activeTab === 'what-missing' && !whatMissing) {
      api.getWhatAmIMissing(id).then(setWhatMissing);
    } else if (activeTab === 'telemetry-gaps' && telemetryGaps.length === 0) {
      api.getTelemetryGaps(id).then(setTelemetryGaps);
    } else if (activeTab === 'postmortem' && !postmortem) {
      api.getPostmortem(id).then(setPostmortem).catch(() => {});
    }
  }, [activeTab, id]);

  const handleStatusChange = async (newStatus: string) => {
    if (!id) return;
    setStatusUpdating(true);
    try {
      await api.updateStatus(id, newStatus);
      await loadIncident();
    } catch (e) {
      console.error(e);
    } finally {
      setStatusUpdating(false);
    }
  };

  const handleRunInvestigation = async () => {
    if (!id) return;
    setInvestigating(true);
    try {
      await api.triggerInvestigation(id);
      await loadIncident();
      const eg = await api.getEvidenceGraph(id);
      setEvidenceGraph(eg);
    } catch (e) {
      console.error(e);
    } finally {
      setInvestigating(false);
    }
  };

  const handleCopilotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!copilotQuery.trim()) return;

    const query = copilotQuery;
    setCopilotQuery('');
    setCopilotHistory(prev => [...prev, { sender: 'user', text: query }]);
    setCopilotLoading(true);

    try {
      const res = await api.askCopilot(query, copilotMode, id);
      setCopilotHistory(prev => [
        ...prev,
        {
          sender: 'bot',
          text: res.answer,
          details: res.technical_details,
          actions: res.suggested_actions
        }
      ]);
    } catch (err: any) {
      setCopilotHistory(prev => [
        ...prev,
        { sender: 'bot', text: 'Error contacting AI Copilot. Offline heuristic analyzer active.' }
      ]);
    } finally {
      setCopilotLoading(false);
    }
  };

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !verifiedCause) return;
    try {
      await api.submitFeedback(id, {
        verified_root_cause: verifiedCause,
        hypothesis_accuracy: accuracy,
        useful_recommendations: incident?.recommendations.map(r => r.action) || []
      });
      setFeedbackSuccess(true);
      setTimeout(() => setFeedbackSuccess(false), 3000);
    } catch (e) {
      console.error(e);
    }
  };

  const handleGeneratePostmortem = async () => {
    if (!id) return;
    try {
      const res = await api.generatePostmortem(id);
      setPostmortem(res.postmortem);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-sm font-mono text-gray-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-blue-500" />
        Loading Incident Telemetry Workspace...
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="p-12 text-center text-sm font-mono text-gray-400">
        Incident not found.
      </div>
    );
  }

  const TABS = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'timeline', label: 'Timeline', icon: GitCommit },
    { id: 'patterns', label: 'Error Patterns', icon: Cpu },
    { id: 'evidence-graph', label: 'Evidence Graph', icon: Network },
    { id: 'blast-radius', label: 'Service Blast Radius', icon: Activity },
    { id: 'investigation', label: 'AI Investigation', icon: Sparkles },
    { id: 'what-missing', label: 'What Am I Missing?', icon: AlertCircle },
    { id: 'telemetry-gaps', label: 'Telemetry Gaps', icon: Eye },
    { id: 'troubleshooting', label: 'Troubleshooting & Runbooks', icon: BookOpen },
    { id: 'copilot', label: 'Ops Copilot', icon: MessageSquare },
    { id: 'postmortem', label: 'Postmortem', icon: FileDown },
    { id: 'audit', label: 'Learning & Review', icon: History }
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Header & Triage Ribbon */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <span className="font-mono text-xl font-extrabold text-blue-400">{incident.incident_number}</span>
              <SeverityBadge severity={incident.severity} size="md" />
              <ImpactBadge impact={incident.customer_impact} />
              {incident.source_scenario && (
                <span className="text-[11px] font-mono bg-purple-950/60 text-purple-300 border border-purple-800/40 px-2.5 py-0.5 rounded">
                  {incident.source_scenario}
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">{incident.title}</h1>
          </div>

          {/* Incident Status Controller */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-gray-400">STATUS:</span>
            <select
              value={incident.status}
              disabled={statusUpdating}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="bg-gray-900 border border-gray-700 text-xs font-mono text-gray-200 rounded px-3 py-1.5 focus:outline-none focus:border-blue-500 font-semibold uppercase"
            >
              <option value="OPEN">OPEN</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="MITIGATED">MITIGATED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="CLOSED">CLOSED</option>
            </select>

            <button
              onClick={handleRunInvestigation}
              disabled={investigating}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-mono hover:bg-blue-500 transition shadow-lg shadow-blue-600/20 disabled:opacity-50"
            >
              <Sparkles className={`w-3.5 h-3.5 ${investigating ? 'animate-spin' : ''}`} />
              {investigating ? 'Investigating...' : 'Trigger AI Analysis'}
            </button>

            <button
              onClick={() => handleExport('markdown')}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 border border-gray-700 text-gray-200 rounded text-xs font-mono hover:bg-gray-700 transition"
              title="Export shareable incident summary report"
            >
              <FileDown className="w-3.5 h-3.5 text-blue-400" />
              Export Summary
            </button>
          </div>
        </div>

        {/* Affected Services & Timestamp Metas */}
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-gray-400 pt-2 border-t border-gray-800/80">
          <div>Detected: <span className="text-gray-200">{new Date(incident.created_at).toUTCString()}</span></div>
          <div>Total Events: <span className="text-blue-400 font-semibold">{incident.total_events}</span></div>
          <div>Observed Errors: <span className="text-red-400 font-semibold">{incident.total_errors}</span></div>
          <div>Services: {incident.affected_services.map(s => (
            <span key={s} className="ml-1 px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 text-[10px]">{s}</span>
          ))}</div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-gray-800 pb-px">
        {TABS.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-xs font-mono transition shrink-0 ${
                isActive
                  ? 'bg-[#111827] text-blue-400 border-t-2 border-blue-500 font-bold'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-900/40'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Executive Summary */}
          {incident.summary && (
            <div className="bg-[#111827] border border-blue-500/30 rounded-xl p-5 space-y-2">
              <h3 className="text-xs font-mono uppercase tracking-wider text-blue-400 font-semibold flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Executive Forensic Incident Summary
              </h3>
              <p className="text-sm text-gray-200 leading-relaxed font-sans">{incident.summary}</p>
            </div>
          )}

          {/* Deterministic Severity Decision Breakdown */}
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-orange-400" />
                Deterministic Severity Policy Matrix
              </h3>
              <span className="text-xs font-mono text-gray-400">Rules-Based Engine (Non-LLM)</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {incident.severity_rationale?.reasons.map((r, idx) => (
                <div key={idx} className="p-3.5 rounded-lg bg-gray-900/60 border border-gray-800/80 space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="font-bold text-gray-200">{r.rule}</span>
                    <span className="text-amber-400 font-semibold">{r.weight}</span>
                  </div>
                  <p className="text-xs text-gray-400">{r.description}</p>
                  {r.supporting_event_ids.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[10px] font-mono text-gray-500 pt-1">
                      <span>Citations:</span>
                      {r.supporting_event_ids.map(eid => (
                        <span key={eid} className="px-1 rounded bg-gray-800 text-blue-300">{eid}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Normalized Events Stream Table */}
          <div className="bg-[#111827] border border-gray-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-xs font-mono uppercase tracking-wider text-white font-semibold">
                Normalized Telemetry Log Stream ({incident.events.length} Entries)
              </h3>
              <span className="text-[11px] font-mono text-gray-400">Masked & Standardized</span>
            </div>
            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-gray-900/80 text-gray-400 uppercase text-[10px] sticky top-0 border-b border-gray-800">
                  <tr>
                    <th className="py-2.5 px-3">Event ID</th>
                    <th className="py-2.5 px-3">Level</th>
                    <th className="py-2.5 px-3">Service</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Transaction / Trace</th>
                    <th className="py-2.5 px-3">Redacted Message</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 text-gray-300">
                  {incident.events.map(e => (
                    <tr key={e.id} className="hover:bg-gray-800/30">
                      <td className="py-2 px-3 font-bold text-blue-400">{e.event_id}</td>
                      <td className="py-2 px-3">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          e.log_level === 'CRITICAL' ? 'bg-red-950 text-red-400' :
                          e.log_level === 'ERROR' ? 'bg-red-900/60 text-red-300' :
                          e.log_level === 'WARN' ? 'bg-yellow-950 text-yellow-400' : 'bg-gray-800 text-gray-300'
                        }`}>
                          {e.log_level}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-gray-300">{e.service}</td>
                      <td className="py-2 px-3">{e.http_status || '-'}</td>
                      <td className="py-2 px-3 text-[11px] text-gray-400">{e.transaction_id || e.trace_id || '-'}</td>
                      <td className="py-2 px-3 max-w-md truncate text-gray-300" title={e.message}>
                        {e.redaction_applied && <span className="text-amber-400 mr-1.5">[REDACTED]</span>}
                        {e.message}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: TIMELINE */}
      {activeTab === 'timeline' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono">
              Reconstructed Forensic Timeline
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">Chronologically ordered milestones distinguishing earliest underlying causes from customer impact.</p>
          </div>

          {timeline ? (
            <div className="relative pl-6 space-y-6 border-l-2 border-gray-800 ml-3">
              {timeline.items.map((item, idx) => (
                <div key={idx} className="relative group">
                  <div className={`absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full border-2 ${
                    item.tags.includes('FIRST_OBSERVED_EVENT') ? 'bg-blue-500 border-white ring-4 ring-blue-500/20' :
                    item.tags.includes('EARLIEST_UNDERLYING_EVENT') ? 'bg-red-500 border-white ring-4 ring-red-500/20' :
                    item.tags.includes('FIRST_CUSTOMER_IMPACT') ? 'bg-orange-500 border-white ring-4 ring-orange-500/20' :
                    item.tags.includes('RECOVERY_CONFIRMATION') ? 'bg-emerald-500 border-white ring-4 ring-emerald-500/20' :
                    'bg-gray-800 border-gray-600'
                  }`} />
                  <div className="bg-gray-900/80 border border-gray-800 rounded-lg p-4 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-blue-400">{item.event_id}</span>
                        <span className="text-xs font-mono text-gray-300">[{item.service}]</span>
                        {item.http_status && (
                          <span className="text-[10px] font-mono bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded">
                            HTTP {item.http_status}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-gray-500">
                        {item.timestamp ? new Date(item.timestamp).toISOString() : 'Undated sequence'}
                      </span>
                    </div>

                    <p className="text-xs font-mono text-gray-300 leading-relaxed">{item.message}</p>

                    {item.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {item.tags.map(t => (
                          <span key={t} className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                            t === 'FIRST_OBSERVED_EVENT' ? 'bg-blue-950 text-blue-300 border border-blue-800' :
                            t === 'EARLIEST_UNDERLYING_EVENT' ? 'bg-red-950 text-red-300 border border-red-800' :
                            t === 'FIRST_CUSTOMER_IMPACT' ? 'bg-orange-950 text-orange-300 border border-orange-800' :
                            'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          }`}>
                            ★ {t.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs font-mono text-gray-500">Reconstructing timeline...</div>
          )}
        </div>
      )}

      {/* TAB 3: ERROR PATTERNS */}
      {activeTab === 'patterns' && (
        <div className="space-y-6">
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
            <div>
              <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono">
                Normalized Error Fingerprints ({incident.patterns.length})
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">Clustered recurring failure signatures by stripping dynamic transaction IDs, timestamps, and memory hashes.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {incident.patterns.map(p => (
                <div key={p.id} className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-purple-400">FP-{p.fingerprint}</span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-red-950/60 text-red-400 border border-red-800/40 font-bold">
                      {p.occurrence_count} Occurrences
                    </span>
                  </div>
                  <div className="text-xs font-mono text-gray-400">Service: <span className="text-gray-200">{p.service}</span></div>
                  <div className="p-2.5 rounded bg-gray-950 border border-gray-800 font-mono text-xs text-gray-300 break-words">
                    {p.pattern_template}
                  </div>
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-gray-500 pt-1">
                    <span>Sample Events:</span>
                    {p.sample_event_ids.map(eid => (
                      <span key={eid} className="px-1.5 py-0.5 rounded bg-gray-800 text-blue-300">{eid}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: EVIDENCE GRAPH */}
      {activeTab === 'evidence-graph' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono">
                Verifiable Evidence & Attribution Graph
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">Bipartite graph tracing AI Hypotheses directly to concrete, immutable Event IDs (`EVT-xxx`). Non-existent IDs rejected.</p>
            </div>
          </div>

          {evidenceGraph ? (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-4 space-y-3">
                  <h4 className="text-xs font-mono font-bold uppercase text-purple-400">1. Hypotheses (Roots)</h4>
                  {evidenceGraph.nodes.filter(n => n.type === 'hypothesis').map(n => (
                    <div key={n.id} className="p-3 rounded bg-gray-800/60 border border-purple-800/40 space-y-1">
                      <div className="font-mono text-xs font-bold text-white">{n.label}</div>
                      <div className="text-[11px] text-gray-400">{n.metadata?.description}</div>
                      <span className="text-[10px] font-mono text-purple-300 font-bold">Confidence: {n.metadata?.confidence}</span>
                    </div>
                  ))}
                </div>

                <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-4 space-y-3">
                  <h4 className="text-xs font-mono font-bold uppercase text-blue-400">2. Supporting Events (Facts)</h4>
                  <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                    {evidenceGraph.nodes.filter(n => n.type === 'event').map(n => (
                      <div key={n.id} className="p-2 rounded bg-gray-800/60 border border-gray-700 text-xs font-mono text-blue-300 flex items-center justify-between">
                        <span>{n.label}</span>
                        <span className="text-[10px] text-gray-500">INGESTED FACT</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-4 space-y-3">
                  <h4 className="text-xs font-mono font-bold uppercase text-emerald-400">3. Actionable Mitigation</h4>
                  {evidenceGraph.nodes.filter(n => n.type === 'recommendation').map(n => (
                    <div key={n.id} className="p-3 rounded bg-gray-800/60 border border-emerald-800/40 space-y-1">
                      <div className="font-mono text-xs font-bold text-emerald-300">{n.label}</div>
                      <div className="text-[11px] text-gray-400">{n.metadata?.rationale}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-xs font-mono text-gray-500">Compiling evidence graph...</div>
          )}
        </div>
      )}

      {/* TAB 5: BLAST RADIUS */}
      {activeTab === 'blast-radius' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono">
              Topological Service Dependency & Blast Radius Analyzer
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Distinguishes between <span className="text-red-400 font-bold">OBSERVED IMPACT</span> (actual errors in logs) and <span className="text-orange-400 font-bold">POTENTIAL BLAST RADIUS</span> (exposed upstream callers).
            </p>
          </div>

          {blastRadius ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {blastRadius.nodes.map(node => (
                <div
                  key={node.service}
                  className={`p-4 rounded-xl border space-y-2 ${
                    node.status === 'OBSERVED_IMPACT'
                      ? 'bg-red-950/40 border-red-700/60'
                      : node.status === 'POTENTIAL_BLAST_RADIUS'
                      ? 'bg-orange-950/30 border-orange-700/50'
                      : 'bg-gray-900/40 border-gray-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-white">{node.service}</span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                      node.status === 'OBSERVED_IMPACT' ? 'bg-red-900 text-red-300' :
                      node.status === 'POTENTIAL_BLAST_RADIUS' ? 'bg-orange-900 text-orange-300' : 'bg-gray-800 text-gray-400'
                    }`}>
                      {node.status}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-gray-400">
                    Observed Errors: <span className="font-bold text-gray-200">{node.error_count}</span>
                  </div>
                  <p className="text-[11px] text-gray-400">
                    {node.status === 'OBSERVED_IMPACT' ? 'Direct failure events logged in service telemetry.' :
                     node.status === 'POTENTIAL_BLAST_RADIUS' ? 'Exposed to downstream timeout propagation via dependency tree.' :
                     'Operating within normal latency parameters.'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs font-mono text-gray-500">Traversing service topology DAG...</div>
          )}
        </div>
      )}

      {/* TAB 6: AI INVESTIGATION */}
      {activeTab === 'investigation' && (
        <div className="space-y-6">
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  Evidence-Grounded AI Hypotheses
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">Strictly verified against ingested telemetry. Hallucinated event citations are purged.</p>
              </div>
              <button
                onClick={handleRunInvestigation}
                disabled={investigating}
                className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-mono hover:bg-blue-500 transition"
              >
                {investigating ? 'Analyzing...' : 'Re-run Analysis'}
              </button>
            </div>

            {incident.hypotheses.length === 0 ? (
              <div className="text-center py-8 space-y-3">
                <p className="text-xs font-mono text-gray-400">No AI hypotheses generated yet.</p>
                <button
                  onClick={handleRunInvestigation}
                  className="px-4 py-2 bg-blue-600 text-white rounded text-xs font-mono font-semibold"
                >
                  Generate Initial Investigation
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {incident.hypotheses.map(h => (
                  <div
                    key={h.id}
                    className={`p-5 rounded-xl border space-y-3 ${
                      h.is_primary ? 'bg-blue-950/20 border-blue-600/50' : 'bg-gray-900/60 border-gray-800'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-blue-400">{h.hypothesis_code}</span>
                        <span className="font-semibold text-white text-sm">{h.title}</span>
                        {h.is_primary && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-600 text-white font-bold">
                            PRIMARY HYPOTHESIS
                          </span>
                        )}
                      </div>
                      <span className="text-xs font-mono font-bold text-amber-400">Confidence: {h.confidence}</span>
                    </div>

                    <p className="text-xs text-gray-300 leading-relaxed font-sans">{h.description}</p>

                    {/* Supporting Evidence Citations */}
                    <div className="space-y-1.5 pt-2 border-t border-gray-800/80">
                      <div className="text-[11px] font-mono uppercase text-gray-400 font-semibold">Supporting Forensic Citations:</div>
                      <div className="flex flex-wrap gap-1.5">
                        {h.supporting_evidence_codes.map(code => (
                          <span key={code} className="px-2 py-0.5 rounded bg-gray-800 text-blue-300 font-mono text-xs border border-gray-700">
                            {code}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Verification Checklist */}
                    {h.verification_steps.length > 0 && (
                      <div className="space-y-1.5 pt-1">
                        <div className="text-[11px] font-mono uppercase text-gray-400 font-semibold">Verification Procedure:</div>
                        <ul className="space-y-1">
                          {h.verification_steps.map((step, idx) => (
                            <li key={idx} className="text-xs text-gray-400 flex items-start gap-2 font-mono">
                              <span className="text-blue-400">→</span>
                              <span>{step}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 7: WHAT AM I MISSING? */}
      {activeTab === 'what-missing' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              'What Am I Missing?' Adversarial Audit
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">Second-pass critical analysis designed to challenge initial diagnosis, uncover telemetry blindspots, and prevent premature closure.</p>
          </div>

          {whatMissing ? (
            <div className="space-y-6">
              {/* Prioritized Gaps Checklist */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono font-bold uppercase text-gray-300">Identified Forensic Gaps & Ambiguities</h4>
                {whatMissing.gaps_identified.map((gap, idx) => (
                  <div key={idx} className="p-4 rounded-lg bg-gray-900 border border-gray-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-gray-200">{gap.category}</span>
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                        gap.risk_level === 'CRITICAL' ? 'bg-red-950 text-red-400' :
                        gap.risk_level === 'HIGH' ? 'bg-orange-950 text-orange-400' : 'bg-yellow-950 text-yellow-400'
                      }`}>
                        {gap.risk_level} RISK
                      </span>
                    </div>
                    <p className="text-xs text-gray-300">{gap.description}</p>
                    <div className="text-xs font-mono text-emerald-400 bg-emerald-950/30 p-2 rounded border border-emerald-900/40">
                      Check: {gap.recommended_check}
                    </div>
                  </div>
                ))}
              </div>

              {/* Alternative Hypotheses */}
              <div className="p-4 rounded-lg bg-gray-900/60 border border-gray-800 space-y-2">
                <h4 className="text-xs font-mono font-bold uppercase text-blue-400">Alternative Hypotheses to Consider</h4>
                <ul className="space-y-1.5">
                  {whatMissing.alternative_hypotheses.map((alt, idx) => (
                    <li key={idx} className="text-xs font-mono text-gray-300 flex items-start gap-2">
                      <span className="text-blue-400">?</span>
                      <span>{alt}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="text-xs font-mono text-gray-500">Auditing diagnostic assumptions...</div>
          )}
        </div>
      )}

      {/* TAB 8: TELEMETRY GAPS */}
      {activeTab === 'telemetry-gaps' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono flex items-center gap-2">
              <Eye className="w-4 h-4 text-purple-400" />
              Telemetry Gap Detector & Instrumentation Guide
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">Identifies missing signals (trace propagation, duration metrics, state machines) to improve future observability.</p>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {telemetryGaps.map((gap, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-bold text-white">{gap.missing_signal}</span>
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                    gap.priority === 'HIGH' ? 'bg-red-950 text-red-400 border border-red-800/40' : 'bg-yellow-950 text-yellow-400'
                  }`}>
                    {gap.priority} PRIORITY
                  </span>
                </div>
                <div className="text-xs font-mono text-gray-400">Affected Boundary: <span className="text-gray-200">{gap.affected_service}</span></div>
                <p className="text-xs text-gray-300">{gap.operational_impact}</p>
                <div className="p-2.5 rounded bg-gray-950 border border-gray-800 text-xs font-mono text-emerald-400">
                  Fix: {gap.instrumentation_fix}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 9: TROUBLESHOOTING & RUNBOOKS */}
      {activeTab === 'troubleshooting' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono">
              Actionable Troubleshooting & Recommended Procedures
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">Matched from curated SRE catalog based on observed failure patterns.</p>
          </div>

          <div className="space-y-4">
            {incident.recommendations.map(r => (
              <div key={r.id} className="p-4 rounded-xl bg-gray-900 border border-gray-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-emerald-400">PRIORITY #{r.priority}</span>
                  {r.associated_runbook_id && (
                    <span className="text-xs font-mono text-blue-400 bg-blue-950/60 px-2 py-0.5 rounded border border-blue-800/50">
                      {r.associated_runbook_id}
                    </span>
                  )}
                </div>
                <div className="text-sm font-bold text-white">{r.action}</div>
                <p className="text-xs text-gray-400">{r.rationale}</p>
                {r.verification_step && (
                  <div className="text-xs font-mono text-emerald-400 bg-emerald-950/20 p-2.5 rounded border border-emerald-900/30">
                    Verification: {r.verification_step}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 10: OPS COPILOT (EMBEDDED) */}
      {activeTab === 'copilot' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-blue-400" />
                Ops Knowledge Copilot (Incident Grounded)
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">Ask questions grounded in the telemetry and evidence of {incident.incident_number}.</p>
            </div>
            {/* Mode Switcher */}
            <div className="flex items-center gap-1 bg-gray-900 p-1 rounded border border-gray-800 text-xs font-mono">
              <button
                onClick={() => setCopilotMode('LEARNING')}
                className={`px-3 py-1 rounded transition ${copilotMode === 'LEARNING' ? 'bg-blue-600 text-white font-bold' : 'text-gray-400'}`}
              >
                LEARNING MODE
              </button>
              <button
                onClick={() => setCopilotMode('ENGINEERING')}
                className={`px-3 py-1 rounded transition ${copilotMode === 'ENGINEERING' ? 'bg-blue-600 text-white font-bold' : 'text-gray-400'}`}
              >
                ENGINEERING MODE
              </button>
            </div>
          </div>

          {/* Chat Stream */}
          <div className="min-h-64 max-h-96 overflow-y-auto space-y-4 pr-2">
            {copilotHistory.length === 0 ? (
              <div className="text-center py-10 space-y-3">
                <p className="text-xs font-mono text-gray-500">Ask any operational or architectural question about this incident.</p>
                <div className="flex flex-wrap justify-center gap-2 max-w-xl mx-auto">
                  {[
                    "Why was this marked with its current severity?",
                    "What evidence supports the leading hypothesis?",
                    "How do we verify complete payment recovery?",
                    "What telemetry is missing to confirm root cause?"
                  ].map(prompt => (
                    <button
                      key={prompt}
                      onClick={() => setCopilotQuery(prompt)}
                      className="text-[11px] font-mono bg-gray-900 hover:bg-gray-800 text-gray-300 px-3 py-1.5 rounded border border-gray-800 transition text-left"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              copilotHistory.map((item, idx) => (
                <div key={idx} className={`p-4 rounded-xl text-xs space-y-2 ${
                  item.sender === 'user' ? 'bg-blue-950/30 border border-blue-800/40 ml-12 text-blue-200' : 'bg-gray-900 border border-gray-800 mr-12 text-gray-200'
                }`}>
                  <div className="font-mono text-[10px] text-gray-500 uppercase">{item.sender === 'user' ? 'You' : 'Ops Copilot'}</div>
                  <div className="leading-relaxed font-sans">{item.text}</div>
                  {item.details && (
                    <div className="p-2.5 rounded bg-gray-950 border border-gray-800 font-mono text-emerald-400 text-[11px]">
                      {item.details}
                    </div>
                  )}
                  {item.actions && item.actions.length > 0 && (
                    <div className="space-y-1 pt-1">
                      <div className="font-mono text-[10px] uppercase text-gray-400 font-bold">Suggested Actions:</div>
                      {item.actions.map((act, i) => (
                        <div key={i} className="font-mono text-[11px] text-gray-400">→ {act}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
            {copilotLoading && (
              <div className="text-xs font-mono text-gray-500 animate-pulse">
                Copilot is formulating grounded response...
              </div>
            )}
          </div>

          {/* Chat Input */}
          <form onSubmit={handleCopilotSubmit} className="flex gap-2">
            <input
              type="text"
              value={copilotQuery}
              onChange={(e) => setCopilotQuery(e.target.value)}
              placeholder="Ask about this incident, payment status, or runbook steps..."
              className="flex-1 px-4 py-2.5 bg-gray-900 border border-gray-800 rounded-lg text-xs font-mono text-gray-200 focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={!copilotQuery.trim() || copilotLoading}
              className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-xs font-mono font-semibold hover:bg-blue-500 disabled:opacity-50 transition"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}

      {/* TAB 11: POSTMORTEM */}
      {activeTab === 'postmortem' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono">
                Postmortem Report Drafter
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">Objective, blameless SRE postmortem grounded in observed telemetry and verified actions.</p>
            </div>
            <button
              onClick={handleGeneratePostmortem}
              className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-mono hover:bg-blue-500 transition"
            >
              {postmortem ? 'Regenerate Draft' : 'Draft Postmortem'}
            </button>
          </div>

          {postmortem ? (
            <div className="space-y-6">
              <div className="p-4 rounded-lg bg-gray-900 border border-gray-800 space-y-2">
                <span className="font-mono text-xs text-blue-400 font-bold uppercase">Executive Summary</span>
                <p className="text-xs text-gray-300 leading-relaxed font-sans">{postmortem.executive_summary}</p>
              </div>

              <div className="p-4 rounded-lg bg-gray-900 border border-gray-800 space-y-2">
                <span className="font-mono text-xs text-amber-400 font-bold uppercase">Root Cause Analysis</span>
                <p className="text-xs text-gray-300 leading-relaxed font-sans">{postmortem.root_cause_analysis}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-800/40 space-y-2">
                  <span className="font-mono text-xs text-emerald-400 font-bold uppercase">What Went Well</span>
                  <ul className="space-y-1">
                    {postmortem.what_went_well?.map((item: string, i: number) => (
                      <li key={i} className="text-xs text-gray-300 font-mono">✓ {item}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-4 rounded-lg bg-red-950/20 border border-red-800/40 space-y-2">
                  <span className="font-mono text-xs text-red-400 font-bold uppercase">What Went Wrong</span>
                  <ul className="space-y-1">
                    {postmortem.what_went_wrong?.map((item: string, i: number) => (
                      <li key={i} className="text-xs text-gray-300 font-mono">✕ {item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Action Items */}
              <div className="p-4 rounded-lg bg-gray-900 border border-gray-800 space-y-3">
                <span className="font-mono text-xs text-blue-400 font-bold uppercase">Preventive Action Items</span>
                <div className="space-y-2">
                  {postmortem.action_items?.map((act: any, i: number) => (
                    <div key={i} className="flex items-center justify-between p-2.5 rounded bg-gray-950 border border-gray-800 text-xs font-mono">
                      <span className="text-gray-200">{act.action}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-gray-500">Owner: {act.owner}</span>
                        <span className="px-1.5 py-0.5 rounded bg-blue-900 text-blue-300 font-bold">{act.priority}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 space-y-3">
              <p className="text-xs font-mono text-gray-500">No postmortem drafted yet.</p>
              <button
                onClick={handleGeneratePostmortem}
                className="px-4 py-2 bg-blue-600 text-white rounded text-xs font-mono font-semibold"
              >
                Draft Postmortem Now
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 12: INCIDENT LEARNING & AUDIT */}
      {activeTab === 'audit' && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-white uppercase font-mono">
              Human-in-the-Loop Incident Learning Hub
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Confirm verified root causes, reject incorrect AI hypotheses, and store human-reviewed outcomes for future incident retrieval.
            </p>
          </div>

          <form onSubmit={handleFeedbackSubmit} className="space-y-4 max-w-2xl">
            <div>
              <label className="text-xs font-mono uppercase text-gray-300 font-semibold block mb-1.5">
                Engineer Verified Root Cause
              </label>
              <textarea
                rows={3}
                value={verifiedCause}
                onChange={(e) => setVerifiedCause(e.target.value)}
                placeholder="Document the definitive verified cause after resolution (e.g. acquiring bank database deadlock confirmed by partner NOC)..."
                className="w-full p-3 bg-gray-900 border border-gray-800 rounded-lg text-xs font-mono text-gray-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="text-xs font-mono uppercase text-gray-300 font-semibold block mb-1.5">
                AI Hypothesis Accuracy Evaluation
              </label>
              <div className="flex gap-4">
                {(['VERIFIED', 'PARTIAL', 'REJECTED'] as const).map(opt => (
                  <label key={opt} className="flex items-center gap-2 text-xs font-mono text-gray-300 cursor-pointer">
                    <input
                      type="radio"
                      name="accuracy"
                      value={opt}
                      checked={accuracy === opt}
                      onChange={() => setAccuracy(opt)}
                      className="text-blue-600"
                    />
                    <span>{opt}</span>
                  </label>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={!verifiedCause.trim()}
              className="px-5 py-2.5 bg-blue-600 text-white rounded text-xs font-mono font-semibold hover:bg-blue-500 disabled:opacity-50 transition"
            >
              Commit Verified Outcome
            </button>

            {feedbackSuccess && (
              <span className="ml-3 text-xs font-mono text-emerald-400">
                ✓ Recorded to verified learning store!
              </span>
            )}
          </form>
        </div>
      )}

      {/* Export Shareable Summary Modal */}
      {exportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-[#111827] border border-gray-800 rounded-xl max-w-3xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2">
                <FileDown className="w-5 h-5 text-blue-400" />
                <h3 className="text-sm font-bold text-white font-mono uppercase">
                  Shareable Incident Summary ({exportFormat.toUpperCase()})
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleExport('markdown')}
                  className={`px-2.5 py-1 text-xs font-mono rounded ${exportFormat === 'markdown' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300'}`}
                >
                  Markdown
                </button>
                <button
                  onClick={() => handleExport('json')}
                  className={`px-2.5 py-1 text-xs font-mono rounded ${exportFormat === 'json' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300'}`}
                >
                  JSON
                </button>
                <button
                  onClick={() => handleExport('slack')}
                  className={`px-2.5 py-1 text-xs font-mono rounded ${exportFormat === 'slack' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-300'}`}
                >
                  Slack
                </button>
                <button
                  onClick={() => setExportModalOpen(false)}
                  className="text-gray-400 hover:text-white text-sm ml-2 font-mono px-2"
                >
                  ✕
                </button>
              </div>
            </div>

            <textarea
              readOnly
              rows={14}
              value={exportContent}
              className="w-full p-3 bg-gray-950 border border-gray-800 rounded-lg text-xs font-mono text-gray-200 focus:outline-none resize-none leading-relaxed"
            />

            <div className="flex items-center justify-between pt-2">
              <span className="text-[11px] font-mono text-gray-500">
                Ready for on-call bridge, postmortem archive, or Slack notification.
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleCopyExport}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded text-xs font-mono font-semibold transition"
                >
                  {copySuccess ? '✓ Copied!' : 'Copy to Clipboard'}
                </button>
                <button
                  onClick={handleDownloadExport}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-mono font-semibold transition flex items-center gap-1.5"
                >
                  <FileDown className="w-3.5 h-3.5" />
                  Download File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
