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

        function formatComment(comment) {
            if (Array.isArray(comment)) return comment.map((c) => escapeHtml(c)).join('\n');
            if (typeof comment === 'string') return escapeHtml(comment);
            return '';
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
