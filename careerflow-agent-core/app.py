# app.py
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from agents.groq_client import GroqClient
from agents.router import Router
from agents.job_match_agent import JobMatchAgent
from agents.section_enhance_agent import SectionEnhanceAgent
from agents.company_research_agent import CompanyResearchAgent
from agents.nl_chat_orchestrator import NLChatOrchestrator
from parsers.resume_parser import parse_resume_file
from store.sqlite_store import Store
from store.vector_store import index_resume
from services.firebase_store import log_message, log_resume_version

# ---- reportlab for structured PDF export ----
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable
from reportlab.lib import colors

import os


app = FastAPI(title="Careerflow Agent Core (Demo)")

# --- CORS so frontend (5173) can call backend (8000) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- init components ---
llm = GroqClient()
router = Router(llm)
job_agent = JobMatchAgent(llm)
section_agent = SectionEnhanceAgent(llm)
company_agent = CompanyResearchAgent(llm)
store = Store()
nl_orchestrator = NLChatOrchestrator(llm=llm, store=store)

# demo user id
DEMO_USER_ID = "demo-user"


# ---------- Pydantic models ----------

class ChatRequest(BaseModel):
    resume_version_id: Optional[int] = None
    user_message: str
    job_description: Optional[str] = None
    company_name: Optional[str] = None
    bullets: Optional[List[str]] = None
    role: Optional[str] = "Software Engineer"


# we keep this around for docs, but we won't use it for validation
class NLChatRequest(BaseModel):
    resume_version_id: Optional[int] = None
    user_message: str
    conversation_id: Optional[str] = "default-conversation"


class ApplyChangeRequest(BaseModel):
    resume_id: int
    base_version_id: int
    edits: List[dict]  # {"index": int, "before": str, "after": str}


class ExportTextRequest(BaseModel):
    text: str
    file_name: Optional[str] = None


# ---------- Helper: build structured PDF from plain text ----------

def build_pdf_from_text(text: str, file_name: str) -> str:
    """Create a clean, structured resume-style PDF from plain text."""
    file_path = os.path.join(os.getcwd(), file_name)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        name="NameStyle",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=10,
    )

    header_style = ParagraphStyle(
        name="HeaderStyle",
        fontSize=12,
        leading=14,
        fontName="Helvetica-Bold",
        textColor=colors.black,
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        name="BodyStyle",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
    )

    flowables = []

    # Split into non-empty lines
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if not lines:
        lines = ["Empty Resume"]

    # --- Name (first line) ---
    flowables.append(Paragraph(lines[0], name_style))

    # --- Contact line (second line) ---
    if len(lines) > 1:
        flowables.append(Paragraph(lines[1], body_style))
        flowables.append(Spacer(1, 10))

    current_section = None
    section_buffer: List[str] = []

    def flush_section():
        nonlocal section_buffer
        if not section_buffer:
            return
        bullets = [Paragraph(item, body_style) for item in section_buffer]
        flowables.append(
            ListFlowable(
                bullets,
                bulletType="bullet",
                start="circle",
                leftIndent=15,
            )
        )
        section_buffer = []

    SECTION_TITLES = {
        "WORK EXPERIENCE",
        "EXPERIENCE",
        "PROJECTS",
        "EDUCATION",
        "TECHNICAL SKILLS",
        "SKILLS",
        "CERTIFICATIONS",
        "CERTIFICATIONS & ACHIEVEMENTS",
    }

    for line in lines[2:]:
        upper = line.upper()

        # Section header detection
        if upper in SECTION_TITLES:
            flush_section()
            current_section = upper
            flowables.append(Spacer(1, 10))
            flowables.append(Paragraph(current_section, header_style))
            continue

        # Bullet detection
        if line.startswith("•") or line.startswith("-"):
            clean = line.lstrip("•-").strip()
            if clean:
                section_buffer.append(clean)
        else:
            # Normal paragraph (job title, summary, etc.)
            flush_section()
            flowables.append(Paragraph(line, body_style))

    flush_section()

    doc.build(flowables)
    return file_path


# ---------- Endpoints ----------

@app.post("/upload_resume")
async def upload_resume(file: UploadFile = File(...)):
    contents = await file.read()
    parsed = parse_resume_file(contents, file.filename)

    # create resume and initial version
    r = store.create_resume(name=file.filename)
    v = store.add_version(
        r.id,
        parsed["raw_text"],
        metadata={"sections": parsed["sections"]},
        parent_version=None,
    )

    # index into vector store
    index_resume(r.id, v.id, parsed["raw_text"])

    # log to Firebase: (user_id, resume_id, version_id, metadata)
    log_resume_version(
        DEMO_USER_ID,
        r.id,
        v.id,
        {"source": "upload", "name": file.filename},
    )

    return {
        "resume_id": r.id,
        "version_id": v.id,
        "parsed_sections": parsed["sections"],
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Original structured endpoint.
    Now:
    - ALWAYS runs job_match if a job_description is provided
    - Still uses router for company_research + section_enhance.
    """
    agents_to_run = router.route(req.user_message)
    output: Dict[str, Any] = {}

    resume_text = ""
    if req.resume_version_id:
        v = store.get_version(req.resume_version_id)
        if not v:
            raise HTTPException(status_code=404, detail="version not found")
        resume_text = v.raw_text

    # ---- company_research stays router-driven ----
    if "company_research" in agents_to_run and req.company_name:
        comp = company_agent.run(req.company_name, extra_context=req.user_message or "")
        output["company_research"] = comp

    # ---- JOB MATCH: force it whenever JD is present ----
    should_run_job_match = bool(req.job_description)
    if should_run_job_match and resume_text:
        jm = job_agent.run(resume_text, req.job_description)
        output["job_match"] = jm
        # mark that we effectively called job_match, even if router didn't
        if "job_match" not in agents_to_run:
            agents_to_run.append("job_match_forced")

    # ---- section_enhance as before ----
    if "section_enhance" in agents_to_run:
        bullets = req.bullets or (resume_text.splitlines()[:5] if resume_text else [])
        se = section_agent.run(bullets, role=req.role or "Software Engineer")
        output["section_enhance"] = se

    return JSONResponse(content={"agents_called": agents_to_run, "result": output})


@app.post("/chat_nl")
async def chat_nl(body: Dict[str, Any] = Body(...)):
    """
    Natural-language chat endpoint.

    We accept flexible JSON from the frontend and normalize keys here
    to avoid validation issues (camelCase vs snake_case etc.).
    """

    # DEBUG: print body so you can see what the frontend actually sends
    print("DEBUG /chat_nl body:", body)

    # Try a bunch of possible key names for the version id
    resume_version_id = (
        body.get("resume_version_id")
        or body.get("resumeVersionId")
        or body.get("version_id")
        or body.get("versionId")
        or body.get("selectedVersionId")
        or body.get("selected_version_id")
    )

    # Try a bunch of possible key names for the user message
    user_message = (
        body.get("user_message")
        or body.get("userMessage")
        or body.get("message")
        or body.get("text")
        or body.get("prompt")
        or body.get("query")
    )

    conversation_id = (
        body.get("conversation_id")
        or body.get("conversationId")
        or "default-conversation"
    )

    if not resume_version_id:
        raise HTTPException(status_code=400, detail="resume_version_id is required")

    if not user_message:
        raise HTTPException(status_code=400, detail="user_message is required")

    # make sure version exists
    v = store.get_version(int(resume_version_id))
    if not v:
        raise HTTPException(status_code=404, detail="version not found")

    # use the orchestrator (LangChain router + existing agents)
    result = nl_orchestrator.handle_message(
        message=user_message,
        resume_version_id=int(resume_version_id),
        role=None,
        company=None,
        job_description=None,
    )

    # log conversation to Firebase
    conv_id = conversation_id or "default-conversation"
    log_message(
        DEMO_USER_ID,
        conv_id,
        role="user",
        content=user_message,
        extra={"resume_version_id": int(resume_version_id)},
    )
    log_message(
        DEMO_USER_ID,
        conv_id,
        role="assistant",
        content=str(result),
        extra={"resume_version_id": int(resume_version_id)},
    )

    return JSONResponse(
        content={
            "resume_version_id": int(resume_version_id),
            "result": result,
        }
    )


@app.post("/apply_changes")
def apply_changes(req: ApplyChangeRequest):
    """
    Applies edits to the base_version_id raw_text.
    Each edit: {"index": int, "before": str, "after": str}
    """
    base = store.get_version(req.base_version_id)
    if not base:
        raise HTTPException(status_code=404, detail="base version not found")

    raw = base.raw_text
    for edit in req.edits:
        before = edit.get("before")
        after = edit.get("after")
        if not after:
            continue
        if before and before in raw:
            raw = raw.replace(before, after, 1)
        else:
            raw = raw + "\n" + after

    new_v = store.add_version(
        req.resume_id,
        raw,
        metadata={"applied_edits": req.edits},
        parent_version=req.base_version_id,
    )

    # index new version + log to Firebase
    index_resume(req.resume_id, new_v.id, raw)
    log_resume_version(
        DEMO_USER_ID,
        req.resume_id,
        new_v.id,
        {"source": "applied_edits"},
    )

    return {"new_version_id": new_v.id}


@app.get("/resume/{resume_id}/versions")
def list_versions(resume_id: int):
    versions = store.list_versions(resume_id)
    data = []
    for v in versions:
        meta_preview = ""
        try:
            meta_preview = (v.metadata_json or "")[:300]
        except Exception:
            meta_preview = ""
        data.append(
            {
                "version_id": v.id,
                "created_at": str(v.created_at),
                "parent": v.parent_version,
                "metadata_preview": meta_preview,
            }
        )
    return {"resume_id": resume_id, "versions": data}


# ---------- CLEAN, STRUCTURED PDF EXPORT FOR A RESUME VERSION ----------

@app.get("/resume/{resume_version_id}/export_pdf")
def export_resume_pdf(resume_version_id: int):
    """
    Export a specific resume VERSION as a clean, structured PDF.

    Note: `resume_version_id` here is a VERSION id from sqlite_store (not resume_id).
    """
    v = store.get_version(resume_version_id)
    if not v:
        raise HTTPException(status_code=404, detail="Resume version not found")

    raw_text = v.raw_text or "Empty Resume"

    file_name = f"resume_{resume_version_id}.pdf"
    file_path = build_pdf_from_text(raw_text, file_name)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=file_name,
    )


# ---------- NEW: EXPORT ARBITRARY TEXT (e.g. translated resume) AS PDF ----------

@app.post("/export_pdf_from_text")
def export_pdf_from_text(req: ExportTextRequest):
    """
    Take arbitrary resume text (e.g. translated output from /chat_nl)
    and return a structured PDF.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    safe_name = req.file_name or "resume_chat_export.pdf"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"

    file_path = build_pdf_from_text(req.text, safe_name)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=safe_name,
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
