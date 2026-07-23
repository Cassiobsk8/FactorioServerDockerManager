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
            },
            resourceFields: [],
            resourcePreviousValues: {},
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
            'nauvis': '🌍',
            'vulcanus': '🌋',
            'gleba': '🌿',
            'fulgora': '🔴',
            'aquilo': '❄'
        };

        function formatPlanet(field) {
            const planets = field.planet_exclusive;
            if (planets && planets.length > 0) {
                const planet = planets[0];
                const icon = PLANET_ICONS[planet] || '';
                const name = planet.charAt(0).toUpperCase() + planet.slice(1);
                return `${icon} ${name}`;
            }
            const icon = PLANET_ICONS['nauvis'] || '';
            return `${icon} Nauvis`;
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
            const hint = document.getElementById('wb-create-hint');

            if (!badge || !container) return;

            badge.className = 'badge';

            if (status === 'ready') {
                badge.classList.add('badge-active');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.updated');
                badge.textContent = t('world_builder.preview.status.updated');
                container.classList.remove('outdated');
                if (hint) hint.style.display = 'none';
            } else if (status === 'outdated') {
                badge.classList.add('badge-inactive');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.outdated');
                badge.textContent = t('world_builder.preview.status.outdated');
                container.classList.add('outdated');
                if (hint) hint.style.display = 'block';
            } else if (status === 'generating') {
                badge.classList.add('badge-active');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.generating');
                badge.textContent = t('world_builder.preview.status.generating');
                container.classList.remove('outdated');
                if (hint) hint.style.display = 'none';
            } else if (status === 'error') {
                badge.classList.add('badge-inactive');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.error');
                badge.textContent = t('world_builder.preview.status.error');
                container.classList.add('outdated');
                if (hint) hint.style.display = 'none';
            } else {
                badge.classList.add('badge-inactive');
                badge.setAttribute('data-i18n', 'world_builder.preview.status.outdated');
                badge.textContent = t('world_builder.preview.status.outdated');
                container.classList.add('outdated');
                if (hint) hint.style.display = 'block';
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
        }

        async function updatePreview() {
            if (wbState.preview.isLoading) return;

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
            return `<input type="range" class="wb-resource-discrete-input" data-control="${name}" min="0" max="11" step="1" value="${index}" ${disabled ? 'disabled' : ''} /><span class="wb-resource-value" data-control="${name}">${factorioIndexToLabel(index)}</span>`;
        }

        function createResourceCheckbox(name, checked, disabled) {
            return `<input type="checkbox" class="wb-resource-checkbox" data-control="${name}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''} />`;
        }

        function handleResourceEnableChange(e) {
            const input = e.target;
            const row = input.closest('.wb-resource-row');
            if (!row) return;

            const resourceId = row.dataset.resource;
            const enabled = input.checked;
            const sliders = row.querySelectorAll('.wb-resource-discrete-input');
            const valueSpans = row.querySelectorAll('.wb-resource-value');

            if (enabled) {
                const prev = wbState.resourcePreviousValues[resourceId] || {frequency: 1, size: 1, richness: 1};
                wbState.worldConfig.settings.autoplace_controls[resourceId] = { ...prev };

                sliders.forEach(slider => {
                    slider.disabled = false;
                    const control = slider.dataset.control;
                    const val = prev[control] != null ? prev[control] : 1;
                    slider.value = factorioValueToIndex(val);
                    const span = slider.parentElement.querySelector(`.wb-resource-value[data-control="${control}"]`);
                    if (span) span.textContent = factorioIndexToLabel(factorioValueToIndex(val));
                });
            } else {
                const current = wbState.worldConfig.settings.autoplace_controls[resourceId] || {frequency: 1, size: 1, richness: 1};
                wbState.resourcePreviousValues[resourceId] = { ...current };

                wbState.worldConfig.settings.autoplace_controls[resourceId] = { frequency: 0, size: 0, richness: 0 };

                sliders.forEach(slider => {
                    slider.disabled = true;
                });
                valueSpans.forEach(span => {
                    span.textContent = factorioIndexToLabel(factorioValueToIndex(0));
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
            return `<div class="wb-resource-row">
                ${createCheckboxPlaceholder(name)}
                ${createSliderPlaceholder('Frequency')}
                ${createSliderPlaceholder('Size')}
                ${createSliderPlaceholder('Richness')}
            </div>`;
        }

        function createTerrainSubheader(label1, label2) {
            return `<div class="wb-terrain-subheader">
                <span></span>
                <span>${label1}</span>
                <span>${label2}</span>
            </div>`;
        }

        function createTerrainRowWithCheckbox(name, slider1, slider2) {
            return `<div class="wb-terrain-row">
                ${createCheckboxPlaceholder(name)}
                ${createSliderPlaceholder(slider1)}
                ${createSliderPlaceholder(slider2)}
            </div>`;
        }

        function createTerrainRow(name, slider1, slider2) {
            return `<div class="wb-terrain-row">
                <span class="wb-terrain-label">${name}</span>
                ${createSliderPlaceholder(slider1)}
                ${createSliderPlaceholder(slider2)}
            </div>`;
        }

        function createTerrainSelectRow(name, options) {
            const opts = (options || []).map(o => `<option>${o}</option>`).join('');
            return `<div class="wb-terrain-row">
                <span class="wb-terrain-label">${name}</span>
                <div class="wb-placeholder-select">
                    <span>${name}</span>
                    <select disabled>${opts}</select>
                </div>
                <span></span>
            </div>`;
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

        async function loadResourceFields() {
            if (wbState.resourceFields && wbState.resourceFields.length > 0) return;

            try {
                const res = await fetch('/api/world-builder/config-engine?source_file=map-gen-settings.json');
                if (!res.ok) {
                    renderResourcesError('Failed to load resource configuration');
                    return;
                }
                const data = await res.json();

                const fields = (data.fields || []).filter(f => {
                    const category = f.category || '';
                    const isResource = category === 'Resources';
                    const id = f.id || '';
                    const isAutoplaceControl = id.startsWith('autoplace_controls.');
                    const byOriginalType = f.original_type === 'AutoplaceControl';
                    const byFormType = f.type === 'AutoplaceControl' || (f.type === 'group' && byOriginalType);
                    return isResource && (isAutoplaceControl || byFormType);
                });

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

                if (!wbState.worldConfig.settings) {
                    wbState.worldConfig.settings = {};
                }
                if (!wbState.worldConfig.settings.autoplace_controls) {
                    wbState.worldConfig.settings.autoplace_controls = {};
                }

                renderResources(fields);
            } catch (err) {
                renderResourcesError('Failed to load resources');
                console.warn('[WorldBuilder] Error loading resource fields:', err);
            }
        }

        function renderResourcesError(message) {
            const body = document.querySelector('#wb-tab-resources .wb-resources-body');
            if (!body) return;
            body.innerHTML = `<div class="wb-resource-error">${message}</div>`;
        }

        function renderResources(fields) {
            const panel = document.getElementById('wb-tab-resources');
            if (!panel || !fields.length) return;

            const body = panel.querySelector('.wb-resources-body');
            if (!body) return;

            body.innerHTML = fields.map(field => {
                const resourceId = field.id.replace('autoplace_controls.', '');
                const rawDefaults = field.default || {};
                const controlDefaults = (rawDefaults && typeof rawDefaults === 'object' && !Array.isArray(rawDefaults))
                    ? rawDefaults
                    : {frequency: 1, size: 1, richness: 1};
                const current = (wbState.worldConfig.settings && wbState.worldConfig.settings.autoplace_controls && wbState.worldConfig.settings.autoplace_controls[resourceId]) || controlDefaults;

                const isDisabled = current && current.frequency === 0 && current.size === 0 && current.richness === 0;
                const displayValues = (isDisabled && wbState.resourcePreviousValues[resourceId])
                    ? wbState.resourcePreviousValues[resourceId]
                    : current;
                const effective = displayValues || controlDefaults;

                const freq = (effective && effective.frequency != null) ? effective.frequency : controlDefaults.frequency;
                const size = (effective && effective.size != null) ? effective.size : controlDefaults.size;
                const richness = (effective && effective.richness != null) ? effective.richness : controlDefaults.richness;

                const canBeDisabled = field.can_be_disabled !== false;

                const i18nKey = `world_builder.resource.${resourceId.replace(/-/g, '_')}`;

                return `<div class="wb-resource-row" data-resource="${resourceId}">
                    <label class="wb-resource-checkbox-wrapper">
                        ${canBeDisabled ? `<input type="checkbox" class="wb-resource-checkbox" data-control="enabled" ${isDisabled ? '' : 'checked'} />` : ''}
                    </label>
                    <span class="wb-resource-label" data-i18n="${i18nKey}">${field.label || resourceId}</span>
                    <span class="wb-resource-planet">${formatPlanet(field)}</span>
                    <label class="wb-resource-slider">
                        ${createDiscreteSlider('frequency', factorioValueToIndex(freq), isDisabled)}
                    </label>
                    <label class="wb-resource-slider">
                        ${createDiscreteSlider('size', factorioValueToIndex(size), isDisabled)}
                    </label>
                    <label class="wb-resource-slider">
                        ${createDiscreteSlider('richness', factorioValueToIndex(richness), isDisabled)}
                    </label>
                </div>`;
            }).join('');

            body.querySelectorAll('.wb-resource-discrete-input').forEach(input => {
                input.addEventListener('input', handleResourceChange);
                input.addEventListener('change', handleResourceChange);
            });

            body.querySelectorAll('.wb-resource-checkbox').forEach(input => {
                input.addEventListener('change', handleResourceEnableChange);
            });
        }

        function handleResourceChange(e) {
            const input = e.target;
            const row = input.closest('.wb-resource-row');
            if (!row) return;

            const resourceId = row.dataset.resource;
            const control = input.dataset.control;
            const index = parseInt(input.value, 10);
            const value = factorioIndexToValue(index);

            const valueSpan = input.parentElement.querySelector(`.wb-resource-value[data-control="${control}"]`);
            if (valueSpan) valueSpan.textContent = factorioIndexToLabel(index);

            if (!wbState.worldConfig.settings) {
                wbState.worldConfig.settings = {};
            }
            if (!wbState.worldConfig.settings.autoplace_controls) {
                wbState.worldConfig.settings.autoplace_controls = {};
            }
            if (!wbState.worldConfig.settings.autoplace_controls[resourceId]) {
                wbState.worldConfig.settings.autoplace_controls[resourceId] = {};
            }
            wbState.worldConfig.settings.autoplace_controls[resourceId][control] = value;

            markPreviewOutdated();
        }

        function populateTabs() {
            const resourcesPanel = document.getElementById('wb-tab-resources');
            const terrainPanel = document.getElementById('wb-tab-terrain');
            const enemyPanel = document.getElementById('wb-tab-enemy');
            const advancedPanel = document.getElementById('wb-tab-advanced');

            if (resourcesPanel) {
                resourcesPanel.innerHTML = `<div class="wb-resources-table-wrapper">
                    <div class="wb-resources-header">
                        <span class="wb-resource-checkbox-header"></span>
                        <span data-i18n="world_builder.resource.header.resource">Resource</span>
                        <span data-i18n="world_builder.resource.header.planet">Planet</span>
                        <span data-i18n="world_builder.resource.header.frequency">Frequency</span>
                        <span data-i18n="world_builder.resource.header.size">Size</span>
                        <span data-i18n="world_builder.resource.header.richness">Richness</span>
                    </div>
                    <div class="wb-resources-body"></div>
                </div>`;
            }

            if (terrainPanel) {
                terrainPanel.innerHTML = `<div class="wb-terrain-table-wrapper">
                    <div class="wb-terrain-full-width">
                        ${createSelectPlaceholder('Map type', ['Default', 'Island', 'Continents'])}
                    </div>
                    <div class="wb-terrain-header">
                        <span></span>
                        <span>Scale</span>
                        <span>Coverage</span>
                    </div>
                    <div class="wb-terrain-body">
                        ${createTerrainRowWithCheckbox('Water', 'Scale', 'Coverage')}
                        ${createTerrainRowWithCheckbox('Trees', 'Scale', 'Coverage')}
                        ${createTerrainDivider()}
                        ${createTerrainSubheader('Frequency', 'Continuity')}
                        ${createTerrainRowWithCheckbox('Cliffs', 'Frequency', 'Continuity')}
                        ${createTerrainDivider()}
                        ${createTerrainSubheader('Scale', 'Bias')}
                        ${createTerrainRow('Moisture', 'Scale', 'Bias')}
                        ${createTerrainSelectRow('Terrain', ['Default', 'Sand', 'Red desert'])}
                    </div>
                </div>`;
            }

            if (enemyPanel) {
                enemyPanel.innerHTML = `<div class="wb-enemy-table-wrapper">
                    <div class="wb-enemy-group">
                        ${createEnemyRowWithCheckbox('Enemy Bases', 'Frequency', 'Size')}
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group">
                        ${createEnemyCheckboxRow('Peaceful Mode')}
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group">
                        ${createEnemySliderRow('Starting Area')}
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group">
                        ${createEnemySliderRow('Maximum Expansion Distance')}
                        ${createEnemySliderRow('Minimum Group Size')}
                        ${createEnemySliderRow('Maximum Group Size')}
                        ${createEnemySliderRow('Minimum Cooldown')}
                        ${createEnemySliderRow('Maximum Cooldown')}
                    </div>
                    ${createTerrainDivider()}
                    <div class="wb-enemy-group">
                        ${createEnemySlidersRow('Time', 'Destroy', 'Pollution')}
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

        function initWorldBuilder() {
            if (worldBuilderInitialized) return;
            worldBuilderInitialized = true;

            populateTabs();
            initWbTabs();

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

            markPreviewOutdated();

            loadResourceFields();
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initWorldBuilder);
        } else {
            initWorldBuilder();
        }
