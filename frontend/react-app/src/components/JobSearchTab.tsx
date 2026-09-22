import { useState } from "react";
import { api, ApiError } from "../api";
import type { Candidate, JobListing } from "../types";

export function JobSearchTab({ candidate }: { candidate: Candidate }) {
  const [keywords, setKeywords] = useState("");
  const [country, setCountry] = useState("");
  const [location, setLocation] = useState("");
  const [daysBack, setDaysBack] = useState(0);
  const [workModel, setWorkModel] = useState("");
  const [searching, setSearching] = useState(false);
  const [listings, setListings] = useState<JobListing[]>([]);
  const [providerErrors, setProviderErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  async function handleSearch() {
    setSearching(true);
    setError(null);
    setSavedMessage(null);
    try {
      const result = await api.searchJobs({
        keywords,
        country: country || undefined,
        location: location || undefined,
        daysBack: daysBack || undefined,
        workModel: workModel || undefined,
      });
      setListings(result.listings);
      setProviderErrors(result.provider_errors);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  async function handleSaveAndAnalyze(listing: JobListing) {
    const key = `${listing.source}_${listing.external_id}`;
    setSavingKey(key);
    setSavedMessage(null);
    setError(null);
    try {
      const savedJob = await api.saveJobListing(listing);
      await api.analyzeJob({ candidate_id: candidate.id, job_id: savedJob.id });
      setSavedMessage(`Saved and analyzed '${listing.title}' — see it in the Job Analysis tab.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save/analyze this listing.");
    } finally {
      setSavingKey(null);
    }
  }

  return (
    <div>
      <div className="card">
        <h3>Search for vacancies</h3>
        <p className="muted">
          Searches Arbeitnow (always available) and Adzuna (if configured on the backend), deduplicates results
          across providers.
        </p>
        <div className="field-row">
          <div>
            <label>Keywords</label>
            <input type="text" value={keywords} onChange={(e) => setKeywords(e.target.value)} />
          </div>
          <div>
            <label>Country code (e.g. de, gb, us)</label>
            <input type="text" value={country} onChange={(e) => setCountry(e.target.value)} />
          </div>
          <div>
            <label>Location</label>
            <input type="text" value={location} onChange={(e) => setLocation(e.target.value)} />
          </div>
        </div>
        <div className="field-row">
          <div>
            <label>Published in the last N days (0 = any time)</label>
            <input
              type="number"
              min={0}
              value={daysBack}
              onChange={(e) => setDaysBack(Number(e.target.value))}
            />
          </div>
          <div>
            <label>Work model</label>
            <select value={workModel} onChange={(e) => setWorkModel(e.target.value)}>
              <option value="">Any</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">Onsite</option>
            </select>
          </div>
        </div>
        <button onClick={handleSearch} disabled={searching}>
          {searching ? "Searching..." : "Search"}
        </button>
      </div>

      {error && <div className="banner banner-danger">{error}</div>}
      {savedMessage && <div className="banner banner-success">{savedMessage}</div>}
      {Object.entries(providerErrors).map(([provider, message]) => (
        <div key={provider} className="banner banner-warning">
          {provider} search failed (other providers' results are still shown below): {message}
        </div>
      ))}

      {listings.length > 0 && <p className="muted">{listings.length} unique listing(s) found.</p>}
      {listings.map((listing) => {
        const key = `${listing.source}_${listing.external_id}`;
        const metaBits = [listing.location, listing.publication_date ? `posted ${listing.publication_date}` : null, listing.remote_type].filter(
          Boolean,
        );
        return (
          <div key={key} className="card">
            <strong>
              {listing.title}
              {listing.company ? ` @ ${listing.company}` : ""}
            </strong>{" "}
            <span className="badge badge-neutral">{listing.source}</span>
            {metaBits.length > 0 && <p className="muted">{metaBits.join(" · ")}</p>}
            {listing.source_url && (
              <p>
                <a href={listing.source_url} target="_blank" rel="noreferrer">
                  View original posting
                </a>
              </p>
            )}
            <p>{listing.description.slice(0, 400)}{listing.description.length > 400 ? "…" : ""}</p>
            <button onClick={() => handleSaveAndAnalyze(listing)} disabled={savingKey === key}>
              {savingKey === key ? "Saving..." : "Save & analyze"}
            </button>
          </div>
        );
      })}
    </div>
  );
}
