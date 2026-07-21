        let schemaConfigInitialized = false;
        let schemaFormFields = [];
        let schemaFormValues = {};

        function getSchemaConfigSourceFile() {
            const select = document.getElementById('schema-config-source');
            return select ? select.value : '';
        }

        function renderSchemaCategories(categories) {
            const container = document.getElementById('schema-config-categories');
            if (!container) return;
            container.innerHTML = '';
            categories.forEach((category) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'schema-config-category-button';
                button.textContent = category;
                button.addEventListener('click', () => {
                    container.querySelectorAll('.schema-config-category-button').forEach((btn) => btn.classList.remove('active'));
                    button.classList.add('active');
                    renderSchemaFieldsForCategory(category);
                });
                container.appendChild(button);
            });
        }

        function renderSchemaFieldsForCategory(category) {
            const container = document.getElementById('schema-config-fields');
            if (!container) return;
            container.innerHTML = '';
            const fields = schemaFormFields.filter((f) => f.category === category);
            fields.forEach((field) => {
                const wrapper = document.createElement('div');
                wrapper.className = 'schema-field';
                wrapper.dataset.fieldId = field.id;
                const label = document.createElement('label');
                label.innerHTML = `<strong>${field.label}</strong><br/><small>${field.description}</small>`;
                wrapper.appendChild(label);
                let input;
                if (field.type === 'boolean') {
                    input = document.createElement('input');
                    input.type = 'checkbox';
                    input.checked = !!schemaFormValues[field.id];
                } else if (field.type === 'enum') {
                    input = document.createElement('select');
                    (field.options || []).forEach((opt) => {
                        const option = document.createElement('option');
                        option.value = opt;
                        option.textContent = opt;
                        if (schemaFormValues[field.id] === opt) option.selected = true;
                        input.appendChild(option);
                    });
                } else if (field.type === 'range') {
                    input = document.createElement('input');
                    input.type = 'range';
                    input.min = field.min ?? 0;
                    input.max = field.max ?? 100;
                    input.value = schemaFormValues[field.id] ?? field.default ?? 0;
                    const valueLabel = document.createElement('span');
                    valueLabel.className = 'schema-range-value';
                    valueLabel.textContent = input.value;
                    input.addEventListener('input', () => {
                        valueLabel.textContent = input.value;
                        schemaFormValues[field.id] = parseFloat(input.value);
                    });
                    wrapper.appendChild(valueLabel);
                } else if (field.type === 'group') {
                    input = document.createElement('div');
                    input.className = 'schema-group';
                    const groupFields = schemaFormFields.filter((f) => f.id.startsWith(field.id + '.'));
                    groupFields.forEach((gf) => {
                        const groupItem = document.createElement('div');
                        groupItem.className = 'schema-group-item';
                        const groupLabel = document.createElement('label');
                        groupLabel.innerHTML = `<small>${gf.label}</small>`;
                        groupItem.appendChild(groupLabel);
                        const groupInput = document.createElement('input');
                        groupInput.type = 'number';
                        groupInput.step = 'any';
                        groupInput.value = schemaFormValues[gf.id] ?? gf.default ?? 0;
                        groupInput.addEventListener('input', () => {
                            schemaFormValues[gf.id] = parseFloat(groupInput.value);
                        });
                        groupItem.appendChild(groupInput);
                        input.appendChild(groupItem);
                    });
                } else if (field.type === 'array') {
                    input = document.createElement('textarea');
                    input.rows = 4;
                    input.value = JSON.stringify(schemaFormValues[field.id] ?? field.default ?? [], null, 2);
                    input.addEventListener('input', () => {
                        try {
                            schemaFormValues[field.id] = JSON.parse(input.value);
                        } catch (e) {
                            // ignore parse errors until serialize
                        }
                    });
                } else {
                    input = document.createElement('input');
                    input.type = 'text';
                    input.value = schemaFormValues[field.id] ?? field.default ?? '';
                    input.addEventListener('input', () => {
                        schemaFormValues[field.id] = input.value;
                    });
                }
                if (input) {
                    input.dataset.fieldId = field.id;
                    wrapper.appendChild(input);
                }
                container.appendChild(wrapper);
            });
        }

        async function loadSchemaConfigEngine() {
            const sourceFile = getSchemaConfigSourceFile();
            try {
                const res = await fetch('/api/world-builder/config-engine?source_file=' + encodeURIComponent(sourceFile));
                if (!res.ok) return;
                const data = await res.json();
                schemaFormFields = data.fields || [];
                renderSchemaCategories(data.categories || []);
                if (data.categories && data.categories.length > 0) {
                    renderSchemaFieldsForCategory(data.categories[0]);
                }
            } catch (err) {
                // ignore
            }
        }

        async function loadSchemaDefaults() {
            const sourceFile = getSchemaConfigSourceFile();
            try {
                const res = await fetch('/api/world-builder/default-config?source_file=' + encodeURIComponent(sourceFile));
                if (!res.ok) return;
                const data = await res.json();
                schemaFormValues = data.values || {};
                const activeCategory = document.querySelector('.schema-config-category-button.active');
                if (activeCategory) {
                    renderSchemaFieldsForCategory(activeCategory.textContent);
                }
            } catch (err) {
                // ignore
            }
        }

        async function serializeSchemaConfig() {
            const sourceFile = getSchemaConfigSourceFile();
            const output = document.getElementById('schema-config-output');
            try {
                const res = await fetch('/api/world-builder/serialize-config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ values: schemaFormValues, source_file: sourceFile }),
                });
                if (!res.ok) {
                    const err = await res.json();
                    if (output) output.textContent = 'Error: ' + (err.error || res.statusText);
                    return;
                }
                const data = await res.json();
                if (output) output.textContent = JSON.stringify(data.data, null, 2);
            } catch (err) {
                if (output) output.textContent = 'Error: ' + err.message;
            }
        }

        async function deserializeSchemaConfig() {
            const sourceFile = getSchemaConfigSourceFile();
            const output = document.getElementById('schema-config-output');
            const raw = output ? output.textContent.trim() : '';
            if (!raw) {
                alert('No serialized data to deserialize.');
                return;
            }
            try {
                const data = JSON.parse(raw);
                const res = await fetch('/api/world-builder/deserialize-config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ data, source_file: sourceFile }),
                });
                if (!res.ok) {
                    const err = await res.json();
                    alert('Error: ' + (err.error || res.statusText));
                    return;
                }
                const result = await res.json();
                schemaFormValues = result.values || {};
                const activeCategory = document.querySelector('.schema-config-category-button.active');
                if (activeCategory) {
                    renderSchemaFieldsForCategory(activeCategory.textContent);
                }
            } catch (err) {
                alert('Invalid JSON: ' + err.message);
            }
        }

        function initSchemaConfigPage() {
            if (schemaConfigInitialized) return;
            schemaConfigInitialized = true;
            loadSchemaConfigEngine();
            const sourceSelect = document.getElementById('schema-config-source');
            if (sourceSelect) {
                sourceSelect.addEventListener('change', loadSchemaConfigEngine);
            }
            const loadBtn = document.getElementById('schema-config-load-defaults');
            if (loadBtn) loadBtn.addEventListener('click', loadSchemaDefaults);
            const serializeBtn = document.getElementById('schema-config-serialize');
            if (serializeBtn) serializeBtn.addEventListener('click', serializeSchemaConfig);
            const deserializeBtn = document.getElementById('schema_config-deserialize');
            if (deserializeBtn) deserializeBtn.addEventListener('click', deserializeSchemaConfig);
        }
