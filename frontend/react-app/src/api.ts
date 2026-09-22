import type {
  Candidate,
  Evidence,
  GeneratedApplication,
  Job,
  JobMatch,
  JobSearchResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: options?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response body wasn't JSON; fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  createOrGetCandidate: (name: string, email?: string) =>
    request<Candidate>("/candidates", { method: "POST", body: JSON.stringify({ name, email }) }),

  getCandidate: (candidateId: string) => request<Candidate>(`/candidates/${candidateId}`),

  uploadDocument: (candidateId: string, documentType: string, file: File) => {
    const form = new FormData();
    form.append("document_type", documentType);
    form.append("file", file);
    return request<Evidence[]>(`/candidates/${candidateId}/documents`, { method: "POST", body: form });
  },

  listEvidence: (candidateId: string, status?: string) => {
    const query = status ? `?status=${status}` : "";
    return request<Evidence[]>(`/candidates/${candidateId}/evidence${query}`);
  },

  updateEvidence: (evidenceId: string, action: "approve" | "reject", concept?: string, description?: string) =>
    request<Evidence>(`/evidence/${evidenceId}`, {
      method: "PATCH",
      body: JSON.stringify({ action, concept, description }),
    }),

  searchJobs: (params: {
    keywords: string;
    country?: string;
    location?: string;
    daysBack?: number;
    workModel?: string;
  }) => {
    const query = new URLSearchParams();
    query.set("keywords", params.keywords);
    if (params.country) query.set("country", params.country);
    if (params.location) query.set("location", params.location);
    if (params.daysBack) query.set("days_back", String(params.daysBack));
    if (params.workModel) query.set("work_model", params.workModel);
    return request<JobSearchResponse>(`/jobs/search?${query.toString()}`);
  },

  saveJobListing: (listing: unknown) =>
    request<Job>("/jobs/listing", { method: "POST", body: JSON.stringify(listing) }),

  listJobs: () => request<Job[]>("/jobs"),

  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),

  analyzeJob: (payload: { candidate_id: string; description_text?: string; job_id?: string }) =>
    request<JobMatch>("/jobs/analyze", { method: "POST", body: JSON.stringify(payload) }),

  getJobMatch: (jobId: string, candidateId: string) =>
    request<JobMatch>(`/jobs/${jobId}/match?candidate_id=${candidateId}`),

  generateApplication: (payload: { candidate_id: string; candidate_name: string; job_id: string }) =>
    request<GeneratedApplication>("/applications/generate", { method: "POST", body: JSON.stringify(payload) }),

  getLatestApplication: (jobId: string, candidateId: string) =>
    request<GeneratedApplication>(`/applications/${jobId}?candidate_id=${candidateId}`),
};
