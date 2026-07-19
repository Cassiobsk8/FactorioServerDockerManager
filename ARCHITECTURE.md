# Architecture

This document describes the **frozen** information architecture of the
Factorio Server Manager frontend. It is the reference for where new features
belong. When contributing, place functionality in the area described below to
keep the navigation consistent and avoid scattering features across the wrong
screens.

The architecture was defined and frozen in **version 2.8.0** (Information
Architecture Refactor). After this point the top-level structure must remain
stable so that future modules can be slotted into predictable locations.

## Application

The five primary navigation areas, accessible from the sidebar tabs.

### Dashboard

**Responsibility:** Quick server operations.

Everything related to operating the server right now lives here:

- Server status and install state
- Resource metrics (CPU, RAM, disk, uptime, version)
- Active save and RCON connection summary
- Server start / stop / restart / install actions
- Inline server name editing
- Live logs

### Saves

**Responsibility:** Save management.

All world/save lifecycle operations:

- Create new world
- Upload save
- List, search and sort saves
- Select active save
- Rename, download and delete saves

### Console

**Responsibility:** RCON management.

Everything related to the RCON connection lives here (settings + console):

- RCON settings (host, port, password, timeout, test connection)
- RCON command console
- Quick actions (save world, players online, server status)
- Broadcast
- Players online list

### Server Settings

**Responsibility:** Advanced server configuration.

Grouped, collapsible configuration:

- **World** — `server-settings.json` (functional) and `map-settings.json`
- **Access Control** — Admins, Whitelist, Banlist
- **Advanced** — Server ID

#### Settings Module Card

All modules inside Server Settings must use the `.settings-module-card` CSS
component. This component centralizes:

- padding, margin and min-height
- border, border-radius and background (via `.card`)
- flex layout with consistent gap
- state styling: loading, empty, error, success, disabled

Current modules using `.settings-module-card`:

- `server-settings.json`
- `map-settings.json`
- Admins
- Whitelist
- Banlist
- Server ID

Future modules must add the `.settings-module-card` class to their root
`<section>` element.

### About

**Responsibility:** Application information.

- Project description and developer
- Licenses and credits
- Project statistics
- Support / donation

## Sidebar

**Responsibility:** Application preferences.

Fixed area at the bottom of the sidebar, always visible regardless of the
active tab:

- **Language** — interface language dropdown. Applies immediately and persists
  automatically (no Save button).

> Note: the Server Settings tab previously held Language, RCON, Server Name and
> Installation cards. Those were moved to their dedicated areas (Sidebar,
> Console, Dashboard) and removed from Server Settings during the refactor.

## Future Modules

Planned modules and where they are expected to live once implemented, based on
the frozen structure above.

### World Manager

Belongs in **Saves** (save/world lifecycle) and/or the **Server Settings →
World** group (`map-settings.json`). Covers richer world creation, map
generation and world preview.

### Access Control

Belongs in **Server Settings → Access Control** group. Covers Admins,
Whitelist and Banlist management.

### Map Settings

Belongs in **Server Settings → World** group (`map-settings.json`). Currently a
placeholder; will replace the placeholder card with the real editor.

### Multi-Server

Cross-cutting. Requires a server selector at the **Sidebar** / **Dashboard**
level and per-server scoping of Dashboard, Saves, Console and Server Settings.

### Templates

Belongs in **Saves** (save templates) and/or a new **Server Settings** group
for reusable configuration templates.

### Backups

Belongs in **Saves** (backup/restore of worlds) as a companion to save
management.

### Scheduler

Belongs in **Dashboard** (scheduled quick operations) or as a new **Server
Settings** group for automation.

---

## Contribution Guideline

Before adding a feature, ask: *which responsibility does this serve?*

- Operating the running server → **Dashboard**
- Managing worlds/saves → **Saves**
- Talking to the server via RCON → **Console**
- Changing server configuration → **Server Settings**
- Showing project/legal info → **About**
- User-facing preference (language, theme, etc.) → **Sidebar**

If a responsibility does not fit any area, propose a new top-level area rather
than overloading an existing one — but remember the top-level architecture is
**frozen**, so new areas require an explicit architecture change.
