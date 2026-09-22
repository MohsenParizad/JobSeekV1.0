"""V0.1 MVP UI: upload a CV/reference, extract evidence, review and approve it.

Streamlit is used here deliberately per docs/architecture.md — this UI calls
backend services directly and holds no business logic itself; a FastAPI +
React split happens in V0.5 without touching backend/.
"""
import streamlit as st

from backend.config import settings
from backend.db import get_session, init_db
from backend.models.evidence import DocumentType, EvidenceStatus
from backend.providers.llm import get_llm_provider
from backend.services.documents.extraction import EvidenceExtractionService
from backend.services.documents.parser import (
    FileTooLargeError,
    UnsupportedFileTypeError,
    extract_text,
    save_upload,
)
from backend.services.evidence.store import EvidenceStore
from backend.services.generation.service import generate_application_material, revalidate
from backend.services.generation.store import GenerationStore
from backend.services.jobs.analysis import analyze_and_match
from backend.services.jobs.store import JobStore
from backend.services.matching.store import MatchStore

st.set_page_config(page_title="JobSeek — Candidate Profile", layout="wide")
init_db()


def _build_match_view(session, job, job_match) -> list[dict]:
    """Joins a JobMatch's per-requirement results back to their requirement
    and evidence rows for display, while the session is still open."""
    requirement_by_id = {r.id: r for r in job.requirements}
    evidence_by_id = {e.id: e for e in EvidenceStore(session).list_evidence(job_match.candidate_id)}
    rows = []
    for rm in job_match.requirement_matches:
        requirement = requirement_by_id.get(rm.requirement_id)
        if requirement is None:
            continue
        matched_evidence = [evidence_by_id[eid] for eid in rm.matched_evidence_ids if eid in evidence_by_id]
        rows.append(
            {
                "concept": requirement.concept,
                "importance": requirement.importance.value,
                "match_type": rm.match_type.value,
                "explanation": rm.explanation,
                "matched_evidence": [{"concept": e.concept} for e in matched_evidence],
            }
        )
    return rows


def _build_generation_view(record, validations) -> dict:
    return {
        "tailored_summary": record.tailored_summary,
        "emphasized_experience": record.emphasized_experience,
        "cv_suggestions": record.cv_suggestions,
        "cover_letter": record.cover_letter,
        "validations": [
            {
                "statement": v.statement,
                "concept": v.concept,
                "supported": v.supported,
                "matched_evidence_concept": v.matched_evidence_concept,
            }
            for v in validations
        ],
    }


DOCUMENT_TYPE_LABELS = {
    DocumentType.CV: "CV",
    DocumentType.EMPLOYMENT_REFERENCE: "Employment reference (Arbeitszeugnis)",
    DocumentType.CERTIFICATE: "Certificate",
}

if "candidate_name" not in st.session_state:
    st.session_state.candidate_name = ""

st.sidebar.header("Candidate")
candidate_name = st.sidebar.text_input("Your name", value=st.session_state.candidate_name)
st.session_state.candidate_name = candidate_name

if not settings.anthropic_api_key:
    st.sidebar.warning(
        "No ANTHROPIC_API_KEY configured — using the deterministic fake extractor. "
        "Set it in .env for real extraction."
    )

if not candidate_name:
    st.info("Enter your name in the sidebar to get started.")
    st.stop()

with get_session() as session:
    candidate = EvidenceStore(session).get_or_create_candidate(candidate_name)
    candidate_id = candidate.id

tab_documents, tab_profile, tab_job_analysis, tab_generate = st.tabs(
    ["Documents", "Candidate Profile", "Job Analysis", "Generate Application"]
)

with tab_documents:
    st.subheader("Upload a document")
    doc_type_label = st.selectbox("Document type", list(DOCUMENT_TYPE_LABELS.values()))
    doc_type = next(k for k, v in DOCUMENT_TYPE_LABELS.items() if v == doc_type_label)
    uploaded_file = st.file_uploader("CV or reference (PDF or DOCX)", type=["pdf", "docx"])

    if uploaded_file is not None and st.button("Extract evidence"):
        content = uploaded_file.getvalue()
        try:
            with st.spinner("Parsing and extracting evidence..."):
                stored_path = save_upload(content, uploaded_file.name, settings.document_storage_dir)
                document_text = extract_text(stored_path)

                with get_session() as session:
                    store = EvidenceStore(session)
                    document = store.save_document(
                        candidate_id=candidate_id,
                        document_type=doc_type,
                        original_filename=uploaded_file.name,
                        storage_path=stored_path,
                        raw_text=document_text,
                    )
                    extraction_service = EvidenceExtractionService(get_llm_provider())
                    items = extraction_service.extract(document_text)
                    store.save_pending_evidence(candidate_id, document.id, items)
            st.success(f"Extracted {len(items)} evidence item(s). Review them below.")
        except (UnsupportedFileTypeError, FileTooLargeError) as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Review extracted evidence")

    with get_session() as session:
        pending = EvidenceStore(session).list_evidence(candidate_id, status=EvidenceStatus.PENDING)
        pending_view = [
            {
                "id": e.id,
                "category": e.category.value,
                "concept": e.concept,
                "description": e.description,
                "source_text": e.source_text,
                "organization": e.organization,
                "confidence": e.confidence.value,
            }
            for e in pending
        ]

    if not pending_view:
        st.caption("No pending evidence to review.")
    for item in pending_view:
        with st.expander(f"{item['concept']}  ·  {item['category']}  ·  confidence: {item['confidence']}"):
            concept = st.text_input("Concept", value=item["concept"], key=f"concept_{item['id']}")
            description = st.text_input("Description", value=item["description"], key=f"desc_{item['id']}")
            st.caption(f"Source: “{item['source_text']}”")
            if item["organization"]:
                st.caption(f"Organization: {item['organization']}")
            col_approve, col_reject = st.columns(2)
            if col_approve.button("Approve", key=f"approve_{item['id']}"):
                with get_session() as session:
                    EvidenceStore(session).approve(item["id"], concept=concept, description=description)
                st.rerun()
            if col_reject.button("Reject", key=f"reject_{item['id']}"):
                with get_session() as session:
                    EvidenceStore(session).reject(item["id"])
                st.rerun()

with tab_profile:
    st.subheader("Verified evidence")
    with get_session() as session:
        approved = EvidenceStore(session).list_evidence(candidate_id, status=EvidenceStatus.APPROVED)
        approved_view = [
            {"category": e.category.value, "concept": e.concept, "description": e.description} for e in approved
        ]

    if not approved_view:
        st.caption("No verified evidence yet — approve items in the Documents tab.")
    else:
        by_category: dict[str, list[dict]] = {}
        for item in approved_view:
            by_category.setdefault(item["category"], []).append(item)
        for category, items in sorted(by_category.items()):
            st.markdown(f"**{category.title()}**")
            for item in items:
                st.markdown(f"- ☑ {item['concept']} — {item['description']}")

with tab_job_analysis:
    st.subheader("Analyze a job against your verified evidence")

    with get_session() as session:
        existing_jobs = JobStore(session).list_jobs()

    NEW_JOB_OPTION = "— New job description —"
    job_options = {NEW_JOB_OPTION: None}
    for job in existing_jobs:
        label = job.title + (f" @ {job.company}" if job.company else "")
        job_options[f"{label}  ({job.created_at:%Y-%m-%d})"] = job.id
    selected_label = st.selectbox("Job", list(job_options.keys()))
    selected_job_id = job_options[selected_label]

    job_view = None
    match_rows = None

    if selected_job_id is None:
        description_text = st.text_area("Paste the job description", height=250)
        if st.button("Analyze & match") and description_text.strip():
            with st.spinner("Extracting requirements and matching against your verified evidence..."):
                with get_session() as session:
                    job, job_match = analyze_and_match(session, candidate_id, get_llm_provider(), description_text)
                    job_view = {"title": job.title, "company": job.company, "score": job_match.score}
                    match_rows = _build_match_view(session, job, job_match)
            st.success(f"Analyzed '{job_view['title']}' — {len(match_rows)} requirement(s) found.")
    else:
        with get_session() as session:
            job = JobStore(session).get_job(selected_job_id)
            job_match = MatchStore(session).get_latest_match(candidate_id, selected_job_id)
            if job is not None and job_match is not None:
                job_view = {"title": job.title, "company": job.company, "score": job_match.score}
                match_rows = _build_match_view(session, job, job_match)

    if match_rows is not None:
        st.divider()
        title_line = job_view["title"] + (f" @ {job_view['company']}" if job_view["company"] else "")
        st.markdown(f"### {title_line}")
        st.metric("Fit score", f"{job_view['score']:.1f} / 100")

        groups: dict[str, list[dict]] = {"direct": [], "related": [], "transferable": [], "missing": []}
        for row in match_rows:
            groups[row["match_type"]].append(row)

        SECTION_LABELS = {
            "direct": ("Direct evidence", "✓"),
            "related": ("Related evidence", "~"),
            "transferable": ("Transferable evidence", "~"),
            "missing": ("Gaps", "✗"),
        }
        for match_type in ("direct", "related", "transferable", "missing"):
            rows = groups[match_type]
            if not rows:
                continue
            label, marker = SECTION_LABELS[match_type]
            st.markdown(f"**{label}**")
            for row in rows:
                cited = ", ".join(e["concept"] for e in row["matched_evidence"])
                citation = f" _(from: {cited})_" if cited else ""
                st.markdown(f"- {marker} **{row['concept']}** ({row['importance']}) — {row['explanation']}{citation}")

with tab_generate:
    st.subheader("Generate tailored application material")
    st.caption(
        "Every claim below is checked against your verified evidence by an independent validator — "
        "not just asked of the model that wrote the text."
    )

    with get_session() as session:
        jobs_for_generation = JobStore(session).list_jobs()

    if not jobs_for_generation:
        st.caption("Analyze a job in the Job Analysis tab first.")
    else:
        gen_job_options = {}
        for job in jobs_for_generation:
            label = job.title + (f" @ {job.company}" if job.company else "")
            gen_job_options[f"{label}  ({job.created_at:%Y-%m-%d})"] = job.id
        gen_selected_label = st.selectbox("Job", list(gen_job_options.keys()), key="generate_job_select")
        gen_job_id = gen_job_options[gen_selected_label]

        with get_session() as session:
            existing_record = GenerationStore(session).get_latest(candidate_id, gen_job_id)
            generation_view = None
            if existing_record is not None:
                verified_evidence = EvidenceStore(session).list_evidence(candidate_id, status=EvidenceStatus.APPROVED)
                validations = revalidate(existing_record, verified_evidence)
                generation_view = _build_generation_view(existing_record, validations)

        button_label = "Regenerate" if generation_view else "Generate application material"
        if st.button(button_label):
            try:
                with st.spinner("Generating tailored application material..."):
                    with get_session() as session:
                        record, validations = generate_application_material(
                            session, candidate_id, candidate_name, gen_job_id, get_llm_provider()
                        )
                        generation_view = _build_generation_view(record, validations)
                st.success("Generated.")
            except ValueError as exc:
                st.error(str(exc))

        if generation_view is not None:
            st.divider()
            unsupported = [v for v in generation_view["validations"] if not v["supported"]]
            if unsupported:
                st.error(
                    f"⚠ {len(unsupported)} claim(s) could not be verified against your evidence — "
                    "review before sending this application."
                )
                for v in unsupported:
                    st.markdown(f'- ❌ "{v["statement"]}" (concept: {v["concept"]}) — no matching verified evidence')
            elif generation_view["validations"]:
                st.success("✓ Every claim in this material is grounded in your verified evidence.")

            st.markdown("**Tailored summary**")
            st.write(generation_view["tailored_summary"])

            if generation_view["emphasized_experience"]:
                st.markdown("**Experience to emphasize**")
                for item in generation_view["emphasized_experience"]:
                    st.markdown(f"- {item}")

            if generation_view["cv_suggestions"]:
                st.markdown("**CV suggestions**")
                for item in generation_view["cv_suggestions"]:
                    st.markdown(f"- {item}")

            st.markdown("**Cover letter**")
            st.text_area("Cover letter", value=generation_view["cover_letter"], height=250, label_visibility="collapsed")

            with st.expander("Claim-by-claim validation"):
                for v in generation_view["validations"]:
                    icon = "✓" if v["supported"] else "❌"
                    note = (
                        f" (matches verified evidence: {v['matched_evidence_concept']})"
                        if v["supported"]
                        else " (no matching verified evidence)"
                    )
                    st.markdown(f'- {icon} "{v["statement"]}"{note}')
