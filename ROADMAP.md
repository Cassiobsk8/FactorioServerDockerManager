# Roadmap

## Version 3.0

Status: World Builder V1 COMPLETED
Status: World Builder V1.2 COMPLETED
Status: World Builder V1.3.1 COMPLETED
Status: Hotfix HF-INSTALL-03 COMPLETED

Focus:

- World Builder V1
  - Create worlds with configurable parameters (World Name, Seed, Planet, Preset)
  - Generate previews using official Factorio binary (`--map-preview`)
  - Create save files (`--create`) with validation
  - Single-screen layout: 30% configuration / 70% preview
  - Explicit preview update (no auto-refresh)
  - Integrated as new SPA tab following existing Design System
- World Builder V1.2 - Seed Generator Refinement
  - Replaced "Random Seed" checkbox with "🎲 Generate" button
  - Seed is always editable; Generate button fills it with a random integer
  - `random_seed` inferred from UI (empty seed = random, filled seed = explicit)
  - No auto-preview on seed change
- World Builder V1.3.1 - Installation Validation
  - Automatic detection of real vs fake/placeholder Factorio binary
  - UI shows clear message when installation is incomplete
  - Preview and Create World disabled until real binary is present
- Hotfix HF-INSTALL-03 - Dev Environment Validation
  - Full installation validation: binary, data/, config/, --version
  - `install_server()` validates AFTER extraction and BEFORE marking complete
  - On failure: writes error to `install_progress.json` and aborts

---

## Version 2.8

Status: Architecture Frozen (Information Architecture Refactor complete)
Status: Access Control Module Frozen

Focus:

- Information Architecture Refactor (Dashboard / Saves / Console / Server Settings / About) - DONE
- Access Control (Admins, Whitelist, Banlist CRUD + UX Polish) - DONE
- Architecture stable for: World Manager, Multi-Server, Map Settings

Upcoming (post-freeze):

- World Manager
- Multi-Server
- Map Settings
- Mod Manager
- Mod Portal integration
- Backup improvements

---

## Version 2.7

Focus:

- Visual Map Generator
- World Preview
- Better World Creation

✅ Sprint 2.7.2e - Frontend Polish Preview COMPLETED

---

## Version 2.6

✅ COMPLETED

Frontend Foundation

---
