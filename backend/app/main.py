"""
app/main.py
Ponto de entrada da aplicação FastAPI — PON Planner.

Inicializa a aplicação, registra os roteadores, configura CORS
e serve o frontend estático em http://localhost:8000/app.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.controllers import projetos, calculo, pastas

app = FastAPI(
    title="PON Planner API",
    description=(
        "API RESTful para modelagem e cálculo de orçamento óptico "
        "em redes FTTH baseadas em arquitetura PON.\n\n"
        "TCC — Everton José Serighelli | IFC Campus Videira (2026)"
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Roteadores da API
# ---------------------------------------------------------------------------
app.include_router(projetos.router, prefix="/projetos", tags=["Projetos"])
app.include_router(calculo.router,  prefix="/calculo",  tags=["Cálculo Óptico"])
app.include_router(pastas.router,   prefix="/pastas",   tags=["Pastas"])

# ---------------------------------------------------------------------------
# Frontend estático — servido em /app
# ---------------------------------------------------------------------------
# No container: WORKDIR=/app, frontend copiado para /app/frontend/
# main.py fica em /app/app/main.py → sobe dois níveis para /app/
_BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(_BASE_DIR, "frontend", "public")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    # Fallback: tenta o caminho de desenvolvimento local
    _DEV_DIR = os.path.join(_BASE_DIR, "..", "frontend", "public")
    if os.path.isdir(_DEV_DIR):
        app.mount("/app", StaticFiles(directory=_DEV_DIR, html=True), name="frontend")


@app.get("/", tags=["Status"])
def raiz():
    """Verifica se a API está no ar."""
    return {
        "status": "ok",
        "app": "PON Planner API",
        "versao": "1.0.0",
        "frontend": "http://localhost:8000/app",
        "frontend_dir_encontrado": os.path.isdir(FRONTEND_DIR),
        "frontend_dir": FRONTEND_DIR,
    }