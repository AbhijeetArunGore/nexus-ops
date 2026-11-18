import {
  IncidentSummary, IncidentDetail, TimelineResponse,
  BlastRadiusResponse, EvidenceGraphResponse, WhatAmIMissingResponse,
  TelemetryGapItem, Runbook, ScenarioMeta, CopilotResponse
} from '../types';

const API_BASE = '/api/v1';

export const api = {
  // Health
  getHealth: async () => {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },
  getReady: async () => {
    const res = await fetch(`${API_BASE}/ready`);
    return res.json();
  },

  // Analyses
  pasteLogs: async (content: string, title?: string): Promise<IncidentSummary> => {
    const res = await fetch(`${API_BASE}/analyses/paste`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, title })
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to analyze pasted logs');
    return res.json();
  },

  uploadLogs: async (file: File, title?: string): Promise<IncidentSummary> => {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);

    const res = await fetch(`${API_BASE}/analyses/upload`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Failed to upload log file');
    return res.json();
  },

  // Incidents
  listIncidents: async (filters?: { severity?: string; status?: string; service?: string }): Promise<IncidentSummary[]> => {
    const params = new URLSearchParams();
    if (filters?.severity) params.append('severity', filters.severity);
    if (filters?.status) params.append('status', filters.status);
    if (filters?.service) params.append('service', filters.service);

    const res = await fetch(`${API_BASE}/incidents?${params.toString()}`);
    return res.json();
  },

  getIncident: async (id: string): Promise<IncidentDetail> => {
    const res = await fetch(`${API_BASE}/incidents/${id}`);
    if (!res.ok) throw new Error('Incident not found');
    return res.json();
  },

  updateStatus: async (id: string, status: string) => {
    const res = await fetch(`${API_BASE}/incidents/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    return res.json();
  },

  triggerInvestigation: async (id: string) => {
    const res = await fetch(`${API_BASE}/incidents/${id}/investigate`, { method: 'POST' });
    return res.json();
  },

  getTimeline: async (id: string): Promise<TimelineResponse> => {
    const res = await fetch(`${API_BASE}/incidents/${id}/timeline`);
    return res.json();
  },

  getBlastRadius: async (id: string): Promise<BlastRadiusResponse> => {
    const res = await fetch(`${API_BASE}/incidents/${id}/blast-radius`);
    return res.json();
  },

  getEvidenceGraph: async (id: string): Promise<EvidenceGraphResponse> => {
    const res = await fetch(`${API_BASE}/incidents/${id}/evidence-graph`);
    return res.json();
  },

  getWhatAmIMissing: async (id: string): Promise<WhatAmIMissingResponse> => {
    const res = await fetch(`${API_BASE}/incidents/${id}/what-am-i-missing`, { method: 'POST' });
    return res.json();
  },

  getTelemetryGaps: async (id: string): Promise<TelemetryGapItem[]> => {
    const res = await fetch(`${API_BASE}/incidents/${id}/telemetry-gaps`);
    return res.json();
  },

  submitFeedback: async (id: string, payload: {
    verified_root_cause: string;
    hypothesis_accuracy: string;
    useful_recommendations: string[];
    remediation_notes?: string;
  }) => {
    const res = await fetch(`${API_BASE}/incidents/${id}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return res.json();
  },

  getPostmortem: async (id: string) => {
    const res = await fetch(`${API_BASE}/incidents/${id}/postmortem`);
    return res.json();
  },

  generatePostmortem: async (id: string) => {
    const res = await fetch(`${API_BASE}/incidents/${id}/postmortem`, { method: 'POST' });
    return res.json();
  },

  // Copilot
  askCopilot: async (query: string, mode: 'LEARNING' | 'ENGINEERING', incidentId?: string): Promise<CopilotResponse> => {
    const url = incidentId ? `${API_BASE}/copilot/ask?incident_id=${incidentId}` : `${API_BASE}/copilot/ask`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, mode })
    });
    return res.json();
  },

  // Export Incident Report
  exportIncident: async (id: string, format: 'markdown' | 'json' | 'slack' = 'markdown'): Promise<any> => {
    const res = await fetch(`${API_BASE}/incidents/${id}/export?format=${format}`);
    if (!res.ok) throw new Error('Failed to export incident summary');
    return res.json();
  },

  // Scenarios
  listScenarios: async (): Promise<ScenarioMeta[]> => {
    const res = await fetch(`${API_BASE}/scenarios`);
    return res.json();
  },

  runScenario: async (id: string): Promise<IncidentSummary> => {
    const res = await fetch(`${API_BASE}/scenarios/${id}/run`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run scenario');
    return res.json();
  },

  // Runbooks
  listRunbooks: async (query?: string): Promise<Runbook[]> => {
    const url = query ? `${API_BASE}/runbooks?query=${encodeURIComponent(query)}` : `${API_BASE}/runbooks`;
    const res = await fetch(url);
    return res.json();
  }
};
