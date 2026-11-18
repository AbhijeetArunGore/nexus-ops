import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, FileText, ShieldCheck, Cpu, ArrowRight, Loader2, Sparkles } from 'lucide-react';
import { api } from '../../services/api';

export const LogInvestigator: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'upload' | 'paste'>('paste');
  const [file, setFile] = useState<File | null>(null);
  const [pasteContent, setPasteContent] = useState<string>('');
  const [title, setTitle] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [isDragging, setIsDragging] = useState<boolean>(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      const validExts = ['.log', '.txt', '.json', '.jsonl', '.csv'];
      const hasValidExt = validExts.some(ext => droppedFile.name.toLowerCase().endsWith(ext));
      if (!hasValidExt) {
        setErrorMsg(`Unsupported file type '${droppedFile.name}'. Permitted formats: .log, .txt, .json, .jsonl, .csv`);
        return;
      }
      if (droppedFile.size > 10 * 1024 * 1024) {
        setErrorMsg(`File exceeds maximum permitted size of 10MB.`);
        return;
      }
      setErrorMsg(null);
      setFile(droppedFile);
    }
  };
  const loadSample = () => {
    setTitle("Bank Gateway Degradation & Connection Timeout");
    setPasteContent(`2026-11-18T10:00:00.120Z [payment-api] INFO POST /payments/v1/order txn_id=SYN-TXN-8801 amount=3400.00 currency=INR
2026-11-18T10:00:00.250Z [payment-orchestrator] INFO Dispatching payment authorization to bank-connector txn_id=SYN-TXN-8801
2026-11-18T10:00:00.310Z [bank-connector] INFO Sending ISO8583 authorization to external partner Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret
2026-11-18T10:00:15.350Z [bank-connector] ERROR SocketTimeout: Partner bank did not respond within 15000ms txn_id=SYN-TXN-8801
2026-11-18T10:00:15.360Z [payment-api] ERROR HTTP 504 Gateway Timeout waiting for orchestrator response txn_id=SYN-TXN-8801
2026-11-18T10:00:16.100Z [customer-checkout] ERROR Payment initiation timed out for user 4111222233334444 with cvv: 890
2026-11-18T10:00:18.200Z [order-db] WARN HikariPool connection pool saturation: active=95/100 idle=0 pending_threads=12
2026-11-18T10:00:20.300Z [bank-connector] WARN CircuitBreaker 'AcquiringPartnerA' tripped to OPEN state (error_rate=80%)`);
  };

  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pasteContent.trim()) {
      setErrorMsg("Please provide log content to analyze.");
      return;
    }
    setErrorMsg(null);
    setIsProcessing(true);
    try {
      const res = await api.pasteLogs(pasteContent, title || undefined);
      navigate(`/incidents/${res.id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to process logs.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setErrorMsg("Please select a file to upload.");
      return;
    }
    setErrorMsg(null);
    setIsProcessing(true);
    try {
      const res = await api.uploadLogs(file, title || undefined);
      navigate(`/incidents/${res.id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to upload log file.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
          Telemetry & Log Investigator
          <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            INGESTION ENGINE
          </span>
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Ingest multi-format application logs. Automatically normalizes telemetry, masks PCI/PII data, detects bursts, and establishes deterministic severity.
        </p>
      </div>

      {/* Mode Selector Tabs */}
      <div className="flex border-b border-gray-800">
        <button
          onClick={() => setActiveTab('paste')}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition ${
            activeTab === 'paste'
              ? 'border-blue-500 text-blue-400 bg-blue-500/5'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          Direct Log Paste
        </button>
        <button
          onClick={() => setActiveTab('upload')}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition ${
            activeTab === 'upload'
              ? 'border-blue-500 text-blue-400 bg-blue-500/5'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <UploadCloud className="w-4 h-4" />
          File Upload (.log, .txt, .json, .csv)
        </button>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-lg bg-red-950/60 border border-red-800/80 text-red-300 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {/* Direct Paste Form */}
      {activeTab === 'paste' && (
        <form onSubmit={handlePasteSubmit} className="space-y-6">
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-mono uppercase tracking-wider text-gray-300 font-semibold">
                Investigation Title (Optional)
              </label>
              <button
                type="button"
                onClick={loadSample}
                className="text-xs font-mono text-blue-400 hover:text-blue-300 flex items-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Load Sample Pine Labs Gateway Incident
              </button>
            </div>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Acquiring Partner Latency Spike on UPI & Cards"
              className="w-full px-4 py-2.5 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono"
            />

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-mono uppercase tracking-wider text-gray-300 font-semibold">
                  Raw Log Telemetry Stream
                </label>
                <span className="text-[11px] font-mono text-gray-500">
                  {pasteContent.split('\n').filter(Boolean).length} lines detected
                </span>
              </div>
              <textarea
                rows={12}
                value={pasteContent}
                onChange={(e) => setPasteContent(e.target.value)}
                placeholder="Paste JSONL, Java Log4j/Logback, Python stack traces, or standard server logs here..."
                className="w-full p-4 bg-gray-900 border border-gray-800 rounded-lg text-xs font-mono text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500 leading-relaxed resize-y"
              />
            </div>

            {/* Ingestion Pipeline Guarantees */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-gray-900/60 border border-gray-800/80 text-xs">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-gray-200 font-mono">Automatic Redaction</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">Card PANs, CVVs, API tokens, and secrets masked before storage.</div>
                </div>
              </div>
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-gray-900/60 border border-gray-800/80 text-xs">
                <Cpu className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-gray-200 font-mono">Deterministic Severity</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">Policy rules classify CRITICAL/HIGH/MED based on observed facts.</div>
                </div>
              </div>
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-gray-900/60 border border-gray-800/80 text-xs">
                <Sparkles className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-gray-200 font-mono">Evidence-Grounded AI</div>
                  <div className="text-[11px] text-gray-400 mt-0.5">Hypotheses must cite exact verified event IDs. Non-existent IDs rejected.</div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isProcessing || !pasteContent.trim()}
              className="flex items-center gap-2 px-6 py-3 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-500 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-600/20 font-mono"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing Telemetry...
                </>
              ) : (
                <>
                  Run Deterministic Pipeline
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* File Upload Form */}
      {activeTab === 'upload' && (
        <form onSubmit={handleFileUploadSubmit} className="space-y-6">
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
            <div>
              <label className="text-xs font-mono uppercase tracking-wider text-gray-300 font-semibold block mb-2">
                Investigation Title (Optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Batch Ingestion: Core Banking Settlement Log"
                className="w-full px-4 py-2.5 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-10 text-center transition cursor-pointer ${
                isDragging ? 'border-blue-500 bg-blue-500/10' : 'border-gray-800 hover:border-blue-500/50 bg-gray-900/40'
              }`}
            >
              <input
                type="file"
                id="file-upload"
                accept=".log,.txt,.json,.jsonl,.csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
              />
              <label htmlFor="file-upload" className="cursor-pointer space-y-3 block">
                <UploadCloud className="w-10 h-10 text-blue-400 mx-auto" />
                <div className="text-sm font-semibold text-gray-200">
                  {file ? file.name : "Click to select or drag and drop log file"}
                </div>
                <div className="text-xs text-gray-500 font-mono">
                  Supported formats: .log, .txt, .json, .jsonl, .csv (Max size: 10MB)
                </div>
                {file && (
                  <div className="text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-3 py-1 rounded inline-block">
                    Size: {(file.size / 1024).toFixed(1)} KB
                  </div>
                )}
              </label>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isProcessing || !file}
              className="flex items-center gap-2 px-6 py-3 rounded-lg bg-blue-600 text-white font-semibold text-sm hover:bg-blue-500 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-600/20 font-mono"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading & Normalizing...
                </>
              ) : (
                <>
                  Upload and Ingest
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
