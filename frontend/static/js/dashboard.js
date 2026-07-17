        const logsOutput = document.getElementById('logs-output');
        let logsInterval;

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
                logsOutput.scrollTop = logsOutput.scrollHeight;
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
                const newStatus = data.status || serverStatus.textContent;
                serverStatus.textContent = newStatus;
                const isOnline = newStatus === 'running' || newStatus === 'online';
                serverStatus.className = `status-value badge ${isOnline ? 'badge-online' : 'badge-offline'}`;
                const statusDot = document.getElementById('server-status-dot');
                if (statusDot) {
                    statusDot.className = `status-dot ${isOnline ? 'status-dot-online' : 'status-dot-offline'}`;
                }
                installStatus.textContent = data.install_status || installStatus.textContent;
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

        if (logsOutput) {
            fetchLogs();
            logsInterval = setInterval(fetchLogs, 2000);
        }

        fetchMetrics();
        setInterval(fetchMetrics, 2000);
