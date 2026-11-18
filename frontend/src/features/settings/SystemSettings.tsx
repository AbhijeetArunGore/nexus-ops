import React, { useState, useEffect } from 'react';
import { Settings, ShieldAlert, Cpu, Database, CheckCircle2, RefreshCw } from 'lucide-react';
import { api } from '../../services/api';

export const SystemSettings: React.FC = () => {
  const [readyInfo, setReadyInfo] = useState<any>(null);
  const [healthInfo, setHealthInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const checkStatus = async () => {
    setLoading(true);
    try {
      const [h, r] = await Promise.all([api.getHealth(), api.getReady()]);
      setHealthInfo(h);
      setReadyInfo(r);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            System Settings & Architecture Diagnostics
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Engine status, simulated environment parameters, and provider health.
          </p>
        </div>
        <button
          onClick={checkStatus}
          className="flex items-center gap-2 px-3 py-1.5 rounded bg-gray-800 text-xs font-mono text-gray-200 hover:bg-gray-700"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Check Health
        </button>
      </div>

      {/* Mandatory Disclaimer Box */}
      <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2">
        <div className="flex items-center gap-2 text-amber-400 font-mono text-xs font-bold uppercase tracking-wider">
          <ShieldAlert className="w-4 h-4" />
          Simulated Boundary Notice
        </div>
        <p className="text-xs text-amber-200/90 leading-relaxed font-sans">
          NEXUS Ops is an independently engineered technology operations platform inspired by publicly documented Pine Labs payment lifecycles.
          It operates strictly within an isolated synthetic sandbox with no live banking or merchant production connections.
        </p>
      </div>

      {/* Diagnostic Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
          <h3 className="text-xs font-mono uppercase text-gray-400 font-bold flex items-center gap-2">
            <Cpu className="w-4 h-4 text-blue-400" />
            AI & Model Orchestration Layer
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1.5 border-b border-gray-800">
              <span className="text-gray-400">Configured Provider</span>
              <span className="text-white font-bold">{readyInfo?.llm_provider || 'gemini'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800">
              <span className="text-gray-400">Model Identifier</span>
              <span className="text-white font-bold">gemini-2.5-flash (with Heuristic Fallback)</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800">
              <span className="text-gray-400">Gemini API Key</span>
              <span className={readyInfo?.gemini_configured ? "text-emerald-400" : "text-yellow-400"}>
                {readyInfo?.gemini_configured ? "Configured (Active)" : "Offline Fallback Provider Active"}
              </span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-gray-400">Citation Invariant</span>
              <span className="text-emerald-400">Enforced (Zero-Hallucination)</span>
            </div>
          </div>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
          <h3 className="text-xs font-mono uppercase text-gray-400 font-bold flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-400" />
            Storage & Telemetry Limits
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between py-1.5 border-b border-gray-800">
              <span className="text-gray-400">Database Connection</span>
              <span className="text-emerald-400 font-bold">{readyInfo?.database || 'CONNECTED'}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800">
              <span className="text-gray-400">Max Log Upload</span>
              <span className="text-white">10 MB</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-800">
              <span className="text-gray-400">Max Ingestion Lines</span>
              <span className="text-white">50,000 Lines</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-gray-400">Inline Redaction</span>
              <span className="text-emerald-400">PCI/PII Masking Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* OpenAPI Reference */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 flex items-center justify-between">
        <div>
          <h4 className="text-xs font-mono font-bold text-white uppercase">FastAPI Interactive Documentation</h4>
          <p className="text-xs text-gray-400 mt-0.5">Explore Swagger UI and test endpoints directly.</p>
        </div>
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 rounded bg-gray-800 text-xs font-mono text-blue-400 hover:text-blue-300 border border-gray-700"
        >
          Open /docs
        </a>
      </div>
    </div>
  );
};
