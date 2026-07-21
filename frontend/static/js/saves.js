        let openMenuFilename = null;

        async function loadSaves() {
            const tbody = document.getElementById('saves-list');
            const empty = document.getElementById('saves-empty');
            const table = document.getElementById('saves-table');
            if (!tbody) return;

            try {
                const data = await BootstrapCache.get('saves', async () => {
                    const res = await fetch('/api/saves');
                    if (!res.ok) throw new Error('saves_failed');
                    return res.json();
                });
                const saves = data.saves || [];

                const previouslyOpen = document.querySelector('.saves-menu-dropdown.open');
                if (previouslyOpen) {
                    const row = previouslyOpen.closest('tr');
                    if (row) openMenuFilename = row.dataset.filename;
                }

                const existingRows = new Map();
                Array.from(tbody.querySelectorAll('tr')).forEach((tr) => {
                    existingRows.set(tr.dataset.filename, tr);
                });

                const incomingNames = new Set(saves.map((s) => s.name));
                existingRows.forEach((tr, filename) => {
                    if (!incomingNames.has(filename)) {
                        tr.remove();
                        existingRows.delete(filename);
                    }
                });

                if (saves.length === 0) {
                    if (empty) empty.style.display = 'block';
                    if (table) table.style.display = 'none';
                    const countEl = document.getElementById('saves-count');
                    if (countEl) countEl.textContent = t('saves.toolbar.count').replace('{count}', 0);
                    return;
                }

                if (empty) empty.style.display = 'none';
                if (table) table.style.display = 'table';

                const countEl = document.getElementById('saves-count');
                if (countEl) countEl.textContent = t('saves.toolbar.count').replace('{count}', saves.length);

                for (const save of saves) {
                    const isActive = save.active;
                    const date = new Date(save.modified * 1000).toLocaleDateString(currentLang === 'zh_CN' ? 'zh-CN' : currentLang.replace('_', '-'));
                    const size = (save.size / (1024 * 1024)).toFixed(1) + ' MB';
                    const badgeClass = isActive ? 'badge-active' : 'badge-inactive';
                    const statusText = isActive ? t('status.active') : t('status.inactive');
                    const escapedName = escapeHtml(save.name);
                    const encodedName = encodeURIComponent(save.name);
                    const selectButton = !isActive
                        ? `<button type="button" class="text-button select-save" data-filename="${escapedName}">${t('saves.select')}</button>`
                        : `<button type="button" class="text-button select-save-disabled" disabled data-i18n="saves.select">${t('saves.select')}</button>`;

                    if (existingRows.has(save.name)) {
                        const tr = existingRows.get(save.name);
                        const badge = tr.querySelector('.badge');
                        if (badge) {
                            badge.className = `badge ${badgeClass}`;
                            badge.setAttribute('data-i18n', isActive ? 'status.active' : 'status.inactive');
                            badge.innerHTML = statusText;
                        }
                        const nameEl = tr.querySelector('.save-name');
                        if (nameEl) nameEl.textContent = escapedName;
                        const dateEl = tr.querySelector('.save-meta-date');
                        if (dateEl) dateEl.textContent = date;
                        const sizeEl = tr.querySelector('.save-meta-size');
                        if (sizeEl) sizeEl.textContent = size;
                        if (openMenuFilename !== save.name) {
                            const actionsContainer = tr.querySelector('.saves-actions');
                            if (actionsContainer) {
                                actionsContainer.innerHTML = `
                                    <div class="saves-menu">
                                        <button type="button" class="saves-menu-button" data-filename="${escapedName}" aria-haspopup="true" aria-expanded="false">
                                            <span class="saves-menu-icon">⋮</span>
                                        </button>
                                        <div class="saves-menu-dropdown">
                                            <button type="button" class="saves-menu-item rename-save" data-filename="${escapedName}">${t('saves.rename')}</button>
                                            <a href="/download-save/${encodedName}" class="saves-menu-item download-save" download>${t('saves.download')}</a>
                                            <button type="button" class="saves-menu-item" disabled>${t('saves.duplicate')}</button>
                                            <div class="saves-menu-separator"></div>
                                            <button type="button" class="saves-menu-item danger-button delete-save" data-filename="${escapedName}">${t('saves.delete')}</button>
                                        </div>
                                    </div>
                                    ${selectButton}
                                `;
                            }
                        }
                    } else {
                        const tr = document.createElement('tr');
                        tr.dataset.filename = save.name;
                        tr.innerHTML = `
                            <td>
                                <div class="save-main">
                                    <div class="save-name-row">
                                        <span class="badge ${badgeClass}" data-i18n="${isActive ? 'status.active' : 'status.inactive'}">${statusText}</span>
                                        <span class="save-name">${escapedName}</span>
                                    </div>
                                    <span class="save-meta">
                                        <span class="save-meta-item">--</span>
                                        <span class="save-meta-sep">•</span>
                                        <span class="save-meta-item save-meta-date">${date}</span>
                                        <span class="save-meta-sep">•</span>
                                        <span class="save-meta-item save-meta-size">${size}</span>
                                    </span>
                                </div>
                            </td>
                            <td>
                                <div class="saves-actions">
                                    <div class="saves-menu">
                                        <button type="button" class="saves-menu-button" data-filename="${escapedName}" aria-haspopup="true" aria-expanded="false">
                                            <span class="saves-menu-icon">⋮</span>
                                        </button>
                                        <div class="saves-menu-dropdown">
                                            <button type="button" class="saves-menu-item rename-save" data-filename="${escapedName}">${t('saves.rename')}</button>
                                            <a href="/download-save/${encodedName}" class="saves-menu-item download-save" download>${t('saves.download')}</a>
                                            <button type="button" class="saves-menu-item" disabled>${t('saves.duplicate')}</button>
                                            <div class="saves-menu-separator"></div>
                                            <button type="button" class="saves-menu-item danger-button delete-save" data-filename="${escapedName}">${t('saves.delete')}</button>
                                        </div>
                                    </div>
                                    ${selectButton}
                                </div>
                            </td>
                        `;
                        tbody.appendChild(tr);
                        existingRows.set(save.name, tr);
                    }
                }

                if (openMenuFilename) {
                    const targetRow = tbody.querySelector(`tr[data-filename="${openMenuFilename}"]`);
                    if (targetRow) {
                        const menuButton = targetRow.querySelector('.saves-menu-button');
                        if (menuButton) {
                            const menu = menuButton.nextElementSibling;
                            if (menu) {
                                menu.classList.add('open');
                                menuButton.setAttribute('aria-expanded', 'true');
                            }
                        }
                    }
                    openMenuFilename = null;
                }
            } catch (err) {
                // ignore
            }
        }

        async function createSave() {
            const nameInput = document.getElementById('new-save-name');
            const seedInput = document.getElementById('new-save-seed');
            if (!nameInput) return;

            const name = nameInput.value.trim();
            const seed = seedInput ? seedInput.value.trim() : null;
            if (!name) return;

            try {
                const res = await fetch('/api/saves/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, seed }),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    alert(t('error.create_world_failed'));
                    return;
                }
                nameInput.value = '';
                if (seedInput) seedInput.value = '';
                loadSaves();
            } catch (err) {
                alert(t('error.create_world_exception'));
            }
        }

        async function selectSave(filename) {
            try {
                const res = await fetch('/api/saves/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename }),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    alert(t('error.select_save_failed'));
                    return;
                }
                loadSaves();
            } catch (err) {
                alert(t('error.select_save_exception'));
            }
        }

        async function deleteSave(filename) {
            if (!confirm(t('confirm.delete_save').replace('{filename}', filename))) return;
            try {
                const res = await fetch(`/api/saves/${encodeURIComponent(filename)}`, { method: 'DELETE' });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    alert(t('error.delete_save_failed'));
                    return;
                }
                loadSaves();
            } catch (err) {
                alert(t('error.delete_save_exception'));
            }
        }

        async function renameSave(filename) {
            const newName = prompt(t('prompt.rename_save'), filename);
            if (!newName || newName === filename) return;
            try {
                const res = await fetch('/api/saves/rename', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ old_name: filename, new_name: newName }),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    alert(t('error.rename_save_failed'));
                    return;
                }
                loadSaves();
            } catch (err) {
                alert(t('error.rename_save_exception'));
            }
        }

        async function downloadSave(filename) {
            const link = document.createElement('a');
            link.href = `/download-save/${encodeURIComponent(filename)}`;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        document.addEventListener('click', (e) => {
            const target = e.target;

            const menuButton = target.closest('.saves-menu-button');
            if (menuButton) {
                toggleMenu(menuButton);
                return;
            }

            if (target.classList.contains('select-save')) {
                selectSave(target.dataset.filename);
                return;
            }

            if (target.classList.contains('delete-save')) {
                deleteSave(target.dataset.filename);
                return;
            }

            if (target.classList.contains('rename-save')) {
                renameSave(target.dataset.filename);
                return;
            }

            if (target.closest('.download-save')) {
                e.preventDefault();
                const link = target.closest('.download-save');
                const href = link.getAttribute('href') || '';
                const filename = href.split('/').pop() || '';
                if (filename) downloadSave(decodeURIComponent(filename));
                closeAllMenus();
                return;
            }

            if (target.classList.contains('saves-menu-item') && !target.classList.contains('disabled')) {
                const menuItem = target;
                const filename = menuItem.dataset.filename;
                if (menuItem.classList.contains('download-save')) {
                    downloadSave(filename);
                }
                closeAllMenus();
            }
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.saves-menu')) {
                closeAllMenus();
            }
        });

        function closeAllMenus() {
            document.querySelectorAll('.saves-menu-dropdown.open').forEach((menu) => {
                menu.classList.remove('open');
                const button = menu.parentElement.querySelector('.saves-menu-button');
                if (button) button.setAttribute('aria-expanded', 'false');
            });
        }

        function toggleMenu(button) {
            const menu = button.nextElementSibling;
            const isOpen = menu.classList.contains('open');
            closeAllMenus();
            if (!isOpen) {
                menu.classList.add('open');
                button.setAttribute('aria-expanded', 'true');
            }
        }

        const createForm = document.getElementById('create-save-form');
        if (createForm) {
            createForm.addEventListener('submit', (e) => {
                e.preventDefault();
                createSave();
            });
        }

        setInterval(loadSaves, 5000);
        loadSaves();
