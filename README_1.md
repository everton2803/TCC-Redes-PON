# PON Planner — Ferramenta para Cálculo e Planejamento de Redes Ópticas de Acesso

TCC — Everton José Serighelli | IFC Campus Videira (2026)

## Descrição

Aplicação web interativa para modelagem visual de topologias de redes ópticas PON
e cálculo automático do orçamento óptico em projetos FTTH.

## Estrutura do Projeto

```
pon-planner/
├── backend/
│   ├── app/
│   │   ├── controllers/   # Rotas da API RESTful (FastAPI)
│   │   ├── models/        # Modelos de dados (Pydantic)
│   │   ├── services/      # Lógica de negócio e cálculos ópticos
│   │   └── schemas/       # Schemas de validação e serialização
│   ├── data/
│   │   └── projects/      # Projetos salvos em JSON
│   └── tests/             # Testes unitários e de integração
├── frontend/
│   ├── src/
│   │   ├── components/    # Componentes da interface (canvas D3.js)
│   │   ├── services/      # Comunicação com a API
│   │   └── utils/         # Utilitários JS
│   └── public/            # HTML, CSS, assets estáticos
└── docs/                  # Documentação técnica
```

## Stack Tecnológica

| Camada      | Tecnologia                        |
|-------------|-----------------------------------|
| Frontend    | HTML5, CSS3, JavaScript + D3.js   |
| Backend     | Python 3.11+ + FastAPI            |
| Persistência| JSON (arquivos locais)            |
| Deploy      | Docker + Docker Compose           |
| Comunicação | HTTP/REST + JSON                  |

## Como Rodar

```bash
# Com Docker Compose
docker-compose up

# Manualmente
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
```

A API ficará disponível em `http://localhost:8000` e a documentação automática em `http://localhost:8000/docs`.