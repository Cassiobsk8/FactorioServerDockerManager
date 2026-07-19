        let currentLang = 'en';
        let translations = {};
        let fallbackTranslations = {};

        function detectBrowserLanguage() {
            const nav = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
            if (nav.startsWith('pt-br') || nav === 'pt-br') return 'pt_BR';
            if (nav.startsWith('es')) return 'es';
            if (nav.startsWith('zh')) return 'zh_CN';
            return 'en';
        }

        async function loadSettings() {
            try {
                const res = await fetch('/api/settings');
                if (!res.ok) return null;
                const data = await res.json();
                return data.language || null;
            } catch (e) {
                return null;
            }
        }

        async function fetchTranslations(lang) {
            try {
                const res = await fetch(`/api/translations/${lang}`);
                if (!res.ok) return {};
                return await res.json();
            } catch (e) {
                return {};
            }
        }

        function t(key) {
            const value = translations[key];
            if (value !== undefined && value !== '') return value;
            const fallback = fallbackTranslations[key];
            if (fallback !== undefined && fallback !== '') return fallback;
            return key;
        }

        function translatePage() {
            document.querySelectorAll('[data-i18n]').forEach((el) => {
                const key = el.getAttribute('data-i18n');
                const value = t(key);
                if (value) el.textContent = value;
            });

            document.querySelectorAll('[data-i18n-html]').forEach((el) => {
                const key = el.getAttribute('data-i18n-html');
                const value = t(key);
                if (value) el.innerHTML = value;
            });

            document.querySelectorAll('[data-i18n-attr]').forEach((el) => {
                const spec = el.getAttribute('data-i18n-attr');
                const [attr, key] = spec.split(',').map((s) => s.trim());
                const value = t(key);
                if (value && attr) el.setAttribute(attr, value);
            });

            document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
                const key = el.getAttribute('data-i18n-placeholder');
                const value = t(key);
                if (value) el.setAttribute('placeholder', value);
            });

            document.querySelectorAll('[data-i18n-title]').forEach((el) => {
                const key = el.getAttribute('data-i18n-title');
                const value = t(key);
                if (value) el.setAttribute('title', value);
            });

            retranslateRcon();
        }

        function retranslateRcon() {
            // All RCON labels use data-i18n / data-i18n-placeholder and are
            // refreshed by translatePage(); the badge and players list are
            // kept in sync by pollRconStatus / fetchRconStatusOnce.
        }

        async function applyLanguage(lang) {
            currentLang = lang;
            const fetched = await fetchTranslations(lang);
            translations = Object.assign({}, fallbackTranslations, fetched);
            translatePage();
            try { loadSaves(); } catch (e) { /* ignore */ }
            try { fetchAndRenderSettings(); } catch (e) { /* ignore */ }
            const sidebarSelect = document.getElementById('sidebar-language-select');
            if (sidebarSelect) sidebarSelect.value = lang;
        }

        async function changeLanguage(lang) {
            try {
                await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ language: lang }),
                });
            } catch (e) {
                // ignore
            }
            await applyLanguage(lang);
        }

        async function initLanguage() {
            fallbackTranslations = await fetchTranslations('en');
            const saved = await loadSettings();
            const lang = saved || detectBrowserLanguage();
            await applyLanguage(lang);
            initSidebarPreferences();
        }

        function initSidebarPreferences() {
            const sidebarSelect = document.getElementById('sidebar-language-select');
            if (!sidebarSelect) return;
            sidebarSelect.value = currentLang;
            sidebarSelect.addEventListener('change', (e) => {
                changeLanguage(e.target.value);
            });
        }
