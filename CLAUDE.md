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
- **Fonte PRINCIPAL de estágio BR: `api-vagas` (Meu Padrinho).** É a API Node
  `matheusaudibert/jobs-api`, que agrega vagas do meupadrinho.com.br (mercado
  brasileiro). Escolhida porque Indeed (403 anti-bot) e Gupy (SPA + API só com
  token enterprise) não dão pra raspar de forma confiável e barata.
  - Roda como **serviço separado** (Docker ou `node index.js`), NÃO é
    biblioteca Python. Clonado em `api-vagas/` (fora do nosso git, continua
    no `.gitignore` — é um repo próprio, não um submódulo).
  - **Fork próprio:** https://github.com/arthurcamargo03/api-vagas (upstream:
    matheusaudibert/jobs-api). O deploy usa o fork; o `index.js` foi ajustado
    pra ler `process.env.PORT` e há um `render.yaml` no fork.
  - Rotas GET: `/estagio`, `/junior`, `/pleno`, `/senior` — cada uma devolve
    só UMA vaga (a mais recente). O dedup por link no SQLite cuida do resto.
  - URL configurada via `JOBS_API_BASE_URL` no `.env`
    (local: `http://localhost:3001`; deploy: URL pública do serviço).
  - Consumida por `src/jobs_api_client.py`, que normaliza pro mesmo formato
    (`VagaEncontrada`) das outras fontes e entra no mesmo pipeline.
- Fontes complementares: **Remotive e Arbeitnow** (APIs JSON públicas, vagas
  remotas/globais) — best-effort. Indeed e Gupy ficam como best-effort também
  (retornam vazio quando bloqueiam). NUNCA LinkedIn (ToS + anti-bot pesado).
- Controle de vagas já enviadas: **SQLite** (não JSON) — mais robusto pra
  crescer e evita duplicatas de forma mais segura.
- Agendamento: **externo, via cron do GitHub Actions** — o `main.py` roda UM
  ciclo e sai (não há mais loop/BlockingScheduler). Escolhido porque cobre a
  tarefa periódica de graça (Actions é ilimitado em repo público), evitando o
  custo de um processo 24h.

## Arquitetura de deploy (final)
- **api-vagas → Render (Web Service, free tier).** Precisa ser Web Service, não
  Background Worker, porque o bot o consome via HTTP. Trade-off: free tier dorme
  após ~15 min (cold start ~1 min), tratado em `jobs_api_client.py` com timeout
  de 60s na 1ª tentativa + retry.
- **bot Python → GitHub Actions (cron, 1 ciclo por execução, a cada 2h).** Não
  vira Background Worker no Render porque isso é pago ($7/mês); Actions faz o
  agendamento de graça.
- **Persistência do dedup:** o ambiente do Actions é efêmero, então o
  `.github/workflows/rodar-bot.yml` commita o `vagas.db` de volta no repo —
  apenas quando muda (i.e., quando houve vaga nova), com `[skip ci]`. Por isso o
  `vagas.db` saiu do `.gitignore` (precisa ser rastreado).
- **Conexão entre os dois:** o bot recebe `JOBS_API_BASE_URL` como GitHub Secret,
  apontando pra URL pública do api-vagas no Render (`https://api-vagas-xxxx.onrender.com`).
- Secrets do Actions: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `JOBS_API_BASE_URL`.

## Riscos conhecidos (não ignorar)
- Indeed e Gupy têm proteção anti-bot (Cloudflare, rate limiting). Usar
  headers de user-agent realistas, delays entre requisições, e ter
  tratamento de erro robusto para quando o HTML mudar ou bloquear o IP.
- Verificar periodicamente se a estrutura HTML das páginas mudou (scraper
  vai quebrar em algum momento — isso é esperado, não é bug de código).

## Stack
- `requests` + `BeautifulSoup4` — scraping
- `python-telegram-bot` — postagem no Telegram
- GitHub Actions (cron) — agendamento externo (era `APScheduler`, removido)
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
