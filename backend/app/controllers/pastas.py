"""
controllers/pastas.py
Rotas REST para gerenciamento hierárquico de pastas e projetos.

Endpoints:
  GET    /pastas                              → árvore da raiz
  GET    /pastas/{caminho}/conteudo           → árvore de subpasta
  POST   /pastas/nova/{caminho}               → cria pasta
  DELETE /pastas/del/{caminho}                → exclui pasta e conteúdo

  POST   /pastas/raiz/projetos/{nome}         → salva projeto na raiz
  GET    /pastas/raiz/projetos/{nome}         → carrega projeto da raiz
  DELETE /pastas/raiz/projetos/{nome}         → exclui projeto da raiz

  POST   /pastas/{caminho}/projetos/{nome}    → salva projeto em subpasta
  GET    /pastas/{caminho}/projetos/{nome}    → carrega projeto de subpasta
  DELETE /pastas/{caminho}/projetos/{nome}    → exclui projeto de subpasta
"""

from fastapi import APIRouter, HTTPException, status
from app.models.network import Projeto
from app.services import projeto_service as svc

router = APIRouter()


# ---------------------------------------------------------------------------
# Pastas — listagem
# ---------------------------------------------------------------------------

@router.get("", summary="Listar raiz")
def listar_raiz():
    return svc.listar_arvore("")


@router.get("/{caminho:path}/conteudo", summary="Listar subpasta")
def listar_pasta(caminho: str):
    return svc.listar_arvore(caminho)


# ---------------------------------------------------------------------------
# Pastas — criar / excluir (prefixos distintos para evitar conflito com :path)
# ---------------------------------------------------------------------------

@router.post("/nova/{caminho:path}", status_code=status.HTTP_201_CREATED, summary="Criar pasta")
def criar_pasta(caminho: str):
    try:
        svc.criar_pasta(caminho)
        return {"caminho": caminho, "criado": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/del/{caminho:path}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir pasta")
def excluir_pasta(caminho: str):
    try:
        ok = svc.excluir_pasta(caminho)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Pasta '{caminho}' não encontrada.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Projetos na raiz  (/pastas/raiz/projetos/{nome})
# ---------------------------------------------------------------------------

@router.post("/raiz/projetos/{nome}", status_code=status.HTTP_201_CREATED, summary="Salvar na raiz")
def salvar_raiz(nome: str, projeto: Projeto):
    try:
        return svc.salvar_projeto("", nome, projeto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/raiz/projetos/{nome}", summary="Carregar da raiz")
def carregar_raiz(nome: str):
    proj = svc.carregar_projeto("", nome)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Projeto '{nome}' não encontrado na raiz.")
    return proj


@router.delete("/raiz/projetos/{nome}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir da raiz")
def excluir_raiz(nome: str):
    ok = svc.excluir_projeto_arquivo("", nome)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Projeto '{nome}' não encontrado.")


# ---------------------------------------------------------------------------
# Projetos em subpastas  (/pastas/{caminho}/projetos/{nome})
# ---------------------------------------------------------------------------

@router.post("/{caminho:path}/projetos/{nome}", status_code=status.HTTP_201_CREATED, summary="Salvar em subpasta")
def salvar_em_pasta(caminho: str, nome: str, projeto: Projeto):
    try:
        return svc.salvar_projeto(caminho, nome, projeto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{caminho:path}/projetos/{nome}", summary="Carregar de subpasta")
def carregar_de_pasta(caminho: str, nome: str):
    proj = svc.carregar_projeto(caminho, nome)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Projeto '{nome}' não encontrado em '{caminho}'.")
    return proj


@router.delete("/{caminho:path}/projetos/{nome}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir de subpasta")
def excluir_de_pasta(caminho: str, nome: str):
    ok = svc.excluir_projeto_arquivo(caminho, nome)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Projeto '{nome}' não encontrado.")