        async function fetchAndRenderSettings() {
            const container = document.getElementById('server-settings-container');
            if (!container) return;

            try {
                const res = await fetch('/server-settings');
                if (!res.ok) return;
                const data = await res.json();
                console.debug('fetch /server-settings ->', data);
                const fields = data.fields || [];
                if (!fields.length) {
                    const info = data.file_info || {};
                    container.innerHTML = `<p>${t('config.no_settings')} arquivo_exists=${info.exists} size=${info.size}</p>`;
                    return;
                }
                container.innerHTML = renderSettingsFields(fields);
                bindSettingsFieldEvents();
            } catch (err) {
                // ignore
            }
        }

        async function saveLanguageForm() {
            const select = document.getElementById('language-select');
            if (!select) return;
            const lang = select.value;
            try {
                await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ language: lang }),
                });
            } catch (e) {
                // ignore
            }
        }

        async function saveServerSettingsForm(e) {
            if (e) e.preventDefault();
            const form = document.getElementById('server-settings-form');
            if (!form) return;
            const formData = new FormData(form);
            try {
                await fetch('/server-settings', {
                    method: 'POST',
                    body: formData,
                });
                fetchAndRenderSettings();
            } catch (err) {
                // ignore
            }
        }

        const SETTINGS_META = {
            name: { label: t('settings.name'), category: t('settings.cat_general'), open: true },
            description: { label: t('settings.description'), category: t('settings.cat_general'), open: true },
            tags: { label: t('settings.tags'), category: t('settings.cat_general'), open: true, type: 'tags' },
            game_password: { label: t('settings.game_password'), category: t('settings.cat_general'), open: true, type: 'password' },

            visibility: { label: t('settings.visibility'), category: t('settings.cat_network'), open: true, type: 'visibility' },
            'visibility.public': { label: t('settings.visibility_public'), category: t('settings.cat_network') },
            'visibility.lan': { label: t('settings.visibility_lan'), category: t('settings.cat_network') },
            require_user_verification: { label: t('settings.require_user_verification'), category: t('settings.cat_network'), open: true },

            username: { label: t('settings.username'), category: t('settings.cat_advanced'), type: 'password', hint: t('settings.username_hint') },
            password: { label: t('settings.password'), category: t('settings.cat_advanced'), type: 'password', hint: t('settings.password_hint') },
            token: { label: t('settings.token'), category: t('settings.cat_advanced'), type: 'password', hint: t('settings.token_hint') },

            max_players: {
                label: t('settings.max_players'), category: t('settings.cat_players'), open: true, min: 0, step: 1,
                hint: t('settings.max_players_hint'),
            },
            ignore_player_limit_for_returning_players: {
                label: t('settings.ignore_player_limit'), category: t('settings.cat_players'), open: true,
            },
            allow_commands: {
                label: t('settings.allow_commands'), category: t('settings.cat_players'), open: true, type: 'select',
                options: ['true', 'false', 'admins-only'],
                hint: t('settings.allow_commands_hint'),
            },
            afk_autokick_interval: {
                label: t('settings.afk_autokick_interval'), category: t('settings.cat_players'), open: true, min: 0, step: 1,
                hint: t('settings.afk_autokick_hint'),
            },

            autosave_interval: {
                label: t('settings.autosave_interval'), category: t('settings.cat_autosave'), open: true, min: 0, step: 1,
                hint: t('settings.autosave_interval_hint'),
            },
            autosave_slots: {
                label: t('settings.autosave_slots'), category: t('settings.cat_autosave'), open: true, min: 1, step: 1,
                hint: t('settings.autosave_slots_hint'),
            },
            autosave_only_on_server: { label: t('settings.autosave_only_on_server'), category: t('settings.cat_autosave'), open: true },
            auto_pause: { label: t('settings.auto_pause'), category: t('settings.cat_autosave'), open: true },
            auto_pause_when_players_connect: { label: t('settings.auto_pause_when_connect'), category: t('settings.cat_autosave'), open: true },
            only_admins_can_pause_the_game: { label: t('settings.only_admins_pause'), category: t('settings.cat_autosave'), open: true },
            non_blocking_saving: { label: t('settings.non_blocking_saving'), category: t('settings.cat_autosave'), open: true },

            max_upload_in_kilobytes_per_second: {
                label: t('settings.max_upload_kbps'), category: t('settings.cat_upload'), open: true, min: 0, step: 1,
                hint: t('settings.max_upload_kbps_hint'),
            },
            max_upload_slots: {
                label: t('settings.max_upload_slots'), category: t('settings.cat_upload'), open: true, min: 0, step: 1,
                hint: t('settings.max_upload_slots_hint'),
            },
            minimum_latency_in_ticks: {
                label: t('settings.min_latency_ticks'), category: t('settings.cat_upload'), open: true, min: 0, step: 1,
                hint: t('settings.min_latency_ticks_hint'),
            },
        };

        const ADVANCED_PATHS = [
            'username', 'password', 'token',
            'max_heartbeats_per_second',
            'minimum_segment_size', 'minimum_segment_size_peer_count',
            'maximum_segment_size', 'maximum_segment_size_peer_count',
        ];

        function fieldLabel(field) {
            const meta = SETTINGS_META[field.path];
            if (meta && meta.label) return meta.label;
            return field.key;
        }

        function fieldCategory(field) {
            const meta = SETTINGS_META[field.path];
            if (meta && meta.category) return meta.category;
            if (ADVANCED_PATHS.includes(field.path)) return t('settings.cat_advanced');
            if (field.type === 'object' && field.key === 'visibility') return t('settings.cat_network');
            return t('settings.cat_advanced');
        }

        function tooltipHtml(field) {
            const meta = SETTINGS_META[field.path];
            let tip = '';
            if (meta && meta.hint) tip = meta.hint;
            else if (field.comment) tip = Array.isArray(field.comment) ? field.comment.join(' ') : field.comment;
            if (!tip) return '';
            return `<span class="field-tooltip" tabindex="0" role="button" aria-label="Ajuda">ⓘ<span class="tooltip-pop">${escapeHtml(tip)}</span></span>`;
        }

        function renderInput(field) {
            const name = `settings.${escapeAttr(field.path)}`;
            const meta = SETTINGS_META[field.path] || {};

            if (meta.type === 'visibility') {
                return '';
            }
            if (meta.type === 'tags') {
                const arr = Array.isArray(field.value) ? field.value : [];
                const text = arr.join(', ');
                return `<input type="text" class="tags-input" name="${name}" value="${escapeAttr(text)}" data-tags="1" placeholder="${t('settings.tags_placeholder')}" />`;
            }
            if (meta.type === 'password') {
                return `<span class="password-field">
                    <input type="password" name="${name}" value="${escapeAttr(field.value || '')}" data-mask="1" />
                    <button type="button" class="text-button reveal-button" data-reveal>${t('config.show')}</button>
                </span>`;
            }
            if (meta.type === 'select') {
                const opts = meta.options || [];
                const sel = opts.map((o) => `<option value="${escapeAttr(o)}" ${String(field.value) === String(o) ? 'selected' : ''}>${escapeHtml(o)}</option>`).join('');
                return `<select name="${name}">${sel}</select>`;
            }
            if (field.type === 'boolean') {
                return `<select name="${name}">
                    <option value="true" ${field.value ? 'selected' : ''} data-i18n="settings.value_true">true</option>
                    <option value="false" ${!field.value ? 'selected' : ''} data-i18n="settings.value_false">false</option>
                </select>`;
            }
            if (field.type === 'integer' || field.type === 'number') {
                const min = meta.min !== undefined ? `min="${meta.min}"` : '';
                const max = meta.max !== undefined ? `max="${meta.max}"` : '';
                const step = meta.step !== undefined ? `step="${meta.step}"` : '';
                return `<input type="number" name="${name}" value="${escapeAttr(field.value)}" ${min} ${max} ${step} />`;
            }
            if (field.type === 'json') {
                return `<textarea name="${name}" rows="6">${escapeHtml(field.value || '')}</textarea>`;
            }
            return `<input type="text" name="${name}" value="${escapeAttr(field.value || '')}" />`;
        }

        function renderVisibilityChildren(children) {
            return children.map((child) => {
                const cname = `settings.${escapeAttr(child.path)}`;
                const checked = child.value ? 'checked' : '';
                const label = fieldLabel(child);
                return `<label class="checkbox-row">
                    <input type="checkbox" name="${cname}" value="true" data-bool="1" ${checked} />
                    <input type="hidden" name="${cname}" value="${child.value ? 'true' : 'false'}" data-bool-hidden="1" />
                    <span>${escapeHtml(label)}</span>
                </label>`;
            }).join('');
        }

        function renderField(field) {
            if (field.type === 'object') {
                if (field.key === 'visibility') {
                    return `<div class="field-row">
                        <div class="field-label">${escapeHtml(fieldLabel(field))} ${tooltipHtml(field)}</div>
                        <div class="visibility-box">
                            ${renderVisibilityChildren(field.children || [])}
                        </div>
                    </div>`;
                }
                return `<div class="field-row">
                    <div class="field-label">${escapeHtml(fieldLabel(field))} ${tooltipHtml(field)}</div>
                    <div class="object-children">
                        ${(field.children || []).map(renderField).join('')}
                    </div>
                </div>`;
            }

            if (SETTINGS_META[field.path] && SETTINGS_META[field.path].type === 'visibility') return '';

            return `<div class="field-row">
                <div class="field-label">${escapeHtml(fieldLabel(field))} ${tooltipHtml(field)}</div>
                ${renderInput(field)}
            </div>`;
        }

        function renderSettingsFields(fields) {
            const categories = {
                [t('settings.cat_general')]: [], [t('settings.cat_network')]: [], [t('settings.cat_players')]: [], [t('settings.cat_autosave')]: [], [t('settings.cat_upload')]: [], [t('settings.cat_advanced')]: [],
            };

            for (const field of fields) {
                const cat = fieldCategory(field);
                (categories[cat] || categories[t('settings.cat_advanced')]).push(field);
            }

            const columnLeft = [t('settings.cat_general'), t('settings.cat_players'), t('settings.cat_upload')];
            const columnRight = [t('settings.cat_network'), t('settings.cat_autosave'), t('settings.cat_advanced')];

            function renderColumn(cats) {
                return cats.map((cat) => {
                    const items = categories[cat] || [];
                    if (!items.length) return '';
                    const open = (SETTINGS_META[items[0].path] && SETTINGS_META[items[0].path].open) || false;
                    const openAttr = open ? 'open' : '';
                    const body = items.map(renderField).join('');
                    return `<details class="settings-section" ${openAttr} data-category="${escapeAttr(cat)}">
                        <summary><span class="summary-icon">${open ? '▼' : '▶'}</span>${escapeHtml(cat)}</summary>
                        <div class="section-body">${body}</div>
                    </details>`;
                }).join('');
            }

            return `<div class="settings-columns">
                <div class="settings-column">${renderColumn(columnLeft)}</div>
                <div class="settings-column">${renderColumn(columnRight)}</div>
            </div>`;
        }

        function bindSettingsFieldEvents() {
            document.querySelectorAll('#server-settings-container .reveal-button').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const input = btn.parentElement.querySelector('input[data-mask]');
                    if (!input) return;
                    if (input.type === 'password') {
                        input.type = 'text';
                        btn.textContent = t('config.hide');
                    } else {
                        input.type = 'password';
                        btn.textContent = t('config.show');
                    }
                });
            });

            document.querySelectorAll('#server-settings-container details.settings-section').forEach((det) => {
                const summary = det.querySelector('summary');
                if (!summary) return;
                summary.addEventListener('click', (e) => {
                    e.preventDefault();
                    det.open = !det.open;
                    const icon = summary.querySelector('.summary-icon');
                    if (icon) icon.textContent = det.open ? '▼' : '▶';
                });
            });

            document.querySelectorAll('#server-settings-container input[data-bool]').forEach((cb) => {
                const hidden = cb.parentElement.querySelector('input[data-bool-hidden]');
                if (!hidden) return;
                cb.addEventListener('change', () => {
                    hidden.value = cb.checked ? 'true' : 'false';
                });
            });

            const form = document.getElementById('server-settings-form');
            if (form && !form.dataset.bound) {
                form.dataset.bound = '1';
                form.addEventListener('submit', () => {
                    document.querySelectorAll('#server-settings-container input[data-tags]').forEach((input) => {
                        const parts = input.value.split(',').map((p) => p.trim()).filter((p) => p.length);
                        const hidden = document.createElement('input');
                        hidden.type = 'hidden';
                        hidden.name = input.name;
                        hidden.value = JSON.stringify(parts);
                        input.name = '';
                        form.appendChild(hidden);
                    });
                });
            }

            const toggleAll = document.getElementById('toggle-all-sections');
            if (toggleAll) {
                toggleAll.onclick = () => {
                    const sections = document.querySelectorAll('#server-settings-container details.settings-section');
                    const anyClosed = Array.from(sections).some((s) => !s.open);
                    sections.forEach((s) => {
                        s.open = anyClosed;
                        const icon = s.querySelector('.summary-icon');
                        if (icon) icon.textContent = anyClosed ? '▼' : '▶';
                    });
                    toggleAll.textContent = anyClosed ? t('config.collapse_all') : t('config.expand_all');
                };
            }
        }

        const languageForm = document.getElementById('language-form');
        if (languageForm) {
            languageForm.addEventListener('submit', (e) => {
                e.preventDefault();
                saveLanguageForm();
            });
        }

        const serverSettingsForm = document.getElementById('server-settings-form');
        if (serverSettingsForm) {
            serverSettingsForm.addEventListener('submit', (e) => {
                saveServerSettingsForm(e);
            });
        }
