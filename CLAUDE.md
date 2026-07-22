# Contexto do Projeto — Bot de Vagas de Estágio

## O que é
Script Python que raspa vagas de estágio em TI (Indeed e Gupy) e posta
automaticamente num canal do Telegram (e futuramente Discord), sem
intervenção manual. Roda a cada 1-2h via agendador.

## Objetivo
Projeto de portfólio que demonstra scraping, consumo de API externa,
agendamento e deploy. Há possível exploração futura de um modelo de negócio,
não detalhada aqui.

## Decisões já tomadas
- **Começar pelo Telegram**, não Discord (API mais simples, bot token via
  BotFather, sem precisa configurar servidor/webhook).
- **[SUPERSEDIDO em 2026-07 — ver "Meu Padrinho direto" abaixo]** O bot agora bate
  DIRETO na API do Meu Padrinho; o serviço `api-vagas` no Render saiu do pipeline
  (redundante, pode desligar). O texto abaixo descreve o arranjo antigo.
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
- Fontes complementares: Indeed e Gupy — best-effort (retornam vazio quando
  bloqueiam). NUNCA LinkedIn (ToS + anti-bot pesado).

## Meu Padrinho direto (2026-07) — substitui o serviço api-vagas
- **O que mudou:** o bot deixou de consumir o serviço `api-vagas` no Render e
  passou a chamar DIRETO a API pública do Meu Padrinho
  (`https://meupadrinho.com.br/api`), em `src/meupadrinho_client.py`. O antigo
  `src/jobs_api_client.py` ficou deprecado (mantido de referência).
- **Por que:** (1) sem cold start — o Meu Padrinho é site de produção, sempre no
  ar (o Render free dormia ~15 min e acordava em ~1 min); (2) mais volume — a
  lista traz ~10 vagas/ciclo, não só a 1 mais recente que a api-vagas expunha.
- **Filtro de localização (o pedido do dono, que mora em Curitiba):**
  - `forma_trabalho == 'remoto'` → mantém (remoto Brasil, dá pra fazer daqui).
  - `local` contém Curitiba OU região metropolitana (Pinhais, São José dos
    Pinhais, Colombo, Araucária, Campo Largo, Fazenda Rio Grande, Almirante
    Tamandaré, Piraquara, Quatro Barras, Campina Grande do Sul), com
    presencial/híbrido → mantém.
  - outra cidade presencial/híbrido (Santos, Jundiaí, BH…) → descarta.
  - Match normalizado (minúsculo, sem acento). `local`/`link_vaga` só vêm no
    endpoint de DETALHES, então é 1 request de lista + 1 de detalhe por vaga.
  - **Log por ciclo:** `Meu Padrinho (estagio): N brutas → X mantidas
    (Curitiba/remoto) + Z fora de local + W tipo indesejado (freelance/pós)`.
- **Filtro de TIPO (além do de local):** barra pelo título `freelance`/`freela`,
  `mestrado`, `doutorado`, `pos-graduacao` — mesmo vindo como "estágio", não
  serve pro canal (estágio pra graduação). Checado no título da lista, antes do
  request de detalhe. NÃO barra `bolsa`/`bolsista` sozinhos de propósito
  (estágio BR costuma ser "bolsa-auxílio", legítimo).
- **Impacto no deploy:** a api-vagas no Render virou redundante — pode desligar,
  e o secret `JOBS_API_BASE_URL` no GitHub Actions fica sem uso (inofensivo).

## Remotive desplugado (2026-07)
- **O que aconteceu:** a API pública do Remotive
  (`https://remotive.com/api/remote-jobs?search=…`) parou de respeitar o
  parâmetro `search`. Testado: `intern`, `internship`, `estagio desenvolvimento`,
  `python`, `nurse` e até uma string aleatória sem sentido devolvem **a MESMA
  lista de 41 vagas** (`job-count: 41` como inventário total — o Remotive real
  tem milhares). Ou seja, viraram um feed fixo das ~41 recentes, sem busca.
- **Por que doeu:** dessas 41, **zero** têm estágio no título — é dominado por
  `Senior/Staff/Head of/Tech Lead`. Como fonte "complementar" de estágio, secou:
  só injetava ruído sênior que o filtro tinha que suprimir (e num ciclo ruim
  vazava). O plano de apertar a query pra `intern` não resolveria nada, porque a
  query é ignorada.
- **Decisão:** `buscar_vagas_remotive()` foi **removida da tupla de fontes** em
  `buscar_todas_vagas()` (opção "desplugar", não deletar). A função e o filtro de
  senioridade continuam no módulo; religar é só readicioná-la à tupla. Se um dia
  precisar de estágio remoto internacional, o caminho é uma fonte com busca real
  (ex.: Arbeitnow), aí sim com ACCEPT estrito `intern`/`internship`.
- **Fonte de estágio que sobra e funciona:** api-vagas (Meu Padrinho, BR nativo).

## Filtro de senioridade (fontes remotas)
- **Estado atual: DORMENTE.** A única fonte que passava por ele era o Remotive,
  agora desplugado (ver seção acima). Mantido no código, aplicado dentro de
  `buscar_vagas_remotive()`, pronto pra quando entrar uma fonte remota nova.
- **Por que existe:** a busca do Remotive é por texto solto, sem filtro de
  nível — devolve muito senior/staff/lead/freelance misturado com o que
  interessa (estágio/júnior). O api-vagas NÃO passa por esse filtro (já vem
  como estágio BR de verdade).
- **Onde:** `_filtrar_por_senioridade()` em `src/scraper.py`, aplicado no
  retorno de `buscar_vagas_remotive` (reaproveitável se Arbeitnow for ligado).
- **Regra por título (case-insensitive, palavra inteira via regex):**
  - DESCARTA se contém: `senior`, `sênior`, `sr.`, `staff`, `lead`,
    `principal`, `head of`, `manager`, `freelance`.
  - ACEITA se contém: `intern`, `internship`, `estagio`, `estágio`, `junior`,
    `júnior`, `jr.`, `entry level`, `entry-level`, `trainee`, `graduate`.
  - **Descarte tem precedência** quando os dois aparecem (prioriza não soltar
    sênior).
- **Match por palavra inteira** (lookarounds, não substring) de propósito:
  evita `intern` casar com "International" e `lead` com "Leadership".
- **Decisão consciente sobre "ambíguo":** título que não bate em nenhuma lista
  é MANTIDO (não descartado) e logado como ambíguo. Preferimos deixar passar
  uma vaga sem palavra-chave óbvia (ex: "Frontend Developer") a perder vaga boa.
  Custo aceito: alguns títulos genéricos/não-dev passam (o filtro é só de
  senioridade, não de relevância de cargo).
- **Log por ciclo:** `Remotive: N brutas → A aceitas + M ambíguas (mantidas)
  + D descartadas`. Títulos de descartadas/ambíguas vão em nível DEBUG.
- Controle de vagas já enviadas: **SQLite** (não JSON) — mais robusto pra
  crescer e evita duplicatas de forma mais segura.
- Agendamento: **externo, via cron do GitHub Actions** — o `main.py` roda UM
  ciclo e sai (não há mais loop/BlockingScheduler). Escolhido porque cobre a
  tarefa periódica de graça (Actions é ilimitado em repo público), evitando o
  custo de um processo 24h.

## Arquitetura de deploy (final)
- **Fonte de estágio → API do Meu Padrinho, chamada direto pelo bot** (sem serviço
  intermediário). Acabou a dependência do Render: nada de cold start. Ver seção
  "Meu Padrinho direto".
  - *(Histórico: antes rodava o serviço `api-vagas` num Render Web Service free.
    Desativado em 2026-07 — dormia após ~15 min e só dava 1 vaga/ciclo.)*
- **bot Python → GitHub Actions (cron, 1 ciclo por execução, a cada 2h).** Não
  vira Background Worker no Render porque isso é pago ($7/mês); Actions faz o
  agendamento de graça.
- **Persistência do dedup:** o ambiente do Actions é efêmero, então o
  `.github/workflows/rodar-bot.yml` commita o `vagas.db` de volta no repo —
  apenas quando muda (i.e., quando houve vaga nova), com `[skip ci]`. Por isso o
  `vagas.db` saiu do `.gitignore` (precisa ser rastreado).
- Secrets do Actions: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. O
  `JOBS_API_BASE_URL` ficou sem uso (o bot não fala mais com o Render) — pode
  remover do GitHub, é inofensivo se ficar.

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
