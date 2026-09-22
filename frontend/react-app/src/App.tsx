import { useEffect, useState } from "react";
import { api, ApiError } from "./api";
import type { Candidate } from "./types";
import { DocumentsTab } from "./components/DocumentsTab";
import { ProfileTab } from "./components/ProfileTab";
import { JobSearchTab } from "./components/JobSearchTab";
import { JobAnalysisTab } from "./components/JobAnalysisTab";
import { GenerateTab } from "./components/GenerateTab";

type TabId = "documents" | "profile" | "search" | "analysis" | "generate";

const TABS: { id: TabId; label: string }[] = [
  { id: "documents", label: "Documents" },
  { id: "profile", label: "Candidate Profile" },
  { id: "search", label: "Job Search" },
  { id: "analysis", label: "Job Analysis" },
  { id: "generate", label: "Generate Application" },
];

export default function App() {
  const [nameInput, setNameInput] = useState(() => localStorage.getItem("jobseek_candidate_name") ?? "");
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("documents");
  // Bumped whenever evidence changes, so tabs that depend on the verified
  // evidence list (Job Analysis, Generate) know to refetch.
  const [evidenceVersion, setEvidenceVersion] = useState(0);

  useEffect(() => {
    const savedName = localStorage.getItem("jobseek_candidate_name");
    if (savedName) {
      bootstrapCandidate(savedName);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function bootstrapCandidate(name: string) {
    setError(null);
    try {
      const created = await api.createOrGetCandidate(name);
      setCandidate(created);
      localStorage.setItem("jobseek_candidate_name", name);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the API. Is the backend running?");
    }
  }

  return (
    <div>
      <div className="app-header">
        <h1>JobSeek</h1>
      </div>
      <p className="app-subtitle">Evidence-grounded job application assistant</p>

      <div className="candidate-bar">
        <div style={{ flex: 1 }}>
          <label htmlFor="candidate-name">Your name</label>
          <input
            id="candidate-name"
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && bootstrapCandidate(nameInput)}
            placeholder="Enter your name to get started"
          />
        </div>
        <button style={{ marginTop: 16 }} onClick={() => bootstrapCandidate(nameInput)} disabled={!nameInput.trim()}>
          {candidate ? "Switch" : "Start"}
        </button>
      </div>

      {error && <div className="banner banner-danger">{error}</div>}

      {!candidate ? (
        <p className="muted">Enter your name above to get started.</p>
      ) : (
        <>
          <div className="tab-bar">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`tab-button ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "documents" && (
            <DocumentsTab candidate={candidate} onEvidenceChanged={() => setEvidenceVersion((v) => v + 1)} />
          )}
          {activeTab === "profile" && <ProfileTab candidate={candidate} evidenceVersion={evidenceVersion} />}
          {activeTab === "search" && <JobSearchTab candidate={candidate} />}
          {activeTab === "analysis" && <JobAnalysisTab candidate={candidate} />}
          {activeTab === "generate" && <GenerateTab candidate={candidate} />}
        </>
      )}
    </div>
  );
}
