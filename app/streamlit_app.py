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

st.set_page_config(page_title="JobSeek — Candidate Profile", layout="wide")
init_db()

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

tab_documents, tab_profile = st.tabs(["Documents", "Candidate Profile"])

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
