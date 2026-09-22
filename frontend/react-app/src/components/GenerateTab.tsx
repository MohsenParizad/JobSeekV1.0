import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { Candidate, GeneratedApplication, Job } from "../types";

export function GenerateTab({ candidate }: { candidate: Candidate }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [generated, setGenerated] = useState<GeneratedApplication | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listJobs().then((list) => {
      setJobs(list);
      if (list.length > 0) setSelectedJobId((current) => current ?? list[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedJobId) return;
    setError(null);
    api
      .getLatestApplication(selectedJobId, candidate.id)
      .then(setGenerated)
      .catch((err) => {
        setGenerated(null);
        if (!(err instanceof ApiError && err.status === 404)) {
          setError(err instanceof ApiError ? err.message : "Failed to load generated application.");
        }
      });
  }, [selectedJobId, candidate.id]);

  async function handleGenerate() {
    if (!selectedJobId) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await api.generateApplication({
        candidate_id: candidate.id,
        candidate_name: candidate.name,
        job_id: selectedJobId,
      });
      setGenerated(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  const unsupported = generated?.validations.filter((v) => !v.supported) ?? [];

  return (
    <div>
      <h3>Generate tailored application material</h3>
      <p className="muted">
        Every claim below is checked against your verified evidence by an independent validator — not just asked of
        the model that wrote the text.
      </p>

      <div className="card">
        <label>Job</label>
        {jobs.length === 0 ? (
          <p className="muted">Analyze a job in the Job Analysis tab first.</p>
        ) : (
          <select value={selectedJobId ?? ""} onChange={(e) => setSelectedJobId(e.target.value)}>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title}
                {j.company ? ` @ ${j.company}` : ""}
              </option>
            ))}
          </select>
        )}
        <button onClick={handleGenerate} disabled={!selectedJobId || generating} style={{ marginTop: 8 }}>
          {generating ? "Generating..." : generated ? "Regenerate" : "Generate application material"}
        </button>
      </div>

      {error && <div className="banner banner-danger">{error}</div>}

      {generated && (
        <div>
          {unsupported.length > 0 ? (
            <div className="banner banner-danger">
              ⚠ {unsupported.length} claim(s) could not be verified against your evidence — review before sending
              this application.
              <ul>
                {unsupported.map((v, i) => (
                  <li key={i}>
                    "{v.statement}" (concept: {v.concept}) — no matching verified evidence
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="banner banner-success">✓ Every claim in this material is grounded in your verified evidence.</div>
          )}

          <div className="card">
            <strong>Tailored summary</strong>
            <p>{generated.tailored_summary}</p>
          </div>

          {generated.emphasized_experience.length > 0 && (
            <div className="card">
              <strong>Experience to emphasize</strong>
              <ul>
                {generated.emphasized_experience.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {generated.cv_suggestions.length > 0 && (
            <div className="card">
              <strong>CV suggestions</strong>
              <ul>
                {generated.cv_suggestions.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="card">
            <strong>Cover letter</strong>
            <textarea rows={12} value={generated.cover_letter} readOnly />
          </div>

          <details className="card">
            <summary>Claim-by-claim validation</summary>
            {generated.validations.map((v, i) => (
              <div key={i} className="evidence-item">
                {v.supported ? "✓" : "❌"} "{v.statement}"{" "}
                {v.supported ? (
                  <span className="muted">(matches verified evidence: {v.matched_evidence_concept})</span>
                ) : (
                  <span className="muted">(no matching verified evidence)</span>
                )}
              </div>
            ))}
          </details>
        </div>
      )}
    </div>
  );
}
