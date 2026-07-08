# Bot de Vagas de Estágio (Telegram)

Script Python que raspa vagas de estágio em TI no Indeed e na Gupy e posta
automaticamente num canal/grupo do Telegram, sem intervenção manual.

## Status
🚧 Em desenvolvimento — estrutura base pronta, seletores de scraping
precisam ser validados/ajustados contra o HTML atual dos sites (ver
comentários `TODO` em `src/scraper.py`).

## Stack
- Python 3.11+
- `requests` + `BeautifulSoup4` — scraping
- `python-telegram-bot` — postagem no Telegram
- `APScheduler` — agendamento
- `sqlite3` — controle de vagas já enviadas (evita duplicatas)

## Como rodar localmente

1. Clone o repositório e entre na pasta:
   ```bash
   git clone <seu-repo>
   cd vagas-bot
   ```

2. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Crie um bot no Telegram via [@BotFather](https://t.me/BotFather) e copie
   o token gerado.

4. Descubra o `chat_id` do canal/grupo onde o bot vai postar (adicione o
   bot ao canal como admin, envie uma mensagem de teste, e consulte
   `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`).

5. Copie `.env.example` para `.env` e preencha os valores:
   ```bash
   cp .env.example .env
   ```

6. Rode o bot:
   ```bash
   python main.py
   ```

## Estrutura do projeto
```
vagas-bot/
├── main.py              # ponto de entrada
├── src/
│   ├── config.py         # carrega variáveis de ambiente
│   ├── scraper.py         # scraping do Indeed e da Gupy
│   ├── storage.py         # controle de vagas já enviadas (SQLite)
│   ├── notifier.py        # postagem no Telegram
│   └── scheduler.py       # orquestra o ciclo raspar -> enviar -> repetir
├── requirements.txt
├── .env.example
└── CLAUDE.md              # contexto do projeto para desenvolvimento com Claude Code
```

## Roadmap
- [ ] Validar/corrigir seletores de scraping do Indeed
- [ ] Validar/corrigir seletores (ou endpoint JSON) da Gupy
- [ ] Testes automatizados básicos
- [ ] Deploy no Railway.app ou Render.com
- [ ] Suporte a Discord (webhook)
- [ ] Dashboard simples com estatísticas de vagas coletadas

## Avisos importantes
- **Não faz scraping do LinkedIn** — a plataforma bloqueia scraping de
  forma agressiva e o risco de banimento de conta/IP é alto.
- Indeed e Gupy têm proteção anti-bot. Espere bloqueios ocasionais e
  necessidade de ajustar headers/delays com o tempo.
- Este projeto extrai dados publicamente visíveis para uso informativo.
  Se for usar comercialmente, revise os termos de uso das fontes.

## Licença
MIT
