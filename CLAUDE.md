# Contexto do Projeto — Bot de Vagas de Estágio

## O que é
Script Python que raspa vagas de estágio em TI (Indeed e Gupy) e posta
automaticamente num canal do Telegram (e futuramente Discord), sem
intervenção manual. Roda a cada 1-2h via agendador.

## Objetivo
Projeto de portfólio (mostra scraping, API externa, agendamento, deploy)
que também pode virar produto real (monetização via acesso pago a canal
de vagas para comunidades de estudantes de TI).

## Decisões já tomadas
- **Começar pelo Telegram**, não Discord (API mais simples, bot token via
  BotFather, sem precisa configurar servidor/webhook).
- Fontes de scraping: **Indeed e Gupy**. NUNCA LinkedIn (bloqueia scraping
  agressivamente e viola ToS de forma mais visada).
- Controle de vagas já enviadas: **SQLite** (não JSON) — mais robusto pra
  crescer e evita duplicatas de forma mais segura.
- Agendamento: `APScheduler` (não `schedule` puro) — mais flexível pra
  rodar em produção (Railway/Render).
- Deploy alvo: Railway.app ou Render.com (free tier, roda 24h).

## Riscos conhecidos (não ignorar)
- Indeed e Gupy têm proteção anti-bot (Cloudflare, rate limiting). Usar
  headers de user-agent realistas, delays entre requisições, e ter
  tratamento de erro robusto para quando o HTML mudar ou bloquear o IP.
- Verificar periodicamente se a estrutura HTML das páginas mudou (scraper
  vai quebrar em algum momento — isso é esperado, não é bug de código).

## Stack
- `requests` + `BeautifulSoup4` — scraping
- `python-telegram-bot` — postagem no Telegram
- `APScheduler` — agendamento
- `sqlite3` (stdlib) — controle de vagas já enviadas
- `python-dotenv` — variáveis de ambiente (token do bot, chat_id)

## Convenções de código
- Português nos comentários e docstrings, inglês nos nomes de
  variáveis/funções (padrão comum em projetos BR pra portfólio internacional).
- Logging estruturado (módulo `logging`, não `print`) — vai facilitar
  debugar quando o scraper quebrar em produção.
- Toda função de scraping deve ter tratamento de exceção — nunca deixar
  o processo inteiro cair por causa de uma página que falhou.

## Prioridades de implementação (nessa ordem)
1. `storage.py` — schema SQLite + funções de salvar/checar vaga já enviada
2. `scraper.py` — scraping do Indeed primeiro (mais simples), depois Gupy
3. `notifier.py` — postagem no Telegram
4. `scheduler.py` + `main.py` — juntar tudo e rodar em loop
5. README com instruções de setup e GIF/screenshot do bot funcionando
6. Deploy no Railway/Render

## Não fazer
- Não implementar scraping do LinkedIn.
- Não usar `print()` para debug em código que vai pro repositório final —
  usar `logging`.
