import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FlaskConical, Play, ArrowRight, ShieldCheck, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { api } from '../../services/api';
import { ScenarioMeta } from '../../types';
import { SeverityBadge } from '../../components/common/SeverityBadge';

export const PaymentReliabilityLab: React.FC = () => {
  const navigate = useNavigate();
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [runningId, setRunningId] = useState<string | null>(null);

  useEffect(() => {
    api.listScenarios().then(data => {
      setScenarios(data);
      setLoading(false);
    });
  }, []);

  const handleRunScenario = async (id: string) => {
    setRunningId(id);
    try {
      const res = await api.runScenario(id);
      navigate(`/incidents/${res.id}`);
    } catch (e) {
      console.error(e);
      setRunningId(null);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Pine Payment Reliability Lab
          </h1>
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
            SIMULATION BENCHMARK
          </span>
        </div>
        <p className="text-sm text-gray-400 mt-1">
          Selectable payment incident scenarios inspired by publicly documented Pine Labs payment lifecycles.
          Every scenario processes synthetic logs through the live deterministic analysis engine.
        </p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-xs font-mono text-gray-500">
          Loading scenario library...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {scenarios.map((scen, idx) => (
            <div
              key={scen.id}
              className="bg-[#111827] border border-gray-800 hover:border-gray-700 rounded-xl p-6 flex flex-col justify-between space-y-4 transition"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-purple-400 font-bold uppercase tracking-wider">
                    {scen.category}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-gray-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-800">
                      {scen.difficulty}
                    </span>
                    <SeverityBadge severity={scen.expected_severity} size="sm" />
                  </div>
                </div>

                <h3 className="text-base font-bold text-white tracking-tight">{scen.title}</h3>
                <p className="text-xs text-gray-300 leading-relaxed font-sans">{scen.description}</p>

                <div className="p-3 rounded-lg bg-gray-900/80 border border-gray-800/80 space-y-1 text-xs font-mono">
                  <div className="text-[10px] text-gray-500 uppercase font-bold">Key Architectural Lesson:</div>
                  <div className="text-blue-300 leading-snug">{scen.key_learning}</div>
                </div>
              </div>

              <div className="pt-2 border-t border-gray-800/80 flex items-center justify-between">
                <span className="text-[11px] font-mono text-gray-500">
                  Expected Root Cause: {scen.expected_primary_hypothesis.slice(0, 32)}...
                </span>
                <button
                  onClick={() => handleRunScenario(scen.id)}
                  disabled={runningId !== null}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-mono font-semibold transition shadow-lg shadow-blue-600/20 disabled:opacity-50"
                >
                  {runningId === scen.id ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Simulating...
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      Run Live Simulation
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
