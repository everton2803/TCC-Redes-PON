"""
services/projeto_service.py
Lógica de negócio para gerenciamento de projetos.

Persiste os projetos como arquivos JSON no diretório data/projects/.
"""

import json
import os
from datetime import datetime, timezone

from app.models.network import Projeto

PROJECTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "projects")


def _caminho(projeto_id: str) -> str:
    return os.path.join(PROJECTS_DIR, f"{projeto_id}.json")


def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def listar_projetos() -> list[dict]:
    """Retorna metadados (id, nome, descricao, atualizado_em) de todos os projetos."""
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    resultado = []
    for arquivo in sorted(os.listdir(PROJECTS_DIR)):
        if arquivo.endswith(".json"):
            with open(os.path.join(PROJECTS_DIR, arquivo)) as f:
                dados = json.load(f)
            resultado.append({
                "id":           dados.get("id"),
                "nome":         dados.get("nome"),
                "descricao":    dados.get("descricao"),
                "criado_em":    dados.get("criado_em"),
                "atualizado_em":dados.get("atualizado_em"),
                "total_nos":    len(dados.get("nos", [])),
                "total_enlaces":len(dados.get("enlaces", [])),
            })
    return resultado


def obter_projeto(projeto_id: str) -> Projeto | None:
    """Carrega um projeto pelo ID. Retorna None se não existir."""
    caminho = _caminho(projeto_id)
    if not os.path.exists(caminho):
        return None
    with open(caminho) as f:
        return Projeto(**json.load(f))


def criar_projeto(projeto: Projeto) -> Projeto:
    """Salva um novo projeto. Define criado_em e atualizado_em."""
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    agora = _agora()
    projeto.criado_em    = agora
    projeto.atualizado_em = agora
    with open(_caminho(projeto.id), "w") as f:
        json.dump(projeto.model_dump(), f, ensure_ascii=False, indent=2)
    return projeto


def atualizar_projeto(projeto_id: str, projeto: Projeto) -> Projeto | None:
    """Atualiza um projeto existente. Retorna None se não existir."""
    if not os.path.exists(_caminho(projeto_id)):
        return None
    projeto.id            = projeto_id
    projeto.atualizado_em = _agora()
    with open(_caminho(projeto_id), "w") as f:
        json.dump(projeto.model_dump(), f, ensure_ascii=False, indent=2)
    return projeto


def excluir_projeto(projeto_id: str) -> bool:
    """Remove o arquivo do projeto. Retorna True se removido, False se não existia."""
    caminho = _caminho(projeto_id)
    if not os.path.exists(caminho):
        return False
    os.remove(caminho)
    return True