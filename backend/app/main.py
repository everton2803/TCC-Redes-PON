"""
app/main.py
Ponto de entrada da aplicação FastAPI — PON Planner.

Inicializa a aplicação, registra os roteadores e configura CORS
para permitir que o frontend (HTML/JS) consuma a API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import projetos, calculo

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
# CORS — permite que o frontend local consuma a API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # em produção, restringir ao domínio do frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Roteadores
# ---------------------------------------------------------------------------
app.include_router(projetos.router, prefix="/projetos", tags=["Projetos"])
app.include_router(calculo.router,  prefix="/calculo",  tags=["Cálculo Óptico"])


@app.get("/", tags=["Status"])
def raiz():
    """Verifica se a API está no ar."""
    return {"status": "ok", "app": "PON Planner API", "versao": "1.0.0"}