import React, { useState } from 'react';
import { BotMessageSquare, Send, Sparkles, BookOpen, Terminal, HelpCircle } from 'lucide-react';
import { api } from '../../services/api';

export const OpsKnowledgeCopilot: React.FC = () => {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'LEARNING' | 'ENGINEERING'>('ENGINEERING');
  const [history, setHistory] = useState<Array<{ sender: 'user' | 'bot'; text: string; details?: string; actions?: string[]; refs?: string[] }>>([
    {
      sender: 'bot',
      text: "Welcome to the NEXUS Ops Technical Copilot. I am trained on public Pine Labs developer documentation, SRE postmortem standards, and payment architecture troubleshooting procedures.",
      details: "Select LEARNING mode for foundational concepts (freshers/L1), or ENGINEERING mode for forensic analysis, pg_stat_activity queries, and circuit-breaker diagnostics (L2/L3 SREs)."
    }
  ]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userQ = query;
    setQuery('');
    setHistory(prev => [...prev, { sender: 'user', text: userQ }]);
    setLoading(true);

    try {
      const res = await api.askCopilot(userQ, mode);
      setHistory(prev => [
        ...prev,
        {
          sender: 'bot',
          text: res.answer,
          details: res.technical_details,
          actions: res.suggested_actions,
          refs: res.source_references
        }
      ]);
    } catch (e) {
      setHistory(prev => [
        ...prev,
        { sender: 'bot', text: 'Error contacting Copilot service. Fallback heuristic active.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const SAMPLE_QUESTIONS = [
    { label: "What is HTTP 504 in payments?", q: "What is HTTP 504 and what does it mean for a payment transaction?" },
    { label: "How does idempotency work?", q: "How should payment idempotency prevent duplicate debit during timeouts?" },
    { label: "Distinguish network latency from DB pool exhaustion", q: "How do we distinguish network latency from database connection exhaustion?" },
    { label: "How should webhook consumers handle duplicates?", q: "How should webhook consumers handle duplicate event deliveries?" },
    { label: "Diagnosing pg_stat_activity lockups", q: "Which PostgreSQL database metrics and queries establish connection pool saturation?" }
  ];

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            Ops Knowledge Copilot
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30">
              DUAL EXPLANATION
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Conversational SRE & payment architecture assistant supporting both educational and deep engineering modes.
          </p>
        </div>

        {/* Dual Mode Switch */}
        <div className="flex items-center gap-1 bg-[#111827] p-1.5 rounded-lg border border-gray-800 text-xs font-mono">
          <button
            onClick={() => setMode('LEARNING')}
            className={`px-3 py-1.5 rounded transition ${
              mode === 'LEARNING' ? 'bg-blue-600 text-white font-bold' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            LEARNING MODE (L1 / Interns)
          </button>
          <button
            onClick={() => setMode('ENGINEERING')}
            className={`px-3 py-1.5 rounded transition ${
              mode === 'ENGINEERING' ? 'bg-blue-600 text-white font-bold' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            ENGINEERING MODE (L2/L3 / SREs)
          </button>
        </div>
      </div>

      {/* Suggested Questions Pill Carousel */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        <span className="text-xs font-mono text-gray-500 shrink-0">SUGGESTED:</span>
        {SAMPLE_QUESTIONS.map(sq => (
          <button
            key={sq.label}
            onClick={() => setQuery(sq.q)}
            className="text-xs font-mono bg-gray-900 hover:bg-gray-800 text-gray-300 px-3 py-1.5 rounded border border-gray-800 transition shrink-0"
          >
            {sq.label}
          </button>
        ))}
      </div>

      {/* Chat Messages Window */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 min-h-[420px] max-h-[550px] overflow-y-auto space-y-4">
        {history.map((msg, idx) => (
          <div
            key={idx}
            className={`p-4 rounded-xl text-xs space-y-2.5 ${
              msg.sender === 'user'
                ? 'bg-blue-950/30 border border-blue-800/40 ml-16 text-blue-200'
                : 'bg-gray-900 border border-gray-800 mr-16 text-gray-200'
            }`}
          >
            <div className="flex items-center justify-between text-[10px] font-mono text-gray-500 uppercase">
              <span>{msg.sender === 'user' ? 'Operator' : `Copilot [${mode}]`}</span>
            </div>

            <p className="leading-relaxed font-sans text-sm text-gray-100">{msg.text}</p>

            {msg.details && (
              <div className="p-3 rounded bg-gray-950 border border-gray-800 font-mono text-emerald-400 text-xs">
                {msg.details}
              </div>
            )}

            {msg.actions && msg.actions.length > 0 && (
              <div className="space-y-1 pt-1 border-t border-gray-800/80">
                <span className="text-[10px] font-mono uppercase text-gray-400 font-bold">Recommended Diagnostic Actions:</span>
                {msg.actions.map((act, i) => (
                  <div key={i} className="text-xs font-mono text-gray-300">→ {act}</div>
                ))}
              </div>
            )}

            {msg.refs && msg.refs.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-1 text-[10px] font-mono text-gray-500">
                <span>References:</span>
                {msg.refs.map((r, i) => (
                  <span key={i} className="text-blue-400 underline">{r}</span>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="text-xs font-mono text-gray-400 animate-pulse flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-400 animate-spin" />
            Synthesizing technical response...
          </div>
        )}
      </div>

      {/* Input Box */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`Ask a question in ${mode} mode (e.g. How does idempotency protect against double charges?)...`}
          className="flex-1 px-4 py-3 bg-[#111827] border border-gray-800 rounded-xl text-xs font-mono text-gray-200 focus:outline-none focus:border-blue-500"
        />
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-mono font-semibold transition disabled:opacity-50 flex items-center gap-2"
        >
          <Send className="w-4 h-4" />
          Ask Copilot
        </button>
      </form>
    </div>
  );
};
