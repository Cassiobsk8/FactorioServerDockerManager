        const AppState = {
            _data: {},

            async bootstrap() {
                const results = await Promise.allSettled([
                    this._load('server-settings', '/server-settings').then((data) => ['serverSettings', data]),
                    this._load('runtime', '/api/status').then((data) => ['runtime', data]),
                    this._load('world-builder-status', '/api/world-builder/status').then((data) => ['worldBuilderStatus', data]),
                    this._load('world-builder-options', '/api/world-builder/options').then((data) => ['worldBuilderOptions', data]),
                    this._load('app-settings', '/api/settings').then((data) => ['settings', data]),
                    this._load('saves', '/api/saves').then((data) => ['saves', data]),
                    this._load('rcon-status', '/api/rcon/status').then((data) => ['rcon', data]),
                ]);

                for (const result of results) {
                    if (result.status === 'fulfilled') {
                        const [key, data] = result.value;
                        this._data[key] = data;
                    }
                }
            },

            _load(key, url) {
                return BootstrapCache.get(key, async () => {
                    const res = await fetch(url);
                    if (!res.ok) throw new Error(`${key}_failed`);
                    return res.json();
                });
            },

            get(key) {
                return this._data[key];
            },

            set(key, value) {
                this._data[key] = value;
            },

            invalidate(key) {
                if (key) {
                    delete this._data[key];
                    BootstrapCache.invalidate(key);
                } else {
                    this._data = {};
                    BootstrapCache.invalidate();
                }
            },
        };