        const logsOutput = document.getElementById('logs-output');
        let logsAutoScroll = true;

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

        async function fetchLogs() {
            if (!logsOutput) {
                return;
            }

            try {
                const response = await fetch('/logs/data');
                if (!response.ok) {
                    return;
                }
                const data = await response.json();
                logsOutput.textContent = data.logs || '';
                if (logsAutoScroll) {
                    logsOutput.scrollTop = logsOutput.scrollHeight;
                }
            } catch (err) {
                // ignore; keep current logs
            }
        }

        async function fetchStatus() {
            const serverStatus = document.getElementById('server-status');
            const installStatus = document.getElementById('install-status');
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

        if (logsOutput) {
            fetchLogs();
            setInterval(fetchLogs, 2000);
        }

        renderHeroActions();
        fetchStatus();
        setInterval(fetchStatus, 2000);

        fetchMetrics();
        setInterval(fetchMetrics, 2000);

        const logsAutoScrollBtn = document.getElementById('logs-auto-scroll');
        if (logsAutoScrollBtn) {
            logsAutoScrollBtn.addEventListener('click', () => {
                logsAutoScroll = !logsAutoScroll;
                logsAutoScrollBtn.classList.toggle('active', logsAutoScroll);
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
