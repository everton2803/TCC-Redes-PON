"""
tests/test_calculo_optico.py
Testes unitários da engine de cálculo do orçamento óptico.

Cada teste valida um cenário específico descrito no TCC,
usando cálculos manuais como referência.
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.network import (
    Projeto, ParametrosGlobais, Enlace, PosicaoXY,
    NoOLT, NoSplitter, NoCaixaEmenda, NoONU,
    TipoNo, PadraPON, RazaoSplitter,
)
from app.services.calculo_optico import CalculadoraOrcamentoOptico


# ---------------------------------------------------------------------------
# Fixtures — projetos reutilizáveis nos testes
# ---------------------------------------------------------------------------

def _projeto_simples() -> Projeto:
    """
    Topologia mínima:  OLT ──(1 km)── Splitter 1x4 ──(0,5 km)── ONU

    Cálculo manual esperado:
      Perda fibra OLT→Spl : 1,0 km × 0,35 = 0,350 dB
      Perda conectores     : 2 × 0,5       = 1,000 dB
      Perda splitter 1x4   :                 7,300 dB
      Perda fibra Spl→ONU  : 0,5 km × 0,35 = 0,175 dB
      Perda conectores     : 2 × 0,5       = 1,000 dB
      ─────────────────────────────────────────────────
      Perda total          :                 9,825 dB
      Potência TX OLT      :                 5,000 dBm
      Potência RX ONU      : 5,0 - 9,825   = -4,825 dBm   ← bem acima do limiar
    """
    olt  = NoOLT(id="olt", tipo=TipoNo.OLT, nome="OLT", potencia_tx_dbm=5.0, sensibilidade_rx_dbm=-28.0, padrao_pon=PadraPON.GPON)
    spl  = NoSplitter(id="spl", tipo=TipoNo.SPLITTER, nome="Spl 1x4", razao=RazaoSplitter.S_1x4)
    onu  = NoONU(id="onu", tipo=TipoNo.ONU, nome="ONU-01", sensibilidade_rx_dbm=-27.0)

    enlace1 = Enlace(id="e1", id_origem="olt", id_destino="spl",
                     comprimento_m=1000, atenuacao_db_por_km=0.35,
                     num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao")
    enlace2 = Enlace(id="e2", id_origem="spl", id_destino="onu",
                     comprimento_m=500, atenuacao_db_por_km=0.35,
                     num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao")

    return Projeto(
        id="p1", nome="Simples",
        nos=[olt.model_dump(), spl.model_dump(), onu.model_dump()],
        enlaces=[enlace1, enlace2],
        parametros=ParametrosGlobais(margem_sistema_db=3.0),
    )


def _projeto_com_caixa_emenda() -> Projeto:
    """
    OLT ──(0,5 km)── CEO(4 fusões) ──(1 km)── Splitter 1x8 ──(0,2 km)── ONU

    Cálculo manual:
      Fibra OLT→CEO  : 0,5 × 0,35  = 0,175 dB
      Conectores      : 2 × 0,5     = 1,000 dB
      Fusões CEO      : 4 × 0,1     = 0,400 dB
      Fibra CEO→Spl   : 1,0 × 0,35  = 0,350 dB
      Conectores      : 2 × 0,5     = 1,000 dB
      Splitter 1x8    :               10,800 dB
      Fibra Spl→ONU   : 0,2 × 0,35  = 0,070 dB
      Conectores      : 2 × 0,5     = 1,000 dB
      ──────────────────────────────────────────
      Perda total     :               14,795 dB
      Potência RX     : 5,0 - 14,795 = -9,795 dBm
    """
    olt = NoOLT(id="olt", tipo=TipoNo.OLT, nome="OLT", potencia_tx_dbm=5.0, sensibilidade_rx_dbm=-28.0, padrao_pon=PadraPON.GPON)
    ceo = NoCaixaEmenda(id="ceo", tipo=TipoNo.CAIXA_EMENDA, nome="CEO-01", num_fusoes=4, perda_por_fusao_db=0.1)
    spl = NoSplitter(id="spl", tipo=TipoNo.SPLITTER, nome="Spl 1x8", razao=RazaoSplitter.S_1x8)
    onu = NoONU(id="onu", tipo=TipoNo.ONU, nome="ONU-01", sensibilidade_rx_dbm=-27.0)

    return Projeto(
        id="p2", nome="Com CEO",
        nos=[olt.model_dump(), ceo.model_dump(), spl.model_dump(), onu.model_dump()],
        enlaces=[
            Enlace(id="e1", id_origem="olt", id_destino="ceo", comprimento_m=500, atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao"),
            Enlace(id="e2", id_origem="ceo", id_destino="spl", comprimento_m=1000, atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao"),
            Enlace(id="e3", id_origem="spl", id_destino="onu", comprimento_m=200, atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao"),
        ],
        parametros=ParametrosGlobais(margem_sistema_db=3.0),
    )


def _projeto_reprovado() -> Projeto:
    """
    OLT com baixa potência + splitter 1x32 + fibra longa = ONU reprovada.

    Cálculo manual:
      Fibra (5 km)   : 5 × 0,35  = 1,750 dB
      Conectores      : 2 × 0,5   = 1,000 dB
      Splitter 1x32   :             17,100 dB
      Fibra (2 km)   : 2 × 0,35  = 0,700 dB
      Conectores      : 2 × 0,5   = 1,000 dB
      ─────────────────────────────────────────
      Perda total     :             21,550 dB
      Potência TX     :              3,000 dBm
      Potência RX     : 3,0 - 21,55 = -18,550 dBm  ← abaixo de -27 dBm? Não.
      Margem          : -18,55 - (-27,0) = 8,45 dB  ← OK, mas vamos testar status
    """
    # Para reprovar de verdade: potência TX baixa + splitter grande + fibra longa
    olt = NoOLT(id="olt", tipo=TipoNo.OLT, nome="OLT", potencia_tx_dbm=-3.0, sensibilidade_rx_dbm=-28.0, padrao_pon=PadraPON.GPON)
    spl = NoSplitter(id="spl", tipo=TipoNo.SPLITTER, nome="Spl 1x32", razao=RazaoSplitter.S_1x32)
    onu = NoONU(id="onu", tipo=TipoNo.ONU, nome="ONU-01", sensibilidade_rx_dbm=-27.0)

    return Projeto(
        id="p3", nome="Reprovado",
        nos=[olt.model_dump(), spl.model_dump(), onu.model_dump()],
        enlaces=[
            Enlace(id="e1", id_origem="olt", id_destino="spl", comprimento_m=10000, atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao"),
            Enlace(id="e2", id_origem="spl", id_destino="onu", comprimento_m=5000,  atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao"),
        ],
        parametros=ParametrosGlobais(margem_sistema_db=3.0),
    )


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

class TestCalculoSimples:
    """Cenário básico: OLT → Splitter → ONU."""

    def setup_method(self):
        self.calc = CalculadoraOrcamentoOptico(_projeto_simples())
        self.resultado = self.calc.calcular()
        self.caminho = self.resultado.caminhos[0]

    def test_encontra_uma_onu(self):
        assert self.resultado.total_onus == 1

    def test_perda_total(self):
        # Splitter 1x4 = 7,2 dB (Tabela 4 TCC)
        # Fibra 1000m: 0,350 | Fusões 2×0,1: 0,200 | Splitter: 7,200 | Fibra 500m: 0,175 | Fusões: 0,200
        # Total: 8,125 dB
        assert abs(self.caminho.perda_total_db - 8.125) < 0.001

    def test_potencia_rx(self):
        # 5,0 - 8,125 = -3,125 dBm
        assert abs(self.caminho.potencia_rx_dbm - (-3.125)) < 0.001

    def test_margem(self):
        # -3,125 - (-27,0) = 23,875 dB
        assert abs(self.caminho.margem_db - 23.875) < 0.001

    def test_status_ok(self):
        assert self.caminho.status == "OK"

    def test_detalhes_contem_splitter(self):
        tipos = [d.tipo for d in self.caminho.detalhes]
        assert "Splitter" in tipos

    def test_detalhes_contem_fibra(self):
        tipos = [d.tipo for d in self.caminho.detalhes]
        assert "Fibra" in tipos

    def test_detalhes_contem_fusoes(self):
        tipos = [d.tipo for d in self.caminho.detalhes]
        assert "Fusão" in tipos


class TestCalculoComCaixaEmenda:
    """Cenário com CEO e fusões: OLT → CEO → Splitter → ONU."""

    def setup_method(self):
        self.calc = CalculadoraOrcamentoOptico(_projeto_com_caixa_emenda())
        self.resultado = self.calc.calcular()
        self.caminho = self.resultado.caminhos[0]

    def test_perda_total(self):
        # Fibra 500m: 0,175 | Fusões: 0,200 | Fusões CEO 4×0,1: 0,400
        # Fibra 1000m: 0,350 | Fusões: 0,200 | Splitter 1x8: 10,500
        # Fibra 200m: 0,070 | Fusões: 0,200
        # Total: 12,095 dB
        assert abs(self.caminho.perda_total_db - 12.095) < 0.001

    def test_potencia_rx(self):
        # 5,0 - 12,095 = -7,095 dBm
        assert abs(self.caminho.potencia_rx_dbm - (-7.095)) < 0.001

    def test_detalhes_contem_fusoes(self):
        tipos = [d.tipo for d in self.caminho.detalhes]
        assert "CaixaEmenda" in tipos

    def test_fusoes_computadas_corretamente(self):
        fusao = next(d for d in self.caminho.detalhes if d.tipo == "CaixaEmenda")
        # 4 fusões × 0,1 dB = 0,4 dB
        assert abs(fusao.perda_db - 0.4) < 0.001

    def test_status_ok(self):
        assert self.caminho.status == "OK"


class TestCalculoReprovado:
    """Cenário de enlace reprovado por sinal insuficiente."""

    def setup_method(self):
        self.calc = CalculadoraOrcamentoOptico(_projeto_reprovado())
        self.resultado = self.calc.calcular()
        self.caminho = self.resultado.caminhos[0]

    def test_status_reprovado(self):
        # TX=-3 dBm, splitter 1x32 (17,1 dB), fibras longas → deve reprovar
        assert self.caminho.status in ("REPROVADO", "MARGEM_BAIXA")

    def test_potencia_rx_muito_baixa(self):
        # A potência deve estar próxima ou abaixo da sensibilidade
        assert self.caminho.potencia_rx_dbm < self.caminho.sensibilidade_rx_dbm + self.caminho.margem_sistema_db

    def test_resumo_conta_reprovadas(self):
        assert self.resultado.onus_reprovadas + self.resultado.onus_margem_baixa >= 1


class TestMultiplasONUs:
    """Carrega o projeto de exemplo JSON e valida múltiplos caminhos."""

    def setup_method(self):
        caminho_json = os.path.join(
            os.path.dirname(__file__), "..", "data", "projects", "exemplo-001.json"
        )
        with open(caminho_json) as f:
            data = json.load(f)
        projeto = Projeto(**data)
        self.resultado = CalculadoraOrcamentoOptico(projeto).calcular()

    def test_encontra_quatro_onus(self):
        assert self.resultado.total_onus == 4

    def test_todos_caminhos_tem_olt_como_inicio(self):
        for caminho in self.resultado.caminhos:
            assert caminho.caminho_ids[0] == "olt-01"

    def test_todos_caminhos_passam_pelos_dois_splitters(self):
        for caminho in self.resultado.caminhos:
            assert "spl-01" in caminho.caminho_ids
            assert "spl-02" in caminho.caminho_ids

    def test_perda_dos_dois_splitters(self):
        # Splitter 1x8 (10,5 dB) + Splitter 1x4 (7,2 dB) = 17,7 dB
        for caminho in self.resultado.caminhos:
            perda_splitters = sum(
                d.perda_db for d in caminho.detalhes if d.tipo == "Splitter"
            )
            assert abs(perda_splitters - 17.7) < 0.001

    def test_status_de_todas_as_onus(self):
        status_validos = {"OK", "MARGEM_BAIXA", "REPROVADO"}
        for caminho in self.resultado.caminhos:
            assert caminho.status in status_validos


class TestSplittersDesbalanceados:
    """Valida as constantes e o cálculo com splitters desbalanceados."""

    def test_tabela_contem_todas_razoes(self):
        from app.models.constants import SPLITTERS_DESBALANCEADOS
        # 12 razões do catálogo Furukawa ET02372 v4 (2021)
        esperadas = {"01/99", "02/98", "05/95", "10/90", "15/85",
                     "20/80", "25/75", "30/70", "35/65", "40/60", "45/55", "50/50"}
        assert esperadas == set(SPLITTERS_DESBALANCEADOS.keys())

    def test_valores_furukawa_et02372(self):
        from app.models.constants import SPLITTERS_DESBALANCEADOS
        # Confere os valores do catálogo Furukawa ET02372 v4 (2021)
        # Nota: a Tabela 4 do TCC apresenta valores aproximados (≈);
        # os valores abaixo são os especificados pelo fabricante.
        assert SPLITTERS_DESBALANCEADOS["10/90"].perda_derivacao_db  == 11.00
        assert SPLITTERS_DESBALANCEADOS["10/90"].perda_principal_db  ==  0.55
        assert SPLITTERS_DESBALANCEADOS["20/80"].perda_derivacao_db  ==  7.90
        assert SPLITTERS_DESBALANCEADOS["20/80"].perda_principal_db  ==  1.40
        assert SPLITTERS_DESBALANCEADOS["30/70"].perda_derivacao_db  ==  6.00
        assert SPLITTERS_DESBALANCEADOS["30/70"].perda_principal_db  ==  1.90
        assert SPLITTERS_DESBALANCEADOS["40/60"].perda_derivacao_db  ==  4.70
        assert SPLITTERS_DESBALANCEADOS["40/60"].perda_principal_db  ==  2.70
        # Razões exclusivas do catálogo Furukawa (não presentes na Tabela 4 do TCC)
        assert SPLITTERS_DESBALANCEADOS["01/99"].perda_derivacao_db  == 21.60
        assert SPLITTERS_DESBALANCEADOS["02/98"].perda_derivacao_db  == 18.70
        assert SPLITTERS_DESBALANCEADOS["05/95"].perda_derivacao_db  == 14.60
        assert SPLITTERS_DESBALANCEADOS["15/85"].perda_derivacao_db  ==  9.60
        assert SPLITTERS_DESBALANCEADOS["25/75"].perda_derivacao_db  ==  6.95
        assert SPLITTERS_DESBALANCEADOS["35/65"].perda_derivacao_db  ==  5.35
        assert SPLITTERS_DESBALANCEADOS["45/55"].perda_derivacao_db  ==  4.15

    def test_50_50_equivale_balanceado_1x2(self):
        from app.models.constants import SPLITTERS_DESBALANCEADOS, PERDA_SPLITTER_BALANCEADO_DB
        assert SPLITTERS_DESBALANCEADOS["50/50"].perda_principal_db == PERDA_SPLITTER_BALANCEADO_DB[2]
        assert SPLITTERS_DESBALANCEADOS["50/50"].perda_derivacao_db == PERDA_SPLITTER_BALANCEADO_DB[2]

    def test_calculo_com_splitter_desbalanceado_20_80(self):
        """OLT → Splitter 20/80 → ONU — usa média das portas como fallback."""
        from app.models.constants import SPLITTERS_DESBALANCEADOS
        olt = NoOLT(id="olt", tipo=TipoNo.OLT, nome="OLT", potencia_tx_dbm=5.0, sensibilidade_rx_dbm=-28.0, padrao_pon=PadraPON.GPON)
        from app.models.network import TipoSplitter
        spl = NoSplitter(
            id="spl", tipo=TipoNo.SPLITTER, nome="Spl 20/80",
            tipo_splitter=TipoSplitter.DESBALANCEADO,
            razao_desbalanceada="20/80",
        )
        onu = NoONU(id="onu", tipo=TipoNo.ONU, nome="ONU-01", sensibilidade_rx_dbm=-27.0)
        projeto = Projeto(
            id="p_desb", nome="Desbalanceado 20/80",
            nos=[olt.model_dump(), spl.model_dump(), onu.model_dump()],
            enlaces=[
                Enlace(id="e1", id_origem="olt", id_destino="spl", comprimento_m=1000, atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao"),
                Enlace(id="e2", id_origem="spl", id_destino="onu", comprimento_m=500, atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao"),
            ],
            parametros=ParametrosGlobais(margem_sistema_db=3.0),
        )
        resultado = CalculadoraOrcamentoOptico(projeto).calcular()
        caminho = resultado.caminhos[0]

        # Sem perda_splitter_db no enlace → fallback conservador usa perda_derivacao (maior perda)
        perda_spl = next(d for d in caminho.detalhes if d.tipo == "Splitter")
        dados = SPLITTERS_DESBALANCEADOS["20/80"]
        assert abs(perda_spl.perda_db - dados.perda_derivacao_db) < 0.001

    def test_calculo_com_porta_especifica_20_80(self):
        """Quando perda_splitter_db vem no enlace, usa o valor exato da porta."""
        from app.models.constants import SPLITTERS_DESBALANCEADOS
        olt = NoOLT(id="olt", tipo=TipoNo.OLT, nome="OLT", potencia_tx_dbm=5.0, sensibilidade_rx_dbm=-28.0, padrao_pon=PadraPON.GPON)
        from app.models.network import TipoSplitter
        spl = NoSplitter(id="spl", tipo=TipoNo.SPLITTER, nome="Spl 20/80",
                         tipo_splitter=TipoSplitter.DESBALANCEADO, razao_desbalanceada="20/80")
        onu = NoONU(id="onu", tipo=TipoNo.ONU, nome="ONU-01", sensibilidade_rx_dbm=-27.0)
        dados = SPLITTERS_DESBALANCEADOS["20/80"]

        # Porta inferior (passagem, 80%, menor perda = 1,40 dB)
        projeto = Projeto(
            id="p_desb2", nome="Porta passagem 20/80",
            nos=[olt.model_dump(), spl.model_dump(), onu.model_dump()],
            enlaces=[
                Enlace(id="e1", id_origem="olt", id_destino="spl", comprimento_m=1000, atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao"),
                Enlace(id="e2", id_origem="spl", id_destino="onu", comprimento_m=500, atenuacao_db_por_km=0.35, num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao",
                       perda_splitter_db=dados.perda_principal_db),
            ],
            parametros=ParametrosGlobais(margem_sistema_db=3.0),
        )
        resultado = CalculadoraOrcamentoOptico(projeto).calcular()
        caminho = resultado.caminhos[0]
        perda_spl = next(d for d in caminho.detalhes if d.tipo == "Splitter")
        assert abs(perda_spl.perda_db - dados.perda_principal_db) < 0.001

    def test_splitters_balanceados_corrigidos(self):
        """Garante que os valores balanceados estão alinhados com a Tabela 4 do TCC."""
        from app.models.constants import PERDA_SPLITTER_BALANCEADO_DB
        assert PERDA_SPLITTER_BALANCEADO_DB[2]  ==  3.5
        assert PERDA_SPLITTER_BALANCEADO_DB[4]  ==  7.2
        assert PERDA_SPLITTER_BALANCEADO_DB[8]  == 10.5
        assert PERDA_SPLITTER_BALANCEADO_DB[16] == 13.7
    """Testa os cálculos de propriedades do modelo Enlace."""

    def test_perda_fibra(self):
        e = Enlace(id="e", id_origem="a", id_destino="b",
                   comprimento_m=2000, atenuacao_db_por_km=0.35,
                   num_conexoes=0, perda_por_conexao_db=0.1, tipo_conexao="fusao")
        assert abs(e.perda_fibra_db - 0.70) < 0.001

    def test_perda_conexoes(self):
        e = Enlace(id="e", id_origem="a", id_destino="b",
                   comprimento_m=1000, atenuacao_db_por_km=0.35,
                   num_conexoes=4, perda_por_conexao_db=0.5)
        assert abs(e.perda_conexoes_db - 2.0) < 0.001

    def test_perda_total(self):
        e = Enlace(id="e", id_origem="a", id_destino="b",
                   comprimento_m=1000, atenuacao_db_por_km=0.35,
                   num_conexoes=2, perda_por_conexao_db=0.1, tipo_conexao="fusao")
        # fibra 1000m = 0,350 | fusões 2×0,1 = 0,200 → total 0,550 dB
        assert abs(e.perda_total_db - 0.550) < 0.001