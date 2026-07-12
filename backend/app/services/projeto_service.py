"""
services/projeto_service.py
Gerenciamento hierárquico de projetos em pastas e subpastas.

Estrutura em disco:
  data/projects/
  ├── pasta_a/
  │   ├── subpasta/
  │   │   └── projeto.json
  │   └── outro.json
  └── raiz.json

Caminhos de pasta são strings com "/" como separador, ex: "cliente_a/bairro_norte".
"""

import json
import os
import re
import shutil
from datetime import datetime, timezone
from app.models.network import Projeto

PROJECTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "projects")
)

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _sanitizar(nome: str) -> str:
    """Remove caracteres perigosos de nomes de pasta/arquivo."""
    nome = nome.strip().replace("\\", "/")
    # Remove .. e caracteres inválidos
    nome = re.sub(r"\.\.", "", nome)
    nome = re.sub(r"[^\w\s\-/.]", "", nome, flags=re.UNICODE)
    return nome.strip("/")


def _pasta_abs(caminho_pasta: str) -> str:
    """Converte caminho relativo de pasta para absoluto, validando que fica dentro de PROJECTS_DIR."""
    pasta = os.path.normpath(os.path.join(PROJECTS_DIR, _sanitizar(caminho_pasta)))
    if not pasta.startswith(PROJECTS_DIR):
        raise ValueError("Caminho de pasta inválido.")
    return pasta


def _arquivo_abs(caminho_pasta: str, nome_arquivo: str) -> str:
    pasta = _pasta_abs(caminho_pasta)
    nome  = _sanitizar(nome_arquivo).replace("/", "_")
    if not nome.endswith(".json"):
        nome += ".json"
    return os.path.join(pasta, nome)


# ---------------------------------------------------------------------------
# Operações de pasta
# ---------------------------------------------------------------------------

def listar_arvore(caminho_pasta: str = "") -> dict:
    """
    Retorna a árvore de pastas e projetos a partir de caminho_pasta.
    Formato:
      {
        "caminho": "cliente_a/bairro_norte",
        "pastas": [ { "nome": "expansao", "caminho": "cliente_a/bairro_norte/expansao" }, ... ],
        "projetos": [ { "nome": "rede_ftth", "caminho_pasta": "...", "atualizado_em": "...", ... }, ... ]
      }
    """
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    pasta_abs = _pasta_abs(caminho_pasta)
    os.makedirs(pasta_abs, exist_ok=True)

    pastas   = []
    projetos = []

    for entry in sorted(os.scandir(pasta_abs), key=lambda e: e.name):
        rel = os.path.relpath(entry.path, PROJECTS_DIR).replace("\\", "/")
        if entry.is_dir():
            pastas.append({"nome": entry.name, "caminho": rel})
        elif entry.is_file() and entry.name.endswith(".json"):
            try:
                with open(entry.path, encoding="utf-8") as f:
                    dados = json.load(f)
                projetos.append({
                    "nome_arquivo":  entry.name[:-5],  # sem .json
                    "caminho_pasta": caminho_pasta or "",
                    "id":            dados.get("id"),
                    "nome":          dados.get("nome"),
                    "atualizado_em": dados.get("atualizado_em"),
                    "total_nos":     len(dados.get("nos", [])),
                    "total_enlaces": len(dados.get("enlaces", [])),
                })
            except Exception:
                pass  # ignora JSONs corrompidos

    return {
        "caminho": caminho_pasta or "",
        "pastas":  pastas,
        "projetos": projetos,
    }


def criar_pasta(caminho_pasta: str) -> bool:
    """Cria uma pasta (e subpastas intermediárias). Retorna True se criada."""
    pasta_abs = _pasta_abs(caminho_pasta)
    os.makedirs(pasta_abs, exist_ok=True)
    return True


def renomear_pasta(caminho_atual: str, novo_nome: str) -> bool:
    """Renomeia uma pasta. Retorna True se renomeada."""
    abs_atual = _pasta_abs(caminho_atual)
    pai       = os.path.dirname(abs_atual)
    abs_novo  = os.path.join(pai, _sanitizar(novo_nome).replace("/", "_"))
    if not os.path.exists(abs_atual):
        return False
    os.rename(abs_atual, abs_novo)
    return True


def excluir_pasta(caminho_pasta: str) -> bool:
    """Remove pasta e todo seu conteúdo. Retorna True se removida."""
    pasta_abs = _pasta_abs(caminho_pasta)
    if not os.path.exists(pasta_abs) or pasta_abs == PROJECTS_DIR:
        return False
    shutil.rmtree(pasta_abs)
    return True


# ---------------------------------------------------------------------------
# Operações de projeto
# ---------------------------------------------------------------------------

def salvar_projeto(caminho_pasta: str, nome_arquivo: str, projeto: Projeto) -> Projeto:
    """Salva um projeto em caminho_pasta/nome_arquivo.json."""
    pasta_abs = _pasta_abs(caminho_pasta)
    os.makedirs(pasta_abs, exist_ok=True)

    agora = _agora()
    if not projeto.criado_em:
        projeto.criado_em = agora
    projeto.atualizado_em = agora

    arq = _arquivo_abs(caminho_pasta, nome_arquivo)
    with open(arq, "w", encoding="utf-8") as f:
        json.dump(projeto.model_dump(), f, ensure_ascii=False, indent=2)
    return projeto


def carregar_projeto(caminho_pasta: str, nome_arquivo: str) -> Projeto | None:
    """Carrega um projeto de caminho_pasta/nome_arquivo.json."""
    arq = _arquivo_abs(caminho_pasta, nome_arquivo)
    if not os.path.exists(arq):
        return None
    with open(arq, encoding="utf-8") as f:
        return Projeto(**json.load(f))


def excluir_projeto_arquivo(caminho_pasta: str, nome_arquivo: str) -> bool:
    """Remove o arquivo do projeto. Retorna True se removido."""
    arq = _arquivo_abs(caminho_pasta, nome_arquivo)
    if not os.path.exists(arq):
        return False
    os.remove(arq)
    return True


def mover_projeto(
    origem_pasta: str, nome_arquivo: str, destino_pasta: str
) -> bool:
    """Move um projeto entre pastas."""
    arq_origem  = _arquivo_abs(origem_pasta, nome_arquivo)
    pasta_dest  = _pasta_abs(destino_pasta)
    os.makedirs(pasta_dest, exist_ok=True)
    arq_destino = os.path.join(pasta_dest, os.path.basename(arq_origem))
    if not os.path.exists(arq_origem):
        return False
    shutil.move(arq_origem, arq_destino)
    return True


# ---------------------------------------------------------------------------
# Compatibilidade com endpoints legados (usados pelos testes existentes)
# ---------------------------------------------------------------------------

def _caminho_legado(projeto_id: str) -> str:
    return os.path.join(PROJECTS_DIR, f"{projeto_id}.json")


def listar_projetos() -> list[dict]:
    arvore = listar_arvore("")
    return arvore["projetos"]


def obter_projeto(projeto_id: str) -> Projeto | None:
    arq = _caminho_legado(projeto_id)
    if not os.path.exists(arq):
        return None
    with open(arq, encoding="utf-8") as f:
        return Projeto(**json.load(f))


def criar_projeto(projeto: Projeto) -> Projeto:
    return salvar_projeto("", projeto.id, projeto)


def atualizar_projeto(projeto_id: str, projeto: Projeto) -> Projeto | None:
    arq = _caminho_legado(projeto_id)
    if not os.path.exists(arq):
        return None
    projeto.id = projeto_id
    projeto.atualizado_em = _agora()
    with open(arq, "w", encoding="utf-8") as f:
        json.dump(projeto.model_dump(), f, ensure_ascii=False, indent=2)
    return projeto


def excluir_projeto(projeto_id: str) -> bool:
    arq = _caminho_legado(projeto_id)
    if not os.path.exists(arq):
        return False
    os.remove(arq)
    return True