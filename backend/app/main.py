from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.tenders import router as tenders_router
from app.api.documents import router as documents_router
from app.api.requirements import router as requirements_router
from app.api.company import router as company_router
from app.api.intelligence import router as intelligence_router
from app.api.audit import router as audit_router


app = FastAPI(
    title="Tender Intelligence API"
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(tenders_router)
app.include_router(documents_router)
app.include_router(requirements_router)
app.include_router(company_router)
app.include_router(intelligence_router)
app.include_router(audit_router)
