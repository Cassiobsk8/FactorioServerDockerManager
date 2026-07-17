        async function loadSaves() {
            const tbody = document.getElementById('saves-list');
            const empty = document.getElementById('saves-empty');
            const table = document.getElementById('saves-table');
            if (!tbody) return;

            try {
                const res = await fetch('/api/saves');
                if (!res.ok) return;
                const data = await res.json();
                const saves = data.saves || [];

                tbody.innerHTML = '';
                if (saves.length === 0) {
                    if (empty) empty.style.display = 'block';
                    if (table) table.style.display = 'none';
                    return;
                }

                if (empty) empty.style.display = 'none';
                if (table) table.style.display = 'table';

                for (const save of saves) {
                    const tr = document.createElement('tr');
                    tr.dataset.filename = save.name;

                    const date = new Date(save.modified * 1000).toLocaleDateString(currentLang === 'zh_CN' ? 'zh-CN' : currentLang.replace('_', '-'));
                    const size = (save.size / (1024 * 1024)).toFixed(1) + ' MB';
                    const isActive = save.active;

                    tr.innerHTML = `
                        <td>${escapeHtml(save.name)}</td>
                        <td class="save-date">${date}</td>
                        <td class="save-size">${size}</td>
                        <td>
                            <span class="badge ${isActive ? 'badge-active' : 'badge-inactive'}">
                                ${isActive ? t('status.active') : t('status.inactive')}
                            </span>
                        </td>
                        <td>
                            <div class="button-row">
                                ${!isActive ? `<button type="button" class="text-button select-save" data-filename="${escapeHtml(save.name)}">${t('saves.select')}</button>` : ''}
                                <button type="button" class="text-button rename-save" data-filename="${escapeHtml(save.name)}">${t('saves.rename')}</button>
                                ${!isActive ? `<button type="button" class="text-button danger-button delete-save" data-filename="${escapeHtml(save.name)}">${t('saves.delete')}</button>` : ''}
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
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
                    alert(err.error || t('error.create_world_failed'));
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
                    alert(err.error || t('error.select_save_failed'));
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
                    alert(err.error || t('error.delete_save_failed'));
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
                    alert(err.error || t('error.rename_save_failed'));
                    return;
                }
                loadSaves();
            } catch (err) {
                alert(t('error.rename_save_exception'));
            }
        }

        document.addEventListener('click', (e) => {
            const target = e.target;
            if (target.classList.contains('select-save')) {
                selectSave(target.dataset.filename);
            } else if (target.classList.contains('delete-save')) {
                deleteSave(target.dataset.filename);
            } else if (target.classList.contains('rename-save')) {
                renameSave(target.dataset.filename);
            }
        });

        const createForm = document.getElementById('create-save-form');
        if (createForm) {
            createForm.addEventListener('submit', (e) => {
                e.preventDefault();
                createSave();
            });
        }

        setInterval(loadSaves, 5000);
        loadSaves();
