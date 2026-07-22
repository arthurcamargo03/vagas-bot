# Bot de Vagas de Estágio (Telegram)

Bot que coleta vagas de estágio em TI (foco no mercado brasileiro) e posta
automaticamente num grupo/canal do Telegram, sem intervenção manual.

## Arquitetura (deploy)

Um único serviço, **sem custo e sem servidor próprio**:

```
┌─────────────────────────┐   HTTPS GET /api/vagas   ┌──────────────────────────┐
│  GitHub Actions (cron)   │ ───────────────────────▶ │  Meu Padrinho (produção)  │
│  dispara 1 ciclo a cada  │                          │  meupadrinho.com.br/api   │
│  2h → roda main.py       │ ◀─────────────────────── │  (estágios BR)            │
│  (bot Python)            │   lista + detalhes       └──────────────────────────┘
│  → filtra Curitiba/remoto│
│  → posta no Telegram     │
│  → commita vagas.db      │
└─────────────────────────┘
```

- **Fonte principal**: o bot chama **direto a API pública do Meu Padrinho**
  (`meupadrinho.com.br/api`), pega a lista de estágios recentes e **filtra por
  localização** — mantém remoto Brasil e Curitiba+região (presencial/híbrido),
  descarta outras cidades. Site de produção, sempre no ar → sem cold start.
- **bot Python**: **não roda como processo contínuo**. É disparado pelo
  **cron do GitHub Actions**, um ciclo completo por execução (a cada 2h). Sem
  servidor próprio → custo zero. O `vagas.db` (dedup) é commitado de volta no
  repo para sobreviver entre execuções.

> **Histórico:** até 2026-07 a fonte BR passava por um serviço Node intermediário
> (`api-vagas`, fork de matheusaudibert/jobs-api) hospedado num Render Web Service
> free. Foi aposentado — dormia após ~15 min (cold start) e só entregava 1 vaga
> por ciclo. O bot agora fala direto com o Meu Padrinho.

## Stack
- Python 3.11+ (`requests` + `BeautifulSoup4` para scraping, `python-telegram-bot`
  para o Telegram, `sqlite3` para dedup, `python-dotenv` para config)
- Fonte de estágio BR: API pública do Meu Padrinho (consumida direto)
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

3. Crie um bot no Telegram via [@BotFather](https://t.me/BotFather), copie o
   token, e descubra o `chat_id` do grupo (adicione o bot, mande uma mensagem,
   e consulte `https://api.telegram.org/bot<TOKEN>/getUpdates`).

4. Copie `.env.example` para `.env` e preencha:
   ```bash
   cp .env.example .env
   ```

5. Rode **um ciclo** (não é mais loop — roda uma vez e sai):
   ```bash
   python main.py
   ```

## Estrutura do projeto
```
vagas-bot/
├── main.py                       # ponto de entrada: roda 1 ciclo e sai
├── src/
│   ├── config.py                 # carrega variáveis de ambiente
│   ├── scraper.py                # agrega fontes (Meu Padrinho, Indeed, Gupy)
│   ├── meupadrinho_client.py     # cliente do Meu Padrinho (fonte BR principal)
│   ├── jobs_api_client.py        # [deprecado] antigo cliente do api-vagas/Render
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

Não há servidor pra subir — o bot fala direto com o Meu Padrinho. Só faltam os
secrets e ativar o workflow.

### 1. Secrets no GitHub (repo do bot)
Em **Settings > Secrets and variables > Actions > New repository secret**,
cadastre os dois:

| Secret               | Valor                              |
|----------------------|------------------------------------|
| `TELEGRAM_BOT_TOKEN` | token do @BotFather                |
| `TELEGRAM_CHAT_ID`   | id do grupo/canal (ex: `-100...`)  |

### 2. Ativar o workflow
O `.github/workflows/rodar-bot.yml` já está no repo. Ele roda sozinho a cada
2h; para testar na hora, use **Actions > rodar-bot > Run workflow**
(`workflow_dispatch`). O workflow commita o `vagas.db` de volta só quando há
vaga nova, mantendo o histórico limpo.

## Avisos importantes
- **Não faz scraping do LinkedIn** (ToS + anti-bot agressivo).
- Indeed e Gupy têm proteção anti-bot e entram como best-effort (retornam vazio
  quando bloqueiam) — a fonte confiável é o Meu Padrinho.
- Este projeto extrai dados publicamente visíveis para uso informativo. Para uso
  comercial, revise os termos das fontes.

## Licença
MIT
