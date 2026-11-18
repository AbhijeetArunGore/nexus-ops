import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/common/Navbar';
import { Sidebar } from './components/common/Sidebar';
import { OperationsOverview } from './features/dashboard/OperationsOverview';
import { LogInvestigator } from './features/investigator/LogInvestigator';
import { IncidentList } from './features/incidents/IncidentList';
import { IncidentWorkspace } from './features/incidents/IncidentWorkspace';
import { PaymentReliabilityLab } from './features/simulations/PaymentReliabilityLab';
import { OpsKnowledgeCopilot } from './features/copilot/OpsKnowledgeCopilot';
import { RunbookLibrary } from './features/runbooks/RunbookLibrary';
import { IncidentLearningHub } from './features/learning/IncidentLearningHub';
import { SystemSettings } from './features/settings/SystemSettings';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0B0F19] text-gray-100 flex flex-col font-['Plus_Jakarta_Sans',sans-serif]">
        <Navbar />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 overflow-y-auto min-h-[calc(100vh-3.5rem)]">
            <Routes>
              <Route path="/" element={<OperationsOverview />} />
              <Route path="/investigate" element={<LogInvestigator />} />
              <Route path="/incidents" element={<IncidentList />} />
              <Route path="/incidents/:id" element={<IncidentWorkspace />} />
              <Route path="/lab" element={<PaymentReliabilityLab />} />
              <Route path="/copilot" element={<OpsKnowledgeCopilot />} />
              <Route path="/runbooks" element={<RunbookLibrary />} />
              <Route path="/learning" element={<IncidentLearningHub />} />
              <Route path="/settings" element={<SystemSettings />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;
