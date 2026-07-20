        let worldBuilderInitialized = false;
        let currentPreviewHash = null;
        let isLoadingPreview = false;
        let factorioInstallationValid = true;

        function generateRandomSeed() {
            return Math.floor(Math.random() * 1000000000);
        }

        async function loadWorldBuilderOptions() {
            const planetSelect = document.getElementById('wb-planet');
            if (!planetSelect) return;

            try {
                const res = await fetch('/api/world-builder/options?planet=' + encodeURIComponent(planetSelect.value || 'nauvis'));
                if (!res.ok) return;
                const data = await res.json();

                planetSelect.innerHTML = '';
                (data.planets || []).forEach((planet) => {
                    const option = document.createElement('option');
                    option.value = planet;
                    option.textContent = planet;
                    planetSelect.appendChild(option);
                });
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
                const res = await fetch('/api/world-builder/status');
                if (!res.ok) {
                    throw new Error('status_check_failed');
                }
                const data = await res.json();
                factorioInstallationValid = !!data.valid;

                if (!factorioInstallationValid) {
                    if (banner) banner.style.display = 'flex';
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
                factorioInstallationValid = false;
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
            currentPreviewHash = null;
            const image = document.getElementById('wb-preview-image');
            const container = document.getElementById('wb-preview-container');
            const placeholder = container ? container.querySelector('.preview-placeholder') : null;

            if (image) {
                image.style.display = 'none';
                image.src = '';
            }
            if (placeholder) {
                placeholder.style.display = 'block';
            }
            setPreviewStatus('outdated');
        }

        async function updatePreview() {
            if (isLoadingPreview) return;

            const worldNameInput = document.getElementById('wb-world-name');
            const seedInput = document.getElementById('wb-seed');
            const planetSelect = document.getElementById('wb-planet');

            if (!worldNameInput) return;

            const worldName = worldNameInput.value.trim();
            if (!worldName) {
                alert(t('error.create_world_failed'));
                return;
            }

            isLoadingPreview = true;
            const updateButton = document.getElementById('wb-update-preview');
            const createButton = document.getElementById('wb-create-world');
            if (updateButton) updateButton.disabled = true;
            if (createButton) createButton.disabled = true;

            setPreviewStatus('generating');

            try {
                const res = await fetch('/api/world-builder/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        world_name: worldName,
                        seed: seedInput ? seedInput.value.trim() : null,
                        random_seed: !(seedInput && seedInput.value.trim()),
                        planet: planetSelect ? planetSelect.value : 'nauvis',
                    }),
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    alert(t('world_builder.error.preview_failed') + ': ' + (err.error || err.message || res.statusText));
                    setPreviewStatus('error');
                    return;
                }

                const data = await res.json();
                currentPreviewHash = data.preview_hash;

                const image = document.getElementById('wb-preview-image');
                const container = document.getElementById('wb-preview-container');
                const placeholder = container ? container.querySelector('.preview-placeholder') : null;

                if (image && data.preview_url) {
                    image.src = data.preview_url;
                    image.style.display = 'block';
                }
                if (placeholder) {
                    placeholder.style.display = 'none';
                }
                setPreviewStatus('ready');
            } catch (err) {
                alert(t('world_builder.error.preview_failed'));
                setPreviewStatus('error');
            } finally {
                isLoadingPreview = false;
                if (updateButton) updateButton.disabled = false;
                if (createButton) createButton.disabled = false;
            }
        }

        async function createWorld() {
            if (isLoadingPreview) return;

            const worldNameInput = document.getElementById('wb-world-name');
            const seedInput = document.getElementById('wb-seed');
            const planetSelect = document.getElementById('wb-planet');

            if (!worldNameInput) return;

            const worldName = worldNameInput.value.trim();
            if (!worldName) {
                alert(t('error.create_world_failed'));
                return;
            }

            if (!currentPreviewHash) {
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
                        world_name: worldName,
                        seed: seedInput ? seedInput.value.trim() : null,
                        random_seed: !(seedInput && seedInput.value.trim()),
                        planet: planetSelect ? planetSelect.value : 'nauvis',
                        preview_hash: currentPreviewHash,
                    }),
                });

                if (!res.ok && res.status !== 201) {
                    const err = await res.json().catch(() => ({}));
                    alert(t('world_builder.error.create_failed') + ': ' + (err.error || err.message || res.statusText));
                    return;
                }

                const data = await res.json();
                alert(t('world_builder.create_world') + ': ' + (data.save_file || worldName));
                markPreviewOutdated();
            } catch (err) {
                alert(t('world_builder.error.create_exception'));
            } finally {
                if (createButton) createButton.disabled = false;
            }
        }

        function initWorldBuilder() {
            if (worldBuilderInitialized) return;
            worldBuilderInitialized = true;

            const worldNameInput = document.getElementById('wb-world-name');
            const seedInput = document.getElementById('wb-seed');
            const generateButton = document.getElementById('wb-generate-seed');
            const planetSelect = document.getElementById('wb-planet');
            const updateButton = document.getElementById('wb-update-preview');
            const createButton = document.getElementById('wb-create-world');

            if (generateButton && seedInput) {
                generateButton.addEventListener('click', () => {
                    seedInput.value = generateRandomSeed();
                    markPreviewOutdated();
                });
            }

            const inputs = [worldNameInput, seedInput, planetSelect];
            inputs.forEach((input) => {
                if (input) {
                    input.addEventListener('input', markPreviewOutdated);
                    input.addEventListener('change', markPreviewOutdated);
                }
            });

            if (updateButton) {
                updateButton.addEventListener('click', updatePreview);
            }
            if (createButton) {
                createButton.addEventListener('click', createWorld);
            }

            loadWorldBuilderOptions();
            checkWorldBuilderStatus();
            markPreviewOutdated();
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initWorldBuilder);
        } else {
            initWorldBuilder();
        }