# Privacy & security notes

CVs and employment references are personal data. Rules for this codebase:

- Uploaded documents and the local database live under `data/`, which is
  git-ignored in full — never commit a real CV, reference letter, or the
  `.db` file.
- Secrets (API keys, connection strings) live in `.env`, which is
  git-ignored; `.env.example` documents the required keys with empty values.
- Uploaded file type and size are validated before parsing
  (`backend/services/documents/parser.py`).
- Filenames from uploads are not trusted as storage paths — documents are
  stored under a generated id, not the original filename.
- Extracted evidence text (short source snippets) may be logged for
  debugging during development; full document text and application logs
  containing personal data are not committed or shared outside the local
  environment.
- When document text is sent to an external LLM provider (Anthropic), that
  is the only point personal data leaves the local machine. This happens
  only for the extraction/generation calls described in
  `docs/architecture.md`, using the key in `.env`.
- Document deletion: candidates can delete an uploaded document, which
  removes both the stored file and any evidence rows sourced from it
  (`EvidenceStore.delete_document`).
