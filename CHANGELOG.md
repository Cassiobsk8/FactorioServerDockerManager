# Changelog

## 3.0.0 - World Builder V1

Status: Epic World Builder V1 Completed

### Added

- World Builder feature (Epic World Builder V1)
- Backend service `backend/services/world_builder_service.py` with `generate_preview()` and `create_world()`
- Backend model `backend/services/world_config.py` (`WorldConfig` dataclass)
- Backend blueprint `backend/routes/world_builder_routes.py` with routes:
  - `GET /api/world-builder/options` — planets and presets
  - `POST /api/world-builder/preview` — generate map preview via official Factorio binary
  - `POST /api/world-builder/create` — create save from configuration
  - `GET /api/world-builder/preview-image/<hash>` — serve generated preview PNG
- Frontend module `frontend/static/js/world_builder.js` with `updatePreview`, `createWorld`, `markPreviewOutdated`
- New SPA tab "World Builder" in sidebar navigation
- Layout split: 30% configuration (left) / 70% preview (right)
- Fields: World Name, Seed, Random Seed toggle, Planet select
- Preview status badges: Updated / Outdated / Generating / Error
- World Builder i18n keys across 4 locales (`en`, `pt_BR`, `es`, `zh_CN`)
- CSS classes: `.world-builder-layout`, `.world-builder-preview`, `.world-builder-preview-image`, `.checkbox-row`

### Changed

- `backend/app.py` — registered `world_builder_routes` blueprint
- `frontend/templates/index.html` — added World Builder tab and panel
- `frontend/static/js/app.js` — tab switch handler refreshes World Builder options
- `frontend/static/css/app.css` — added World Builder layout and preview styles
- `backend/version.py` — bumped to 3.0.0

### Validation

- Backend: 281 passed
- Frontend UI: 17 passed
- World Builder service: 12 passed
- World Builder routes: 8 passed
- No regressions detected

---

## 3.0.0 - WB-HF-01 - Corrigir movimentação de arquivos entre filesystems

Status: Hotfix Completed

### Fixed

- Movimentação de arquivos gerados pelo World Builder agora usa `shutil.move()` em vez de `Path.replace()`
- Eliminado `OSError: [Errno 18] Invalid cross-device link` ao mover previews e saves entre `/tmp` e volume Docker

### Architecture

- Criado helper privado `_move_generated_file(source, destination)` em `backend/services/world_builder_service.py`
- Helper cria diretórios de destino automaticamente, preserva o nome do arquivo e lança exceções padronizadas
- Toda movimentação de previews e saves agora utiliza exclusivamente o helper

### Validation

- Backend: 21 passed
- No regressions detected

---

## 3.0.0 - WB-HF-02 - Servir previews através de rota dedicada

Status: Hotfix Completed

### Fixed

- Previews agora são servidos através de rota dedicada `/api/world-builder/preview-image/<hash>.png`
- Eliminado HTTP 404 ao acessar previews, que antes retornavam `/static/world-builder/previews/<hash>.png` (fora do `static_folder`)

### Architecture

- Rota `GET /api/world-builder/preview-image/<preview_hash>` usa `send_from_directory()` com `PREVIEWS_DIR`
- `generate_preview()` retorna URL da rota dedicada tanto para previews existentes quanto para recém-gerados
- Previews são artefatos de tempo de execução e não fazem parte do `static_folder`

### Validation

- Backend: 320 passed
- Frontend UI: 18 passed
- No regressions detected

---

## 3.0.0 - WB-HF-04 - Normalizar hash do preview na rota de download

Status: Hotfix Completed

### Fixed

- Corrigido HTTP 404 na rota `/api/world-builder/preview-image/<hash>` causado por duplicação da extensão `.png`
- Rota agora aceita tanto `/api/world-builder/preview-image/<hash>` quanto `/api/world-builder/preview-image/<hash>.png`

### Architecture

- Rota normaliza `preview_hash` removendo sufixo `.png` antes de montar o caminho do arquivo
- Compatibilidade mantida com clientes que utilizam qualquer um dos formatos

### Validation

- Backend: 321 passed
- Frontend UI: 18 passed
- No regressions detected

---

## 3.0.0 - World Builder V1.2 - Seed Generator Refinement

Status: Refinement Completed

### Changed

- Replaced "Random Seed" checkbox with "🎲 Generate" button next to Seed field
- Seed is now always editable; clicking "Generate" fills it with a random integer (0-999999999)
- `random_seed` is inferred from the UI: `true` when Seed is empty, `false` when Seed has a value
- No automatic preview generation on seed change; preview is marked as outdated instead
- Added `.seed-row` CSS class for inline input + button layout
- Updated i18n: added `world_builder.generate_seed`, removed `world_builder.random_seed`

### Validation

- Backend: 281 passed
- Frontend UI: 17 passed
- No regressions detected

---

## 3.0.0 - World Builder V1.3.1 - Installation Validation

Status: Investigation + Fix Completed

### Added

- Automatic detection of real vs fake/placeholder Factorio binary
- Backend validation: `validate_factorio_binary()` checks ELF magic bytes (`\x7fELF`)
- New API endpoint: `GET /api/world-builder/status` returns installation validity
- Frontend status banner shown when installation is invalid or incomplete
- Preview, Create World, and Generate Seed buttons are disabled when installation is invalid

### Changed

- `backend/services/world_builder_service.py` — `generate_preview()` and `create_world()` now validate binary before execution
- `backend/routes/world_builder_routes.py` — added `/api/world-builder/status` endpoint
- `frontend/static/js/world_builder.js` — added `checkWorldBuilderStatus()`; disables UI on invalid installation
- `frontend/templates/index.html` — added `#wb-status-banner`
- `frontend/static/css/app.css` — added `.world-builder-status-banner`
- `frontend/i18n/*.json` — added `world_builder.status.unavailable` and `world_builder.status.unavailable_detail`

### Validation

- Backend: 288 passed
- Frontend UI: 23 passed
- No regressions detected

---

## 3.0.0 - World Builder WB-V1.7 - Remoção do Uso de `--preset`

Status: Refinement Completed

### Removed

- `preset` field from `WorldConfig` (`backend/services/world_config.py`)
- Preset validation (`unsupported preset`) and dependency on `preset_catalog.py`
- `backend/services/preset_catalog.py` module entirely
- `--preset` argument from the Factorio command in both `generate_preview()` and `create_world()`
- `presets` key from `GET /api/world-builder/options` response
- Preset field from the interface (`frontend/templates/index.html`, `world_builder.js`)
- `world_builder.preset` i18n key from all 4 locales (`en`, `pt_BR`, `es`, `zh_CN`)

### Changed

- World Builder now works directly over `map-gen-settings.json` using Factorio's default settings and the user-provided seed
- Frontend no longer sends `preset` in `/api/world-builder/preview` or `/api/world-builder/create` requests

### Architecture

- Presets are no longer passed as command-line parameters to the Factorio executable
- Future presets will be treated only as configuration templates loading values into the editor

### Validation

- Backend: 314 passed
- Frontend UI: 23 passed
- No regressions detected

---

Status: Hotfix Completed

### Added

- Full installation validation in `backend/services/factorio_service.py`:
  - Checks `bin/x64/factorio` exists and is executable
  - Checks `data/` directory exists
  - Checks `config/` directory exists
  - Runs `factorio --version` and validates return code
- `validate_installation()` returns `{valid, binary, data_dir, config_dir, version}`
- `install_server()` now calls `validate_installation()` AFTER extraction and BEFORE marking `status=complete`
- On validation failure: writes `status=error` to `install_progress.json` and aborts installation

### Changed

- `backend/services/factorio_service.py` — `install_server()` validates installation before completion; `_extract_archive()` no longer marks complete
- `backend/tests/test_server_lifecycle_regression.py` — updated install test to include `data/` and `config/` dirs and `--version`-capable fake binary; added 6 new validation tests

### Validation

- Backend: 294 passed
- No regressions detected

---

## 2.8.7 - LogViewer ReferenceError Fix (Hotfix H7.2B)

Status: Resolved

### Root Cause

A instrumentação em `_apply()`/`update()` (`frontend/static/js/log_viewer.js`)
identificou objetivamente a causa raiz: `ReferenceError: strSlice is not defined`
lançado dentro de `_computeNewContent()` em todo poll com crescimento de log.

A implementação do helper de fatiamento era `strSliceImpl(...)`, mas os dois
pontos de chamada em `_computeNewContent()` usavam `strSlice(...)` — um erro de
rename: o nome da chamada não foi atualizado para a implementação existente.
Como `_computeNewContent()` rodava antes de `this._lastText = nextText`, o erro
impedia a atualização de `_lastText` e o DOM não era alterado; o polling parava
de refletir qualquer novo conteúdo após o primeiro append/edição divergente.

### Changed

- `frontend/static/js/log_viewer.js` — renomeadas as duas chamadas em
  `_computeNewContent()` de `strSlice(...)` para `strSliceImpl(...)`, casando
  com a única implementação existente. Nome consistente em todo o arquivo;
  nenhum wrapper ou função duplicada criada.
- `backend/tests/test_log_viewer.py` — adicionada regressão
  `test_compute_new_content_uses_defined_symbols` garantindo que todo
  `strSlice(` é `strSliceImpl(` (sem símbolo inexistente) e que os caminhos
  de append/edição divergente produzem o `diff` correto e atualizam
  `this._lastText` + DOM.

### Validation

- Backend: 254 passed.
- LogViewer: 17 passed (inclui a nova regressão H7.2B).
- Esperado pós-correção confirmado pela instrumentação: nenhum `ReferenceError`;
  `this._lastText` passa de `0` para `nextText.length`; `DOM BEFORE` →
  `DOM AFTER` indica mudança.

## 2.8.7 - Live Log Polling Investigation (Hotfix H7.2)

Status: Resolved

### Root Cause

O Live Log parou de atualizar continuamente após o H7.1 porque o método
`_apply` de `frontend/static/js/log_viewer.js` acessava `diff.appended.length`
mesmo no caminho de *full replace* (`diff.fullReplace === true`), onde
`diff.appended` é `undefined`. Isso lançava um `TypeError` silencioso dentro da
cadeia de promises do `fetch`, que era engolido por `_tickCatch`. Como o erro
impedia `this._lastText = nextText` de executar, o estado interno ficava
"travado" no conteúdo antigo: todo poll seguinte recomputava contra o
`_lastText` obsoleto, repetia o *full replace* e relançava o erro — o polling
morria permanentemente após a primeira atualização divergente (linha reescrita
in-place, rotação, etc.). O primeiro carregamento funcionava porque é tratado
pelo branch `_lastText === ''`.

### Changed

- `frontend/static/js/log_viewer.js` — `_apply` agora faz branch apenas em
  `diff.fullReplace` e só referencia `diff.appended` dentro do branch
  `else` (onde ele sempre existe). `this._lastText` é atualizado em todos os
  caminhos, então o polling nunca mais "trava".
- Backend confirmado íntegro: `LogManager.read_server_log()` / `read_active_log()`
  relê o arquivo físico a cada chamada (`_read` → `path.read_text()`), sem cache
  em memória e sem file handles persistentes. Endpoints `/logs/data` e
  `/api/logs` continuam sendo chamados periodicamente via `setInterval`.

### Validation

- `backend/tests/test_log_viewer.py`: harna JS→Python corrigido para a versão
  atual do `log_viewer.js`; adicionados testes de regressão para atualização
  contínua após update divergente, crescimento do log, no-op entre polls e
  sessão longa (150 ticks) sem perda de linhas.
- `backend/tests/test_log_manager.py`: adicionados testes confirmando releitura
  do arquivo físico a cada `read_server_log()` / `read_active_log()`.
- Backend: 253 passed.

## 2.8.7 - Official Log Routing (Hotfix H7)

Status: Resolved

### Added

- `backend/services/log_manager.py` — `LogManager` centraliza todos os arquivos de log (install, server, crash, runtime). Aplicação acessa logs apenas via `LogManager` / `get_log_manager()`.
- Servidor iniciado com o parâmetro oficial `--console-log=<logs/server.log>` como origem principal dos logs (`StartupConfiguration.console_log`, emitido por `RuntimeStartupBuilder`).
- `LogManager.migrate_existing_installation()` migra instalações existentes preservando `logs/server.log` e importando `factorio-current.log` / `factorio-previous.log` (sem perda de logs antigos).
- `LogManager.rotate()` prepara rotação futura por tamanho (contrato de rotação documentado).

### Changed

- `factorio_service.start_server()` não redireciona mais stdout/stderr; o Factorio escreve diretamente via `--console-log`.
- `get_logs()`, `clear_logs()`, `log_error()`, `begin_install_logging()`/`end_install_logging()` e `clear_installation()` roteados pelo `LogManager`.
- `config.py`: novos caminhos `crash.log` e `runtime.log`; nomes de log extraídos para constantes.
- `backend/version.py`: 2.8.0 → 2.8.7 ("Official Log Routing").

### Validation

- Testes de `LogManager` (17): criação automática, leitura, append, clear por fase, rotação e compatibilidade/migração. Backend: 219 passed.

## 2.8.1 - Access Control Freeze

Status: Module Frozen (Tarefa 5/5)

Sprint 2.8.1 / Tarefa 5/5 - Access Control Freeze

### Validation

- Backend: `access_control_service` covers read/write for admins, whitelist, banlist with dedupe, trim, sort and file cleanup.
- API: `GET /api/access-control`, `POST /api/access-control/<list_key>`, `DELETE /api/access-control/<list_key>` validated.
- Frontend: Access Control cards render state, count, records, empty state, loading state, errors and add/remove interactions.
- Internationalization: all 4 locales (en, pt_BR, es, zh_CN) include `access_control.*` and `confirm.remove_access` keys.
- Responsiveness: `settings-group-body` collapses to 1 column at 980px; access control cards inherit the grid behavior.
- Design System: cards use centralized tokens (`--spacing-*`, `--radius-*`, `--border`, `--text`, `--subtext`, `--accent`, `--success`, `--color-danger-light`, `--badge-offline-*`).
- Tests: 15 access-control tests pass (service + CRUD).

### Freeze

Access Control module is stable and ready for production use.

Sprint 2.8.1 / Tarefa 4/5 - Access Control UX Polish

### Added

- Loading state: animated 3-dot indicator per card during initial load and add/remove operations; inputs and buttons disabled while loading.
- Removal confirmation: `confirm()` dialog before deleting an entry, with friendly message including list title and player name.
- Friendly error messages: backend errors (duplicate, not found, empty) mapped to localized user-facing messages.
- i18n keys: `access_control.error.duplicate`, `access_control.error.not_found`, `confirm.remove_access` (en/pt_BR/es/zh_CN).
- Empty state copy refined to friendly tone ("No entries yet" / "Nenhuma entrada ainda").

### Changed

- No functional changes; only UX/UI polish on top of existing CRUD foundation.

## 2.8.1 - Access Control Foundation

Sprint 2.8.1 / Tarefa 3/5 - Access Control CRUD

### Added

- Backend write layer in `access_control_service`:
  - `add_to_list(key, name)` — trims, rejects empty, rejects duplicates, auto-sorts, persists (creates file if missing)
  - `remove_from_list(key, name)` — removes entry, deletes file when last entry removed
  - Serialization keeps correct shape per list (adminlist `{"admins":[...]}`, whitelist/banlist arrays)
- API endpoints: `POST /api/access-control/<list_key>` (add) and `DELETE /api/access-control/<list_key>` (remove)
- Frontend CRUD in Access Control cards:
  - Per-item remove (×) button
  - Add row with input + Save + Cancel (Enter adds, Escape cancels)
  - Error messages for empty/duplicate/failed operations
- i18n keys: `access_control.name_placeholder`, `access_control.save`, `access_control.cancel`, `access_control.remove`, `access_control.error.empty`, `access_control.error.failed` (en/pt_BR/es/zh_CN)
- CSS for add row, input, save/cancel buttons and remove button
- Backend tests for the CRUD layer

### Validation

- No duplicates (rejected both in backend and frontend context)
- Extra spaces trimmed automatically
- Records auto-sorted on write
- Internationalized (all 4 locales)

Sprint 2.8.1 / Tarefa 2/5 - Read Access Lists

### Added

- Access Control cards now display the list contents (names) for Admins, Whitelist and Banlist
- Read-only list rendering with empty state ("No entries") when a valid file has zero records
- i18n key `access_control.empty` (en/pt_BR/es/zh_CN)
- CSS for `.access-control-list`, `.access-control-item`, `.access-control-empty`

### Notes

- Still read-only: lists are displayed but not editable (editing planned for a later sprint).
- Names are rendered as text content (no HTML injection).

Sprint 2.8.1 / Tarefa 1/5 - Access Control Foundation

### Added

- Read-only backend layer for Access Control lists (`access_control_service`):
  - Locates, reads and validates `server-adminlist.json`, `server-whitelist.json`, `server-banlist.json`
  - Returns record count, file existence, validity and error messages
  - Accepts both legacy (array) and object (`admins`/`bans`) Factorio formats
- API endpoint `GET /api/access-control` returning admins/whitelist/banlist status
- Frontend Access Control cards (Admins, Whitelist, Banlist) in Server Settings:
  - Real cards replacing placeholders
  - Read-only: show record count, file state (loaded / not found / invalid) and error messages
  - Auto-refresh every 5s via `access_control.js`
- i18n keys `access_control.state.ok|missing|invalid` (en/pt_BR/es/zh_CN)
- Config paths `ADMINLIST_PATH`, `WHITELIST_PATH`, `BANLIST_PATH` in `backend/config.py`
- Tests for the access control service

### Notes

- Read-only by design: no file is edited or written, no save action.
- Missing files are a valid state (not an error); only malformed JSON or wrong shape is flagged invalid.
- Editing capabilities are planned for a later Access Control sprint.

## 2.8.0 - Information Architecture Refactor

Status: Architecture Frozen (Tarefa 6/6)

Sprint 2.8.0 / Tarefa 1/6 - Information Architecture Refactor

### Changed

- Navigation reorganized into 5 areas: Dashboard, Saves, Console, Server Settings, About
- Renamed `Status` tab to `Dashboard` (quick server operations)
- Renamed `Configuração/Configuration` tab to `Server Settings` (advanced server config)
- Moved all RCON responsibility (settings + console) into the new `Console` tab
- i18n keys renamed: `menu.status` -> `menu.dashboard`, `menu.config` -> `menu.server_settings`, added `menu.console`
- `backend/version.py` bumped to 2.8.0

### Notes

- No functionality was removed in this task; only navigation responsibilities were reorganized.
- Saves, Console, Server Settings and About contents preserved as-is.

Sprint 2.8.0 / Tarefa 2/6 - Sidebar Preferences

### Added

- Fixed `Preferences` area at the bottom of the Sidebar
- Language dropdown in the Sidebar that applies immediately and persists automatically (no Save button)
- i18n key `preferences.title`

### Notes

- Old language form in `Server Settings` was intentionally kept (removal happens after validation).
- Selecting a language in either the Sidebar or Server Settings updates both and persists via `/api/settings`.

Sprint 2.8.0 / Tarefa 4/6 - Server Settings Refactor

### Added

- Server Settings tab restructured into collapsible groups:
  - `General` (open): language, server install, general config
  - `World` (open): `server-settings.json` (functional) + `map-settings.json` placeholder
  - `Access Control`: Admins, Whitelist, Banlist placeholders
  - `Advanced`: Server ID placeholder
- i18n keys: `settings.group.general`, `settings.group.world`, `settings.group.access_control`, `settings.group.advanced`, `config.map_settings_title`, `config.admins_title`, `config.whitelist_title`, `config.banlist_title`, `config.server_id_title`, `config.placeholder_coming_soon`

### Changed

- Server Settings panel now uses `.settings-groups` block layout instead of `.config-grid`

### Removed

- Unused `.config-grid` CSS rule

### Notes

- Only the visual structure was implemented. Map Settings, Access Control and Advanced remain placeholders with no functionality.
- All existing functionality (language, install, config, server-settings.json) preserved within the new `General`/`World` groups.

Sprint 2.8.0 / Tarefa 5/6 - Configuration Cleanup

### Removed

- Language card from Server Settings (moved to Sidebar Preferences in Tarefa 2/6)
- RCON card from Server Settings (moved to Console tab in Tarefa 1/6)
- Server name / password config card from Server Settings (server name moved to Dashboard hero inline edit; now redundant in settings)
- Installation card (archive URL + install/delete) from Server Settings (install available via Dashboard hero actions)
- Dead `saveLanguageForm` and `#language-form` handler from `config.js`
- Orphaned i18n keys: `config.server_title`, `config.installed`, `config.archive_url`, `config.archive_url_placeholder`, `config.install_button`, `config.delete_install`, `config.confirm_delete_install`, `config.general_title`, `config.server_name`, `config.server_password`, `config.save_changes`, `settings.group.general`
- `General` group merged into `World` group in Server Settings

### Notes

- All removed functionality remains available: Language (Sidebar), RCON (Console), Server name (Dashboard hero), Installation (Dashboard hero actions).
- Server Settings tab now contains only: World (server-settings.json + map-settings.json placeholder), Access Control (placeholders), Advanced (placeholder).
- The install modal and its guarded JS were intentionally kept (still functional, not part of the removed cards).

Sprint 2.8.0 / Tarefa 6/6 - Architecture Freeze

### Validation

- Navigation: 5 tabs (Dashboard, Saves, Console, Server Settings, About) correctly mapped to 5 panels.
- Dashboard: status, metrics, hero actions, logs, active-save, RCON status card intact.
- Saves: create/upload/list/rename/delete/download/search preserved.
- Console: RCON console + quick actions + broadcast + players + RCON settings intact.
- Server Settings: World (server-settings.json + map-settings.json), Access Control, Advanced groups present.
- Sidebar: nav + fixed Preferences (Language) area, persists automatically.
- About: hero, developer, project, support, licenses, stats intact.
- Internationalization: 4 locales (en/pt_BR/es/zh_CN) valid JSON; all template + JS i18n keys resolve; added missing `dashboard.title` to en.json.
- Responsiveness: breakpoints at 420/640/900/980/1100px; settings-group-body collapses to 1 column at 980px.
- Design System: centralized CSS tokens (colors, spacing, radius, shadow, transition, typography) intact.
- Removed dead `language-select` reference from `i18n.js` (sidebar now owns language select).

### Freeze

Architecture is stable and ready for upcoming features: World Manager, Multi-Server, Access Control, Map Settings.

## 2.7.0 - Frontend Polish

### Added

- Rich Saves Table with status badges, metadata and action menu
- Saves Toolbar with search and sort placeholders
- Quick Server Rename inline editing on Dashboard Hero Card
- `/api/server-name` endpoint for server name persistence
- New i18n keys for saves, status states and server name editing

### Changed

- Saves table layout redesigned with modern card styling
- Action buttons consolidated into dropdown menu (Select, Rename, Download, Duplicate, Delete)
- Partial DOM updates for saves list during polling (performance improvement)
- RCON status card restructured to match Active Save card layout
- Log panel now occupies full remaining viewport height with internal scroll
- Status translations now use `status.state.*` keys instead of raw values
- Design System tokens enforced across saves table spacing and typography

### Fixed

- Save action menu hitbox now responds to clicks on the entire button area
- Save action menu remains open during automatic polling
- Download action no longer navigates to `/download-save/undefined`
- Server status translation fallback displaying `status.state.not_installed`
- Save row alignment consistency across active/inactive saves
- CSS dead code and unused variables removed
- JavaScript dead code removed (`formatComment`, `logsInterval`, unused `meta` variable)
- i18n cleanup: removed unused keys, added missing translations
- config.js brace balance fixed

### Security

- Removed exposure of internal backend error messages in frontend alerts

## 2.6.1 - Frontend Polish Preview

### Changed

- Dashboard reorganizado
- Hero Card redesenhado
- Cards de Save e RCON incorporados ao Hero
- Logs em largura total
- Botões contextuais
- Status internacionalizados
- Botão "Parar" com estilo Danger
- Dashboard preparado para futura arquitetura Multi-Server

### Fixed

- Hierarquia visual do Dashboard
- Espaçamentos
- Traduções de estados
- Consistência visual

## 2.6.0 - Frontend Foundation

### Added

- Frontend modular architecture
- Dedicated install.log
- Dedicated server.log

### Changed

- JavaScript separated into modules
- CSS extracted from template
- Backend log routing
- Centralized frontend bootstrap

### Fixed

- Configuration layout regression
- Dashboard polling
- RCON Test Connection
- Installation log history
- Active tab navigation
- Server log handling

### Removed

- Inline JavaScript
- Inline CSS
- Shared installation/server log

## 2.5.0 - RCON Edition

### Added

- Complete Source RCON support
- Persistent RCON connection
- Players Online
- Broadcast
- Save via RCON
- Connection monitoring
- Automatic reconnect
- Improved logging
- Internationalization
- Dashboard redesign
- Save Manager
- Configuration editor
- About page redesign

### Changed

- Unified RCON state management
- Frontend synchronization
- Persistent connection architecture
- Configuration UI
- Logging format

### Fixed

- Multiple RCON reconnect issues
- Badge synchronization
- Polling behavior
- HTTP status endpoint
- Connection state inconsistencies
- Frontend status bugs
- Legacy RCON issues

### Removed

- Legacy RCON methods
- Duplicate status logic
- Dead code
- Unused helpers
