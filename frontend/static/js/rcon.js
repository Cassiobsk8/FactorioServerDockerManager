        const consoleOutput = document.getElementById('console-output');
        const consoleInput = document.getElementById('console-input');
        const consoleForm = document.getElementById('console-form');
        const consoleStatusBadge = document.getElementById('console-status-badge');
        const rconStatusBadge = document.getElementById('rcon-status-badge');
        const playersList = document.getElementById('players-list');
        const commandHistory = [];
        let historyIndex = -1;

        function appendConsole(text, kind) {
            if (!consoleOutput) return;
            const line = document.createElement('div');
            line.className = `console-line${kind ? ' console-line-' + kind : ''}`;
            line.textContent = text;
            consoleOutput.appendChild(line);
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }

        function setRconBadge(state, caller, apiResponse) {
            const previous = consoleStatusBadge ? consoleStatusBadge.textContent : 'unknown';
            console.debug('[RCON BADGE]', {
                caller: caller || 'unknown',
                previousState: previous,
                newState: state,
                apiResponse: apiResponse || null
            });
            let text, cls;
            if (state === 'connected') {
                text = `🟢 ${t('rcon.connected')}`;
                cls = 'badge-online';
            } else if (state === 'not_configured') {
                text = `⚪ ${t('rcon.not_configured')}`;
                cls = 'badge-offline';
            } else if (state === 'testing') {
                text = `🟡 ${t('rcon.testing')}`;
                cls = 'badge-offline';
            } else {
                text = `🔴 ${t('rcon.disconnected')}`;
                cls = 'badge-offline';
            }
            if (consoleStatusBadge) {
                consoleStatusBadge.textContent = text;
                consoleStatusBadge.className = `badge ${cls}`;
            }
            if (rconStatusBadge) {
                rconStatusBadge.textContent = text;
                rconStatusBadge.className = `badge ${cls}`;
            }
        }

        function refreshRconStatusUI(status, caller) {
            if (!status) return;
            const previousBadge = consoleStatusBadge ? consoleStatusBadge.textContent : 'unknown';
            const isStatusEndpoint = Object.prototype.hasOwnProperty.call(status, 'configured');
            if (!isStatusEndpoint) {
                console.debug('[RCON BADGE SKIP] response is not from /api/rcon/status', {
                    caller: caller || 'unknown',
                    previousBadge,
                    statusKeys: Object.keys(status)
                });
                if (playersList && Array.isArray(status.players)) {
                    renderPlayers(status.players);
                }
                return;
            }
            if (!status.configured) {
                setRconBadge('not_configured', caller || 'refreshRconStatusUI', status);
            } else {
                setRconBadge(status.connected ? 'connected' : 'disconnected', caller || 'refreshRconStatusUI', status);
            }
            if (playersList && Array.isArray(status.players)) {
                renderPlayers(status.players);
            }
        }

        function renderPlayers(players) {
            if (!playersList) return;
            playersList.innerHTML = '';
            const list = players || [];
            if (!list.length) {
                const li = document.createElement('li');
                li.className = 'players-empty';
                li.textContent = t('rcon.no_players');
                playersList.appendChild(li);
                return;
            }
            for (const name of list) {
                const li = document.createElement('li');
                li.textContent = name;
                playersList.appendChild(li);
            }
        }

        function friendlyRconError(err) {
            const msg = String(err || '').toLowerCase();
            if (msg.includes('not configured')) return t('rcon.error.not_configured');
            if (msg.includes('auth')) return t('rcon.error.auth_failed');
            if (msg.includes('timed out') || msg.includes('timeout')) return t('rcon.error.timeout');
            if (msg.includes('refused') || msg.includes('connect') || msg.includes('offline')) return t('rcon.error.server_offline');
            return t('rcon.error.technical');
        }

        async function rconCommand(command) {
            if (!command) return;
            appendConsole(`> ${command}`, 'cmd');
            try {
                const res = await fetch('/api/rcon/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command }),
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    appendConsole(friendlyRconError(data.error), 'error');
                } else {
                    if (data.response) appendConsole(data.response, 'response');
                }
            } catch (err) {
                appendConsole(friendlyRconError(err.message), 'error');
            }
        }

        async function rconQuick(action, body) {
            try {
                const res = await fetch(`/api/rcon/${action}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body || {}),
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    appendConsole(friendlyRconError(data.error), 'error');
                } else {
                    if (data.response) appendConsole(data.response, 'response');
                }
                return data;
            } catch (err) {
                appendConsole(friendlyRconError(err.message), 'error');
                return null;
            }
        }

        const consoleCopy = document.getElementById('console-copy');
        if (consoleCopy) {
            consoleCopy.addEventListener('click', async () => {
                if (!consoleOutput) return;
                const text = consoleOutput.innerText || '';
                try {
                    await navigator.clipboard.writeText(text);
                    consoleCopy.textContent = t('rcon.copied');
                    setTimeout(() => { consoleCopy.textContent = t('rcon.copy_output'); }, 1500);
                } catch (err) {
                    consoleCopy.textContent = t('rcon.copy_failed');
                    setTimeout(() => { consoleCopy.textContent = t('rcon.copy_output'); }, 1500);
                }
            });
        }

        const consoleClear = document.getElementById('console-clear');
        if (consoleClear) {
            consoleClear.addEventListener('click', () => {
                if (consoleOutput) consoleOutput.innerHTML = '';
            });
        }

        if (consoleForm) {
            consoleForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const value = consoleInput.value.trim();
                if (!value) return;
                commandHistory.push(value);
                if (commandHistory.length > 50) commandHistory.shift();
                historyIndex = commandHistory.length;
                rconCommand(value);
                consoleInput.value = '';
            });
        }

        if (consoleInput) {
            consoleInput.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowUp') {
                    if (commandHistory.length === 0) return;
                    historyIndex = Math.max(0, historyIndex - 1);
                    consoleInput.value = commandHistory[historyIndex] || '';
                    e.preventDefault();
                } else if (e.key === 'ArrowDown') {
                    if (commandHistory.length === 0) return;
                    historyIndex = Math.min(commandHistory.length, historyIndex + 1);
                    consoleInput.value = commandHistory[historyIndex] || '';
                    e.preventDefault();
                }
            });
        }

        const qaSaveWorld = document.getElementById('qa-save-world');
        if (qaSaveWorld) qaSaveWorld.addEventListener('click', () => rconQuick('save'));

        const qaPlayersOnline = document.getElementById('qa-players-online');
        if (qaPlayersOnline) qaPlayersOnline.addEventListener('click', () => rconCommand('/players'));

        const qaServerStatus = document.getElementById('qa-server-status');
        if (qaServerStatus) qaServerStatus.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/rcon/status');
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    appendConsole(friendlyRconError(data.error), 'error');
                } else {
                    renderPlayers(data.players || []);
                    appendConsole(t('rcon.server_status') + ': ' + (data.connected ? t('rcon.connected') : t('rcon.disconnected')), 'response');
                }
            } catch (err) {
                appendConsole(friendlyRconError(err.message), 'error');
            }
        });

        const qaBroadcast = document.getElementById('qa-broadcast');
        const broadcastMessage = document.getElementById('broadcast-message');
        if (qaBroadcast) qaBroadcast.addEventListener('click', () => {
            const msg = broadcastMessage ? broadcastMessage.value.trim() : '';
            if (!msg) return;
            rconQuick('broadcast', { message: msg });
            if (broadcastMessage) broadcastMessage.value = '';
        });

        const rconSettingsForm = document.getElementById('rcon-settings-form');
        const rconTestButton = document.getElementById('rcon-test-button');
        const rconTestResult = document.getElementById('rcon-test-result');

        if (rconSettingsForm) {
            rconSettingsForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const host = document.getElementById('rcon-host').value.trim();
                const port = document.getElementById('rcon-port').value.trim();
                const password = document.getElementById('rcon-password').value;
                const timeout = document.getElementById('rcon-timeout').value.trim();
                try {
                    const res = await fetch('/api/rcon/settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ host, port, password, timeout }),
                    });
                    if (!res.ok) {
                        const err = await res.json().catch(() => ({}));
                        appendConsole(friendlyRconError(err.error), 'error');
                    }
                } catch (err) {
                    appendConsole(friendlyRconError(err.message), 'error');
                }
            });
        }

        async function runRconTest() {
            const host = document.getElementById('rcon-host').value.trim();
            const portRaw = document.getElementById('rcon-port').value.trim();
            const password = document.getElementById('rcon-password').value;
            const timeoutRaw = document.getElementById('rcon-timeout').value.trim();

            if (!host) {
                if (rconTestResult) {
                    rconTestResult.textContent = t('rcon.error.host_required');
                    rconTestResult.className = 'rcon-test-result failed';
                }
                return;
            }
            if (!portRaw || !/^\d+$/.test(portRaw) || Number(portRaw) < 1 || Number(portRaw) > 65535) {
                if (rconTestResult) {
                    rconTestResult.textContent = t('rcon.error.port_invalid');
                    rconTestResult.className = 'rcon-test-result failed';
                }
                return;
            }
            if (!password) {
                if (rconTestResult) {
                    rconTestResult.textContent = t('rcon.error.password_required');
                    rconTestResult.className = 'rcon-test-result failed';
                }
                return;
            }

            if (rconTestResult) {
                rconTestResult.textContent = t('rcon.testing');
                rconTestResult.className = 'rcon-test-result';
            }
            if (rconTestButton) rconTestButton.disabled = true;

             try {
                 const res = await fetch('/api/rcon/test', {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({ host, port: portRaw, password, timeout: timeoutRaw }),
                 });
                 const data = await res.json().catch(() => ({}));
                 if (rconTestResult) {
                     if (data && data.connected) {
                         rconTestResult.textContent = `✓ ${t('rcon.test_success')}`;
                         rconTestResult.className = 'rcon-test-result ok';
                     } else {
                         const reason = data && data.error ? friendlyRconError(data.error) : t('rcon.test_failed');
                         rconTestResult.textContent = `✗ ${t('rcon.test_failed')} - ${reason}`;
                         rconTestResult.className = 'rcon-test-result failed';
                     }
                 }
             } catch (err) {
                 if (rconTestResult) {
                     rconTestResult.textContent = `✗ ${t('rcon.test_failed')} - ${friendlyRconError(err.message)}`;
                     rconTestResult.className = 'rcon-test-result failed';
                 }
             } finally {
                 if (rconTestButton) rconTestButton.disabled = false;
             }
        }

        if (rconTestButton) {
            rconTestButton.addEventListener('click', runRconTest);
        }

        async function pollRconStatus() {
            try {
                const data = await BootstrapCache.get('rcon-status', async () => {
                    const res = await fetch('/api/rcon/status');
                    if (!res.ok) throw new Error('rcon_status_failed');
                    return res.json();
                });
                refreshRconStatusUI(data, 'pollRconStatus');
            } catch (err) {
            }
        }

        async function fetchRconStatusOnce() {
            try {
                const data = await BootstrapCache.get('rcon-status', async () => {
                    const res = await fetch('/api/rcon/status');
                    if (!res.ok) throw new Error('rcon_status_failed');
                    return res.json();
                });
                refreshRconStatusUI(data, 'fetchRconStatusOnce');
            } catch (err) {
            }
        }
