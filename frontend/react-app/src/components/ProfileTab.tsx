import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import type { Candidate, Evidence } from "../types";

export function ProfileTab({ candidate, evidenceVersion }: { candidate: Candidate; evidenceVersion: number }) {
  const [approved, setApproved] = useState<Evidence[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listEvidence(candidate.id, "approved")
      .then(setApproved)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load evidence."));
  }, [candidate.id, evidenceVersion]);

  if (error) return <div className="banner banner-danger">{error}</div>;
  if (approved.length === 0) {
    return <p className="muted">No verified evidence yet — approve items in the Documents tab.</p>;
  }

  const byCategory = approved.reduce<Record<string, Evidence[]>>((acc, item) => {
    (acc[item.category] ??= []).push(item);
    return acc;
  }, {});

  return (
    <div>
      <h3>Verified evidence</h3>
      {Object.entries(byCategory)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([category, items]) => (
          <div key={category} className="card">
            <strong style={{ textTransform: "capitalize" }}>{category}</strong>
            {items.map((item) => (
              <div key={item.id} className="evidence-item">
                ☑ {item.concept} — {item.description}
              </div>
            ))}
          </div>
        ))}
    </div>
  );
}
