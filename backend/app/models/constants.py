"""
models/constants.py
Constantes técnicas e tabelas de referência para redes PON.

Fonte: Keiser (2011), ITU-T G.984 (GPON), IEEE 802.3ah (EPON),
       Oliviero & Cianfrani (2014), Tabela 4 do TCC (APNIC Blog, 2024;
       Holight Optical, 2025b).
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Tabela de perdas de splitters BALANCEADOS (1xN)
# Valores em dB — Tabela 4 do TCC
# ---------------------------------------------------------------------------
PERDA_SPLITTER_BALANCEADO_DB: dict[int, float] = {
    2:   3.5,   # 1x2  — 50/50
    4:   7.2,   # 1x4
    8:  10.5,   # 1x8
    16: 13.7,   # 1x16
    32: 17.1,   # 1x32  (não consta na Tabela 4; mantido como referência)
    64: 20.5,   # 1x64  (não consta na Tabela 4; mantido como referência)
}

# Mantido por compatibilidade com o código da Etapa 2
PERDA_SPLITTER_DB = PERDA_SPLITTER_BALANCEADO_DB


# ---------------------------------------------------------------------------
# Splitters DESBALANCEADOS (1x2 assimétrico)
# Cada entrada representa uma porta do splitter: (porta_principal, porta_derivação)
# A chave é a razão "menor_porta/maior_porta" em percentual (ex: "10/90").
# Valores em dB — Tabela 4 do TCC (APNIC Blog, 2024; Holight Optical, 2025b).
#
# Interpretação:
#   porta_principal  → recebe a fração MAIOR do sinal (menos perda)
#   porta_derivacao  → recebe a fração MENOR do sinal (mais perda)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerdaSplitterDesbalanceado:
    """Perdas de inserção das duas portas de saída de um splitter desbalanceado."""
    rotulo: str           # ex: "10/90"
    perda_principal_db: float   # porta que recebe a maior fração de potência
    perda_derivacao_db: float   # porta que recebe a menor fração de potência
    descricao: str


SPLITTERS_DESBALANCEADOS: dict[str, PerdaSplitterDesbalanceado] = {
    # -----------------------------------------------------------------------
    # Fonte: Furukawa Electric LatAm — ET02372 v4 (01/10/2021) e
    #        Tabela de Perdas de Splitters Desbalanceados (uso no mercado FTTH BR)
    #
    # Convenção das colunas:
    #   perda_derivacao_db  → porta que recebe a fração MENOR (ex: 1% em 1/99)
    #   perda_principal_db  → porta que recebe a fração MAIOR (ex: 99% em 1/99)
    #
    # Leitura: "01/99" = 1% derivação / 99% passagem
    # -----------------------------------------------------------------------
    "01/99": PerdaSplitterDesbalanceado(
        rotulo="01/99",
        perda_principal_db=0.09,   # porta 99%
        perda_derivacao_db=21.60,  # porta 1%
        descricao="1% derivação / 99% passagem — Furukawa ET02372"
    ),
    "02/98": PerdaSplitterDesbalanceado(
        rotulo="02/98",
        perda_principal_db=0.16,   # porta 98%
        perda_derivacao_db=18.70,  # porta 2%
        descricao="2% derivação / 98% passagem — Furukawa ET02372"
    ),
    "05/95": PerdaSplitterDesbalanceado(
        rotulo="05/95",
        perda_principal_db=0.36,   # porta 95%
        perda_derivacao_db=14.60,  # porta 5%
        descricao="5% derivação / 95% passagem — Furukawa ET02372"
    ),
    "10/90": PerdaSplitterDesbalanceado(
        rotulo="10/90",
        perda_principal_db=0.55,   # porta 90%
        perda_derivacao_db=11.00,  # porta 10%
        descricao="10% derivação / 90% passagem — Furukawa ET02372 / Tabela 4 TCC"
    ),
    "15/85": PerdaSplitterDesbalanceado(
        rotulo="15/85",
        perda_principal_db=1.00,   # porta 85%
        perda_derivacao_db=9.60,   # porta 15%
        descricao="15% derivação / 85% passagem — Furukawa ET02372"
    ),
    "20/80": PerdaSplitterDesbalanceado(
        rotulo="20/80",
        perda_principal_db=1.40,   # porta 80%
        perda_derivacao_db=7.90,   # porta 20%
        descricao="20% derivação / 80% passagem — Furukawa ET02372 / Tabela 4 TCC"
    ),
    "25/75": PerdaSplitterDesbalanceado(
        rotulo="25/75",
        perda_principal_db=1.70,   # porta 75%
        perda_derivacao_db=6.95,   # porta 25%
        descricao="25% derivação / 75% passagem — Furukawa ET02372"
    ),
    "30/70": PerdaSplitterDesbalanceado(
        rotulo="30/70",
        perda_principal_db=1.90,   # porta 70%
        perda_derivacao_db=6.00,   # porta 30%
        descricao="30% derivação / 70% passagem — Furukawa ET02372 / Tabela 4 TCC"
    ),
    "35/65": PerdaSplitterDesbalanceado(
        rotulo="35/65",
        perda_principal_db=2.30,   # porta 65%
        perda_derivacao_db=5.35,   # porta 35%
        descricao="35% derivação / 65% passagem — Furukawa ET02372"
    ),
    "40/60": PerdaSplitterDesbalanceado(
        rotulo="40/60",
        perda_principal_db=2.70,   # porta 60%
        perda_derivacao_db=4.70,   # porta 40%
        descricao="40% derivação / 60% passagem — Furukawa ET02372 / Tabela 4 TCC"
    ),
    "45/55": PerdaSplitterDesbalanceado(
        rotulo="45/55",
        perda_principal_db=3.15,   # porta 55%
        perda_derivacao_db=4.15,   # porta 45%
        descricao="45% derivação / 55% passagem — Furukawa ET02372"
    ),
    "50/50": PerdaSplitterDesbalanceado(
        rotulo="50/50",
        perda_principal_db=3.50,   # portas iguais — equivale ao balanceado 1x2
        perda_derivacao_db=3.50,
        descricao="50/50 — simétrico, equivalente ao splitter balanceado 1x2"
    ),
}

# ---------------------------------------------------------------------------
# Atenuação da fibra óptica monomodo (SMF — G.652)
# ---------------------------------------------------------------------------
ATENUACAO_SMF_1310nm_DB_KM = 0.30   # dB/km — janela de 1310 nm (mais comum em PON)
ATENUACAO_SMF_1550nm_DB_KM = 0.20   # dB/km — janela de 1550 nm

# ---------------------------------------------------------------------------
# Perdas típicas de elementos passivos
# ---------------------------------------------------------------------------
PERDA_CONECTOR_SC_APC_DB  = 0.5    # dB — conector SC/APC (padrão FTTH)
PERDA_CONECTOR_SC_UPC_DB  = 0.5    # dB — conector SC/UPC
PERDA_FUSAO_MECANICA_DB   = 0.03    # dB — fusão por arco elétrico
PERDA_FUSAO_RAPIDA_DB     = 0.03    # dB — emenda rápida (fusão mecânica)

# ---------------------------------------------------------------------------
# Potência de transmissão típica das OLTs (classes ópticas ITU-T G.984.2)
# ---------------------------------------------------------------------------
CLASSES_OTICAS_OLT: dict[str, dict] = {
    "Classe B+": {
        "potencia_tx_min_dbm": 1.5,
        "potencia_tx_max_dbm": 5.0,
        "sensibilidade_rx_dbm": -28.0,
        "descricao": "Classe mais comum em redes GPON residenciais"
    },
    "Classe C+": {
        "potencia_tx_min_dbm": 3.0,
        "potencia_tx_max_dbm": 7.0,
        "sensibilidade_rx_dbm": -30.0,
        "descricao": "Alta potência — longas distâncias ou alta divisão"
    },
    "Classe A": {
        "potencia_tx_min_dbm": -3.0,
        "potencia_tx_max_dbm": 2.0,
        "sensibilidade_rx_dbm": -24.0,
        "descricao": "Classe básica — curtas distâncias"
    },
}

# ---------------------------------------------------------------------------
# Sensibilidade típica dos receptores ONU/ONT
# ---------------------------------------------------------------------------
SENSIBILIDADE_ONU_GPON_DBM = -27.0   # dBm — receptor típico GPON
SENSIBILIDADE_ONU_EPON_DBM = -24.0   # dBm — receptor típico EPON

# ---------------------------------------------------------------------------
# Margem de sistema recomendada
# ---------------------------------------------------------------------------
MARGEM_SISTEMA_DB = 3.0   # dB — reserva para degradações futuras

# ---------------------------------------------------------------------------
# Limites máximos de divisão por padrão PON
# ---------------------------------------------------------------------------
DIVISAO_MAXIMA_PON: dict[str, int] = {
    "GPON": 128,
    "EPON": 64,
}