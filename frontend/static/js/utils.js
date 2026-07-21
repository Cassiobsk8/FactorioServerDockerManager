        function escapeHtml(str) {
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function escapeAttr(str) {
            return escapeHtml(str);
        }

        function formatMB(mb) {
            const value = Number(mb) || 0;
            if (value >= 1024) return `${(value / 1024).toFixed(1)} GB`;
            return `${value.toFixed(0)} MB`;
        }

        function formatUptime(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            if (h > 0) return `${h}h ${m}m`;
            if (m > 0) return `${m}m ${s}s`;
            return `${s}s`;
        }

        function percent(used, total) {
            const u = Number(used) || 0;
            const t = Number(total) || 0;
            if (t <= 0) return 0;
            return Math.min(100, Math.round((u / t) * 100));
        }

        const BootstrapCache = {
            _cache: {},
            _pending: {},

            async get(key, fetcher, options = {}) {
                const cached = this._cache[key];
                if (cached && !options.force) {
                    const age = Date.now() - cached.timestamp;
                    if (age < 1000) {
                        return cached.data;
                    }
                }

                if (this._pending[key]) {
                    return this._pending[key];
                }

                const promise = fetcher().then(data => {
                    this._cache[key] = { data, timestamp: Date.now() };
                    delete this._pending[key];
                    return data;
                }).catch(err => {
                    delete this._pending[key];
                    throw err;
                });

                this._pending[key] = promise;
                return promise;
            },

            invalidate(key) {
                if (key) {
                    delete this._cache[key];
                } else {
                    this._cache = {};
                }
            },

            isStale(key, maxAge = 30000) {
                const cached = this._cache[key];
                if (!cached) return true;
                return Date.now() - cached.timestamp > maxAge;
            },
        };
