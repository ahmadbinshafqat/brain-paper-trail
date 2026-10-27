from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from app.analyzer import rank_quotable_sentences
from app.config import settings
from app.database import create_db_and_tables, get_session
from app.models import Document, Sentence
from app.pdf_utils import extract_pdf_text
from app.schemas import AnalyzeResponse, DocumentSummary, SentenceResult, TextAnalyzeRequest

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


def persist_analysis(session: Session, *, title: str, source_type: str, text: str, top_n: int) -> AnalyzeResponse:
    if len(text) > settings.max_text_chars:
        raise HTTPException(status_code=413, detail=f"Input is too large. Limit is {settings.max_text_chars} characters.")

    ranked = rank_quotable_sentences(text, top_n=top_n)
    if not ranked:
        raise HTTPException(status_code=422, detail="No analyzable sentences found. Try a longer document with complete sentences.")

    document = Document(title=title.strip() or "Untitled", source_type=source_type)
    session.add(document)
    session.commit()
    session.refresh(document)

    rows: list[Sentence] = []
    for item in ranked:
        sentence = Sentence(
            document_id=document.id,
            text=item.text,
            score=item.score,
            position=item.position,
            is_selected=item.is_selected,
        )
        session.add(sentence)
        rows.append(sentence)
    session.commit()
    for row in rows:
        session.refresh(row)

    return AnalyzeResponse(
        document_id=document.id,
        title=document.title,
        source_type=document.source_type,
        created_at=document.created_at,
        sentences=[
            SentenceResult(
                id=row.id,
                text=row.text,
                score=row.score,
                position=row.position,
                is_selected=row.is_selected,
            )
            for row in sorted(rows, key=lambda s: s.score, reverse=True)
        ],
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    documents = session.exec(select(Document).order_by(Document.created_at.desc()).limit(8)).all()
    return templates.TemplateResponse("index.html", {"request": request, "documents": documents, "settings": settings})


@app.post("/ui/analyze-text")
def analyze_text_form(
    title: str = Form("Pasted text"),
    text: str = Form(...),
    session: Session = Depends(get_session),
):
    result = persist_analysis(session, title=title, source_type="text", text=text, top_n=settings.top_n_sentences)
    return RedirectResponse(url=f"/documents/{result.document_id}", status_code=303)


@app.post("/ui/analyze-pdf")
async def analyze_pdf_form(
    title: str = Form("Uploaded PDF"),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if file.content_type not in {"application/pdf", "application/octet-stream"} and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    text = extract_pdf_text(await file.read())
    result = persist_analysis(session, title=title or file.filename, source_type="pdf", text=text, top_n=settings.top_n_sentences)
    return RedirectResponse(url=f"/documents/{result.document_id}", status_code=303)


@app.post("/analyze-text", response_model=AnalyzeResponse)
def analyze_text_api(payload: TextAnalyzeRequest, session: Session = Depends(get_session)):
    return persist_analysis(
        session,
        title=payload.title,
        source_type="text",
        text=payload.text,
        top_n=payload.top_n or settings.top_n_sentences,
    )


@app.post("/analyze-pdf", response_model=AnalyzeResponse)
async def analyze_pdf_api(
    title: str = Form("Uploaded PDF"),
    top_n: int = Form(None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    text = extract_pdf_text(await file.read())
    return persist_analysis(
        session,
        title=title or file.filename,
        source_type="pdf",
        text=text,
        top_n=top_n or settings.top_n_sentences,
    )


@app.get("/documents", response_model=list[DocumentSummary])
def list_documents(session: Session = Depends(get_session)):
    docs = session.exec(select(Document).order_by(Document.created_at.desc())).all()
    summaries: list[DocumentSummary] = []
    for doc in docs:
        count = session.exec(select(func.count(Sentence.id)).where(Sentence.document_id == doc.id)).one()
        summaries.append(DocumentSummary(id=doc.id, title=doc.title, source_type=doc.source_type, created_at=doc.created_at, sentence_count=count))
    return summaries


@app.get("/documents/{document_id}", response_class=HTMLResponse)
def view_document(document_id: int, request: Request, session: Session = Depends(get_session)):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    sentences = session.exec(select(Sentence).where(Sentence.document_id == document_id).order_by(Sentence.score.desc())).all()
    return templates.TemplateResponse("document.html", {"request": request, "document": document, "sentences": sentences})


@app.get("/health")
def health():
    return {"ok": True, "app": settings.app_name}
