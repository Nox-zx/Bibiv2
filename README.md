# Bibi

Primeiro núcleo funcional da Bibi: Discord + SQLite + Gemini Cognitivo.

## Estado

- Discord: ligado
- SQLite/SQLAlchemy: ligado
- Gemini Cognitivo: ligado
- Structured output: Pydantic
- Memória inicial: ligada
- Reflexiva: schema + gateway prontos; ciclo de reflexão ainda será conectado
- Jogos/economia: ainda não implementados
- Protecção de quota: activa

## Protecção da Gemini

O gateway distingue erros de quota diária (`429 RESOURCE_EXHAUSTED` com `GenerateRequestsPerDayPerProject-FreeTier`) de erros transitórios. Ao atingir a quota diária, não faz retries inúteis: o circuito de chamadas fica bloqueado até à próxima meia-noite do horário do Pacífico.

Pedidos directos à Bibi recebem no máximo uma mensagem mecânica de fallback por canal a cada 5 minutos enquanto a Gemini estiver indisponível.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Preencher `.env` e executar:

```bash
python main.py
```

## Variáveis importantes

- `DISCORD_TOKEN`
- `GEMINI_API_KEY`
- `GUILD_ID` (opcional; acelera sync de slash commands)
- `CREATOR_ID` (preparado para a camada de relação)
- `COGNITIVE_MODEL=gemini-3.6-flash`
- `REFLECTIVE_MODEL=gemini-3.5-flash-lite`

## Nota

Os modelos actuais não usam `temperature`, `top_p` ou `top_k` no pedido. A configuração do gateway foi deliberadamente construída sem esses parâmetros.