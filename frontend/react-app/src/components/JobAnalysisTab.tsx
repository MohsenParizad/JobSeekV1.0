import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { Candidate, Job, JobMatch, MatchType } from "../types";

const NEW_JOB_OPTION = "__new__";

const SECTION_LABELS: Record<MatchType, { label: string; marker: string }> = {
  direct: { label: "Direct evidence", marker: "✓" },
  related: { label: "Related evidence", marker: "~" },
  transferable: { label: "Transferable evidence", marker: "~" },
  missing: { label: "Gaps", marker: "✗" },
};

export function JobAnalysisTab({ candidate }: { candidate: Candidate }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState(NEW_JOB_OPTION);
  const [descriptionText, setDescriptionText] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [jobMatch, setJobMatch] = useState<JobMatch | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listJobs().then(setJobs).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (selectedJobId === NEW_JOB_OPTION) {
      setJob(null);
      setJobMatch(null);
      return;
    }
    setError(null);
    Promise.all([api.getJob(selectedJobId), api.getJobMatch(selectedJobId, candidate.id)])
      .then(([j, m]) => {
        setJob(j);
        setJobMatch(m);
      })
      .catch((err) => {
        setJob(null);
        setJobMatch(null);
        if (err instanceof ApiError && err.status === 404) {
          setError("This job hasn't been analyzed for this candidate yet.");
        } else {
          setError(err instanceof ApiError ? err.message : "Failed to load job match.");
        }
      });
  }, [selectedJobId, candidate.id]);

  async function handleAnalyze() {
    if (!descriptionText.trim()) return;
    setAnalyzing(true);
    setError(null);
    try {
      const match = await api.analyzeJob({ candidate_id: candidate.id, description_text: descriptionText });
      const analyzedJob = await api.getJob(match.job_id);
      setJob(analyzedJob);
      setJobMatch(match);
      const refreshedJobs = await api.listJobs();
      setJobs(refreshedJobs);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  const requirementByGroup: Record<MatchType, JobMatch["requirement_matches"]> = {
    direct: [],
    related: [],
    transferable: [],
    missing: [],
  };
  jobMatch?.requirement_matches.forEach((rm) => requirementByGroup[rm.match_type].push(rm));

  return (
    <div>
      <h3>Analyze a job against your verified evidence</h3>
      <div className="card">
        <label>Job</label>
        <select value={selectedJobId} onChange={(e) => setSelectedJobId(e.target.value)}>
          <option value={NEW_JOB_OPTION}>— New job description —</option>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>
              {j.title}
              {j.company ? ` @ ${j.company}` : ""}
            </option>
          ))}
        </select>

        {selectedJobId === NEW_JOB_OPTION && (
          <>
            <label style={{ marginTop: 12 }}>Paste the job description</label>
            <textarea rows={10} value={descriptionText} onChange={(e) => setDescriptionText(e.target.value)} />
            <button onClick={handleAnalyze} disabled={analyzing || !descriptionText.trim()} style={{ marginTop: 8 }}>
              {analyzing ? "Analyzing..." : "Analyze & match"}
            </button>
          </>
        )}
      </div>

      {error && <div className="banner banner-danger">{error}</div>}

      {job && jobMatch && (
        <div>
          <h3>
            {job.title}
            {job.company ? ` @ ${job.company}` : ""}
          </h3>
          <p>
            Fit score: <span className="score-pill">{jobMatch.score.toFixed(1)}</span> / 100
          </p>

          {(Object.keys(SECTION_LABELS) as MatchType[]).map((matchType) => {
            const rows = requirementByGroup[matchType];
            if (rows.length === 0) return null;
            const { label, marker } = SECTION_LABELS[matchType];
            return (
              <div key={matchType} className="card">
                <strong>{label}</strong>
                {rows.map((rm) => {
                  const cited = rm.matched_evidence.map((e) => e.concept).join(", ");
                  return (
                    <div key={rm.requirement_id} className="requirement-item">
                      {marker} <strong>{rm.concept}</strong> ({rm.importance}) — {rm.explanation}
                      {cited && <span className="muted"> (from: {cited})</span>}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
