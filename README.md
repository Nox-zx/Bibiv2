# Bibi v0.1.0

Build completa e executável da Bibi.

A v0.1 estabelece a fundação da filosofia definida para a Bibi:
- Brix Community é a casa da Bibi.
- Bibi é uma entidade do servidor, não apenas um chatbot que responde.
- Perception, Attention, World, Self, Emotion, Memory, Cognition e Action são fronteiras separadas.
- O Gemini é usado para cognição; Python mantém factos do servidor e controla execução.
- Bibi não responde automaticamente a todas as conversas.
- Não são usados erros de digitação artificiais.
- O estado emocional pode mudar e influencia o contexto cognitivo.
- O tempo é fornecido à cognição quando relevante.
- Existem cinco tipos de memória preparados: episódica, semântica, social, relacional e autobiográfica.
- Existem quatro API keys Gemini rotativas.
- Cognitive e Reflective usam Flash-Lite por configuração.
- O Reflective Mind existe como processo separado e não é chamado em cada mensagem.

## Instalação

1. `pip install -r requirements.txt`
2. Copiar `.env.example` para `.env`
3. Preencher `DISCORD_TOKEN` e até quatro `GEMINI_API_KEY_*`.
4. Activar Message Content Intent no Discord Developer Portal.
5. `python main.py`

A build não contém tokens.
