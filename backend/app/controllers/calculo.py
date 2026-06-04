"""
controllers/calculo.py
Rotas REST para cálculo do orçamento óptico.

Endpoints:
  POST /calculo/orcamento          → calcula a partir de um projeto no corpo
  POST /calculo/orcamento/{id}     → calcula a partir de um projeto salvo
  GET  /calculo/splitters          → lista todas as tabelas de splitters
"""

from fastapi import APIRouter, HTTPException, status

from app.models.network import Projeto
from app.models.constants import (
    PERDA_SPLITTER_BALANCEADO_DB,
    SPLITTERS_DESBALANCEADOS,
)
from app.services.calculo_optico import CalculadoraOrcamentoOptico
from app.services import projeto_service

router = APIRouter()


@router.post("/orcamento", summary="Calcular orçamento óptico (projeto no corpo)")
def calcular_inline(projeto: Projeto):
    """
    Recebe um projeto completo no corpo da requisição e retorna
    o orçamento óptico calculado para todos os caminhos OLT → ONU.

    Útil para cálculo em tempo real enquanto o usuário edita
    a topologia no frontend, sem precisar salvar o projeto antes.
    """
    try:
        calculadora = CalculadoraOrcamentoOptico(projeto)
        return calculadora.calcular()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/orcamento/{projeto_id}", summary="Calcular orçamento óptico (projeto salvo)")
def calcular_por_id(projeto_id: str):
    """
    Carrega um projeto salvo pelo ID e retorna o orçamento óptico calculado.
    """
    projeto = projeto_service.obter_projeto(projeto_id)
    if not projeto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projeto '{projeto_id}' não encontrado."
        )
    try:
        calculadora = CalculadoraOrcamentoOptico(projeto)
        return calculadora.calcular()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/splitters", summary="Listar tabelas de splitters")
def listar_splitters():
    """
    Retorna as tabelas de referência de perdas de splitters
    balanceados e desbalanceados disponíveis no sistema.

    Usado pelo frontend para popular os formulários de cadastro de splitters.
    """
    return {
        "balanceados": [
            {
                "razao": f"1x{razao}",
                "perda_db": perda,
                "descricao": f"Splitter balanceado 1x{razao} — {perda} dB",
            }
            for razao, perda in PERDA_SPLITTER_BALANCEADO_DB.items()
        ],
        "desbalanceados": [
            {
                "razao": rotulo,
                "perda_principal_db": s.perda_principal_db,
                "perda_derivacao_db": s.perda_derivacao_db,
                "descricao": s.descricao,
            }
            for rotulo, s in SPLITTERS_DESBALANCEADOS.items()
        ],
    }