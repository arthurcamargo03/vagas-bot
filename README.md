# Bot de Vagas de Estágio (Telegram)

Bot que coleta vagas de estágio em TI (foco no mercado brasileiro) e posta
automaticamente num grupo/canal do Telegram, sem intervenção manual.

## Arquitetura (deploy)

Dois serviços independentes, ambos **sem custo**:

```
┌─────────────────────────┐        HTTP GET /estagio        ┌──────────────────────┐
│  GitHub Actions (cron)   │  ─────────────────────────────▶ │  api-vagas (Render)   │
│  dispara 1 ciclo a cada  │                                 │  Web Service, free    │
│  2h → roda main.py       │ ◀───────────────────────────── │  (Meu Padrinho / BR)  │
│  (bot Python)            │        vaga mais recente        └──────────────────────┘
│  → posta no Telegram     │
│  → commita vagas.db      │
└─────────────────────────┘
```

- **api-vagas** (fonte principal de estágio BR): serviço Node separado
  ([fork de matheusaudibert/jobs-api](https://github.com/arthurcamargo03/api-vagas)),
  hospedado no **Render como Web Service (free tier)**. Precisa expor HTTP porque
  o bot o consome — por isso não é Background Worker. Free tier dorme após
  ~15 min; o bot trata o cold start com timeout maior + retry.
- **bot Python**: **não roda como processo contínuo**. É disparado pelo
  **cron do GitHub Actions**, um ciclo completo por execução (a cada 2h). Sem
  servidor próprio → custo zero. O `vagas.db` (dedup) é commitado de volta no
  repo para sobreviver entre execuções.

**Por que essa combinação?** Background Worker no Render é pago ($7/mês) e o
free Web Service dorme; GitHub Actions cron cobre a tarefa periódica de graça
(ilimitado em repo público), mantendo o intervalo original de ~1-2h.

## Stack
- Python 3.11+ (`requests` + `BeautifulSoup4` para scraping, `python-telegram-bot`
  para o Telegram, `sqlite3` para dedup, `python-dotenv` para config)
- api-vagas: Node.js/Express (serviço à parte)
- Orquestração/agendamento: GitHub Actions (cron)

## Como rodar localmente

1. Clone e entre na pasta:
   ```bash
   git clone https://github.com/arthurcamargo03/vagas-bot
   cd vagas-bot
   ```

2. Ambiente virtual + dependências:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Suba o api-vagas localmente (noutro terminal):
   ```bash
   git clone https://github.com/arthurcamargo03/api-vagas
   cd api-vagas && npm ci && node index.js   # serve em http://localhost:3001
   ```

4. Crie um bot no Telegram via [@BotFather](https://t.me/BotFather), copie o
   token, e descubra o `chat_id` do grupo (adicione o bot, mande uma mensagem,
   e consulte `https://api.telegram.org/bot<TOKEN>/getUpdates`).

5. Copie `.env.example` para `.env` e preencha:
   ```bash
   cp .env.example .env
   ```

6. Rode **um ciclo** (não é mais loop — roda uma vez e sai):
   ```bash
   python main.py
   ```

## Estrutura do projeto
```
vagas-bot/
├── main.py                       # ponto de entrada: roda 1 ciclo e sai
├── src/
│   ├── config.py                 # carrega variáveis de ambiente
│   ├── scraper.py                # agrega fontes (api-vagas, Remotive, ...)
│   ├── jobs_api_client.py        # cliente do api-vagas (fonte BR principal)
│   ├── storage.py                # dedup de vagas já enviadas (SQLite)
│   ├── notifier.py               # postagem no Telegram
│   └── scheduler.py              # orquestra UM ciclo (raspar -> filtrar -> enviar)
├── .github/workflows/
│   └── rodar-bot.yml             # cron que dispara o bot a cada 2h
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

## Deploy

### 1. api-vagas no Render (Web Service, free)
1. Faça deploy do fork **[arthurcamargo03/api-vagas](https://github.com/arthurcamargo03/api-vagas)**
   (a pasta já tem `render.yaml` e `Dockerfile`).
2. No Render: **New > Blueprint** (usa o `render.yaml`) ou **New > Web Service**
   apontando pro repo, runtime **Docker**, plano **Free**.
3. Após o deploy, o Render gera uma URL pública tipo
   `https://api-vagas-xxxx.onrender.com`. **Anote essa URL** — vira o
   `JOBS_API_BASE_URL` do bot.

### 2. Secrets no GitHub (repo do bot)
Em **Settings > Secrets and variables > Actions > New repository secret**,
cadastre os três:

| Secret               | Valor                                                        |
|----------------------|-------------------------------------------------------------|
| `TELEGRAM_BOT_TOKEN` | token do @BotFather                                         |
| `TELEGRAM_CHAT_ID`   | id do grupo/canal (ex: `-100...`)                          |
| `JOBS_API_BASE_URL`  | a URL pública do api-vagas no Render (do passo 1)          |

### 3. Ativar o workflow
O `.github/workflows/rodar-bot.yml` já está no repo. Ele roda sozinho a cada
2h; para testar na hora, use **Actions > rodar-bot > Run workflow**
(`workflow_dispatch`). O workflow commita o `vagas.db` de volta só quando há
vaga nova, mantendo o histórico limpo.

## Avisos importantes
- **Não faz scraping do LinkedIn** (ToS + anti-bot agressivo).
- Indeed e Gupy têm proteção anti-bot e entram como best-effort (retornam vazio
  quando bloqueiam) — a fonte confiável é o api-vagas.
- Este projeto extrai dados publicamente visíveis para uso informativo. Para uso
  comercial, revise os termos das fontes.

## Licença
MIT
