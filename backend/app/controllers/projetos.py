"""
controllers/projetos.py
Rotas REST para gerenciamento de projetos de rede PON.

Endpoints:
  GET    /projetos            → lista todos os projetos
  POST   /projetos            → cria um novo projeto
  GET    /projetos/{id}       → retorna um projeto completo
  PUT    /projetos/{id}       → atualiza um projeto existente
  DELETE /projetos/{id}       → remove um projeto
"""

from fastapi import APIRouter, HTTPException, status
from app.models.network import Projeto
from app.services import projeto_service

router = APIRouter()


@router.get("", summary="Listar projetos")
def listar():
    """Retorna metadados de todos os projetos salvos."""
    return projeto_service.listar_projetos()


@router.post("", status_code=status.HTTP_201_CREATED, summary="Criar projeto")
def criar(projeto: Projeto):
    """
    Cria e persiste um novo projeto de rede PON.

    O campo `id` é gerado automaticamente se não informado.
    Os campos `criado_em` e `atualizado_em` são preenchidos pelo servidor.
    """
    return projeto_service.criar_projeto(projeto)


@router.get("/{projeto_id}", summary="Obter projeto")
def obter(projeto_id: str):
    """Retorna o projeto completo (nós, enlaces e parâmetros)."""
    projeto = projeto_service.obter_projeto(projeto_id)
    if not projeto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projeto '{projeto_id}' não encontrado."
        )
    return projeto


@router.put("/{projeto_id}", summary="Atualizar projeto")
def atualizar(projeto_id: str, projeto: Projeto):
    """
    Substitui completamente um projeto existente.

    Envia o projeto inteiro (nós + enlaces + parâmetros) no corpo da requisição.
    O campo `atualizado_em` é atualizado automaticamente.
    """
    atualizado = projeto_service.atualizar_projeto(projeto_id, projeto)
    if not atualizado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projeto '{projeto_id}' não encontrado."
        )
    return atualizado


@router.delete("/{projeto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir projeto")
def excluir(projeto_id: str):
    """Remove permanentemente um projeto."""
    removido = projeto_service.excluir_projeto(projeto_id)
    if not removido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projeto '{projeto_id}' não encontrado."
        )