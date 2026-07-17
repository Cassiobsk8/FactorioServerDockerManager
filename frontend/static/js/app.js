        const tabButtons = document.querySelectorAll('.tab-button');
        const panels = document.querySelectorAll('.tab-panel');
        const installButton = document.getElementById('install-button');
        const installModal = document.getElementById('install-modal');
        const closeModal = document.getElementById('close-modal');
        const archivePathInput = document.getElementById('archive-path');
        const installProgressFill = document.getElementById('install-progress-fill');
        const installModalMessage = document.getElementById('install-modal-message');
        const installProgressMeta = document.getElementById('install-progress-meta');
        let installInterval;

        tabButtons.forEach((button) => {
            button.addEventListener('click', () => {
                tabButtons.forEach((btn) => btn.classList.remove('active'));
                panels.forEach((panel) => panel.classList.remove('active'));

                button.classList.add('active');
                document.getElementById(`${button.dataset.tab}-panel`).classList.add('active');
                if (button.dataset.tab === 'config') {
                    fetchAndRenderSettings();
                }
                if (button.dataset.tab === 'console') {
                    fetchRconStatusOnce();
                }
            });
        });

        function openInstallModal() {
            installModal.style.display = 'flex';
        }

        function closeInstallModal() {
            installModal.style.display = 'none';
            clearInterval(installInterval);
        }

        async function fetchInstallProgress() {
            try {
                const response = await fetch('/install/progress');
                if (!response.ok) {
                    installModalMessage.textContent = t('modal.progress_error');
                    return;
                }
                const progress = await response.json();
                const { status, stage, message, downloaded, total } = progress;

                installModalMessage.textContent = message || t('modal.progress_received');

                if (stage === 'download' && total > 0) {
                    const percent = Math.min(100, Math.round((downloaded / total) * 100));
                    installProgressFill.style.width = `${percent}%`;
                    installProgressMeta.textContent = `${percent}% (${downloaded}/${total} bytes)`;
                } else if (stage === 'install') {
                    installProgressFill.style.width = '100%';
                    installProgressMeta.textContent = t('modal.installing');
                } else if (status === 'complete') {
                    installProgressFill.style.width = '100%';
                    installProgressMeta.textContent = t('modal.complete');
                    try { fetchAndRenderSettings(); } catch (e) { /* ignore */ }
                    clearInterval(installInterval);
                } else if (status === 'error') {
                    installProgressFill.style.width = '100%';
                    installProgressMeta.textContent = `${t('modal.unknown_error')}: ${message}`;
                    clearInterval(installInterval);
                } else {
                    installProgressFill.style.width = '0%';
                    installProgressMeta.textContent = message || t('modal.waiting_action');
                }
            } catch (err) {
                installModalMessage.textContent = t('modal.progress_fetch_error');
                installProgressMeta.textContent = err.message;
                clearInterval(installInterval);
            }
        }

        async function startInstallation() {
            openInstallModal();
            installModalMessage.textContent = t('modal.preparing');
            installProgressFill.style.width = '0%';
            installProgressMeta.textContent = t('modal.waiting');

            const logsEl = document.getElementById('logs-output');
            if (logsEl) {
                logsEl.textContent = '';
                logsEl.scrollTop = 0;
            }

            const response = await fetch('/install/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ archive_path: archivePathInput.value.trim() }),
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                installModalMessage.textContent = t('modal.start_failed');
                installProgressMeta.textContent = error.error || t('modal.unknown_error');
                return;
            }

            fetchInstallProgress();
            installInterval = setInterval(fetchInstallProgress, 1500);
        }

        function formatDate(timestamp) {
            if (!timestamp) return '--';
            return new Date(timestamp * 1000).toLocaleString(currentLang === 'zh_CN' ? 'zh-CN' : currentLang.replace('_', '-'));
        }

        let lastInstallStatus = null;
        async function pollInstallProgressForUI() {
            try {
                const res = await fetch('/install/progress');
                if (!res.ok) return;
                const data = await res.json();
                const status = data.status;
                if (status && status !== lastInstallStatus) {
                    if (status === 'complete') {
                        fetchAndRenderSettings();
                    }
                    lastInstallStatus = status;
                }
            } catch (err) {
                // ignore
            }
        }

        pollInstallProgressForUI();
        setInterval(pollInstallProgressForUI, 2000);

        if (installButton) {
            installButton.addEventListener('click', (event) => {
                event.preventDefault();
                startInstallation();
            });
        }

        if (closeModal) {
            closeModal.addEventListener('click', closeInstallModal);
        }

        initLanguage();
