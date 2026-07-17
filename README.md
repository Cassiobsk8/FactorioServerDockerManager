# Factorio Server Docker Manager

This project aims to control and monitor a Factorio server installed and run inside the same container on ZimaOS.

## Current Version

**2.5.0**

**Release:** RCON Edition

## Highlights

- Persistent RCON
- Save Manager
- Dashboard
- Multi-language
- Configuration Editor

## Current scope (Level 1 MVP)

The project now includes a simple web interface for:

- Install the Factorio server inside the container
- Start server
- Stop server
- Restart server
- View logs
- Change server name
- Change server password
- Upload save files
- Download save files

## Installation sources

You can provide a local archive path or a direct URL for the Factorio server archive using the install form.

Environment variables supported:

- `FACTORIO_SERVER_ARCHIVE`: local archive path inside the container
- `FACTORIO_SERVER_ARCHIVE_URL`: download URL for the archive

## Project structure

- backend/: Flask application and Docker integration
- frontend/: templates and static assets
- docker/: Dockerfile for containerization

## How to run locally

1. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. Start the application:
   ```bash
   python backend/app.py
   ```
3. Open http://localhost:5000

## Automated tests

Run the test suite with:

```bash
pytest -q backend/tests
```

This coverage includes config persistence, save file handling, extraction normalization, and platform startup guards.

## Notes for ZimaOS

The app expects a Docker container named `factorio` by default. You can override it with the environment variable `FACTORIO_CONTAINER_NAME`.

For a real deployment, the container must be created and started before the manager can control it.
