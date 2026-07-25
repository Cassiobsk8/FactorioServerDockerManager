        const wbState = {
            worldConfig: {
                world_name: '',
                seed: null,
                random_seed: true,
                planet: 'nauvis',
                settings: {},
                map_settings: {},
            },
            preview: {
                hash: null,
                config: null,
                isLoading: false,
                autoUpdate: false,
                autoUpdateTimer: null,
                pendingAutoUpdate: false,
            },
            resourceFields: [],
            terrainFeatureFields: [],
            resourcePreviousValues: {},
            enemyBasesPreviousValues: {},
            glebaEnemyBasesPreviousValues: {},
            ui: {
                factorioValid: true,
            },
        };

        const FACTORIO_SLIDER_VALUES = [0.166666667, 0.25, 0.333333333, 0.5, 0.75, 1, 1.333333333, 1.5, 2, 3, 4, 6];
        const FACTORIO_SLIDER_LABELS = ['17%', '25%', '33%', '50%', '75%', '100%', '133%', '150%', '200%', '300%', '400%', '600%'];

        function factorioValueToIndex(value) {
            if (typeof value !== 'number' || !isFinite(value)) return 5;
            let closestIndex = 0;
            let closestDiff = Math.abs(FACTORIO_SLIDER_VALUES[0] - value);
            for (let i = 1; i < FACTORIO_SLIDER_VALUES.length; i++) {
                const diff = Math.abs(FACTORIO_SLIDER_VALUES[i] - value);
                if (diff < closestDiff) {
                    closestDiff = diff;
                    closestIndex = i;
                }
            }
            return closestIndex;
        }

        function factorioIndexToValue(index) {
            const i = Math.max(0, Math.min(11, Math.round(index)));
            return FACTORIO_SLIDER_VALUES[i];
        }

        function factorioIndexToLabel(index) {
            const i = Math.max(0, Math.min(11, Math.round(index)));
            return FACTORIO_SLIDER_LABELS[i];
        }

        const PLANET_ICONS = {
            'nauvis': '🌎',
            'vulcanus': '🌋',
            'gleba': '🌿',
            'fulgora': '⚡',
            'aquilo': '🧊'
        };

        function getPlanetDisplay(field) {
            const planets = field.planet_exclusive;
            if (planets && planets.length > 0) {
                const planet = planets[0];
                const icon = PLANET_ICONS[planet] || '';
                const name = planet.charAt(0).toUpperCase() + planet.slice(1);
                return { icon, name };
            }
            return { icon: PLANET_ICONS['nauvis'] || '🌎', name: 'Nauvis' };
        }

        function formatPlanet(field) {
            const { icon, name } = getPlanetDisplay(field);
            return `${icon} ${name}`;
        }

        function getAutoplaceControlDefaults(resourceId) {
            const field = [...wbState.resourceFields, ...wbState.terrainFeatureFields, ...wbState.cliffFields]
                .find(candidate => candidate.id === `autoplace_controls.${resourceId}`);
            const defaults = field && field.default;
            return defaults && typeof defaults === 'object' && !Array.isArray(defaults)
                ? { ...defaults }
                : {};
        }

        function isAutoplaceControlDisabled(values, controls) {
            return controls.every(control => values && [0, 'none'].includes(values[control]));
        }

        let worldBuilderInitialized = false;
        function generateRandomSeed() {
            return Math.floor(Math.random() * 1000000000);
        }

        function getCurrentConfig() {
            return { ...wbState.worldConfig };
        }

        function updateWorldConfig(partial) {
            if (partial.world_name !== undefined) {
                wbState.worldConfig.world_name = (partial.world_name || '').trim();
            }
            if (partial.seed !== undefined) {
                const trimmed = partial.seed == null ? null : String(partial.seed).trim();
                wbState.worldConfig.seed = trimmed;
                wbState.worldConfig.random_seed = !trimmed;
            }
            if (partial.planet !== undefined) {
                wbState.worldConfig.planet = partial.planet || 'nauvis';
            }
        }

        async function fetchCurrentConfigHash() {
            const config = getCurrentConfig();
            try {
                const res = await fetch('/api/world-builder/config-hash', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config),
                });
                if (!res.ok) return null;
                const data = await res.json();
                return data.config_hash || null;
            } catch (err) {
                return null;
            }
        }

        async function refreshPreviewStatus() {
            const configHash = await fetchCurrentConfigHash();
            if (!configHash) {
                setPreviewStatus('error');
                return;
            }

            const createButton = document.getElementById('wb-create-world');

            if (configHash !== wbState.preview.hash) {
                setPreviewStatus('outdated');
                if (createButton) createButton.disabled = true;
            } else {
                setPreviewStatus('ready');
                if (createButton) createButton.disabled = false;
            }
        }

        async function loadWorldBuilderOptions() {
            const planetSelect = document.getElementById('wb-planet');
            if (!planetSelect) return;

            try {
                const cached = AppState.get('worldBuilderOptions');
                const data = cached || await BootstrapCache.get('world-builder-options', async () => {
                    const res = await fetch('/api/world-builder/options?planet=' + encodeURIComponent(planetSelect.value || 'nauvis'));
                    if (!res.ok) throw new Error('options_failed');
                    return res.json();
                });

                const currentValue = planetSelect.value;
                planetSelect.innerHTML = '';
                (data.planets || []).forEach((planet) => {
                    const option = document.createElement('option');
                    option.value = planet;
                    option.textContent = planet;
                    planetSelect.appendChild(option);
                });
                if (currentValue && data.planets.includes(currentValue)) {
                    planetSelect.value = currentValue;
                }
            } catch (err) {
                // ignore
            }
        }

        async function checkWorldBuilderStatus() {
            const banner = document.getElementById('wb-status-banner');
            const updateButton = document.getElementById('wb-update-preview');
            const createButton = document.getElementById('wb-create-world');
            const generateButton = document.getElementById('wb-generate-seed');
            const inputs = document.querySelectorAll('#world-builder-form input, #world-builder-form select');

            try {
                const cached = AppState.get('worldBuilderStatus');
                const data = cached || await BootstrapCache.get('world-builder-status', async () => {
                    const res = await fetch('/api/world-builder/status');
                    if (!res.ok) throw new Error('status_check_failed');
                    return res.json();
                });
                wbState.ui.factorioValid = !!data.valid;

                if (!wbState.ui.factorioValid) {
                    if (banner) {
                        banner.style.display = 'flex';
                        const title = banner.querySelector('[data-i18n="world_builder.status.unavailable"]');
                        const detail = banner.querySelector('[data-i18n="world_builder.status.unavailable_detail"]');
                        if (data.reason === 'not_installed') {
                            if (title) title.textContent = t('world_builder.status.unavailable');
                            if (detail) detail.textContent = t('world_builder.status.not_installed_detail');
                        } else {
                            if (title) title.textContent = t('world_builder.status.unavailable');
                            if (detail) detail.textContent = data.message || t('world_builder.status.unavailable_detail');
                        }
                    }
                    [updateButton, createButton, generateButton].forEach((btn) => {
                        if (btn) btn.disabled = true;
                    });
                    inputs.forEach((input) => {
                        input.disabled = true;
                    });
                } else {
                    if (banner) banner.style.display = 'none';
                    [updateButton, createButton, generateButton].forEach((btn) => {
                        if (btn) btn.disabled = false;
                    });
                    inputs.forEach((input) => {
                        input.disabled = false;
                    });
                }
            } catch (err) {
                wbState.ui.factorioValid = false;
                if (banner) banner.style.display = 'flex';
                [updateButton, createButton, generateButton].forEach((btn) => {
                    if (btn) btn.disabled = true;
                });
                inputs.forEach((input) => {
                    input.disabled = true;
                });
            }
        }

        function setPreviewStatus(status) {
            const badge = document.getElementById('wb-preview-status');
            const container = document.getElementById('wb-preview-container');
            const image = document.getElementById('wb-preview-image');
            const placeholder = container ? container.querySelector('.preview-placeholder') : null;

            if (!badge || !container) return;

            badge.className = 'badge';

            if (status === 'ready') {
                badge.classList.add('badge-active');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.updated');
                badge.textContent = t('world_builder.preview.status.updated');
                container.classList.remove('outdated');
            } else if (status === 'outdated') {
                badge.classList.add('badge-inactive');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.outdated');
                badge.textContent = t('world_builder.preview.status.outdated');
                container.classList.add('outdated');
            } else if (status === 'generating') {
                badge.classList.add('badge-active');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.generating');
                badge.textContent = t('world_builder.preview.status.generating');
                container.classList.remove('outdated');
            } else if (status === 'error') {
                badge.classList.add('badge-inactive');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.error');
                badge.textContent = t('world_builder.preview.status.error');
                container.classList.add('outdated');
            } else {
                badge.classList.add('badge-inactive');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.outdated');
                badge.textContent = t('world_builder.preview.status.outdated');
                container.classList.add('outdated');
            }
        }

        function markPreviewOutdated() {
            wbState.preview.hash = null;
            wbState.preview.config = null;
            setPreviewStatus('outdated');

            const createButton = document.getElementById('wb-create-world');
            if (createButton) {
                createButton.disabled = true;
            }

            if (wbState.preview.autoUpdate) {
                wbState.preview.pendingAutoUpdate = true;
                if (wbState.preview.autoUpdateTimer) {
                    clearTimeout(wbState.preview.autoUpdateTimer);
                }
                wbState.preview.autoUpdateTimer = setTimeout(() => {
                    wbState.preview.autoUpdateTimer = null;
                    if (wbState.preview.pendingAutoUpdate) {
                        wbState.preview.pendingAutoUpdate = false;
                        updatePreview();
                    }
                }, 500);
            }
        }

        async function updatePreview() {
            if (wbState.preview.isLoading) {
                if (wbState.preview.autoUpdate) {
                    wbState.preview.pendingAutoUpdate = true;
                }
                return;
            }

            if (!wbState.worldConfig.world_name) {
                alert(t('error.create_world_failed'));
                return;
            }

            wbState.preview.isLoading = true;
            const updateButton = document.getElementById('wb-update-preview');
            const createButton = document.getElementById('wb-create-world');
            if (updateButton) updateButton.disabled = true;
            if (createButton) createButton.disabled = true;

            setPreviewStatus('generating');

            try {
                const res = await fetch('/api/world-builder/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(getCurrentConfig()),
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    alert(t('world_builder.error.preview_failed') + ': ' + (err.error || err.message || res.statusText));
                    setPreviewStatus('error');
                    return;
                }

                const data = await res.json();
                wbState.preview.hash = data.preview_hash;
                wbState.preview.config = getCurrentConfig();

                console.log('[WorldBuilder] Preview image generated.');

                const image = document.getElementById('wb-preview-image');
                const container = document.getElementById('wb-preview-container');
                const placeholder = container ? container.querySelector('.preview-placeholder') : null;

                if (image && data.preview_url) {
                    image.src = data.preview_url;
                    image.style.display = 'block';
                    image.onload = () => {
                        const scrollContainer = document.getElementById('wb-preview-container');
                        if (scrollContainer) {
                            scrollContainer.scrollLeft = (scrollContainer.scrollWidth - scrollContainer.clientWidth) / 2;
                            scrollContainer.scrollTop = (scrollContainer.scrollHeight - scrollContainer.clientHeight) / 2;
                        }
                    };
                }
                if (placeholder) {
                    placeholder.style.display = 'none';
                }
                setPreviewStatus('ready');
            } catch (err) {
                alert(t('world_builder.error.preview_failed'));
                setPreviewStatus('error');
            } finally {
                wbState.preview.isLoading = false;
                if (updateButton) updateButton.disabled = false;
                if (createButton) createButton.disabled = false;
                if (wbState.preview.pendingAutoUpdate) {
                    wbState.preview.pendingAutoUpdate = false;
                    updatePreview();
                }
            }
        }

        async function createWorld() {
            if (wbState.preview.isLoading) return;

            if (!wbState.worldConfig.world_name) {
                alert(t('error.create_world_failed'));
                return;
            }

            if (!wbState.preview.hash) {
                alert(t('world_builder.error.preview_failed'));
                return;
            }

            const createButton = document.getElementById('wb-create-world');
            if (createButton) createButton.disabled = true;

            try {
                const res = await fetch('/api/world-builder/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ...getCurrentConfig(),
                        preview_hash: wbState.preview.hash,
                    }),
                });

                if (!res.ok && res.status !== 201) {
                    const err = await res.json().catch(() => ({}));
                    alert(t('world_builder.error.create_failed') + ': ' + (err.error || err.message || res.statusText));
                    return;
                }

                const data = await res.json();
                alert(t('world_builder.create_world') + ': ' + (data.save_file || wbState.worldConfig.world_name));
                markPreviewOutdated();
            } catch (err) {
                alert(t('world_builder.error.create_exception'));
            } finally {
                if (createButton) createButton.disabled = false;
            }
        }

        function createSliderPlaceholder(label) {
            return `<div class="wb-placeholder-slider">
                <label><span>${label}</span>
                    <input type="range" min="0" max="100" value="50" disabled />
                </label>
            </div>`;
        }

        function createCheckboxPlaceholder(label) {
            return `<label class="wb-placeholder-checkbox">
                <input type="checkbox" disabled />
                <span>${label}</span>
            </label>`;
        }

        function createSelectPlaceholder(label, options) {
            const opts = (options || []).map(o => `<option>${o}</option>`).join('');
            return `<label class="wb-placeholder-select">
                <span>${label}</span>
                <select disabled>${opts}</select>
            </label>`;
        }

        function createDiscreteSlider(name, currentIndex, disabled) {
            const index = Math.max(0, Math.min(11, Math.round(currentIndex)));
            return `<input type="range" class="wb-table-discrete-input" data-control="${name}" min="0" max="11" step="1" value="${index}" ${disabled ? 'disabled' : ''} /><span class="wb-table-value" data-control="${name}">${factorioIndexToLabel(index)}</span>`;
        }

        function createResourceCheckbox(name, checked, disabled) {
            return `<input type="checkbox" class="wb-table-checkbox" data-control="${name}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''} />`;
        }

        function handleResourceEnableChange(e) {
            const input = e.target;
            const row = input.closest('.wb-table-row');
            if (!row) return;

            const resourceId = row.dataset.resource;
            const enabled = input.checked;
            const sliders = row.querySelectorAll('.wb-table-discrete-input');
            const valueSpans = row.querySelectorAll('.wb-table-value');
            const defaultValues = {frequency: 1, size: 1, richness: 1};

            if (enabled) {
                const prev = wbState.resourcePreviousValues[resourceId] || defaultValues;
                wbState.worldConfig.settings.autoplace_controls[resourceId] = { ...prev };

                sliders.forEach(slider => {
                    slider.disabled = false;
                    const control = slider.dataset.control;
                    const val = prev[control] != null ? prev[control] : defaultValues[control];
                    slider.value = factorioValueToIndex(val);
                    const span = slider.parentElement.querySelector(`.wb-table-value[data-control="${control}"]`);
                    if (span) span.textContent = factorioIndexToLabel(factorioValueToIndex(val));
                });
            } else {
                const current = wbState.worldConfig.settings.autoplace_controls[resourceId] || defaultValues;
                wbState.resourcePreviousValues[resourceId] = JSON.parse(JSON.stringify({ ...current }));
                wbState.worldConfig.settings.autoplace_controls[resourceId] = {
                    frequency: current.frequency != null ? current.frequency : 1,
                    size: 0,
                    richness: current.richness != null ? current.richness : 1,
                };

                sliders.forEach(slider => {
                    slider.disabled = true;
                    const control = slider.dataset.control;
                    const val = current[control] != null ? current[control] : defaultValues[control];
                    slider.value = factorioValueToIndex(val);
                    const span = slider.parentElement.querySelector(`.wb-table-value[data-control="${control}"]`);
                    if (span) span.textContent = factorioIndexToLabel(factorioValueToIndex(val));
                });
            }

            markPreviewOutdated();
        }

        function createSection(title, content) {
            return `<div class="wb-section">
                <h3 class="wb-section-title">${title}</h3>
                <div class="wb-section-body">${content}</div>
            </div>`;
        }

        function createGroup(title, content) {
            return `<div class="wb-group">
                <h4 class="wb-group-title">${title}</h4>
                <div class="wb-group-body">${content}</div>
            </div>`;
        }

        function createResourceRow(name) {
            return `<div class="wb-table-row">
                ${createCheckboxPlaceholder(name)}
                ${createSliderPlaceholder('Frequency')}
                ${createSliderPlaceholder('Size')}
                ${createSliderPlaceholder('Richness')}
            </div>`;
        }

        function createMapTypeSelect() {
            return `<div class="wb-map-type-row">
                <span class="wb-map-type-label">Tipo de Mapa</span>
                <select class="wb-map-type-select">
                    <option value="default" selected>Elevação Nauvis (Padrão)</option>
                    <option value="lake">Elevação de Lagos</option>
                    <option value="island">Elevação da Ilha</option>
                </select>
            </div>`;
        }

        function createTerrainGroup(headerHtml, rowsHtml, groupClass = '') {
            return `<div class="wb-terrain-group ${groupClass}">
                <div class="wb-terrain-table wb-table">
                    <div class="wb-terrain-table-header">${headerHtml}</div>
                    <div class="wb-table-body">${rowsHtml}</div>
                </div>
            </div>`;
        }

        function createTerrainGroupRow(name, planetHtml, slider1, slider2, dataField) {
            const rowAttrs = dataField ? ` data-field="${dataField}"` : '';
            return `<div class="wb-table-row"${rowAttrs}>
                <div class="wb-terrain-name">
                    <span class="wb-table-label">${name}</span>
                </div>
                <span class="wb-table-planet" title="${planetHtml.name}">${planetHtml.icon}</span>
                <label class="wb-table-slider">${slider1}</label>
                <label class="wb-table-slider">${slider2}</label>
            </div>`;
        }

        function createTerrainSlider(name) {
            return `<input type="range" class="wb-table-discrete-input" data-control="${name}" min="0" max="11" step="1" value="5" disabled />
                    <span class="wb-table-value" data-control="${name}">100%</span>`;
        }

        function createBiasSlider(name) {
            return `<input type="range" class="wb-bias-input" data-control="${name}" min="-0.50" max="0.50" step="0.05" value="0.00" disabled />
                    <span class="wb-bias-value" data-control="${name}">0.00</span>`;
        }

        function createTerrainDivider() {
            return `<div class="wb-terrain-divider"></div>`;
        }

        function createEnemyRowWithCheckbox(name, slider1, slider2) {
            return `<div class="wb-enemy-row">
                ${createCheckboxPlaceholder(name)}
                ${createSliderPlaceholder(slider1)}
                ${createSliderPlaceholder(slider2)}
            </div>`;
        }

        function createEnemyCheckboxRow(name) {
            return `<div class="wb-enemy-row">
                ${createCheckboxPlaceholder(name)}
            </div>`;
        }

        function createEnemySliderRow(label) {
            return `<div class="wb-enemy-slider-row">
                ${createSliderPlaceholder(label)}
            </div>`;
        }

        function createEnemySlidersRow(label1, label2, label3) {
            return `<div class="wb-enemy-row">
                ${createSliderPlaceholder(label1)}
                ${createSliderPlaceholder(label2)}
                ${createSliderPlaceholder(label3)}
            </div>`;
        }

        function createNumericSlider(name, min, max, step, defaultValue) {
            const value = defaultValue != null ? defaultValue : min;
            return `<div class="wb-numeric-slider">
                <input type="range" class="wb-numeric-slider-input" data-control="${name}" min="${min}" max="${max}" step="${step}" value="${value}" />
                <input type="number" class="wb-numeric-slider-value" data-control="${name}" min="${min}" max="${max}" step="${step}" value="${value}" />
            </div>`;
        }

        async function loadResourceFields() {
            if (wbState.resourceFields.length > 0 && wbState.terrainFeatureFields.length > 0) return;

            try {
                const res = await fetch('/api/world-builder/config-engine?source_file=map-gen-settings.json');
                if (!res.ok) {
                    renderResourcesError('Failed to load resource configuration');
                    return;
                }
                const data = await res.json();

                const autoplaceFields = (data.fields || []).filter(f => {
                    const id = f.id || '';
                    const isAutoplaceControl = id.startsWith('autoplace_controls.');
                    const byOriginalType = f.original_type === 'AutoplaceControl';
                    const byFormType = f.type === 'AutoplaceControl' || (f.type === 'group' && byOriginalType);
                    return isAutoplaceControl || byFormType;
                });
                const fields = autoplaceFields.filter(f => {
                    const category = f.category || '';
                    const isResource = category === 'Resources';
                    return isResource;
                });

                const terrainFeatureIds = [
                    'water',
                    'trees',
                    'rocks',
                    'starting_area_moisture',
                    'vulcanus_volcanism',
                    'gleba_water',
                    'gleba_plants',
                    'fulgora_islands',
                ];
                const terrainFieldsById = new Map(autoplaceFields.map(field => [
                    field.id.replace('autoplace_controls.', ''),
                    field,
                ]));
                const terrainFields = terrainFeatureIds
                    .map(id => terrainFieldsById.get(id))
                    .filter(Boolean);

                const cliffIds = [
                    'nauvis_cliff',
                    'gleba_cliff',
                    'fulgora_cliff',
                ];
                const cliffFieldsById = new Map(autoplaceFields.map(field => [
                    field.id.replace('autoplace_controls.', ''),
                    field,
                ]));
                const cliffFields = cliffIds
                    .map(id => cliffFieldsById.get(id))
                    .filter(Boolean);

                fields.sort((a, b) => {
                    const orderA = a.order || '';
                    const orderB = b.order || '';
                    if (orderA !== orderB) return orderA < orderB ? -1 : orderA > orderB ? 1 : 0;
                    const labelA = (a.label || a.id || '').toLowerCase();
                    const labelB = (b.label || b.id || '').toLowerCase();
                    return labelA < labelB ? -1 : labelA > labelB ? 1 : 0;
                });

                if (!fields.length) {
                    renderResourcesError('No resource controls found in schema');
                    console.warn('[WorldBuilder] Resource fields not found in config-engine payload', data);
                    return;
                }

                wbState.resourceFields = fields;
                wbState.terrainFeatureFields = terrainFields;
                wbState.cliffFields = cliffFields;

                if (!wbState.worldConfig.settings) {
                    wbState.worldConfig.settings = {};
                }
                if (!wbState.worldConfig.settings.autoplace_controls) {
                    wbState.worldConfig.settings.autoplace_controls = {};
                }

                renderResources(fields);
                renderTerrainFeatures(terrainFields);
                renderCliffs(cliffFields);
                renderMoistureTerrain();
            } catch (err) {
                renderResourcesError('Failed to load resources');
                console.warn('[WorldBuilder] Error loading resource fields:', err);
            }
        }

        function renderResourcesError(message) {
            const panel = document.getElementById('wb-tab-resources');
            if (!panel) return;
            const table = panel.querySelector('.wb-table');
            const body = table ? table.querySelector('.wb-table-body') : null;
            if (!body) return;
            body.innerHTML = `<div class="wb-table-error">${message}</div>`;
        }

        function renderResources(fields) {
            const panel = document.getElementById('wb-tab-resources');
            if (!panel || !fields.length) return;

            const body = panel.querySelector('.wb-table-body');
            if (!body) return;

            body.innerHTML = fields.map(field => {
                const resourceId = field.id.replace('autoplace_controls.', '');
                const planetDisplay = getPlanetDisplay(field);
                const rawDefaults = field.default || {};
                const controlDefaults = (rawDefaults && typeof rawDefaults === 'object' && !Array.isArray(rawDefaults))
                    ? rawDefaults
                    : {frequency: 1, size: 1, richness: 1};
                const current = (wbState.worldConfig.settings && wbState.worldConfig.settings.autoplace_controls && wbState.worldConfig.settings.autoplace_controls[resourceId]) || controlDefaults;

                const isDisabled = isAutoplaceControlDisabled(current, ['frequency', 'size', 'richness']);
                const displayValues = (isDisabled && wbState.resourcePreviousValues[resourceId])
                    ? wbState.resourcePreviousValues[resourceId]
                    : current;
                const effective = displayValues || controlDefaults;

                const freq = (effective && effective.frequency != null) ? effective.frequency : controlDefaults.frequency;
                const size = (effective && effective.size != null) ? effective.size : controlDefaults.size;
                const richness = (effective && effective.richness != null) ? effective.richness : controlDefaults.richness;

                const canBeDisabled = field.can_be_disabled !== false;

                const i18nKey = `world_builder.resource.${resourceId.replace(/-/g, '_')}`;

                return `<div class="wb-table-row" data-resource="${resourceId}">
                    <label class="wb-table-checkbox-wrapper">
                        ${canBeDisabled ? `<input type="checkbox" class="wb-table-checkbox" data-control="enabled" ${isDisabled ? '' : 'checked'} />` : ''}
                    </label>
                    <span class="wb-table-label" data-i18n="${i18nKey}">${field.label || resourceId}</span>
                    <span class="wb-table-planet" title="${planetDisplay.name}">${planetDisplay.icon}</span>
                    <label class="wb-table-slider">
                        ${createDiscreteSlider('frequency', factorioValueToIndex(freq), isDisabled)}
                    </label>
                    <label class="wb-table-slider">
                        ${createDiscreteSlider('size', factorioValueToIndex(size), isDisabled)}
                    </label>
                    <label class="wb-table-slider">
                        ${createDiscreteSlider('richness', factorioValueToIndex(richness), isDisabled)}
                    </label>
                </div>`;
            }).join('');

            body.querySelectorAll('.wb-table-discrete-input').forEach(input => {
                input.addEventListener('input', handleResourceChange);
                input.addEventListener('change', handleResourceChange);
            });

            body.querySelectorAll('.wb-table-checkbox').forEach(input => {
                input.addEventListener('change', handleResourceEnableChange);
            });
        }

        function renderTerrainFeatures(fields) {
            const panel = document.getElementById('wb-tab-terrain');
            if (!panel || !fields.length) return;

            const body = panel.querySelector('.wb-terrain-features .wb-table-body');
            if (!body) return;

            body.innerHTML = fields.map(field => {
                const resourceId = field.id.replace('autoplace_controls.', '');
                const planetDisplay = getPlanetDisplay(field);
                const rawDefaults = field.default || {};
                const controlDefaults = (rawDefaults && typeof rawDefaults === 'object' && !Array.isArray(rawDefaults))
                    ? rawDefaults
                    : {frequency: 1, size: 1};
                const current = (wbState.worldConfig.settings && wbState.worldConfig.settings.autoplace_controls && wbState.worldConfig.settings.autoplace_controls[resourceId]) || controlDefaults;
                const canBeDisabled = field.can_be_disabled !== false;
                const isDisabled = canBeDisabled && isAutoplaceControlDisabled(current, ['frequency', 'size']);
                const displayValues = (isDisabled && wbState.resourcePreviousValues[resourceId])
                    ? wbState.resourcePreviousValues[resourceId]
                    : current;
                const effective = displayValues || controlDefaults;
                const frequency = effective.frequency != null ? effective.frequency : controlDefaults.frequency;
                const size = effective.size != null ? effective.size : controlDefaults.size;

                return `<div class="wb-table-row" data-resource="${resourceId}">
                    <label class="wb-terrain-name">
                        ${canBeDisabled ? `<input type="checkbox" class="wb-table-checkbox" data-control="enabled" ${isDisabled ? '' : 'checked'} />` : ''}
                        <span class="wb-table-label">${field.label || resourceId}</span>
                    </label>
                    <span class="wb-table-planet" title="${planetDisplay.name}">${planetDisplay.icon}</span>
                    <label class="wb-table-slider">
                        ${createDiscreteSlider('frequency', factorioValueToIndex(frequency), isDisabled)}
                    </label>
                    <label class="wb-table-slider">
                        ${createDiscreteSlider('size', factorioValueToIndex(size), isDisabled)}
                    </label>
                </div>`;
            }).join('');

            body.querySelectorAll('.wb-table-discrete-input').forEach(input => {
                input.addEventListener('input', handleResourceChange);
                input.addEventListener('change', handleResourceChange);
            });
            body.querySelectorAll('.wb-table-checkbox').forEach(input => {
                input.addEventListener('change', handleResourceEnableChange);
            });
        }

        function renderCliffs(fields) {
            const panel = document.getElementById('wb-tab-terrain');
            if (!panel || !fields.length) return;

            const body = panel.querySelector('.wb-terrain-elevation .wb-table-body');
            if (!body) return;

            body.innerHTML = fields.map(field => {
                const resourceId = field.id.replace('autoplace_controls.', '');
                const planetDisplay = getPlanetDisplay(field);
                const rawDefaults = field.default || {};
                const controlDefaults = (rawDefaults && typeof rawDefaults === 'object' && !Array.isArray(rawDefaults))
                    ? rawDefaults
                    : {frequency: 1, size: 2, richness: 0};
                const current = (wbState.worldConfig.settings && wbState.worldConfig.settings.autoplace_controls && wbState.worldConfig.settings.autoplace_controls[resourceId]) || controlDefaults;
                const canBeDisabled = field.can_be_disabled !== false;
                const isDisabled = canBeDisabled && isAutoplaceControlDisabled(current, ['frequency', 'size']);
                const displayValues = (isDisabled && wbState.resourcePreviousValues[resourceId])
                    ? wbState.resourcePreviousValues[resourceId]
                    : current;
                const effective = displayValues || controlDefaults;
                const frequency = effective.frequency != null ? effective.frequency : controlDefaults.frequency;
                const continuity = ['nauvis_cliff', 'gleba_cliff', 'fulgora_cliff'].includes(resourceId) ? 1.0 : (effective.size != null ? effective.size : controlDefaults.size);

                return `<div class="wb-table-row" data-resource="${resourceId}">
                    <label class="wb-terrain-name">
                        ${canBeDisabled ? `<input type="checkbox" class="wb-table-checkbox" data-control="enabled" ${isDisabled ? '' : 'checked'} />` : ''}
                        <span class="wb-table-label">${field.label || resourceId}</span>
                    </label>
                    <span class="wb-table-planet" title="${planetDisplay.name}">${planetDisplay.icon}</span>
                    <label class="wb-table-slider">
                        ${createDiscreteSlider('frequency', factorioValueToIndex(frequency), isDisabled)}
                    </label>
                    <label class="wb-table-slider">
                        ${createDiscreteSlider('size', factorioValueToIndex(continuity), isDisabled)}
                    </label>
                </div>`;
            }).join('');

            body.querySelectorAll('.wb-table-discrete-input').forEach(input => {
                input.addEventListener('input', handleResourceChange);
                input.addEventListener('change', handleResourceChange);
            });
            body.querySelectorAll('.wb-table-checkbox').forEach(input => {
                input.addEventListener('change', handleResourceEnableChange);
            });
        }

        function renderMoistureTerrain() {
            const panel = document.getElementById('wb-tab-terrain');
            if (!panel) return;

            const moistureRow = panel.querySelector('.wb-table-row[data-field="moisture"]');
            const terrainRow = panel.querySelector('.wb-table-row[data-field="terrain"]');
            if (!moistureRow || !terrainRow) return;

            const expr = (wbState.worldConfig.settings && wbState.worldConfig.settings.property_expression_names) || {};

            [moistureRow, terrainRow].forEach(row => {
                const field = row.dataset.field;
                const freqKey = field === 'moisture' ? 'control:moisture:frequency' : 'control:aux:frequency';
                const biasKey = field === 'moisture' ? 'control:moisture:bias' : 'control:aux:bias';

                const freqStr = expr[freqKey] || '1';
                const biasStr = expr[biasKey] || '0';

                const freqVal = parseFloat(freqStr);
                const biasVal = parseFloat(biasStr);

                const freqSlider = row.querySelector('.wb-table-discrete-input');
                const freqValue = row.querySelector('.wb-table-value');
                const biasSlider = row.querySelector('.wb-bias-input');
                const biasValue = row.querySelector('.wb-bias-value');

                if (freqSlider) {
                    freqSlider.value = factorioValueToIndex(freqVal);
                    freqSlider.disabled = false;
                }
                if (freqValue) {
                    freqValue.textContent = factorioIndexToLabel(factorioValueToIndex(freqVal));
                }

                if (biasSlider) {
                    biasSlider.value = biasVal;
                    biasSlider.disabled = false;
                }
                if (biasValue) {
                    biasValue.textContent = biasVal.toFixed(2);
                }
            });

            panel.querySelectorAll('.wb-table-discrete-input').forEach(input => {
                input.addEventListener('input', handleMoistureTerrainChange);
                input.addEventListener('change', handleMoistureTerrainChange);
            });
            panel.querySelectorAll('.wb-bias-input').forEach(input => {
                input.addEventListener('input', handleMoistureTerrainChange);
                input.addEventListener('change', handleMoistureTerrainChange);
            });
        }

        function handleMoistureTerrainChange(e) {
            const input = e.target;
            const row = input.closest('.wb-table-row');
            if (!row) return;

            const field = row.dataset.field;
            const control = input.dataset.control;

            const prop = field === 'moisture' ? 'control:moisture' : 'control:aux';
            const fullKey = `${prop}:${control}`;

            let value;
            if (control === 'frequency') {
                const index = parseInt(input.value, 10);
                value = factorioIndexToValue(index).toString();
                const valueSpan = input.parentElement.querySelector(`.wb-table-value[data-control="${control}"]`);
                if (valueSpan) valueSpan.textContent = factorioIndexToLabel(index);
            } else if (control === 'bias') {
                const num = parseFloat(input.value);
                value = num.toFixed(2);
                const valueSpan = input.parentElement.querySelector(`.wb-bias-value[data-control="${control}"]`);
                if (valueSpan) valueSpan.textContent = num.toFixed(2);
            }

            if (!wbState.worldConfig.settings) {
                wbState.worldConfig.settings = {};
            }
            if (!wbState.worldConfig.settings.property_expression_names) {
                wbState.worldConfig.settings.property_expression_names = {};
            }
            wbState.worldConfig.settings.property_expression_names[fullKey] = value;

            markPreviewOutdated();
        }

        function handleResourceChange(e) {
            const input = e.target;
            const row = input.closest('.wb-table-row');
            if (!row) return;

            const resourceId = row.dataset.resource;
            const control = input.dataset.control;
            const index = parseInt(input.value, 10);
            const value = factorioIndexToValue(index);

            const valueSpan = input.parentElement.querySelector(`.wb-table-value[data-control="${control}"]`);
            if (valueSpan) valueSpan.textContent = factorioIndexToLabel(index);

            if (!wbState.worldConfig.settings) {
                wbState.worldConfig.settings = {};
            }
            if (!wbState.worldConfig.settings.autoplace_controls) {
                wbState.worldConfig.settings.autoplace_controls = {};
            }
            if (!wbState.worldConfig.settings.autoplace_controls[resourceId]) {
                wbState.worldConfig.settings.autoplace_controls[resourceId] = getAutoplaceControlDefaults(resourceId);
            }
            wbState.worldConfig.settings.autoplace_controls[resourceId] = {
                ...getAutoplaceControlDefaults(resourceId),
                ...wbState.worldConfig.settings.autoplace_controls[resourceId],
                [control]: value,
            };

            markPreviewOutdated();
        }

        function populateTabs() {
            const resourcesPanel = document.getElementById('wb-tab-resources');
            const terrainPanel = document.getElementById('wb-tab-terrain');
            const enemyPanel = document.getElementById('wb-tab-enemy');
            const advancedPanel = document.getElementById('wb-tab-advanced');

            if (resourcesPanel) {
                resourcesPanel.innerHTML = `<div class="wb-table">
                    <div class="wb-table-header">
                        <span class="wb-table-checkbox-header"></span>
                        <span data-i18n="world_builder.resource.header.resource">Resource</span>
                        <span></span>
                        <span data-i18n="world_builder.resource.header.frequency">Frequency</span>
                        <span data-i18n="world_builder.resource.header.size">Size</span>
                        <span data-i18n="world_builder.resource.header.richness">Richness</span>
                    </div>
                    <div class="wb-table-body"></div>
                </div>`;
            }

            if (terrainPanel) {
                const nauvis = { icon: PLANET_ICONS['nauvis'], name: 'Nauvis' };

                terrainPanel.innerHTML = `${createMapTypeSelect()}
                    ${createTerrainGroup(
                        '<span></span><span></span><span data-i18n="world_builder.terrain.header.scale">Escala</span><span data-i18n="world_builder.terrain.header.coverage">Cobertura</span>',
                        '',
                        'wb-terrain-features'
                    )}
                    ${createTerrainGroup(
                        '<span></span><span></span><span data-i18n="world_builder.terrain.header.frequency">Frequência</span><span data-i18n="world_builder.terrain.header.continuity">Continuidade</span>',
                        '',
                        'wb-terrain-elevation'
                    )}
                    ${createTerrainGroup(
                        '<span></span><span></span><span data-i18n="world_builder.terrain.header.scale">Escala</span><span data-i18n="world_builder.terrain.header.bias">Viés</span>',
                        [
                            createTerrainGroupRow('Moisture', nauvis, createTerrainSlider('frequency'), createBiasSlider('bias'), 'moisture'),
                            createTerrainGroupRow('Terrain', nauvis, createTerrainSlider('frequency'), createBiasSlider('bias'), 'terrain')
                        ].join('')
                    )}`;
            }

            if (enemyPanel) {
                enemyPanel.innerHTML = `<div class="wb-enemy-table-wrapper">
                    <div class="wb-enemy-group">
                        <div class="wb-table-header">
                            <span class="wb-table-checkbox-header"></span>
                            <span data-i18n="world_builder.enemy.header.frequency">Frequency</span>
                            <span data-i18n="world_builder.enemy.header.size">Size</span>
                        </div>
                        <div class="wb-enemy-row">
                            <label class="wb-placeholder-checkbox">
                                <input type="checkbox" class="wb-table-checkbox" data-control="enemy_bases_enabled" checked />
                                <span>Enemy Bases</span>
                            </label>
                            <label class="wb-table-slider">
                                ${createDiscreteSlider('enemy_bases_frequency', 5, false)}
                            </label>
                            <label class="wb-table-slider">
                                ${createDiscreteSlider('enemy_bases_size', 5, false)}
                            </label>
                        </div>
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group">
                        <div class="wb-enemy-row">
                            <label class="wb-placeholder-checkbox">
                                <input type="checkbox" class="wb-table-checkbox" data-control="gleba_enemy_bases_enabled" checked />
                                <span>Gleba Enemy Bases</span>
                            </label>
                            <label class="wb-table-slider">
                                ${createDiscreteSlider('gleba_enemy_bases_frequency', 5, false)}
                            </label>
                            <label class="wb-table-slider">
                                ${createDiscreteSlider('gleba_enemy_bases_size', 5, false)}
                            </label>
                        </div>
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group">
                        <div class="wb-enemy-row">
                            <label class="wb-placeholder-checkbox">
                                <input type="checkbox" class="wb-table-checkbox" data-control="no_enemies" />
                                <span>No Enemies</span>
                            </label>
                        </div>
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group">
                        <div class="wb-enemy-row">
                            <label class="wb-placeholder-checkbox">
                                <input type="checkbox" class="wb-table-checkbox" data-control="peaceful_mode" />
                                <span>Peaceful Mode</span>
                            </label>
                        </div>
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group">
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Starting Area</span>
                            <label class="wb-table-slider">
                                ${createDiscreteSlider('starting_area_size', 5, false)}
                            </label>
                        </div>
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group" data-group="expansion">
                        <div class="wb-enemy-row">
                            <label class="wb-placeholder-checkbox">
                                <input type="checkbox" class="wb-table-checkbox" data-control="expansion_enabled" checked />
                                <span>Enemy Expansion</span>
                            </label>
                        </div>
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Max Expansion Distance</span>
                            ${createNumericSlider('expansion_max_distance', 2, 20, 1, 7)}
                        </div>
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Minimum Group Size</span>
                            ${createNumericSlider('expansion_min_group_size', 1, 20, 1, 5)}
                        </div>
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Maximum Group Size</span>
                            ${createNumericSlider('expansion_max_group_size', 1, 50, 1, 20)}
                        </div>
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Minimum Expansion Cooldown</span>
                            ${createNumericSlider('expansion_min_cooldown', 1, 60, 1, 4)}
                        </div>
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Maximum Expansion Cooldown</span>
                            ${createNumericSlider('expansion_max_cooldown', 5, 180, 1, 60)}
                        </div>
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group" data-group="evolution">
                        <div class="wb-enemy-row">
                            <label class="wb-placeholder-checkbox">
                                <input type="checkbox" class="wb-table-checkbox" data-control="evolution_enabled" checked />
                                <span>Evolution</span>
                            </label>
                        </div>
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Time Factor</span>
                            ${createNumericSlider('evolution_time_factor', 0, 1000, 10, 40)}
                        </div>
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Destroy Factor</span>
                            ${createNumericSlider('evolution_destroy_factor', 0, 1000, 10, 200)}
                        </div>
                        <div class="wb-enemy-slider-row">
                            <span class="wb-table-label">Pollution Factor</span>
                            ${createNumericSlider('evolution_pollution_factor', 0, 1000, 10, 9)}
                        </div>
                    </div>
                </div>`;
            }

            if (advancedPanel) {
                advancedPanel.innerHTML = [
                    createGroup('Replay', [
                        createCheckboxPlaceholder('Enabled')
                    ]),
                    createGroup('Map', [
                        createSliderPlaceholder('Width'),
                        createSliderPlaceholder('Height')
                    ]),
                    createGroup('Recipes', [
                        createSliderPlaceholder('Difficulty')
                    ]),
                    createGroup('Technology', [
                        createSliderPlaceholder('Difficulty'),
                        createSliderPlaceholder('Price Multiplier'),
                        createSliderPlaceholder('Research Queue')
                    ]),
                    createGroup('Pollution', [
                        createSliderPlaceholder('Absorption Modifier'),
                        createSliderPlaceholder('Attack Cost Modifier'),
                        createSliderPlaceholder('Minimum Damage Trees'),
                        createSliderPlaceholder('Absorbed Per Damaged Tree'),
                        createSliderPlaceholder('Diffusion Ratio')
                    ]),
                ].join('');
            }
        }

        function initWbTabs() {
            document.querySelectorAll('.wb-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    document.querySelectorAll('.wb-tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.wb-tab-panel').forEach(p => p.style.display = 'none');
                    tab.classList.add('active');
                    const panel = document.getElementById('wb-tab-' + tab.dataset.wbTab);
                    if (panel) panel.style.display = '';
                });
            });
        }

        function handleNumericSliderInput(e) {
            const input = e.target;
            const control = input.dataset.control;
            const min = parseFloat(input.min);
            const max = parseFloat(input.max);
            const step = parseFloat(input.step);
            let value = parseFloat(input.value);
            if (isNaN(value)) value = min;
            value = Math.round(value / step) * step;
            value = Math.max(min, Math.min(max, value));
            input.value = value;
            const numberInput = input.parentElement.querySelector(`.wb-numeric-slider-value[data-control="${control}"]`);
            if (numberInput) numberInput.value = value;
            syncNumericSliderPair(control, value);
            updateEnemyNumericModel(control, value);
            markPreviewOutdated();
        }

        function handleNumericInputChange(e) {
            const input = e.target;
            const control = input.dataset.control;
            const min = parseFloat(input.min);
            const max = parseFloat(input.max);
            const step = parseFloat(input.step);
            let value = parseInt(input.value, 10);
            if (isNaN(value)) value = min;
            value = Math.max(min, Math.min(max, value));
            const slider = input.parentElement.querySelector(`.wb-numeric-slider-input[data-control="${control}"]`);
            if (slider) slider.value = value;
            input.value = value;
            if (!['evolution_time_factor', 'evolution_destroy_factor', 'evolution_pollution_factor'].includes(control)) {
                value = Math.round(value / step) * step;
                if (slider) slider.value = value;
                input.value = value;
            }
            syncNumericSliderPair(control, value);
            updateEnemyNumericModel(control, value);
            markPreviewOutdated();
        }

        function syncNumericSliderPair(control, value) {
            const pairMap = {
                'expansion_min_group_size': 'expansion_max_group_size',
                'expansion_max_group_size': 'expansion_min_group_size',
                'expansion_min_cooldown': 'expansion_max_cooldown',
                'expansion_max_cooldown': 'expansion_min_cooldown'
            };
            const pairControl = pairMap[control];
            if (!pairControl) return;

            const pairInput = document.querySelector(`.wb-numeric-slider-input[data-control="${pairControl}"]`);
            const pairNumberInput = document.querySelector(`.wb-numeric-slider-value[data-control="${pairControl}"]`);
            if (!pairInput) return;

            const pairValue = parseFloat(pairInput.value);
            const pairMin = parseFloat(pairInput.min);
            const pairMax = parseFloat(pairInput.max);
            const pairStep = parseFloat(pairInput.step);

            let newPairValue = pairValue;
            if (control.includes('min')) {
                if (value > pairValue) {
                    newPairValue = Math.min(value, pairMax);
                }
            } else {
                if (value < pairValue) {
                    newPairValue = Math.max(value, pairMin);
                }
            }

            newPairValue = Math.round(newPairValue / pairStep) * pairStep;
            newPairValue = Math.max(pairMin, Math.min(pairMax, newPairValue));

            if (newPairValue !== pairValue) {
                pairInput.value = newPairValue;
                if (pairNumberInput) pairNumberInput.value = newPairValue;
            }
            if (newPairValue !== pairValue) {
                pairInput.value = newPairValue;
                if (pairNumberInput) pairNumberInput.value = newPairValue;
            }
        }

        function updateMapGenSetting(key, value) {
            if (!wbState.worldConfig.settings) {
                wbState.worldConfig.settings = {};
            }
            wbState.worldConfig.settings[key] = value;
            markPreviewOutdated();
        }

        function updateMapSetting(path, value) {
            if (!wbState.worldConfig.map_settings) {
                wbState.worldConfig.map_settings = {};
            }
            const parts = path.split('.');
            let obj = wbState.worldConfig.map_settings;
            for (let i = 0; i < parts.length - 1; i++) {
                if (!obj[parts[i]]) {
                    obj[parts[i]] = {};
                }
                obj = obj[parts[i]];
            }
            obj[parts[parts.length - 1]] = value;
            markPreviewOutdated();
        }

        function ensureAutoplaceControl(controlId) {
            if (!wbState.worldConfig.settings) {
                wbState.worldConfig.settings = {};
            }
            if (!wbState.worldConfig.settings.autoplace_controls) {
                wbState.worldConfig.settings.autoplace_controls = {};
            }
            if (!wbState.worldConfig.settings.autoplace_controls[controlId]) {
                wbState.worldConfig.settings.autoplace_controls[controlId] = { frequency: 1, size: 1, richness: 1 };
            }
            return wbState.worldConfig.settings.autoplace_controls[controlId];
        }

        function updateEnemyNumericModel(control, value) {
            const expansionMap = {
                'expansion_max_distance': 'enemy_expansion.max_expansion_distance',
                'expansion_min_group_size': 'enemy_expansion.settler_group_min_size',
                'expansion_max_group_size': 'enemy_expansion.settler_group_max_size',
                'expansion_min_cooldown': 'enemy_expansion.min_expansion_cooldown',
                'expansion_max_cooldown': 'enemy_expansion.max_expansion_cooldown'
            };
            const evolutionMap = {
                'evolution_time_factor': 'enemy_evolution.time_factor',
                'evolution_destroy_factor': 'enemy_evolution.destroy_factor',
                'evolution_pollution_factor': 'enemy_evolution.pollution_factor'
            };
            const path = expansionMap[control] || evolutionMap[control];
            if (!path) return;
            updateMapSetting(path, value);
        }

        function initEnemyTabControls() {
            const enemyBasesCheckbox = document.querySelector('[data-control="enemy_bases_enabled"]');
            if (enemyBasesCheckbox) {
                enemyBasesCheckbox.addEventListener('change', handleEnemyBasesToggle);
                handleEnemyBasesToggle();
            }

            const enemyBasesFrequency = document.querySelector('.wb-table-discrete-input[data-control="enemy_bases_frequency"]');
            const enemyBasesSize = document.querySelector('.wb-table-discrete-input[data-control="enemy_bases_size"]');
            if (enemyBasesFrequency) {
                enemyBasesFrequency.addEventListener('input', handleEnemyBaseSliderChange);
                enemyBasesFrequency.addEventListener('change', handleEnemyBaseSliderChange);
            }
            if (enemyBasesSize) {
                enemyBasesSize.addEventListener('input', handleEnemyBaseSliderChange);
                enemyBasesSize.addEventListener('change', handleEnemyBaseSliderChange);
            }

            const glebaEnemyBasesCheckbox = document.querySelector('[data-control="gleba_enemy_bases_enabled"]');
            if (glebaEnemyBasesCheckbox) {
                glebaEnemyBasesCheckbox.addEventListener('change', handleGlebaEnemyBasesToggle);
                handleGlebaEnemyBasesToggle();
            }

            const glebaFrequency = document.querySelector('.wb-table-discrete-input[data-control="gleba_enemy_bases_frequency"]');
            const glebaSize = document.querySelector('.wb-table-discrete-input[data-control="gleba_enemy_bases_size"]');
            if (glebaFrequency) {
                glebaFrequency.addEventListener('input', handleGlebaEnemyBaseSliderChange);
                glebaFrequency.addEventListener('change', handleGlebaEnemyBaseSliderChange);
            }
            if (glebaSize) {
                glebaSize.addEventListener('input', handleGlebaEnemyBaseSliderChange);
                glebaSize.addEventListener('change', handleGlebaEnemyBaseSliderChange);
            }

            const noEnemies = document.querySelector('[data-control="no_enemies"]');
            if (noEnemies) {
                noEnemies.addEventListener('change', (e) => {
                    updateMapGenSetting('no_enemies_mode', e.target.checked);
                });
            }

            const peacefulMode = document.querySelector('[data-control="peaceful_mode"]');
            if (peacefulMode) {
                peacefulMode.addEventListener('change', (e) => {
                    updateMapGenSetting('peaceful_mode', e.target.checked);
                });
            }

            const expansionEnabled = document.querySelector('[data-control="expansion_enabled"]');
            if (expansionEnabled) {
                expansionEnabled.addEventListener('change', (e) => {
                    updateMapSetting('enemy_expansion.enabled', e.target.checked);
                });
            }

            const evolutionEnabled = document.querySelector('[data-control="evolution_enabled"]');
            if (evolutionEnabled) {
                evolutionEnabled.addEventListener('change', (e) => {
                    updateMapSetting('enemy_evolution.enabled', e.target.checked);
                });
            }

            const startingArea = document.querySelector('.wb-table-discrete-input[data-control="starting_area_size"]');
            if (startingArea) {
                startingArea.addEventListener('input', handleStartingAreaChange);
                startingArea.addEventListener('change', handleStartingAreaChange);
            }
        }

        function handleEnemyBasesToggle() {
            const checkbox = document.querySelector('[data-control="enemy_bases_enabled"]');
            if (!checkbox) return;
            const enabled = checkbox.checked;
            const control = ensureAutoplaceControl('enemy-base');

            if (enabled) {
                const prev = wbState.enemyBasesPreviousValues || { frequency: 1, size: 1, richness: 1 };
                control.frequency = prev.frequency != null ? prev.frequency : 1;
                control.size = prev.size != null ? prev.size : 1;
                control.richness = prev.richness != null ? prev.richness : 1;
            } else {
                wbState.enemyBasesPreviousValues = { ...control };
                control.size = 0;
            }

            document.querySelectorAll('.wb-table-discrete-input[data-control^="enemy_bases_"]').forEach(slider => {
                slider.disabled = !enabled;
                const ctrl = slider.dataset.control;
                const field = ctrl.replace('enemy_bases_', '');
                const val = control[field] != null ? control[field] : 1;
                slider.value = factorioValueToIndex(val);
                const span = slider.parentElement.querySelector(`.wb-table-value[data-control="${ctrl}"]`);
                if (span) span.textContent = factorioIndexToLabel(factorioValueToIndex(val));
            });
        }

        function handleGlebaEnemyBasesToggle() {
            const checkbox = document.querySelector('[data-control="gleba_enemy_bases_enabled"]');
            if (!checkbox) return;
            const enabled = checkbox.checked;
            const control = ensureAutoplaceControl('gleba_enemy_base');

            if (enabled) {
                const prev = wbState.glebaEnemyBasesPreviousValues || { frequency: 1, size: 1, richness: 1 };
                control.frequency = prev.frequency != null ? prev.frequency : 1;
                control.size = prev.size != null ? prev.size : 1;
                control.richness = prev.richness != null ? prev.richness : 1;
            } else {
                wbState.glebaEnemyBasesPreviousValues = { ...control };
                control.size = 0;
            }

            document.querySelectorAll('.wb-table-discrete-input[data-control^="gleba_enemy_bases_"]').forEach(slider => {
                slider.disabled = !enabled;
                const ctrl = slider.dataset.control;
                const field = ctrl.replace('gleba_enemy_bases_', '');
                const val = control[field] != null ? control[field] : 1;
                slider.value = factorioValueToIndex(val);
                const span = slider.parentElement.querySelector(`.wb-table-value[data-control="${ctrl}"]`);
                if (span) span.textContent = factorioIndexToLabel(factorioValueToIndex(val));
            });
        }

        function handleEnemyBaseSliderChange(e) {
            const input = e.target;
            const control = input.dataset.control;
            const field = control.replace('enemy_bases_', '');
            const index = parseInt(input.value, 10);
            const value = factorioIndexToValue(index);

            const span = input.parentElement.querySelector(`.wb-table-value[data-control="${control}"]`);
            if (span) span.textContent = factorioIndexToLabel(index);

            const autoplace = ensureAutoplaceControl('enemy-base');
            autoplace[field] = value;
            markPreviewOutdated();
        }

        function handleGlebaEnemyBaseSliderChange(e) {
            const input = e.target;
            const control = input.dataset.control;
            const field = control.replace('gleba_enemy_bases_', '');
            const index = parseInt(input.value, 10);
            const value = factorioIndexToValue(index);

            const span = input.parentElement.querySelector(`.wb-table-value[data-control="${control}"]`);
            if (span) span.textContent = factorioIndexToLabel(index);

            const autoplace = ensureAutoplaceControl('gleba_enemy_base');
            autoplace[field] = value;
            markPreviewOutdated();
        }

        function handleStartingAreaChange(e) {
            const input = e.target;
            const control = input.dataset.control;
            const index = parseInt(input.value, 10);
            const value = factorioIndexToValue(index);

            const span = input.parentElement.querySelector(`.wb-table-value[data-control="${control}"]`);
            if (span) span.textContent = factorioIndexToLabel(index);

            updateMapGenSetting('starting_area', value);
        }

        function initNumericSliders() {
            document.querySelectorAll('.wb-numeric-slider-input').forEach(input => {
                input.addEventListener('input', handleNumericSliderInput);
                input.addEventListener('change', handleNumericSliderInput);
            });
            document.querySelectorAll('.wb-numeric-slider-value').forEach(input => {
                input.addEventListener('change', handleNumericInputChange);
            });
        }

        function initEnemyTabToggles() {
            const toggleMap = {
                'expansion_enabled': 'expansion',
                'evolution_enabled': 'evolution',
            };
            Object.entries(toggleMap).forEach(([checkboxControl, groupName]) => {
                const checkbox = document.querySelector(`[data-control="${checkboxControl}"]`);
                const group = document.querySelector(`[data-group="${groupName}"]`);
                if (!checkbox || !group) return;
                const toggle = () => {
                    const inputs = group.querySelectorAll('input[type="range"], input[type="number"]');
                    inputs.forEach(input => {
                        input.disabled = !checkbox.checked;
                    });
                };
                checkbox.addEventListener('change', toggle);
                toggle();
            });
        }

        function initWorldBuilder() {
            if (worldBuilderInitialized) return;
            worldBuilderInitialized = true;

            console.log('[WorldBuilder] Preview cache initialized.');

            populateTabs();
            initWbTabs();
            initNumericSliders();
            initEnemyTabToggles();
            initEnemyTabControls();

            const worldNameInput = document.getElementById('wb-world-name');
            const seedInput = document.getElementById('wb-seed');
            const generateButton = document.getElementById('wb-generate-seed');
            const planetSelect = document.getElementById('wb-planet');
            const updateButton = document.getElementById('wb-update-preview');
            const createButton = document.getElementById('wb-create-world');

            if (worldNameInput) {
                updateWorldConfig({ world_name: worldNameInput.value });
                worldNameInput.addEventListener('input', () => {
                    updateWorldConfig({ world_name: worldNameInput.value });
                    refreshPreviewStatus();
                });
                worldNameInput.addEventListener('change', () => {
                    updateWorldConfig({ world_name: worldNameInput.value });
                    refreshPreviewStatus();
                });
            }

            if (seedInput) {
                updateWorldConfig({ seed: seedInput.value });
                seedInput.addEventListener('input', () => {
                    updateWorldConfig({ seed: seedInput.value });
                    refreshPreviewStatus();
                });
                seedInput.addEventListener('change', () => {
                    updateWorldConfig({ seed: seedInput.value });
                    refreshPreviewStatus();
                });
            }

            if (generateButton && seedInput) {
                generateButton.addEventListener('click', () => {
                    const newSeed = generateRandomSeed();
                    seedInput.value = newSeed;
                    updateWorldConfig({ seed: newSeed });
                    markPreviewOutdated();
                });
            }

            if (planetSelect) {
                updateWorldConfig({ planet: planetSelect.value });
                planetSelect.addEventListener('change', () => {
                    updateWorldConfig({ planet: planetSelect.value });
                    markPreviewOutdated();
                });
            }

            if (updateButton) {
                updateButton.addEventListener('click', updatePreview);
            }
            if (createButton) {
                createButton.addEventListener('click', createWorld);
            }

            const autoUpdateCheckbox = document.getElementById('wb-auto-update');
            if (autoUpdateCheckbox) {
                autoUpdateCheckbox.checked = wbState.preview.autoUpdate;
                autoUpdateCheckbox.addEventListener('change', (e) => {
                    wbState.preview.autoUpdate = e.target.checked;
                    if (!wbState.preview.autoUpdate) {
                        if (wbState.preview.autoUpdateTimer) {
                            clearTimeout(wbState.preview.autoUpdateTimer);
                            wbState.preview.autoUpdateTimer = null;
                        }
                        wbState.preview.pendingAutoUpdate = false;
                    }
                });
            }

            markPreviewOutdated();

            const previewContainer = document.getElementById('wb-preview-container');
            if (previewContainer) {
                let isDragging = false;
                let dragStartX = 0;
                let dragStartY = 0;
                let scrollStartLeft = 0;
                let scrollStartTop = 0;

                previewContainer.addEventListener('pointerdown', (e) => {
                    if (e.button !== 0) return;
                    isDragging = true;
                    dragStartX = e.clientX;
                    dragStartY = e.clientY;
                    scrollStartLeft = previewContainer.scrollLeft;
                    scrollStartTop = previewContainer.scrollTop;
                    previewContainer.classList.add('dragging');
                    previewContainer.setPointerCapture(e.pointerId);
                    e.preventDefault();
                });

                previewContainer.addEventListener('pointermove', (e) => {
                    if (!isDragging) return;
                    const deltaX = dragStartX - e.clientX;
                    const deltaY = dragStartY - e.clientY;
                    previewContainer.scrollLeft = scrollStartLeft + deltaX;
                    previewContainer.scrollTop = scrollStartTop + deltaY;
                    e.preventDefault();
                });

                previewContainer.addEventListener('pointerup', (e) => {
                    if (!isDragging) return;
                    isDragging = false;
                    previewContainer.classList.remove('dragging');
                    previewContainer.releasePointerCapture(e.pointerId);
                });

                previewContainer.addEventListener('pointercancel', () => {
                    isDragging = false;
                    previewContainer.classList.remove('dragging');
                });
            }

            loadResourceFields();
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initWorldBuilder);
        } else {
            initWorldBuilder();
        }
