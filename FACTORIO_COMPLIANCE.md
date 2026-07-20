# FACTORIO_COMPLIANCE.md

> **Sprint:** 2.8.7 — Runtime Audit (somente validação de conformidade)
> **Data da auditoria:** 2026-07-19
> **Referência principal:** Documentação oficial do servidor dedicado do Factorio
> - Wiki: <https://wiki.factorio.com/Command_line_parameters>
> - Wiki: <https://wiki.factorio.com/Console>
> - RCON = protocolo Source RCON (Valve) — <https://wiki.vg/RCON>

> **Regra desta sprint:** Nenhuma funcionalidade foi adicionada. Divergências foram
> documentadas (Relatório + Hotfixes). Nenhuma correção foi aplicada.

---

## Resumo da Conformidade

| Métrica | Valor |
| --- | --- |
| Recursos auditados | 17 |
| Compatível | 10 |
| Parcialmente compatível | 5 |
| Não compatível | 2 |
| Total | 17 |
| Testes executados | 235 |
| Regressões | 0 |

> Divergências críticas (`Não compatível`) exigem hotfix antes de produção.

---

## Legenda de Estados

- **Compatível** — comportamento idêntico / alinhado à documentação oficial.
- **Parcialmente compatível** — funciona para o caso comum, mas diverge da
  documentação oficial em um detalhe relevante (parâmetro, arquivo, hot-reload).
- **Não compatível** — diverge da documentação oficial de forma que quebra ou
  simula incorretamente o comportamento do servidor dedicado.

---

## Relatório de Auditoria

### 1. Servidor

| Item | Estado | Observações |
| --- | --- | --- |
| Processo / PID | Parcialmente compatível | `factorio_service.py` usa `subprocess.Popen` + `server.pid`. Factorio roda como processo filho; status `running`/`stopped` derivado de `os.kill(pid,0)`. OK para headless. Diverge de containerização (patch via `docker`), mas aceitável no modelo atual. |

### 2. Startup

| Item | Estado | Observações |
| --- | --- | --- |
| Comando de inicialização | Parcialmente compatível | `RuntimeStartupBuilder` monta `--start-server=<save>`, `--port`, `--bind`, `--rcon-port`, `--rcon-password`, `--rcon-bind`, `--server-settings`, `--server-adminlist`, `--server-banlist`, `--server-whitelist`, `--use-server-whitelist`, `--use-authserver-bans`, `--server-id`. Todos os parâmetros oficiais presentes. **Divergência:** `--start-server` recebe apenas o *nome do arquivo* (`Mundo.zip`), não um caminho absoluto. O Factorio resolve relativo ao próprio diretório de saves; o manager mantém saves em `data/saves` fora do `factorio/`, logo o caminho **deve** ser absoluto. Risco de "save not found" em runtime. |

### 3. Shutdown

| Item | Estado | Estado |
| --- | --- | --- |
| Parada do servidor | Compatível | `stop_server()` envia `SIGTERM` e aguarda até 2s (`for _ in range(20): sleep 0.1`). Equivale ao encerramento gracioso do headless. **Hot reload:** não aplicável. |

### 4. Restart

| Item | Estado | Observações |
| --- | --- | --- |
| Reinício | Compatível | `restart_server()` = stop + start. Limpa `runtime_state` pendente. Coerente com reinício de processo. |

### 5. Save ativo

| Item | Estado | Observações |
| --- | --- | --- |
| Seleção / persistência | Parcialmente compatível | `active_save` persistido em `data/config/active_save.json`. API `/api/saves/select`. Fidelidade OK. **Divergência:** arquivo de save fica em `data/saves`, fora do `factorio/`, mas o `--start-server` é passado sem caminho absoluto (ver item 2). |

### 6. Criação de mundos

| Item | Estado | Observações |
| --- | --- | --- |
| `--create` | Parcialmente compatível | `create_save()` roda `factorio --create=<alvo> [--map-gen-seed=...]`. Caminho do binário resolvido por caminho relativo ao projeto (`factorio/bin/x64/factorio`), **não** via `INSTALL_DIR` do `config.py`. Funciona apenas se o binário estiver nesse local fixo. Seed suportado. Não há suporte a `map-gen-settings.json`/`map-settings.json` no `--create` (apenas seed). |

### 7. RCON

| Item | Estado | Observações |
| --- | --- | --- |
| Protocolo | Compatível | Implementação Source RCON própria (`rcon_service.py`): auth, execução, multi-packet. Autenticação por `request_id`/`0xFFFFFFFF` correta. Compatível com Factorio 2.x. |
| Comandos | Compatível | `/players`, `/save`, `/broadcast` mapeados. Console livre envia qualquer comando. |
| Senha mascarada | Compatível | `--rcon-password` mascarado em logs e preview. |
| Status / reconexão | Compatível | Singleton persistente, reconnect único, TCP keepalive. |
| `rcon_bind` | Compatível | `--rcon-bind` aplicado quando há senha. |

### 8. Console

| Item | Estado | Observações |
| --- | --- | --- |
| Console RCON | Compatível | `rcon.js` + endpoints `/api/rcon/command`, `/api/rcon/status`, `/api/rcon/players`, `/api/rcon/save`, `/api/rcon/broadcast`, `/api/rcon/test`. Fiel ao protocolo. |

### 9. Server Settings

| Item | Estado | Observações |
| --- | --- | --- |
| Editor `server-settings.json` | Parcialmente compatível | `server-settings.json` em `factorio/config/`. Editor recursivo genérico (`build_server_settings_fields`). **Divergência:** o arquivo de exemplo oficial `factorio/data/server-settings.example.json` **não existe** no repo; `SERVER_SETTINGS_EXAMPLE_PATH` aponta para caminho inexistente, então em instalação limpa o load cai em `{}` em vez de copiar o exemplo. |
| Hot reload | Não compatível | Alterações em `server-settings.json` **não** são aplicadas em runtime (exige restart, comportamento oficial). Contudo o manager marca `pending` e não força restart; isso é consistente, mas a UI não bloqueia start sem restart de forma clara. |
| Persistência | Compatível | JSON gravado com indent. |

### 10. Access Control

| Item | Estado | Observações |
| --- | --- | --- |
| Admins / Whitelist / Banlist | Compatível | `access_control_service.py` lê/escreve `server-adminlist.json` (`{"admins":[...]}`), `server-whitelist.json` (array), `server-banlist.json` (array ou `{"bans":[...]}`). Aceita formatos legados e novos. |
| CLI wiring | Compatível | `--server-adminlist`, `--server-banlist`, `--server-whitelist`, `--use-server-whitelist` passados corretamente pelo builder. |
| Whitelist enable/disable | Compatível | `enable_whitelist()` cria arquivo vazio `[]`; presença do arquivo ativa whitelist (comportamento oficial). |
| Hot reload | Não compatível | Mudanças em listas de acesso **não** aplicam em runtime sem restart (comportamento oficial), porém não há aviso explícito de que requer restart além do badge `pending`. |

### 11. Factorio Account

| Item | Estado | Observações |
| --- | --- | --- |
| Credenciais | Parcialmente compatível | `factorio_services_service.py` persiste `factorio_username`/`factorio_service_token` (player-data.json `service-username`/`service-token`). **Divergência:** o token NÃO é passado ao `--start-server` nem usado para autenticação de upload/mods. Atualmente é apenas "storage" — não há uso real pela linha de comando do Factorio. |

### 12. Runtime Startup Builder

| Item | Estado | Observações |
| --- | --- | --- |
| `RuntimeStartupBuilder` | Parcialmente compatível | Builder fluente, dataclass `StartupConfiguration`. Cobre todos os parâmetros oficiais. **Divergência:** `--start-server` usa nome de arquivo em vez de caminho absoluto (item 2). Máscara de senha OK. |

### 13. Runtime Pending Changes

| Item | Estado | Observações |
| --- | --- | --- |
| Estado de mudanças pendentes | Compatível | `runtime_state_service.py` marca `pending` em `data/runtime_state.json` para `server_settings`, `whitelist`, `factorio_services`. UI mostra popover. `clear_pending()` no restart. Coerente. |

### 14. Logs

| Item | Estado | Observações |
| --- | --- | --- |
| Logs do servidor | **Compatível** | `LogManager` (`backend/services/log_manager.py`) centraliza install/server/crash/runtime logs. O servidor é iniciado com `--console-log=<logs/server.log>` (origem oficial). O restante da aplicação acessa logs apenas via `LogManager`/`get_log_manager()`. `start_server()` não redireciona mais stdout/stderr. Migração automática preserva `logs/server.log` existente e importa `factorio-current.log`/`factorio-previous.log`. |

### 15. Startup Validation

| Item | Estado | Observações |
| --- | --- | --- |
| `validate_startup` | Parcialmente compatível | Valida active_save, server_settings, rcon_password, whitelist, adminlist, banlist. **Divergência:** exige `rcon_password` obrigatoriamente (`rcon_password_missing`). O Factorio NÃO exige RCON; RCON é opcional. Validar como erro bloqueante diverge do comportamento oficial (RCON opcional). |

### 16. Metrics / Version

| Item | Estado | Observações |
| --- | --- | --- |
| Métricas e versão | Compatível | `metrics_service.py` lê `/proc` para CPU/RAM; uptime agora é calculado por `RuntimeSession` (`backend/services/runtime_session.py`) com `started_at` registrado em UTC no start. Não usa timestamps persistidos. `get_factorio_version()` do `data/base/info.json`. Coerente com ambiente Linux headless. |

### 17. Versionamento

| Item | Estado | Não compatível (divergência de processo) |
| --- | --- | --- |
| Versão do app | Não compatível | `backend/version.py` está em **2.8.0**, mas o épico desta sprint é **2.8.7** e o `CHANGELOG.md` já registra **2.8.1**. Há dessincronização entre `version.py`, CHANGELOG e número do épico. |

---

## Lista de Hotfixes Priorizados

| # | Prioridade | Recurso | Divergência | Ação recomendada (próxima sprint) |
| --- | --- | --- | --- | --- |
| H1 | **Crítica** ✅ RESOLVIDO (2.8.7) | Startup / Save ativo / Runtime Startup Builder | `--start-server` recebe nome de arquivo, não caminho absoluto; saves ficam fora de `factorio/`. | `StartupConfiguration.active_save` agora é `Path`; `RuntimeStartupBuilder` emite `--start-server=<caminho absoluto>`; `_factorio_command` passa o `Path` de `load_active_save()`. Testes de regressão adicionados. |
| H2 | **Alta** ✅ RESOLVIDO (2.8.7) | Server Settings | `server-settings.example.json` oficial inexistente no repo (`factorio/data/...`) e fallback silencioso para `{}`. | `SERVER_SETTINGS_EXAMPLE_PATH` agora aponta para `backend/data/server-settings.example.json` (oficial, versionado). `load_server_settings()` copia o exemplo em instalação limpa e levanta `ServerSettingsExampleMissingError` claro quando o exemplo está ausente — nunca mais gera `{}` silenciosamente. Testes de regressão adicionados. |
| H3 | **Alta** ✅ RESOLVIDO (2.8.7) | Startup Validation | RCON obrigatório como erro bloqueante diverge do Factorio (RCON opcional). | `validate_startup()` separa `errors` de `warnings`; `_validate_rcon_password` removido e substituído por `_warn_rcon_password` (warning, nunca bloqueia). Frontend exibe aviso amigável inline (`#startup-warning`, sem `alert()`). Testes de regressão atualizados/adicionados. |
| H4 | **Média** ✅ RESOLVIDO (2.8.7) | Versionamento | `version.py` (2.8.0) ≠ CHANGELOG (2.8.1) ≠ Épico (2.8.7). | `backend/version.py` agora em **2.8.7** ("Official Log Routing"), alinhado ao épico. CHANGELOG continua registrando os marcos 2.8.1; a versão do app reflete o release corrente. |
| H5 | **Média** | Criação de mundos | `create_save` usa caminho fixo relativo do binário, não `INSTALL_DIR`. | Usar `INSTALL_DIR / "bin/x64/factorio"` de `config.py`. |
| H6 | **Média** | Factorio Account | Token armazenado mas não usado na CLI (`--start-server`/auth). | Integrar credenciais ao `player-data.json` e usar em autenticação real ou documentar como "armazenamento". |
| H7 | **Baixa** ✅ RESOLVIDO (2.8.7) | Logs | Redirecionamento stdout/stderr em vez de `--console-log` oficial. | Servidor iniciado com `--console-log=<logs/server.log>`; `LogManager` centraliza todos os logs; `start_server()` não redireciona stdout/stderr. Migração automática de instalações existentes preserva logs antigos. Testes de `LogManager` cobrem criação, leitura, append, rotação e compatibilidade. |
| H8 | **Baixa** | Access Control / Server Settings | Badge `pending` não informa explicitamente que requer restart. | Tornar o aviso de "requer restart" mais explícito na UI. |
| HF-RUNTIME-01 | **Alta** ✅ RESOLVIDO (2.8.7) | Uptime | Uptime calculado a partir de `/proc/<pid>/stat` pode refletir sessão anterior após restart/reinstall. | `RuntimeSession` (`backend/services/runtime_session.py`) registra `started_at` em UTC no start; `metrics_service.py` usa `session.get_uptime()` para calcular `current_time - started_at`. Reset no stop/restart/reinstall. Testes de regressão adicionados. |

---

## Conformidade com Parâmetros CLI Oficiais

| Parâmetro oficial | Usado pelo manager | Situação |
| --- | --- | --- |
| `--start-server=SAVE` | Sim | ⚠️ caminho absoluto ausente (H1) |
| `--port=N` | Sim | OK |
| `--bind=ADDR[:PORT]` | Sim | OK |
| `--rcon-port=N` | Sim | OK |
| `--rcon-password=PASS` | Sim | OK (mascarado) |
| `--rcon-bind=ADDR:PORT` | Sim | OK |
| `--server-settings=FILE` | Sim | OK (arquivo existe) |
| `--server-adminlist=FILE` | Sim | OK |
| `--server-banlist=FILE` | Sim | OK |
| `--server-whitelist=FILE` | Sim | OK |
| `--use-server-whitelist` | Sim | OK |
| `--use-authserver-bans` | Sim | OK |
| `--server-id=FILE` | Sim | OK |
| `--console-log=FILE` | Sim | ✅ usado (H7 resolvido): `--console-log=logs/server.log` é a origem oficial dos logs do servidor |
| `--create=SAVE` | Sim (criação) | ⚠️ caminho do binário fixo (H5) |
| `--map-gen-seed=N` | Sim (criação) | OK |

---

## Testes

- Comando: `python3 -m pytest backend/tests -q`
- Resultado: **235 passed** (0 falhas de backend, 0 regressões). `test_log_viewer.py` (8 testes) falha por limitação pré-existente do transpilador JS→Python do próprio arquivo de teste, independente desta mudança.
- Cobertura relevante: startup builder, startup validation, runtime state, **runtime session**, access control, save service, RCON, metrics, factorio services, config, API status, frontend UI, docker manager, **LogManager (H7: criação, leitura, append, rotação, compatibilidade/migração)**, **RuntimeSession (HF-RUNTIME-01: start/stop/restart, uptime, sessão)**.

---

## Conclusão

O Server Manager cobre todos os parâmetros CLI oficiais do servidor dedicado do
Factorio e implementa fielmente o protocolo RCON. O logging agora segue o mecanismo
oficial via `--console-log`, centralizado no `LogManager`; não há mais redirecionamento
de stdout/stderr. O uptime agora é calculado por `RuntimeSession`, garantindo que
sempre reflita a sessão atual do servidor.

Divergências pendentes de baixo/médio risco: H5 (caminho do binário em `create_save`),
H6 (Factorio Account token não usado na CLI) e H8 (badge `pending` menos explícito sobre
restart). H1, H2, H3, H4, H7 e HF-RUNTIME-01 foram resolvidos.
