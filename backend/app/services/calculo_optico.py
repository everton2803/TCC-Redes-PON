"""
services/calculo_optico.py
Engine de cálculo do orçamento óptico para redes PON.

Para cada caminho OLT → ONU, percorre todos os nós e enlaces
intermediários e calcula:
  - Perda total do caminho (dB)
  - Potência recebida na ONU (dBm)
  - Margem disponível (dB)
  - Status de viabilidade (OK / MARGEM_BAIXA / REPROVADO)

Fonte: Keiser (2011), ITU-T G.984, Oliviero & Cianfrani (2014).
"""

from dataclasses import dataclass, field
from typing import Optional
from app.models.constants import PERDA_SPLITTER_DB
from app.models.network import (
    Projeto, Enlace,
    TipoNo, TipoSplitter, NoOLT, NoSplitter, NoCaixaEmenda, NoONU,
    RazaoSplitter,
)
from app.models.constants import SPLITTERS_DESBALANCEADOS


# ---------------------------------------------------------------------------
# Estruturas de resultado
# ---------------------------------------------------------------------------

@dataclass
class DetalhePerda:
    """Contribuição individual de um elemento para a perda total."""
    elemento_id: str
    elemento_nome: str
    tipo: str
    descricao: str
    perda_db: float


@dataclass
class ResultadoCaminho:
    """Resultado completo do orçamento óptico de um caminho OLT → ONU."""
    onu_id: str
    onu_nome: str
    potencia_tx_dbm: float
    perda_total_db: float
    potencia_rx_dbm: float
    sensibilidade_rx_dbm: float
    margem_db: float
    margem_sistema_db: float
    margem_disponivel_db: float
    status: str
    detalhes: list[DetalhePerda] = field(default_factory=list)
    caminho_ids: list[str] = field(default_factory=list)
    # Potência óptica (dBm) nas pontas de cada enlace do caminho
    # { enlace_id → {"inicio": dBm, "fim": dBm} }
    # inicio = potência saindo do nó de origem (após perda do splitter/CEO)
    # fim    = potência chegando no nó destino (após fibra + conexões)
    potencia_por_enlace: dict = field(default_factory=dict)
    erro: Optional[str] = None


@dataclass
class ResultadoProjeto:
    """Resultado agregado do orçamento óptico de todo o projeto."""
    projeto_id: str
    projeto_nome: str
    total_onus: int
    onus_ok: int
    onus_margem_baixa: int
    onus_reprovadas: int
    caminhos: list[ResultadoCaminho] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers de deserialização de nós
# ---------------------------------------------------------------------------

def _parse_no(no_dict: dict):
    """Converte um dicionário de nó para a classe Pydantic correta."""
    tipo = no_dict.get("tipo")
    if tipo == TipoNo.OLT:
        return NoOLT(**no_dict)
    elif tipo == TipoNo.SPLITTER:
        return NoSplitter(**no_dict)
    elif tipo == TipoNo.CAIXA_EMENDA:
        return NoCaixaEmenda(**no_dict)
    elif tipo == TipoNo.ONU:
        return NoONU(**no_dict)
    raise ValueError(f"Tipo de nó desconhecido: {tipo}")


# ---------------------------------------------------------------------------
# Engine de cálculo
# ---------------------------------------------------------------------------

class CalculadoraOrcamentoOptico:
    """
    Realiza o cálculo do orçamento óptico de um projeto de rede PON.

    Algoritmo:
      1. Monta um grafo de adjacência a partir dos enlaces.
      2. Para cada ONU, busca todos os caminhos desde a OLT (DFS).
      3. Para cada caminho, soma as perdas de fibra, conectores,
         splitters, fusões e calcula a potência recebida.
      4. Compara com a sensibilidade da ONU e classifica o resultado.
    """

    def __init__(self, projeto: Projeto):
        self.projeto = projeto
        self.params = projeto.parametros

        # Deserializa os nós
        self.nos: dict[str, NoOLT | NoSplitter | NoCaixaEmenda | NoONU] = {
            no["id"]: _parse_no(no) for no in projeto.nos
        }

        # Indexa enlaces por nó de origem (grafo direcionado)
        self.adjacencia: dict[str, list[Enlace]] = {nid: [] for nid in self.nos}
        for enlace in projeto.enlaces:
            if enlace.id_origem in self.adjacencia:
                self.adjacencia[enlace.id_origem].append(enlace)

        # Localiza a OLT (deve haver exatamente uma)
        olts = [n for n in self.nos.values() if isinstance(n, NoOLT)]
        if not olts:
            raise ValueError("O projeto não contém nenhuma OLT.")
        if len(olts) > 1:
            raise ValueError("O projeto contém mais de uma OLT — suporte a múltiplas OLTs não implementado.")
        self.olt: NoOLT = olts[0]

    # ------------------------------------------------------------------
    # Ponto de entrada público
    # ------------------------------------------------------------------

    def calcular(self) -> ResultadoProjeto:
        """Calcula o orçamento óptico de todos os caminhos OLT → ONU."""
        caminhos: list[ResultadoCaminho] = []

        # Busca todos os caminhos da OLT até cada ONU via DFS
        self._dfs(
            no_atual_id=self.olt.id,
            caminho_ids=[self.olt.id],
            enlaces_caminho=[],
            caminhos_encontrados=caminhos,
        )

        # Classifica resumo
        ok = sum(1 for c in caminhos if c.status == "OK")
        baixa = sum(1 for c in caminhos if c.status == "MARGEM_BAIXA")
        reprovadas = sum(1 for c in caminhos if c.status == "REPROVADO")

        return ResultadoProjeto(
            projeto_id=self.projeto.id,
            projeto_nome=self.projeto.nome,
            total_onus=len(caminhos),
            onus_ok=ok,
            onus_margem_baixa=baixa,
            onus_reprovadas=reprovadas,
            caminhos=caminhos,
        )

    # ------------------------------------------------------------------
    # DFS — busca em profundidade no grafo
    # ------------------------------------------------------------------

    def _dfs(
        self,
        no_atual_id: str,
        caminho_ids: list[str],
        enlaces_caminho: list[Enlace],
        caminhos_encontrados: list[ResultadoCaminho],
    ):
        no_atual = self.nos[no_atual_id]

        # Chegou numa ONU — calcula o orçamento desse caminho
        if isinstance(no_atual, NoONU):
            resultado = self._calcular_caminho(
                caminho_ids=list(caminho_ids),
                enlaces=list(enlaces_caminho),
                onu=no_atual,
            )
            caminhos_encontrados.append(resultado)
            return

        # Continua a busca pelos enlaces saindo deste nó
        for enlace in self.adjacencia.get(no_atual_id, []):
            destino_id = enlace.id_destino

            # Evita ciclos
            if destino_id in caminho_ids:
                continue

            self._dfs(
                no_atual_id=destino_id,
                caminho_ids=caminho_ids + [destino_id],
                enlaces_caminho=enlaces_caminho + [enlace],
                caminhos_encontrados=caminhos_encontrados,
            )

    # ------------------------------------------------------------------
    # Cálculo de perdas de um caminho completo
    # ------------------------------------------------------------------

    def _calcular_caminho(
        self,
        caminho_ids: list[str],
        enlaces: list[Enlace],
        onu: NoONU,
    ) -> ResultadoCaminho:
        detalhes: list[DetalhePerda] = []
        perda_total_db = 0.0
        potencia_atual = self.olt.potencia_tx_dbm
        potencia_por_enlace: dict[str, dict] = {}

        # --- Percorre cada enlace do caminho ---
        for enlace in enlaces:
            no_origem = self.nos[enlace.id_origem]

            # 1. Perdas do nó de origem (splitter ou caixa de emenda)
            if isinstance(no_origem, NoSplitter):
                if enlace.perda_splitter_db is not None:
                    perda_spl = enlace.perda_splitter_db
                    razao_d   = no_origem.razao_desbalanceada or '20/80'
                    descricao = f"Splitter {razao_d} (porta: {perda_spl} dB)"
                else:
                    perda_spl = self._perda_splitter(no_origem)
                    if no_origem.tipo_splitter == 'desbalanceado':
                        descricao = f"Splitter {no_origem.razao_desbalanceada} (média)"
                    else:
                        descricao = f"Splitter 1x{no_origem.razao}"
                detalhes.append(DetalhePerda(
                    elemento_id=no_origem.id,
                    elemento_nome=no_origem.nome,
                    tipo="Splitter",
                    descricao=descricao,
                    perda_db=perda_spl,
                ))
                perda_total_db += perda_spl
                potencia_atual -= perda_spl

            elif isinstance(no_origem, NoCaixaEmenda):
                perda_fusoes = self._perda_fusoes(no_origem)
                if perda_fusoes > 0:
                    detalhes.append(DetalhePerda(
                        elemento_id=no_origem.id,
                        elemento_nome=no_origem.nome,
                        tipo="CaixaEmenda",
                        descricao=f"{no_origem.num_fusoes} fusões × {no_origem.perda_por_fusao_db} dB",
                        perda_db=perda_fusoes,
                    ))
                    perda_total_db += perda_fusoes
                    potencia_atual -= perda_fusoes

            # Potência na ponta de início do enlace (após perdas do nó de origem)
            p_inicio = round(potencia_atual, 3)

            # 2. Perda da fibra
            perda_fibra = enlace.perda_fibra_db
            detalhes.append(DetalhePerda(
                elemento_id=enlace.id,
                elemento_nome=f"Enlace {enlace.id_origem}→{enlace.id_destino}",
                tipo="Fibra",
                descricao=f"{enlace.comprimento_m} m × {enlace.atenuacao_db_por_km} dB/km",
                perda_db=perda_fibra,
            ))
            perda_total_db += perda_fibra
            potencia_atual -= perda_fibra

            # 3. Perda das conexões (fusões ou conectores)
            if enlace.num_conexoes > 0:
                perda_conn  = enlace.perda_conexoes_db
                is_conector = enlace.tipo_conexao.value == 'conector'
                tipo_label  = "Conector" if is_conector else "Fusão"
                detalhes.append(DetalhePerda(
                    elemento_id=enlace.id,
                    elemento_nome=f"{tipo_label}s {enlace.id_origem}→{enlace.id_destino}",
                    tipo=tipo_label,
                    descricao=(
                        f"{enlace.num_conexoes} {tipo_label.lower()}(ões) × "
                        f"{enlace.perda_por_conexao_db} dB"
                    ),
                    perda_db=perda_conn,
                ))
                perda_total_db += perda_conn
                potencia_atual -= perda_conn

            # Registra potência nas pontas deste enlace
            potencia_por_enlace[enlace.id] = {
                "inicio": p_inicio,
                "fim":    round(potencia_atual, 3),
            }

        # --- Calcula margem ---
        potencia_rx   = potencia_atual  # já rastreada ao longo do caminho
        margem        = potencia_rx - onu.sensibilidade_rx_dbm
        margem_disponivel = margem - self.params.margem_sistema_db

        # --- Classificação ---
        if margem_disponivel >= 0:
            status = "OK"
        elif margem >= 0:
            status = "MARGEM_BAIXA"   # link funciona mas sem folga de segurança
        else:
            status = "REPROVADO"      # sinal insuficiente na ONU

        return ResultadoCaminho(
            onu_id=onu.id,
            onu_nome=onu.nome,
            potencia_tx_dbm=self.olt.potencia_tx_dbm,
            perda_total_db=round(perda_total_db, 3),
            potencia_rx_dbm=round(potencia_atual, 3),
            sensibilidade_rx_dbm=onu.sensibilidade_rx_dbm,
            margem_db=round(margem, 3),
            margem_sistema_db=self.params.margem_sistema_db,
            margem_disponivel_db=round(margem_disponivel, 3),
            status=status,
            detalhes=detalhes,
            caminho_ids=caminho_ids,
            potencia_por_enlace=potencia_por_enlace,
        )

    # ------------------------------------------------------------------
    # Cálculo de perdas por elemento
    # ------------------------------------------------------------------

    def _perda_splitter(self, splitter: NoSplitter) -> float:
        """
        Retorna a perda de inserção do splitter balanceado em dB.

        Para splitters desbalanceados, a perda é determinada pela porta
        específica e deve ser enviada pelo frontend em enlace.perda_splitter_db.
        Este método é chamado apenas como fallback quando perda_splitter_db
        está ausente no enlace.
        """
        from app.models.constants import PERDA_SPLITTER_BALANCEADO_DB

        if splitter.tipo_splitter == TipoSplitter.DESBALANCEADO:
            razao = splitter.razao_desbalanceada or "20/80"
            dados = SPLITTERS_DESBALANCEADOS.get(razao)
            if dados is None:
                raise ValueError(f"Razão desbalanceada '{razao}' não encontrada na tabela.")
            # Fallback conservador: usa a porta de maior perda (derivação)
            # O valor correto por porta deve vir em enlace.perda_splitter_db
            return dados.perda_derivacao_db

        # Balanceado
        if splitter.perda_insercao_db is not None:
            return splitter.perda_insercao_db
        razao = splitter.razao.value if isinstance(splitter.razao, RazaoSplitter) else int(splitter.razao)
        return PERDA_SPLITTER_BALANCEADO_DB.get(razao, 10.5)  # fallback: 1x8

    def _perda_fusoes(self, caixa: NoCaixaEmenda) -> float:
        """Retorna a perda total das fusões na caixa de emenda."""
        return caixa.num_fusoes * caixa.perda_por_fusao_db