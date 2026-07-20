(function (global) {
    'use strict';

    function strSliceImpl(s, start, end) {
        return s.slice(start, end);
    }

    function hasActiveSelection(el) {
        const sel = global.getSelection ? global.getSelection() : null;
        if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
            return false;
        }
        const range = sel.getRangeAt(0);
        // Only consider selections anchored inside the log viewer.
        if (!el.contains(range.commonAncestorContainer)) {
            return false;
        }
        return !range.collapsed;
    }

    function LogViewer(element, options) {
        options = options || {};
        this.el = element;
        this.endpoint = options.endpoint || '/logs/data';
        this.autoScroll = true;
        this._lastText = '';
        this._intervalId = null;
        this._pending = false;
        this._onAutoScrollChange = options.onAutoScrollChange || null;
        this._bindScroll();
    }

    LogViewer.prototype._bindScroll = function () {
        this.el.addEventListener('scroll', this._handleScroll.bind(this));
    };

    LogViewer.prototype._handleScroll = function () {
        if (this._pending) {
            return;
        }
        const distanceFromBottom =
            this.el.scrollHeight - this.el.scrollTop - this.el.clientHeight;
        // Threshold of 4px to treat "near bottom" as bottom.
        const atBottom = distanceFromBottom <= 4;
        if (atBottom && !this.autoScroll) {
            this.setAutoScroll(true);
        }
        if (!atBottom && this.autoScroll) {
            this.setAutoScroll(false);
        }
    };

    LogViewer.prototype.setAutoScroll = function (value) {
        if (this.autoScroll === value) {
            return;
        }
        this.autoScroll = value;
        if (value) {
            this.scrollToBottom();
        }
        if (this._onAutoScrollChange) {
            this._onAutoScrollChange(value);
        }
    };

    LogViewer.prototype.scrollToBottom = function () {
        this.el.scrollTop = this.el.scrollHeight;
    };

    LogViewer.prototype._computeNewContent = function (nextText) {
        if (nextText.length <= this._lastText.length) {
            // No growth: either identical or shrunk (rotation/clear).
            if (nextText === this._lastText) {
                return null; // nothing changed
            }
            return { fullReplace: true, text: nextText };
        }
        // Fast path: tail append.
        const lastLen = this._lastText.length;
        const tail = strSliceImpl(nextText, nextText.length - lastLen, nextText.length);
        if (tail === this._lastText) {
            const appended = strSliceImpl(nextText, 0, nextText.length - lastLen);
            return { fullReplace: false, appended: appended };
        }
        // Content diverged (edited middle, rotation, etc.) -> safe full replace.
        return { fullReplace: true, text: nextText };
    };

    LogViewer.prototype._apply = function (nextText) {
        // Preserve user selection: do not touch the DOM while selecting.
        if (hasActiveSelection(this.el)) {
            return;
        }

        const diff = this._computeNewContent(nextText);

        if (diff === null) {
            return; // identical content, nothing to do
        }

        if (diff.fullReplace) {
            // Content diverged (rotation, in-place rewrite) or this is the
            // very first render. Always replace the full text node.
            this.el.textContent = diff.text;
            if (this.autoScroll) {
                this.scrollToBottom();
            }
        }
        if (!diff.fullReplace && diff.appended && diff.appended.length > 0) {
            // Pure tail append: only add the new lines to avoid a full repaint.
            const atBottomBefore = !this.autoScroll
                ? false
                : this.el.scrollHeight - this.el.scrollTop - this.el.clientHeight <= 4;
            this.el.appendChild(document.createTextNode(diff.appended));
            if (atBottomBefore || this.autoScroll) {
                this.scrollToBottom();
            }
        }
        this._lastText = nextText;
    };

    LogViewer.prototype.update = function (text) {
        this._lastText = this._lastText || '';
        this._apply(text);
    };

    LogViewer.prototype.reset = function (text) {
        this._lastText = '';
        this.el.textContent = text || '';
        this._lastText = text || '';
        if (this.autoScroll) {
            this.scrollToBottom();
        }
    };

    LogViewer.prototype._tickFetch = function (res) {
        if (!res.ok) {
            return null;
        }
        return res.json();
    };

    LogViewer.prototype._tickData = function (data) {
        if (data && typeof data.logs === 'string') {
            console.debug("[LOG POLL] response", data.logs.length);
            this.update(data.logs);
        }
    };

    LogViewer.prototype._tickFinally = function () {
        this._pending = false;
    };

    LogViewer.prototype._tickCatch = function () {
        // ignore network errors; keep current logs
    };

    LogViewer.prototype.start = function (intervalMs) {
        const self = this;
        function tick() {
            self._pending = true;
            console.debug("[LOG POLL] request");
            fetch(self.endpoint)
                .then(self._tickFetch.bind(self))
                .then(self._tickData.bind(self))
                .catch(self._tickCatch.bind(self))
                .finally(self._tickFinally.bind(self));
        }
        tick();
        this._intervalId = global.setInterval(tick, intervalMs || 2000);
        return this;
    };

    LogViewer.prototype.copy = function () {
        var text = this._lastText || '';
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
            return Promise.reject('Clipboard API unavailable');
        }
        return navigator.clipboard.writeText(text);
    };

    LogViewer.prototype.stop = function () {
        if (this._intervalId !== null) {
            global.clearInterval(this._intervalId);
            this._intervalId = null;
        }
        return this;
    };

    global.LogViewer = LogViewer;
})(window);
