import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { Candidate, Evidence } from "../types";

const DOCUMENT_TYPES = [
  { value: "cv", label: "CV" },
  { value: "employment_reference", label: "Employment reference (Arbeitszeugnis)" },
  { value: "certificate", label: "Certificate" },
];

export function DocumentsTab({
  candidate,
  onEvidenceChanged,
}: {
  candidate: Candidate;
  onEvidenceChanged: () => void;
}) {
  const [documentType, setDocumentType] = useState("cv");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [pending, setPending] = useState<Evidence[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, { concept: string; description: string }>>({});

  async function loadPending() {
    try {
      const items = await api.listEvidence(candidate.id, "pending");
      setPending(items);
      setEdits(Object.fromEntries(items.map((e) => [e.id, { concept: e.concept, description: e.description }])));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load pending evidence.");
    }
  }

  useEffect(() => {
    loadPending();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidate.id]);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const extracted = await api.uploadDocument(candidate.id, documentType, file);
      setSuccess(`Extracted ${extracted.length} evidence item(s). Review them below.`);
      setFile(null);
      await loadPending();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDecision(evidenceId: string, action: "approve" | "reject") {
    try {
      const edit = edits[evidenceId];
      await api.updateEvidence(evidenceId, action, edit?.concept, edit?.description);
      await loadPending();
      onEvidenceChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update evidence.");
    }
  }

  return (
    <div>
      <div className="card">
        <h3>Upload a document</h3>
        <div className="field-row">
          <div>
            <label htmlFor="document-type">Document type</label>
            <select id="document-type" value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
              {DOCUMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="document-file">File (PDF or DOCX)</label>
            <input
              id="document-file"
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>
        <button onClick={handleUpload} disabled={!file || uploading}>
          {uploading ? "Extracting..." : "Extract evidence"}
        </button>
      </div>

      {error && <div className="banner banner-danger">{error}</div>}
      {success && <div className="banner banner-success">{success}</div>}

      <h3 className="section-title">Review extracted evidence</h3>
      {pending.length === 0 && <p className="muted">No pending evidence to review.</p>}
      {pending.map((item) => {
        const edit = edits[item.id] ?? { concept: item.concept, description: item.description };
        return (
          <div key={item.id} className="card">
            <div className="field-row">
              <div>
                <label>Concept</label>
                <input
                  type="text"
                  value={edit.concept}
                  onChange={(e) =>
                    setEdits((prev) => ({ ...prev, [item.id]: { ...edit, concept: e.target.value } }))
                  }
                />
              </div>
              <div>
                <label>Description</label>
                <input
                  type="text"
                  value={edit.description}
                  onChange={(e) =>
                    setEdits((prev) => ({ ...prev, [item.id]: { ...edit, description: e.target.value } }))
                  }
                />
              </div>
            </div>
            <p className="muted">
              {item.category} · confidence: {item.confidence}
              {item.organization ? ` · ${item.organization}` : ""}
            </p>
            <p className="muted">Source: "{item.source_text}"</p>
            <div className="button-row">
              <button onClick={() => handleDecision(item.id, "approve")}>Approve</button>
              <button className="danger" onClick={() => handleDecision(item.id, "reject")}>
                Reject
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
