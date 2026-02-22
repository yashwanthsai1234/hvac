"""FastAPI entry point for the HVAC Margin Rescue Agent backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.connection import init_db
from backend.routes.portfolio import router as portfolio_router
from backend.routes.dossier import router as dossier_router
from backend.routes.chat import router as chat_router
from backend.routes.email import router as email_router

app = FastAPI(title="HVAC Margin Rescue Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio_router)
app.include_router(dossier_router)
app.include_router(chat_router)
app.include_router(email_router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
