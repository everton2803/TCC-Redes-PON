"""
models/network.py
Modelos de dados da rede óptica PON.

Representa a topologia como um grafo:
  - Nós (nodes): OLT, Splitter, CaixaEmenda, ONU
  - Arestas (links): trechos de fibra óptica entre nós
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid


# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------

class TipoSplitter(str, Enum):
    """Categoria do splitter: balanceado (1xN) ou desbalanceado (assimétrico)."""
    BALANCEADO    = "balanceado"
    DESBALANCEADO = "desbalanceado"


class TipoNo(str, Enum):
    """Tipos de elementos passivos/ativos da rede PON."""
    OLT = "OLT"               # Optical Line Transmitter — ponto de origem
    SPLITTER = "Splitter"     # Divisor óptico passivo
    CAIXA_EMENDA = "CaixaEmenda"  # Caixa de emenda / CEO
    ONU = "ONU"               # Optical Network Unit — terminal do cliente


class PadraPON(str, Enum):
    """Padrão PON utilizado na rede."""
    GPON = "GPON"   # Gigabit PON — até 1:128, 2.5 Gbps downstream
    EPON = "EPON"   # Ethernet PON — até 1:32, 1 Gbps simétrico


class RazaoSplitter(int, Enum):
    """Razões de divisão suportadas para splitters."""
    S_1x2  = 2
    S_1x4  = 4
    S_1x8  = 8
    S_1x16 = 16
    S_1x32 = 32
    S_1x64 = 64


# ---------------------------------------------------------------------------
# Nós da rede
# ---------------------------------------------------------------------------

class PosicaoXY(BaseModel):
    """Coordenadas visuais do nó no canvas (pixels)."""
    x: float = Field(..., description="Posição horizontal no canvas")
    y: float = Field(..., description="Posição vertical no canvas")


class NoBase(BaseModel):
    """Campos comuns a todos os tipos de nó."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único do nó")
    tipo: TipoNo
    nome: str = Field(..., min_length=1, max_length=100, description="Rótulo exibido no canvas")
    posicao: PosicaoXY = Field(default_factory=lambda: PosicaoXY(x=0, y=0))
    observacao: Optional[str] = Field(None, max_length=500)


class NoOLT(NoBase):
    """
    Optical Line Transmitter — origem da rede PON.
    Define a potência de transmissão e o padrão adotado.
    """
    tipo: TipoNo = TipoNo.OLT
    padrao_pon: PadraPON = PadraPON.GPON
    potencia_tx_dbm: float = Field(
        default=5.0,
        ge=-10.0, le=10.0,
        description="Potência de transmissão da OLT em dBm"
    )
    # Limites de sensibilidade do transceptor SFP (classe óptica)
    sensibilidade_rx_dbm: float = Field(
        default=-28.0,
        description="Sensibilidade mínima do receptor OLT em dBm"
    )


class NoSplitter(NoBase):
    """
    Splitter passivo — divide o sinal óptico.

    Balanceado (1xN): todas as saídas recebem a mesma potência.
    Desbalanceado: duas saídas com frações assimétricas (ex: 20/80).
      - porta_principal → maior fração (menos perda) — continua o backbone
      - porta_derivacao → menor fração (mais perda)  — ramal de derivação
    """
    tipo: TipoNo = TipoNo.SPLITTER

    # --- Balanceado ---
    tipo_splitter: TipoSplitter = TipoSplitter.BALANCEADO
    razao: RazaoSplitter = RazaoSplitter.S_1x8

    # --- Desbalanceado ---
    razao_desbalanceada: Optional[str] = Field(
        None,
        description="Razão do splitter desbalanceado: '10/90', '20/80', '30/70' ou '40/60'"
    )

    # --- Sobrescrita manual (qualquer tipo) ---
    perda_insercao_db: Optional[float] = Field(
        None,
        ge=0.0, le=25.0,
        description="Perda de inserção manual em dB — sobrescreve a tabela padrão (balanceado)"
    )
    perda_principal_db: Optional[float] = Field(
        None,
        ge=0.0, le=25.0,
        description="Perda manual da porta principal (desbalanceado)"
    )
    perda_derivacao_db: Optional[float] = Field(
        None,
        ge=0.0, le=25.0,
        description="Perda manual da porta de derivação (desbalanceado)"
    )


class NoCaixaEmenda(NoBase):
    """
    Caixa de emenda óptica (CEO / caixa de distribuição).
    Agrega fusões realizadas dentro da caixa.
    """
    tipo: TipoNo = TipoNo.CAIXA_EMENDA
    num_fusoes: int = Field(
        default=0,
        ge=0, le=288,
        description="Número de fusões realizadas nesta caixa"
    )
    perda_por_fusao_db: float = Field(
        default=0.1,
        ge=0.0, le=0.5,
        description="Perda média por fusão em dB"
    )


class NoONU(NoBase):
    """
    Optical Network Unit — terminal do assinante.
    Define a sensibilidade mínima aceitável para o sinal recebido.
    """
    tipo: TipoNo = TipoNo.ONU
    sensibilidade_rx_dbm: float = Field(
        default=-27.0,
        description="Sensibilidade mínima do receptor ONU em dBm"
    )
    potencia_rx_minima_dbm: float = Field(
        default=-27.0,
        description="Potência mínima aceitável no receptor em dBm"
    )


# ---------------------------------------------------------------------------
# Enlace (aresta) entre dois nós
# ---------------------------------------------------------------------------

class TipoConexao(str, Enum):
    """Tipo de conexão nas extremidades do enlace."""
    FUSAO    = "fusao"     # fusão por arco — perda típica 0,1 dB
    CONECTOR = "conector"  # conector SC/APC — perda típica 0,5 dB


class Enlace(BaseModel):
    """
    Trecho de fibra óptica conectando dois nós.

    A natureza da conexão (fusão ou conector) é determinada pelos nós ligados:
      - ONU → Splitter: conector SC/APC (0,5 dB)
      - Demais: fusão mecânica (0,1 dB)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    id_origem: str = Field(..., description="ID do nó de origem")
    id_destino: str = Field(..., description="ID do nó de destino")

    # Parâmetros da fibra
    comprimento_m: float = Field(
        ...,
        gt=0.0, le=100000.0,
        description="Comprimento do trecho de fibra em metros"
    )
    atenuacao_db_por_km: float = Field(
        default=0.35,
        ge=0.1, le=1.0,
        description="Atenuação da fibra em dB/km (padrão SMF: 0,35 dB/km a 1310 nm)"
    )

    # Conexões nas extremidades (fusão ou conector)
    tipo_conexao: TipoConexao = Field(
        default=TipoConexao.FUSAO,
        description="Tipo de conexão: fusão (0,1 dB) ou conector SC/APC (0,5 dB)"
    )
    num_conexoes: int = Field(
        default=2,
        ge=0, le=20,
        description="Número de conexões (fusões ou conectores) no trecho"
    )
    perda_por_conexao_db: float = Field(
        default=0.1,
        ge=0.0, le=2.0,
        description="Perda por conexão em dB (fusão: 0,1 dB; conector: 0,5 dB)"
    )

    # Campos legados — mantidos para compatibilidade com projetos salvos anteriormente
    num_conectores: Optional[int] = Field(None, exclude=True)
    perda_por_conector_db: Optional[float] = Field(None, exclude=True)

    porta_origem_rel_y: Optional[float] = Field(None, description="Y relativo da porta de saída (uso do frontend)")
    perda_splitter_db: Optional[float] = Field(
        None,
        ge=0.0, le=25.0,
        description="Perda de inserção do splitter desbalanceado para esta porta específica (dB). "
                    "Quando presente, sobrescreve a tabela padrão no cálculo."
    )
    observacao: Optional[str] = Field(None, max_length=500)

    def model_post_init(self, __context):
        """Migra campos legados para os novos se presentes."""
        if self.num_conectores is not None and self.num_conexoes == 2:
            object.__setattr__(self, 'num_conexoes', self.num_conectores)
        if self.perda_por_conector_db is not None:
            object.__setattr__(self, 'perda_por_conexao_db', self.perda_por_conector_db)

    @property
    def comprimento_km(self) -> float:
        """Comprimento em km (conversão interna para cálculo)."""
        return self.comprimento_m / 1000.0

    @property
    def perda_fibra_db(self) -> float:
        """Perda total da fibra no trecho."""
        return self.comprimento_km * self.atenuacao_db_por_km

    @property
    def perda_conexoes_db(self) -> float:
        """Perda total das conexões (fusões ou conectores)."""
        return self.num_conexoes * self.perda_por_conexao_db

    @property
    def perda_total_db(self) -> float:
        """Perda total do enlace."""
        return self.perda_fibra_db + self.perda_conexoes_db


# ---------------------------------------------------------------------------
# Projeto completo
# ---------------------------------------------------------------------------

# União discriminada para aceitar qualquer tipo de nó
NoRede = NoOLT | NoSplitter | NoCaixaEmenda | NoONU


class ParametrosGlobais(BaseModel):
    """
    Parâmetros técnicos padrão aplicados ao projeto.
    Podem ser sobrescritos individualmente em cada elemento.
    """
    atenuacao_fibra_db_por_km: float = Field(
        default=0.35,
        description="Atenuação padrão da fibra monomodo (SMF) em dB/km a 1310 nm"
    )
    perda_conector_db: float = Field(
        default=0.5,
        description="Perda padrão por conector SC/APC em dB"
    )
    perda_fusao_db: float = Field(
        default=0.1,
        description="Perda padrão por fusão mecânica em dB"
    )
    margem_sistema_db: float = Field(
        default=3.0,
        ge=0.0, le=10.0,
        description="Margem de segurança do sistema em dB"
    )


class Projeto(BaseModel):
    """
    Projeto completo de rede óptica PON.
    Contém todos os nós, enlaces e parâmetros globais.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str = Field(..., min_length=1, max_length=200)
    descricao: Optional[str] = Field(None, max_length=1000)
    versao: str = Field(default="1.0.0")
    criado_em: Optional[str] = None     # ISO 8601 — preenchido pelo serviço
    atualizado_em: Optional[str] = None

    parametros: ParametrosGlobais = Field(default_factory=ParametrosGlobais)

    # Elementos da rede
    nos: list[dict] = Field(
        default_factory=list,
        description="Lista de nós (OLT, Splitter, CaixaEmenda, ONU) serializados"
    )
    enlaces: list[Enlace] = Field(
        default_factory=list,
        description="Lista de enlaces (trechos de fibra) entre os nós"
    )

    @field_validator("nos", mode="before")
    @classmethod
    def validar_nos(cls, nos):
        """Aceita lista de dicts — a deserialização tipada ocorre no serviço."""
        return nos