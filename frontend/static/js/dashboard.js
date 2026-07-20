        const logsOutput = document.getElementById('logs-output');
        const logsAutoScrollBtn = document.getElementById('logs-auto-scroll');
        let logViewer = null;

        if (logsOutput) {
            logViewer = new LogViewer(logsOutput, {
                endpoint: '/logs/data',
                onAutoScrollChange: function (enabled) {
                    if (logsAutoScrollBtn) {
                        logsAutoScrollBtn.classList.toggle('active', enabled);
                    }
                },
            });
            window.logViewer = logViewer;
        }

        function formatInstallStatus(status) {
            if (!status) return '';
            if (status === 'installed') return t('status.install_status.installed');
            if (status === 'not installed') return t('status.install_status.not_installed');
            if (status === 'installing') return t('status.install_status.installing');
            if (status.startsWith('configured archive:')) {
                const url = status.replace('configured archive:', '').trim();
                return `${t('status.install_status.archive_configured')} ${url}`;
            }
            if (status === 'configured install URL') return t('status.install_status.install_configured');
            return status;
        }

        function formatStatus(status) {
            // Presentation layer only: never expose internal/technical API states.
            const known = {
                'not_installed': 'status.state.not_installed',
                'running': 'status.state.running',
                'online': 'status.state.running',
                'stopped': 'status.state.stopped',
                'offline': 'status.state.stopped',
                'starting': 'status.state.starting',
                'stopping': 'status.state.stopping',
                'installing': 'status.state.installing',
                'error': 'status.state.error',
            };
            const normalized = String(status || '')
                .trim()
                .toLowerCase()
                .replace(/[\s-]+/g, '_');
            const key = known[normalized] || 'status.state.unknown';
            return t(key);
        }

        async function fetchStatus() {
            const serverStatus = document.getElementById('server-status');
            const installStatus = document.getElementById('install-status');
            const runtimeRestartBadge = document.getElementById('runtime-state-badge-restart');
            const runtimeAppliedBadge = document.getElementById('runtime-state-badge-applied');
            if (!serverStatus || !installStatus) {
                return;
            }

            try {
                const response = await fetch('/status');
                if (!response.ok) {
                    return;
                }
                const data = await response.json();
                const rawStatus = data.status || serverStatus.textContent;
                const isOnline = rawStatus === 'running' || rawStatus === 'online';
                serverStatus.textContent = formatStatus(rawStatus);
                serverStatus.dataset.rawStatus = rawStatus;
                serverStatus.className = `status-value badge ${isOnline ? 'badge-online' : 'badge-offline'}`;
                const statusDot = document.getElementById('server-status-dot');
                if (statusDot) {
                    statusDot.className = `status-dot ${isOnline ? 'status-dot-online' : 'status-dot-offline'}`;
                }
                installStatus.textContent = formatInstallStatus(data.install_status) || installStatus.textContent;

                const runtime = data.runtime_state || {};
                const hasPending = Boolean(runtime.has_pending);
                if (runtimeRestartBadge) {
                    runtimeRestartBadge.style.display = hasPending ? '' : 'none';
                }
                if (runtimeAppliedBadge) {
                    runtimeAppliedBadge.style.display = hasPending ? 'none' : '';
                }

                if (hasPending && runtime.pending) {
                    renderPendingChanges(runtime.pending);
                }

                const factorioBadge = document.getElementById('factorio-account-badge');
                if (factorioBadge && data.factorio_account) {
                    const fs = data.factorio_account;
                    factorioBadge.textContent = t(`factorio_account.status.${fs.status}`);
                    factorioBadge.className = `badge badge-factorio ${fs.status}`;
                }

                renderHeroActions();
            } catch (err) {
                // ignore errors during polling
            }
        }

        async function fetchMetrics() {
            const cpuEl = document.getElementById('metric-cpu');
            const ramEl = document.getElementById('metric-ram');
            const uptimeEl = document.getElementById('metric-uptime');
            const diskEl = document.getElementById('metric-disk');
            const versionEl = document.getElementById('metric-version');
            const savesCountEl = document.getElementById('metric-saves-count');
            const playersEl = document.getElementById('metric-players');
            const modsEl = document.getElementById('metric-mods');

            if (!cpuEl) return;

            try {
                const response = await fetch('/api/status');
                if (!response.ok) return;
                const data = await response.json();
                const server = data.server || {};

                const cpu = server.cpu_percent ?? 0;
                if (cpuEl) cpuEl.textContent = `${cpu}%`;
                const cpuBar = document.getElementById('metric-cpu-bar');
                if (cpuBar) cpuBar.style.width = `${Math.min(100, cpu)}%`;

                const ramUsed = server.ram_used_mb ?? 0;
                const ramTotal = server.ram_total_mb ?? 0;
                if (ramEl) ramEl.textContent = formatMB(ramUsed);
                const ramDetail = document.getElementById('metric-ram-detail');
                if (ramDetail) ramDetail.textContent = `de ${formatMB(ramTotal)}`;
                const ramBar = document.getElementById('metric-ram-bar');
                if (ramBar) ramBar.style.width = `${percent(ramUsed, ramTotal)}%`;

                if (uptimeEl) uptimeEl.textContent = formatUptime(server.uptime_seconds ?? 0);

                const diskUsed = server.disk_used_mb ?? 0;
                const diskTotal = server.disk_total_mb ?? 0;
                if (diskEl) diskEl.textContent = formatMB(diskUsed);
                const diskDetail = document.getElementById('metric-disk-detail');
                if (diskDetail) diskDetail.textContent = `de ${formatMB(diskTotal)}`;
                const diskBar = document.getElementById('metric-disk-bar');
                if (diskBar) diskBar.style.width = `${percent(diskUsed, diskTotal)}%`;

                if (versionEl) versionEl.textContent = server.factorio_version || '--';

                renderActiveSave(server.active_save);

                if (savesCountEl) {
                    const res = await fetch('/api/saves');
                    if (res.ok) {
                        const savesData = await res.json();
                        const saves = savesData.saves || [];
                        savesCountEl.textContent = String(saves.length);
                    }
                }

                if (playersEl) {
                    const playersRes = await fetch('/api/rcon/players');
                    if (playersRes.ok) {
                        const playersData = await playersRes.json();
                        const count = Array.isArray(playersData.players) ? playersData.players.length : (playersData.player_count ?? '--');
                        playersEl.textContent = String(count);
                    } else {
                        playersEl.textContent = '--';
                    }
                }

                if (modsEl) {
                    const modsRes = await fetch('/api/mods');
                    if (modsRes.ok) {
                        const modsData = await modsRes.json();
                        const mods = Array.isArray(modsData.mods) ? modsData.mods : [];
                        modsEl.textContent = String(mods.length);
                    } else {
                        modsEl.textContent = '--';
                    }
                }
            } catch (err) {
                // ignore
            }
        }

        function renderActiveSave(activeSave) {
            const card = document.getElementById('active-save-card');
            const nameEl = document.getElementById('active-save-name');
            const sizeEl = document.getElementById('active-save-size');
            const modifiedEl = document.getElementById('active-save-modified');
            const badgeEl = document.getElementById('active-save-badge');
            if (!card || !nameEl) return;

            if (!activeSave || !activeSave.name) {
                card.classList.add('active-save-empty');
                badgeEl.style.display = 'none';
                nameEl.textContent = t('status.no_save');
                if (sizeEl) sizeEl.textContent = '--';
                if (modifiedEl) modifiedEl.textContent = '--';
                return;
            }

            card.classList.remove('active-save-empty');
            if (badgeEl) badgeEl.style.display = '';
            nameEl.textContent = activeSave.name;
            if (sizeEl) sizeEl.textContent = formatMB((activeSave.size || 0) / (1024 * 1024));
            if (modifiedEl) modifiedEl.textContent = formatDate(activeSave.modified);
        }

        function renderHeroActions() {
            const serverStatusEl = document.getElementById('server-status');
            const status = serverStatusEl?.dataset.rawStatus || '';
            const forms = document.querySelectorAll('.hero-action-form');
            const loading = document.getElementById('hero-loading');
            if (!forms.length && !loading) return;

            const busy = status === 'starting' || status === 'stopping';
            forms.forEach((form) => {
                form.classList.toggle('visible', !busy);
            });
            if (loading) {
                loading.classList.toggle('active', busy);
            }

            if (busy) return;

            const installForm = document.getElementById('action-install');
            const startForm = document.getElementById('action-start');
            const restartForm = document.getElementById('action-restart');
            const stopForm = document.getElementById('action-stop');

            if (installForm) installForm.classList.toggle('visible', status === 'not_installed');
            if (startForm) startForm.classList.toggle('visible', status === 'stopped');
            if (restartForm) restartForm.classList.toggle('visible', status === 'running');
            if (stopForm) stopForm.classList.toggle('visible', status === 'running');
        }

        if (logViewer) {
            logViewer.start(2000);
        }

        renderHeroActions();
        fetchStatus();
        setInterval(fetchStatus, 2000);

        fetchMetrics();
        setInterval(fetchMetrics, 2000);

        if (logsAutoScrollBtn && logViewer) {
            logsAutoScrollBtn.addEventListener('click', () => {
                logViewer.setAutoScroll(!logViewer.autoScroll);
            });
        }

        const copyLogBtn = document.getElementById('logs-copy');
        if (copyLogBtn && logViewer) {
            copyLogBtn.addEventListener('click', async () => {
                try {
                    await logViewer.copy();
                    copyLogBtn.textContent = t('logs.copied');
                    setTimeout(() => {
                        copyLogBtn.textContent = t('logs.copy');
                    }, 2000);
                } catch (err) {
                    copyLogBtn.textContent = t('logs.copy_failed');
                    setTimeout(() => {
                        copyLogBtn.textContent = t('logs.copy');
                    }, 2000);
                }
            });
        }

        const serverNameEl = document.getElementById('server-name');
        const serverNameEditBtn = document.getElementById('server-name-edit');
        const serverNameInput = document.getElementById('server-name-input');
        const serverNameSaveBtn = document.getElementById('server-name-save');
        const serverNameCancelBtn = document.getElementById('server-name-cancel');
        const serverNameEditRow = document.getElementById('server-name-edit-row');

        function openServerNameEdit() {
            if (!serverNameEl || !serverNameEditRow || !serverNameInput) return;
            serverNameEditRow.style.display = 'flex';
            serverNameInput.value = serverNameEl.textContent.trim();
            serverNameInput.focus();
        }

        function closeServerNameEdit() {
            if (!serverNameEditRow) return;
            serverNameEditRow.style.display = 'none';
        }

        async function saveServerName() {
            if (!serverNameInput) return;
            const name = serverNameInput.value.trim();
            if (!name) return;
            try {
                const res = await fetch('/api/server-name', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ server_name: name }),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    console.error(err);
                    return;
                }
                if (serverNameEl) serverNameEl.textContent = name;
                closeServerNameEdit();
            } catch (err) {
                console.error(err);
            }
        }

        if (serverNameEditBtn) {
            serverNameEditBtn.addEventListener('click', openServerNameEdit);
        }
        if (serverNameSaveBtn) {
            serverNameSaveBtn.addEventListener('click', saveServerName);
        }
        if (serverNameCancelBtn) {
            serverNameCancelBtn.addEventListener('click', closeServerNameEdit);
        }
        if (serverNameInput) {
            serverNameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') saveServerName();
                if (e.key === 'Escape') closeServerNameEdit();
            });
        }

        function showStartupWarning(messages) {
            const warningEl = document.getElementById('startup-warning');
            if (!warningEl) return;
            warningEl.innerHTML = '';
            messages.forEach((message) => {
                const item = document.createElement('div');
                item.className = 'startup-warning-item';
                item.textContent = message;
                warningEl.appendChild(item);
            });
            warningEl.style.display = messages.length ? 'block' : 'none';
        }

        async function validateStartup(e) {
            try {
                const res = await fetch('/api/validate-startup', { method: 'POST' });
                if (!res.ok) return;
                const data = await res.json();
                const warnings = (data.warnings || []).map((w) => w.message);
                showStartupWarning(warnings);
                if (!data.valid && data.errors && data.errors.length) {
                    const messages = data.errors.map((err) => err.message);
                    showStartupWarning(warnings.concat(messages));
                    if (e) e.preventDefault();
                }
            } catch (err) {
                // ignore validation errors
            }
        }

        const startForm = document.getElementById('action-start');
        if (startForm) {
            startForm.addEventListener('submit', validateStartup);
        }

        const restartForm = document.getElementById('action-restart');
        if (restartForm) {
            restartForm.addEventListener('submit', validateStartup);
        }

        const startupPreviewModal = document.getElementById('startup-preview-modal');
        const startupPreviewCommand = document.getElementById('startup-preview-command');
        const startupPreviewShow = document.getElementById('startup-preview-show');
        const startupPreviewClose = document.getElementById('startup-preview-close');
        const startupPreviewCopy = document.getElementById('startup-preview-copy');

        async function loadStartupPreview() {
            try {
                const res = await fetch('/api/startup-preview');
                if (!res.ok) return;
                const data = await res.json();
                if (data.command && startupPreviewCommand) {
                    startupPreviewCommand.textContent = data.command.join(' ');
                }
            } catch (err) {
                // ignore preview errors
            }
        }

        function showStartupPreview() {
            if (!startupPreviewModal) return;
            startupPreviewModal.style.display = 'flex';
            loadStartupPreview();
        }

        function hideStartupPreview() {
            if (!startupPreviewModal) return;
            startupPreviewModal.style.display = 'none';
        }

        async function copyStartupPreview() {
            if (!startupPreviewCommand) return;
            try {
                await navigator.clipboard.writeText(startupPreviewCommand.textContent);
                if (startupPreviewCopy) {
                    const original = startupPreviewCopy.textContent;
                    startupPreviewCopy.textContent = t('startup_preview.copied');
                    setTimeout(() => {
                        startupPreviewCopy.textContent = original;
                    }, 1500);
                }
            } catch (err) {
                // ignore clipboard errors
            }
        }

        if (startupPreviewShow) {
            startupPreviewShow.addEventListener('click', showStartupPreview);
        }
        if (startupPreviewClose) {
            startupPreviewClose.addEventListener('click', hideStartupPreview);
        }
        if (startupPreviewCopy) {
            startupPreviewCopy.addEventListener('click', copyStartupPreview);
        }
        if (startupPreviewModal) {
            startupPreviewModal.addEventListener('click', (e) => {
                if (e.target === startupPreviewModal) {
                    hideStartupPreview();
                }
            });
        }

        const factorioForm = document.getElementById('factorio-account-form');
        const factorioUsername = document.getElementById('factorio-username');
        const factorioToken = document.getElementById('factorio-token');
        const factorioToggleToken = document.getElementById('factorio-account-toggle-token');
        const factorioStatusBadge = document.getElementById('factorio-account-status');

        if (factorioToggleToken && factorioToken) {
            factorioToggleToken.addEventListener('click', () => {
                const isPassword = factorioToken.type === 'password';
                factorioToken.type = isPassword ? 'text' : 'password';
                factorioToggleToken.textContent = t(isPassword ? 'factorio_account.hide_token' : 'factorio_account.show_token');
            });
        }

        async function loadFactorioServices() {
            try {
                const res = await fetch('/api/factorio-services');
                if (!res.ok) return;
                const data = await res.json();
                if (factorioUsername) factorioUsername.value = data.username || '';
                if (factorioToken) factorioToken.value = '';
                if (factorioStatusBadge) {
                    factorioStatusBadge.textContent = t(`factorio_account.status.${data.status}`);
                    factorioStatusBadge.className = `badge badge-factorio ${data.status}`;
                }
            } catch (err) {
                // ignore
            }
        }

        if (factorioForm) {
            factorioForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                if (!factorioUsername || !factorioToken) return;
                const username = factorioUsername.value.trim();
                const token = factorioToken.value.trim();
                if (!username || !token) {
                    alert(t('factorio_account.status.not_configured'));
                    return;
                }
                try {
                    const res = await fetch('/api/factorio-services', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, token }),
                    });
                    if (!res.ok) {
                        const data = await res.json().catch(() => ({}));
                        alert(data.error || t('access_control.error.failed'));
                        return;
                    }
                    factorioToken.value = '';
                    await loadFactorioServices();
                } catch (err) {
                    alert(t('access_control.error.failed'));
                }
            });
        }

        loadFactorioServices();

        const pendingChangesPopover = document.getElementById('pending-changes-popover');
        const pendingChangesList = document.getElementById('pending-changes-list');
        const pendingChangesClear = document.getElementById('pending-changes-clear');
        const runtimeRestartBadge = document.getElementById('runtime-state-badge-restart');

        function renderPendingChanges(pending) {
            if (!pendingChangesList) return;
            pendingChangesList.innerHTML = '';
            const entries = Object.entries(pending);
            if (!entries.length) {
                pendingChangesList.innerHTML = '<li>No pending changes</li>';
                return;
            }
            entries.forEach(([key, info]) => {
                const li = document.createElement('li');
                const name = document.createElement('span');
                name.textContent = info.label || key;
                li.appendChild(name);

                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'pending-change-remove';
                removeBtn.textContent = '×';
                removeBtn.addEventListener('click', async () => {
                    try {
                        await fetch(`/api/runtime-state/${encodeURIComponent(key)}`, { method: 'DELETE' });
                        const stateRes = await fetch('/api/runtime-state');
                        if (stateRes.ok) {
                            const state = await stateRes.json();
                            renderPendingChanges(state.pending);
                            if (runtimeRestartBadge) {
                                runtimeRestartBadge.style.display = state.has_pending ? '' : 'none';
                            }
                        }
                    } catch (err) {
                        // ignore
                    }
                });
                li.appendChild(removeBtn);
                pendingChangesList.appendChild(li);
            });
        }

        function togglePendingChangesPopover() {
            if (!pendingChangesPopover) return;
            const isVisible = pendingChangesPopover.style.display !== 'none';
            pendingChangesPopover.style.display = isVisible ? 'none' : 'block';
            if (!isVisible) {
                fetch('/api/runtime-state')
                    .then(res => res.ok ? res.json() : null)
                    .then(data => {
                        if (data && data.pending) {
                            renderPendingChanges(data.pending);
                        }
                    })
                    .catch(() => {});
            }
        }

        if (runtimeRestartBadge) {
            runtimeRestartBadge.addEventListener('click', (e) => {
                e.stopPropagation();
                togglePendingChangesPopover();
            });
        }

        if (pendingChangesClear) {
            pendingChangesClear.addEventListener('click', async () => {
                try {
                    await fetch('/api/runtime-state/clear', { method: 'POST' });
                    if (pendingChangesPopover) pendingChangesPopover.style.display = 'none';
                    if (runtimeRestartBadge) runtimeRestartBadge.style.display = 'none';
                } catch (err) {
                    // ignore
                }
            });
        }

        document.addEventListener('click', (e) => {
            if (pendingChangesPopover && !pendingChangesPopover.contains(e.target) && e.target !== runtimeRestartBadge) {
                pendingChangesPopover.style.display = 'none';
            }
        });
