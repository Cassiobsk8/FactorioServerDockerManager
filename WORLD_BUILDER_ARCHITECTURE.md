# WORLD BUILDER ARCHITECTURE

Versão: 3.0.0
Epic: World Builder
Fase: V1

---

## 1. Objetivos

- Prover uma ferramenta visual e integrada para criação de mundos no Factorio.
- Gerar previews visuais utilizando o próprio binário do Factorio (nunca renderizados pelo navegador).
- Criar arquivos de save prontos para uso no servidor.
- Manter total aderência ao Design System existente do projeto.

## 2. Escopo V1

### Incluído
- Criação de mundo com parâmetros configuráveis (World Name, Seed, Planet).
- Geração de preview via processo real do Factorio.
- Criação de arquivo de save.
- Tela unificada com layout 30% (configuração) / 70% (preview).
- Indicador de status do preview (atualizado / desatualizado).
- Botões: Update Preview e Create World.

### Não Incluído (V2+)
- Wizard multi-step.
- Seleção e configuração de mods.
- Histórico de mundos criados.
- Múltiplos planets com configurações avançadas.

## 3. Princípios de Design

- **Inspirar-se no jogo, não copiar**: a interface remete à estética industrial do Factorio, mas implementada com os componentes existentes do Design System.
- **Fonte da verdade**: o preview é sempre gerado pelo processo real do Factorio; o navegador nunca renderiza o mapa.
- **Single Source of Truth**: a configuração do mundo é o estado central; preview e save derivam dela.
- **Atualização explícita**: o preview atualiza exclusivamente mediante clique em "Update Preview"; sem polling automático e sem auto-refresh.

## 4. Layout da Interface

### Estrutura Geral
- Rota dedicada: `/world-builder`.
- Template próprio: `world_builder.html`.
- Módulo JS próprio: `world_builder.js`.
- Layout CSS Grid: sidebar esquerda (~30%) + área de preview (~70%).

### Área Esquerda (Configuração — ~30%)

Container vertical com cards. Componentes reutilizados do Design System:

- **Card: Identificação**
  - Campo `World Name` (text input, sanitizado).
  - Campo `Seed` (text input) + toggle `Random Seed`.

- **Card: Geração**
  - Campo `Planet` (select dropdown).

- **Card: Ações**
  - Indicador `Status do Preview` (badge component).
  - Botão `Update Preview` (`.secondary-button`).
  - Botão `Create World` (`.danger-button` ou `.primary-button` conforme estado).

### Área Direita (Preview — ~70%)

- Container com imagem responsiva.
- Componente: `<img>` ou `<canvas>` carregando imagem gerada pelo servidor.
- Estados visíveis:
  - **Preview atualizado**: imagem exibida, badge "Updated".
  - **Preview desatualizado**: placeholder, badge "Outdated", imagem anterior opaca.
  - **Gerando**: spinner/skeleton, botões desabilitados.
  - **Erro**: mensagem inline com detalhe.
- A imagem é servida como arquivo estático pelo backend, nunca renderizada via JS/Canvas no cliente.

## 5. Fluxo Completo

### 5.1 Fluxo de Criação de Preview

1. Usuário preenche campos no painel esquerdo.
2. Usuário clica em **Update Preview**.
3. Frontend envia `POST /api/world-builder/preview` com a configuração serializada.
4. Backend valida os dados e aciona `WorldBuilderService.generate_preview()`.
5. O serviço prepara um ambiente temporário e executa o binário do Factorio em modo headless com parâmetros de geração de preview (`--generate-map-preview` ou mecanismo equivalente).
6. O processo escreve a imagem em `data/world-builder/previews/<hash>.png`.
7. Backend retorna `{"preview_url": "/api/world-builder/preview-image/<hash>.png", "status": "ready"}`.
8. Frontend atualiza a área de preview e marca o status como atualizado.

### 5.2 Fluxo de Criação de Save

1. Usuário clica em **Create World**.
2. Frontend valida que o preview está atualizado; se não, exige atualização prévia.
3. Frontend envia `POST /api/world-builder/create` com a configuração e o hash do preview.
4. Backend valida, aciona `WorldBuilderService.create_world()`.
5. O serviço executa o Factorio em modo de geração de save (`--create <save_path>`), com os parâmetros recebidos.
6. O save é escrito em `data/saves/<world_name>.zip`.
7. Backend registra o save no catálogo de saves existente.
8. Backend retorna `{"save_file": "<world_name>.zip", "status": "created"}`.
9. Frontend exibe confirmação e atualiza a lista de saves (se aplicável).

### 5.3 Fluxo de Validação

- Em cada POST, o backend valida:
  - `world_name`: não vazio, sem caracteres inválidos, único.
  - `seed`: inteiro ou string alfanumérica válida; se `random_seed=true`, ignora.
  - `planet`: valor permitido conforme catálogo de planetas suportados pelo binário.
- Em caso de erro, retorna `400 Bad Request` com mensagem específica.

## 6. Componentes

### Backend

#### Serviço: `world_builder_service.py`

Responsável por toda a lógica de negócio do World Builder.

Métodos principais:
- `generate_preview(config: WorldConfig) -> PreviewResult`
  - Prepara diretório temporário.
  - Constrói comando do Factorio para geração de preview.
  - Executa processo com timeout.
  - Move imagem gerada para `data/world-builder/previews/`.
  - Retorna caminho relativo e status.
- `create_world(config: WorldConfig, preview_hash: str) -> WorldResult`
  - Valida que o preview corresponde à configuração.
  - Executa Factorio em modo de criação de save.
  - Move/copia save para `data/saves/`.
  - Atualiza catálogo de saves.
  - Retorna nome do arquivo e status.
- `list_planets() -> list[str]`
  - Retorna planetas suportados pelo binário instalado.

#### Modelo: `world_config.py`

Dataclass ou dicionário tipado representando a configuração do mundo.

Campos:
- `world_name: str`
- `seed: str | None`
- `random_seed: bool`
- `planet: str`
- `preview_hash: str | None` (preenchido após geração)

Validação:
- `planet` é validado contra o catálogo oficial de planetas.
- Nenhum parâmetro `--preset` é enviado ao executável do Factorio.

#### Rotas: `world_builder_routes.py`

Blueprint do Flask registrado em `app.py`.

Rotas:

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/world-builder` | Renderiza a página do World Builder. |
| GET | `/api/world-builder/options` | Retorna planetas disponíveis. |
| POST | `/api/world-builder/preview` | Solicita geração de preview. |
| POST | `/api/world-builder/create` | Cria o mundo (save). |
| GET | `/api/world-builder/preview-status/<hash>` | Consulta status de geração (polling). |
| DELETE | `/api/world-builder/preview/<hash>` | Remove preview cacheado (opcional). |

Arquivos estáticos de preview servidos via rota dedicada `/api/world-builder/preview-image/<hash>` com `send_from_directory`. A rota aceita tanto `<hash>` quanto `<hash>.png` na URL, normalizando o parâmetro internamente. Previews não fazem parte do `static_folder` da aplicação.

#### Modelo de Dados: `data/world-builder/manifest.json`

Registra previews gerados para limpeza e auditoria.

Estrutura:
```json
{
  "previews": [
    {
      "hash": "<sha256>",
      "world_name": "...",
      "seed": "...",
      "planet": "...",
      "created_at": "<iso8601>",
      "file_path": "data/world-builder/previews/<hash>.png"
    }
  ]
}
```

### Frontend

#### Template: `world_builder.html`

- Estrutura baseada no Design System (`app.css` classes).
- Layout CSS Grid: `grid-template-columns: 30% 70%`.
- Reutiliza componentes: `.card`, `.config-card`, `.settings-module-card`, `.secondary-button`, `.danger-button`, `.badge`.
- Inclui traduções via `data-i18n`.
- Carrega módulo `world_builder.js`.

#### Módulo JS: `world_builder.js`

Responsabilidades:
- Gerenciar estado local do formulário.
- Controlar indicador de status do preview.
- Enviar requisições para a API.
- Exibir imagem de preview ou placeholder.
- Tratar erros e estados de loading.
- Atualizar a lista de saves após criação (se integrado com módulo `saves.js`).

Estado local:
```js
const state = {
  config: {
    worldName: '',
    seed: '',
    randomSeed: true,
    planet: 'nauvis'
  },
  preview: {
    status: 'outdated', // 'idle' | 'outdated' | 'generating' | 'ready' | 'error'
    url: null,
    hash: null,
    error: null
  },
  loading: false
};
```

#### CSS: `world_builder.css` (ou seção em `app.css`)

- Estilos específicos do layout 30/70.
- Estilos do container de preview (aspect-ratio, objeto-fit).
- Animações de loading e transições de status.

## 7. API

### POST /api/world-builder/preview

Request:
```json
{
  "world_name": "Meu Mundo",
  "seed": "12345",
  "random_seed": false,
  "planet": "nauvis"
}
```

Response 200:
```json
{
  "preview_url": "/api/world-builder/preview-image/abc123.png",
  "preview_hash": "abc123",
  "status": "ready",
  "generated_at": "2025-01-15T10:00:00Z"
}
```

Response 422:
```json
{
  "error": "invalid_planet",
  "message": "Planeta 'mars' não suportado pela versão instalada."
}
```

### POST /api/world-builder/create

Request:
```json
{
  "world_name": "Meu Mundo",
  "seed": "12345",
  "random_seed": false,
  "planet": "nauvis",
  "preview_hash": "abc123"
}
```

Response 201:
```json
{
  "save_file": "Meu Mundo.zip",
  "save_path": "data/saves/Meu Mundo.zip",
  "status": "created",
  "created_at": "2025-01-15T10:00:00Z"
}
```

Response 409:
```json
{
  "error": "save_exists",
  "message": "Arquivo de save 'Meu Mundo.zip' já existe."
}
```

### GET /api/world-builder/options

Response 200:
```json
{
  "planets": ["nauvis", "vulcanus", "fulgora", "gleba", "aquilo"]
}
```

## 8. Responsabilidades

### Backend
- Validar entradas do usuário.
- Gerenciar ciclo de vida do processo Factorio para geração de preview e save.
- Gerenciar armazenamento de arquivos de preview e saves.
- Servir arquivos estáticos de preview.
- Manter catálogo de planetas suportados.

### Frontend
- Fornecer interface fiel ao Design System.
- Gerenciar estado local do formulário e preview.
- Comunicar-se com a API de forma assíncrona.
- Exibir feedback visual de status, erros e loading.
- Sanitizar entradas antes do envio (validação client-side como UX, não como segurança).

### Serviço (WorldBuilderService)
- Isolar lógica de execução do Factorio do resto da aplicação.
- Gerenciar timeouts e limpeza de processos órfãos.
- Garantir que previews e saves sejam escritos em paths seguros.

## 9. Integração com o Sistema Existente

- **Blueprints**: novo blueprint `world_builder_routes` registrado em `app.py`.
- **Serviços**: `WorldBuilderService` em `backend/services/`.
- **Templates**: novo template `world_builder.html` em `frontend/templates/`.
- **Estáticos**: `frontend/static/js/world_builder.js` e `frontend/static/css/world_builder.css`.
- **i18n**: novas chaves nos arquivos JSON de tradução (`i18n/en.json`, `i18n/pt_BR.json`, etc.).
- **Navegação**: novo item no menu de abas existente ou link direto em Dashboard/Saves.
- **Saves**: após criação, o save fica disponível na lista de saves existente (`/api/saves`).

## 10. Roadmap — Próximas Versões

### V2 — World Manager Aprimorado
- Seleção e configuração de mods no momento da criação.
- Histórico de mundos criados com previews.
- Importação de saves existentes.
- Edição de parâmetros avançados (map settings, richness, frequency).

### V3 — Multi-Planet e Map Exchange Strings
- Suporte a configurações avançadas por planeta.
- Importação/exportação de Map Exchange Strings (presets do jogo).
- Comparação visual de múltiplos presets.

### V4 — Colaboração e Templates
- Templates de mundo salvos pelo usuário.
- Compartilhamento de configurações via link.
- Preview em tempo real (atualização automática com debounce, opcional).

## 11. Implementação Backend V1

### Arquivos criados
- `backend/services/world_config.py` — Dataclass `WorldConfig` com validação embutida.
- `backend/services/world_builder_service.py` — Serviço principal com `generate_preview()` e `create_world()`.
- `backend/routes/world_builder_routes.py` — Blueprint Flask com rotas API e serving de previews.
- `backend/tests/test_world_builder_service.py` — 12 testes de unidade do serviço.
- `backend/tests/test_world_builder_routes.py` — 8 testes de integração das rotas.

### Decisões de implementação
- **Execução oficial**: todo processo usa `subprocess.run` com o binário do Factorio instalado (`factorio/bin/x64/factorio`). Nenhuma lógica de geração de mapa foi implementada no backend.
- **Preview**: utiliza `--map-preview` do Factorio em diretório temporário; o arquivo `preview.png` é movido para `data/world-builder/previews/<sha256>.png`.
- **Save**: utiliza `--create=<path>` com seed opcional e `--map-gen-settings` customizado quando fornecido.
- **Idempotência de preview**: previews são cacheados por hash SHA-256 da configuração; requisições repetidas retornam a imagem existente sem nova execução.
- **Validação**: `world_name` obrigatório; `planet` validado contra catálogo fixo. Save duplicado retorna `409 Conflict`.
- **Rotas implementadas**:
  - `GET /api/world-builder/options`
  - `POST /api/world-builder/preview`
  - `POST /api/world-builder/create`
  - `GET /api/world-builder/preview-image/<hash>`

## 12. Implementação Frontend V1

### Arquivos criados
- `frontend/static/js/world_builder.js` — Módulo JavaScript responsável pela interface do World Builder.
- `frontend/i18n/{en,pt_BR,es,zh_CN}.json` — Chaves de tradução adicionadas em `world_builder.*`.

### Arquivos modificados
- `frontend/templates/index.html` — Novo botão de aba `world-builder` e painel `#world-builder-panel`.
- `frontend/static/css/app.css` — Estilos do layout 30%/70%, preview container, badges e checkbox row.
- `frontend/static/js/app.js` — Handler para troca de aba `world-builder` que recarrega opções.
- `backend/tests/test_frontend_ui.py` — 7 novos testes estruturais para a interface.

### Decisões de implementação
- **Integração SPA**: o World Builder foi adicionado como uma nova aba no SPA existente, seguindo o padrão de tabs já estabelecido.
- **Layout**: CSS Grid com `grid-template-columns: 30% 70%` aplicado via classe `.world-builder-layout`.
- **Componentes reutilizados**: `.card`, `.config-card`, `.stacked-form`, `.secondary-button`, `.danger-button`, `.badge`.
- **Comportamento do preview**:
  - Qualquer alteração nos campos do formulário marca o preview como "desatualizado" (`.outdated`) e oculta a imagem.
  - O preview atualiza exclusivamente mediante clique em "Update Preview".
  - Durante a geração, botões são desabilitados e o status muda para "Gerando preview...".
  - Em caso de erro, o status muda para "Erro no preview" e a imagem anterior fica opaca.
- **Integração com backend**: chamadas `fetch()` para `/api/world-builder/options`, `/api/world-builder/preview` e `/api/world-builder/create`.
- **Imagem do preview**: servida via endpoint `/api/world-builder/preview-image/<hash>` e exibida em `<img>`.

---

## 14. Refinamento WB-V1.2 — Gerador de Seed

### Problema resolvido
O checkbox "Seed Aleatória" não representava bem a ação desejada. O usuário esperava gerar uma nova seed sob demanda.

### Solução
- Substituído o checkbox por um botão "🎲 Gerar" ao lado do campo Seed.
- Ao clicar em "Gerar": é gerada uma seed aleatória inteira (0 a 999.999.999), o campo é atualizado imediatamente e o preview é marcado como "desatualizado".
- Nenhuma geração automática de preview é disparada.
- A seed continua usando o mesmo intervalo aceito pelo Factorio (inteiro positivo).
- O campo Seed permanece editável manualmente.

### Arquivos modificados
- `frontend/templates/index.html` — removido checkbox `wb-random-seed`, adicionado botão `wb-generate-seed` em linha com o input.
- `frontend/static/js/world_builder.js` — adicionada `generateRandomSeed()`, removido handler do checkbox, adicionado handler do botão. `random_seed` agora é inferido: `true` quando o campo está vazio, `false` quando há valor.
- `frontend/static/css/app.css` — adicionada classe `.seed-row` para layout inline do input + botão.
- `frontend/i18n/*.json` — adicionada chave `world_builder.generate_seed`, removida `world_builder.random_seed`.
- `backend/tests/test_frontend_ui.py` — atualizados testes estruturais para refletir o novo layout.

### Comportamento do fluxo
1. Usuário clica em "Gerar" → seed aleatória preenchida.
2. Preview marcado como `outdated`.
3. Usuário clica em "Update Preview" → preview gerado com a seed escolhida.
4. Usuário clica em "Create World" → save criado com a seed escolhida.

---

## 13. Validação e Entrega V1

### Testes
- **Backend**: 281 testes passando (0 regressões).
- **Frontend UI**: 17 testes estruturais passando.
- **World Builder Service**: 12 testes de unidade.
- **World Builder Routes**: 8 testes de integração.

### Arquivos entregues
| Arquivo | Descrição |
|---------|-----------|
| `backend/services/world_config.py` | Dataclass de configuração do mundo. |
| `backend/services/world_builder_service.py` | Serviço: preview e criação de save. |
| `backend/routes/world_builder_routes.py` | Blueprint Flask + endpoints API. |
| `backend/tests/test_world_builder_service.py` | Testes de unidade do serviço. |
| `backend/tests/test_world_builder_routes.py` | Testes de integração das rotas. |
| `frontend/static/js/world_builder.js` | Módulo JS da interface. |
| `frontend/templates/index.html` | Tab + painel World Builder. |
| `frontend/static/css/app.css` | Estilos do layout 30/70, preview, seed row e status banner. |
| `frontend/i18n/*.json` | Chaves de tradução em 4 idiomas. |
| `backend/version.py` | Versão bumped para 3.0.0. |

### Fluxo validado
1. Abrir `/` → aba `World Builder` disponível na sidebar.
2. Carregar presets via `GET /api/world-builder/options`.
3. Usuário altera campos → preview marcado como `outdated`.
4. Clicar `Update Preview` → `POST /api/world-builder/preview` → imagem exibida + badge `updated`.
5. Clicar `Create World` → valida `preview_hash` + `POST /api/world-builder/create` → save criado em `data/saves/`.

### Screenshots esperados
- **Tela World Builder**: sidebar com nova aba "World Builder" selecionada.
- **Área esquerda (30%)**: card de configuração com campos World Name, Seed + botão "🎲 Gerar", Planet, Preset; botões Update Preview e Create World.
- **Área direita (70%)**: preview container com imagem PNG do mapa gerado pelo Factorio; badge "Preview updated" em verde.
- **Estado outdated**: badge "Preview outdated" em cinza, imagem opaca ou placeholder visível.
- **Estado generating**: botões desabilitados, badge "Gerando preview..." ativo.
- **Instalação inválida**: banner amarelo "World Builder Preview indisponível. Instalação do Factorio não concluída." visível; botões e campos desabilitados.

### Regressões
- Nenhuma. Suíte completa de 288 testes permanece verde.

---

## 14. Refinamento WB-V1.3.1 — Validação do Ambiente

### Problema resolvido
O executável do Factorio pode ser um placeholder/script em vez do binário real, causando falha silenciosa na geração de preview.

### Solução
- Adicionada validação automática do binário via magic bytes ELF (`\x7fELF`).
- Novo endpoint `GET /api/world-builder/status` retorna `{valid, reason, message}`.
- Frontend exibe banner amarelo e desabilita controles quando a instalação é inválida.
- Backend bloqueia `generate_preview()` e `create_world()` antes de executar o binário.

### Arquivos modificados
- `backend/services/world_builder_service.py` — adicionada `validate_factorio_binary()`.
- `backend/routes/world_builder_routes.py` — adicionada rota `/api/world-builder/status`.
- `frontend/static/js/world_builder.js` — adicionada `checkWorldBuilderStatus()`.
- `frontend/templates/index.html` — adicionado `#wb-status-banner`.
- `frontend/static/css/app.css` — adicionada `.world-builder-status-banner`.
- `frontend/i18n/*.json` — adicionadas `world_builder.status.unavailable` e `world_builder.status.unavailable_detail`.
- `backend/tests/test_world_builder_service.py` — 3 novos testes para validação de binário.
- `backend/tests/test_world_builder_routes.py` — 3 novos testes para endpoint de status.
- `backend/tests/test_frontend_ui.py` — atualizados testes estruturais.

### Comportamento do fluxo
1. Usuário abre a aba World Builder.
2. Frontend consulta `/api/world-builder/status`.
3. Se inválido: banner visível, controles desabilitados, preview bloqueado.
4. Se válido: comportamento normal (V1.2).

---

## 15. Hotfix HF-INSTALL-03 — Validação Completa da Instalação

### Problema resolvido
O ambiente de desenvolvimento utilizava um placeholder/script Python no lugar do binário real do Factorio. O World Builder falhava silenciosamente porque não havia validação suficiente antes de executar o binário.

### Solução
- Adicionada `validate_installation()` em `backend/services/factorio_service.py`.
- Validação agora verifica:
  1. `factorio/bin/x64/factorio` existe e é executável.
  2. `factorio/data/` existe.
  3. `factorio/config/` existe.
  4. `factorio --version` retorna exit code 0.
- `install_server()` agora chama `validate_installation()` **após** extração e **antes** de marcar `install_progress.json` como `status=complete`.
- Em caso de falha na validação: escreve `status=error` em `install_progress.json` e aborta a instalação.

### Arquivos modificados
- `backend/services/factorio_service.py` — adicionada `validate_installation()`, atualizado `install_server()` e `_extract_archive()`.
- `backend/tests/test_server_lifecycle_regression.py` — atualizado teste de install para incluir `data/`, `config/` e binary `--version`; adicionados 6 testes de validação.

### Comportamento do fluxo
1. Usuário clica em instalar o servidor.
2. Download e extração acontecem normalmente.
3. `validate_installation()` é executada.
4. Se válida: `install_progress.json` recebe `status=complete`.
5. Se inválida: `install_progress.json` recebe `status=error` e a exceção é propagada.

---

## 16. Implementação Backend WB-V1.5 — Integração Oficial com o Executável

### Problema resolvido
O World Builder utilizava parâmetros não oficiais (`--map-preview`) e criava arquivos temporários fora da estrutura prescrita, divergindo da documentação oficial da Wiki do Factorio.

### Solução
- **Parâmetros oficiais**: todo processo usa exclusivamente parâmetros documentados na Wiki do Factorio.
  - Preview: `factorio --generate-map-preview preview.png --map-gen-settings map-gen-settings.json [--map-settings map-settings.json] [--map-gen-seed SEED] [--preset PRESET] [--map-preview-size 1024] [--map-preview-planet PLANET]`
  - Create: `factorio --create save.zip --map-gen-settings map-gen-settings.json [--map-settings map-settings.json] [--map-gen-seed SEED] [--preset PRESET]`
- **Diretório temporário oficial**: criado em `/tmp/world-builder/<uuid>/` para cada operação, contendo `map-gen-settings.json`, `map-settings.json`, `preview.png` ou `save.zip`.
- **Limpeza obrigatória**: diretório temporário removido completamente após sucesso ou falha via `shutil.rmtree`.
- **Captura de execução**: registra comando completo, stdout, stderr, return code e tempo de execução.
- **Tratamento de erro**: mensagens amigáveis retornadas ao frontend; detalhes completos apenas no log.
- **Sem algoritmos próprios**: toda geração é realizada pelo executável oficial do Factorio.

### Arquivos modificados
- `backend/services/world_builder_service.py` — refatoração completa com parâmetros oficiais e temp directory.
- `backend/services/world_config.py` — adicionado campo `map_settings` para suporte a `--map-settings`.
- `backend/tests/test_world_builder_service.py` — 48 testes cobrindo todos os cenários.
- `backend/tests/test_world_builder_routes.py` — 8 testes de integração das rotas.

### Testes adicionados
- `test_generate_preview_uses_official_parameters` — valida comando de preview com parâmetros oficiais.
- `test_generate_preview_with_custom_settings` — valida preset, seed, planeta e map-settings.
- `test_create_world_uses_official_parameters` — valida comando de criação com parâmetros oficiais.
- `test_generate_preview_handles_executable_error` — CalledProcessError.
- `test_create_world_handles_executable_error` — CalledProcessError.
- `test_generate_preview_handles_permission_error` — PermissionError.
- `test_generate_preview_handles_missing_binary` — arquivo inexistente.
- `test_generate_preview_cleans_tempdir_on_success` — limpeza após sucesso.
- `test_generate_preview_cleans_tempdir_on_failure` — limpeza após falha.
- `test_create_world_cleans_tempdir_on_success` — limpeza após sucesso.
- `test_create_world_cleans_tempdir_on_failure` — limpeza após falha.
- `test_generate_preview_handles_timeout` — timeout na preview.
- `test_create_world_handles_timeout` — timeout na criação.
- `test_run_factorio_captures_execution_details` — captura de metadados.
- `test_cleanup_tempdir_*` — utilitário de limpeza.

### Comportamento do fluxo
1. Usuário preenche campos → clica em **Update Preview** ou **Create World**.
2. Backend cria `/tmp/world-builder/<uuid>/` com arquivos JSON de configuração.
3. Executa o binário do Factorio com parâmetros oficiais, usando o temp dir como `cwd`.
4. Após sucesso, move `preview.png` para `data/world-builder/previews/` ou `save.zip` para `data/saves/`.
5. Remove completamente o diretório temporário.
6. Retorna URL/nome do arquivo ao frontend.

---

*Documento de arquitetura atualizado com a entrega completa do World Builder V1, refinamentos WB-V1.2 e WB-V1.3.1, Hotfix HF-INSTALL-03, Integração Oficial WB-V1.5 e Catálogo Oficial de Presets WB-V1.7.*

---

## 17. Implementação Backend WB-V1.7 — Catálogo Oficial de Presets

### Problema resolvido
O frontend enviava valores de preset arbitrários (ex: "normal") sem validação oficial, resultando em erro do executável: "Preset 'normal' doesn't exist".

### Solução
- **PresetCatalog** (`backend/services/preset_catalog.py`): catálogo centralizado com todos os presets oficiais suportados pela CLI do Factorio.
- Cada preset possui: `id` oficial, `label` para exibição, `description` e `planets` compatíveis.
- **Validação backend**: `WorldConfig.validate()` verifica o preset contra o catálogo antes de executar o Factorio.
- **API dinâmica**: `/api/world-builder/options` retorna presets filtrados por planeta, com metadados completos.
- **Frontend dinâmico**: select de presets carregado exclusivamente pela API; nunca valores hardcoded.
- **Nenhum parâmetro/comando alterado**: apenas validação e catálogo.

### Arquivos criados/modificados
- `backend/services/preset_catalog.py` — catálogo oficial de presets.
- `backend/services/world_config.py` — validação usa `is_valid_preset()`.
- `backend/routes/world_builder_routes.py` — usa `list_presets_for_planet()` do catálogo.
- `backend/services/world_builder_service.py` — removida função `list_presets()`.
- `frontend/static/js/world_builder.js` — select de presets carregado da API com label/tooltip.
- `backend/tests/test_world_builder_service.py` — 10 novos testes para o catálogo.
- `backend/tests/test_world_builder_routes.py` — 4 novos testes para a API de presets.

### Testes adicionados
- `test_preset_catalog_contains_expected_ids`
- `test_get_preset_returns_metadata`
- `test_get_preset_returns_none_for_invalid`
- `test_is_valid_preset`
- `test_preset_catalog_serialization`
- `test_options_presets_contain_metadata`
- `test_preview_rejects_invalid_preset`
- `test_create_world_rejects_invalid_preset`

### Estrutura do catálogo
```json
{
  "normal": {
    "id": "normal",
    "label": "Normal",
    "description": "Default world generation with standard settings.",
    "planets": ["nauvis", "vulcanus", "fulgora", "gleba", "aquilo"]
  },
  "marathon": { ... },
  "death_world": {
    "planets": ["nauvis"]
  },
  "island": {
    "planets": ["nauvis"]
  }
}
```

---

## 18. Remoção do Uso de `--preset` (WB-V1.7)

### Problema resolvido
Durante a validação do preview o backend enviava `--preset=normal`, e o executável
oficial do Factorio retornou `Preset "normal" doesn't exist`. Após revisão da
arquitetura, concluiu-se que o conceito de "Preset" não é necessário nesta primeira
versão do World Builder.

### Solução
- **Removido o campo `preset`** de `WorldConfig` (`backend/services/world_config.py`).
- **Removida a validação** de preset (`unsupported preset`) e a dependência de `preset_catalog.py`.
- **Removido o módulo `backend/services/preset_catalog.py`** (catálogo de presets).
- **Removido `--preset`** do comando do Factorio em `generate_preview()` e `create_world()`.
- **Removida a chave `presets`** da resposta de `GET /api/world-builder/options`.
- **Removido o campo Preset** da interface (`frontend/templates/index.html`, `world_builder.js`) e a chave `world_builder.preset` dos arquivos de i18n.
- **Manifesto** (`data/world-builder/manifest.json`) não recebe mais o campo `preset`.

### Arquitetura (nova diretriz)
- Nesta versão o World Builder trabalha diretamente sobre `map-gen-settings.json`,
  utilizando as configurações padrão do Factorio e a `seed` informada pelo usuário.
- Presets serão tratados futuramente apenas como **modelos de configuração**,
  carregando valores no editor, e **não** como parâmetros da linha de comando.

### Parâmetros oficiais utilizados
- **Preview**: `factorio --generate-map-preview preview.png [--map-gen-settings=...] [--map-settings=...] [--map-gen-seed=SEED] [--map-preview-size 1024] [--map-preview-planet=PLANET]`
- **Create**: `factorio --create save.zip [--map-gen-settings=...] [--map-settings=...] [--map-gen-seed=SEED]`
- **Nunca** é adicionado `--preset` ao comando.

### Arquivos modificados
- `backend/services/world_config.py` — removido campo `preset` e validação.
- `backend/services/world_builder_service.py` — removido `PRESETS`, `--preset`, e campo do manifesto/hash.
- `backend/routes/world_builder_routes.py` — removido `presets` da rota `/options` e campo `preset` das rotas.
- `backend/services/preset_catalog.py` — arquivo removido.
- `frontend/templates/index.html` — removido select de Preset.
- `frontend/static/js/world_builder.js` — removido estado/carga/envio de preset.
- `frontend/i18n/*.json` — removida chave `world_builder.preset`.
- `backend/tests/test_world_builder_service.py` — removidos testes do catálogo e asserções de `--preset`.
- `backend/tests/test_world_builder_routes.py` — removidos testes de presets/opções.
- `backend/tests/test_frontend_ui.py` — removidos asserts de campo e i18n de preset.

*Documento de arquitetura atualizado com a entrega completa do World Builder V1, refinamentos WB-V1.2 e WB-V1.3.1, Hotfix HF-INSTALL-03, Integração Oficial WB-V1.5, Catálogo Oficial de Presets WB-V1.7 e Remoção de `--preset` (WB-V1.7).*

