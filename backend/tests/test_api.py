"""
tests/test_api.py
Testes de integração da API REST — PON Planner.

Usa o TestClient do FastAPI (HTTPX) para simular requisições HTTP
sem subir um servidor real.
"""

import sys, os, json, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _projeto_minimo() -> dict:
    """Payload de projeto válido com 1 OLT, 1 Splitter e 1 ONU."""
    pid = str(uuid.uuid4())
    return {
        "id": pid,
        "nome": f"Projeto Teste {pid[:8]}",
        "descricao": "Projeto gerado pelos testes automatizados",
        "parametros": {
            "atenuacao_fibra_db_por_km": 0.35,
            "perda_conector_db": 0.5,
            "perda_fusao_db": 0.1,
            "margem_sistema_db": 3.0,
        },
        "nos": [
            {"id": "olt-t", "tipo": "OLT",     "nome": "OLT",      "potencia_tx_dbm": 5.0, "sensibilidade_rx_dbm": -28.0, "padrao_pon": "GPON"},
            {"id": "spl-t", "tipo": "Splitter", "nome": "Spl 1x4",  "razao": 4},
            {"id": "onu-t", "tipo": "ONU",      "nome": "ONU-01",   "sensibilidade_rx_dbm": -27.0},
        ],
        "enlaces": [
            {"id": "e1", "id_origem": "olt-t", "id_destino": "spl-t",
             "comprimento_m": 1000, "atenuacao_db_por_km": 0.35,
             "num_conexoes": 2, "perda_por_conexao_db": 0.1, "tipo_conexao": "fusao"},
            {"id": "e2", "id_origem": "spl-t", "id_destino": "onu-t",
             "comprimento_m": 500, "atenuacao_db_por_km": 0.35,
             "num_conexoes": 2, "perda_por_conexao_db": 0.1, "tipo_conexao": "fusao"},
        ],
    }


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

class TestStatus:
    def test_raiz_retorna_ok(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# CRUD de Projetos
# ---------------------------------------------------------------------------

class TestProjetoCRUD:

    def test_criar_projeto(self):
        payload = _projeto_minimo()
        r = client.post("/projetos", json=payload)
        assert r.status_code == 201
        dados = r.json()
        assert dados["id"] == payload["id"]
        assert dados["nome"] == payload["nome"]
        assert dados["criado_em"] is not None
        assert dados["atualizado_em"] is not None

    def test_criar_projeto_usa_perda_fusao_padrao_03(self):
        payload = _projeto_minimo()
        payload["parametros"] = {
            "atenuacao_fibra_db_por_km": 0.35,
            "perda_conector_db": 0.5,
            "margem_sistema_db": 3.0,
        }
        r = client.post("/projetos", json=payload)
        assert r.status_code == 201
        assert r.json()["parametros"]["perda_fusao_db"] == 0.03

    def test_obter_projeto(self):
        payload = _projeto_minimo()
        client.post("/projetos", json=payload)
        r = client.get(f"/projetos/{payload['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == payload["id"]

    def test_obter_projeto_inexistente(self):
        r = client.get("/projetos/nao-existe-xyz")
        assert r.status_code == 404

    def test_listar_projetos_retorna_lista(self):
        client.post("/projetos", json=_projeto_minimo())
        r = client.get("/projetos")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_listar_projetos_contem_metadados(self):
        payload = _projeto_minimo()
        client.post("/projetos", json=payload)
        r = client.get("/projetos")
        ids = [p["id"] for p in r.json()]
        assert payload["id"] in ids
        # Verifica campos de metadados
        item = next(p for p in r.json() if p["id"] == payload["id"])
        assert "total_nos" in item
        assert "total_enlaces" in item
        assert item["total_nos"] == 3
        assert item["total_enlaces"] == 2

    def test_atualizar_projeto(self):
        payload = _projeto_minimo()
        client.post("/projetos", json=payload)
        payload["nome"] = "Nome Atualizado"
        r = client.put(f"/projetos/{payload['id']}", json=payload)
        assert r.status_code == 200
        assert r.json()["nome"] == "Nome Atualizado"

    def test_atualizar_projeto_inexistente(self):
        payload = _projeto_minimo()
        payload["id"] = "nao-existe-xyz"
        r = client.put("/projetos/nao-existe-xyz", json=payload)
        assert r.status_code == 404

    def test_excluir_projeto(self):
        payload = _projeto_minimo()
        client.post("/projetos", json=payload)
        r = client.delete(f"/projetos/{payload['id']}")
        assert r.status_code == 204
        # Confirma que foi removido
        r2 = client.get(f"/projetos/{payload['id']}")
        assert r2.status_code == 404

    def test_excluir_projeto_inexistente(self):
        r = client.delete("/projetos/nao-existe-xyz")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Cálculo óptico via API
# ---------------------------------------------------------------------------

class TestCalculoAPI:

    def test_calcular_inline_retorna_resultado(self):
        r = client.post("/calculo/orcamento", json=_projeto_minimo())
        assert r.status_code == 200
        dados = r.json()
        assert "caminhos" in dados
        assert dados["total_onus"] == 1

    def test_calcular_inline_perda_correta(self):
        r = client.post("/calculo/orcamento", json=_projeto_minimo())
        caminho = r.json()["caminhos"][0]
        # Splitter 1x4 = 7,2 dB | fibra 1000m = 0,35 | fusões 2×0,1 = 0,2
        # fibra 500m = 0,175 | fusões 2×0,1 = 0,2 → total 8,125 dB
        assert abs(caminho["perda_total_db"] - 8.125) < 0.001

    def test_calcular_inline_status_ok(self):
        r = client.post("/calculo/orcamento", json=_projeto_minimo())
        assert r.json()["caminhos"][0]["status"] == "OK"

    def test_calcular_por_id(self):
        payload = _projeto_minimo()
        client.post("/projetos", json=payload)
        r = client.post(f"/calculo/orcamento/{payload['id']}")
        assert r.status_code == 200
        assert r.json()["total_onus"] == 1

    def test_calcular_por_id_inexistente(self):
        r = client.post("/calculo/orcamento/nao-existe-xyz")
        assert r.status_code == 404

    def test_calcular_sem_olt_retorna_422(self):
        payload = _projeto_minimo()
        payload["nos"] = [n for n in payload["nos"] if n["tipo"] != "OLT"]
        r = client.post("/calculo/orcamento", json=payload)
        assert r.status_code == 422

    def test_resultado_contem_resumo(self):
        r = client.post("/calculo/orcamento", json=_projeto_minimo())
        dados = r.json()
        assert "onus_ok" in dados
        assert "onus_margem_baixa" in dados
        assert "onus_reprovadas" in dados

    def test_caminho_contem_detalhes(self):
        r = client.post("/calculo/orcamento", json=_projeto_minimo())
        caminho = r.json()["caminhos"][0]
        assert "detalhes" in caminho
        tipos = [d["tipo"] for d in caminho["detalhes"]]
        assert "Splitter" in tipos
        assert "Fibra" in tipos
        # enlaces OLT→Splitter e Splitter→ONU usam fusão por padrão
        assert "Fusão" in tipos


# ---------------------------------------------------------------------------
# Tabelas de splitters
# ---------------------------------------------------------------------------

class TestSplitters:

    def test_listar_splitters_retorna_ambas_tabelas(self):
        r = client.get("/calculo/splitters")
        assert r.status_code == 200
        dados = r.json()
        assert "balanceados" in dados
        assert "desbalanceados" in dados

    def test_splitters_balanceados_contem_6_razoes(self):
        r = client.get("/calculo/splitters")
        assert len(r.json()["balanceados"]) == 6

    def test_splitters_desbalanceados_contem_12_razoes(self):
        r = client.get("/calculo/splitters")
        assert len(r.json()["desbalanceados"]) == 12

    def test_splitter_desbalanceado_contem_campos_corretos(self):
        r = client.get("/calculo/splitters")
        item = r.json()["desbalanceados"][0]
        assert "razao" in item
        assert "perda_principal_db" in item
        assert "perda_derivacao_db" in item
        assert "descricao" in item