# Changelog

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
