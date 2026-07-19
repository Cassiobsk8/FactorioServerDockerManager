# Changelog

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
