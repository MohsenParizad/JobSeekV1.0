// Mirrors backend/api/schemas.py — kept in sync by hand since there's no
// shared-schema codegen yet (a reasonable follow-up once the API stabilizes).

export interface Candidate {
  id: string;
  name: string;
  email: string | null;
}

export interface Evidence {
  id: string;
  category: string;
  concept: string;
  description: string;
  source_text: string;
  organization: string | null;
  confidence: string;
  status: "pending" | "approved" | "rejected";
}

export interface JobListing {
  source: string;
  external_id: string;
  title: string;
  company: string | null;
  location: string | null;
  country: string | null;
  publication_date: string | null;
  description: string;
  employment_type: string | null;
  remote_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  source_url: string | null;
}

export interface JobSearchResponse {
  listings: JobListing[];
  provider_errors: Record<string, string>;
}

export interface JobRequirement {
  id: string;
  category: string;
  concept: string;
  importance: string;
  language_level: string | null;
  source_text: string;
}

export interface Job {
  id: string;
  title: string;
  company: string | null;
  source: string;
  seniority: string | null;
  work_model: string | null;
  location: string | null;
  country: string | null;
  publication_date: string | null;
  source_url: string | null;
  raw_description: string;
  requirements: JobRequirement[];
}

export type MatchType = "direct" | "related" | "transferable" | "missing";

export interface MatchedEvidence {
  id: string;
  concept: string;
}

export interface RequirementMatch {
  requirement_id: string;
  concept: string;
  category: string;
  importance: string;
  match_type: MatchType;
  explanation: string;
  matched_evidence: MatchedEvidence[];
}

export interface JobMatch {
  id: string;
  job_id: string;
  candidate_id: string;
  score: number;
  requirement_matches: RequirementMatch[];
}

export interface ClaimValidation {
  statement: string;
  concept: string;
  supported: boolean;
  matched_evidence_concept: string | null;
}

export interface GeneratedApplication {
  id: string;
  job_id: string;
  candidate_id: string;
  tailored_summary: string;
  emphasized_experience: string[];
  cv_suggestions: string[];
  cover_letter: string;
  validations: ClaimValidation[];
}
