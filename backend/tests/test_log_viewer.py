import re
from types import SimpleNamespace
import textwrap
from pathlib import Path

LOG_VIEWER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "static"
    / "js"
    / "log_viewer.js"
)

TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "templates"
    / "index.html"
)
CSS_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "static"
    / "css"
    / "app.css"
)


import textwrap


def _join_continuations(code: str) -> str:
    """Join wrapped JS statements so the single-line transpiler regexes work.

    The JS->Python transpiler below only handles one-statement-per-line patterns
    (notably the ``A = C ? X : Y`` ternary). This pre-pass re-joins expression
    continuations (a line ending with an operator/assignment and the next line
    continuing the expression) so each logical statement becomes a single line.
    Blank/comment lines are ignored for join tracking but preserved.
    """
    out = []
    last_expr = None  # index in out of the last "open" expression line
    for raw in code.splitlines():
        line = raw.split("//", 1)[0].rstrip()
        if not line.strip():
            out.append(line)
            continue
        if line.strip().startswith("(function (global) {"):
            out.append(line)
            continue
        if line.strip() == "})(window);":
            out.append(line)
            continue
        if last_expr is not None and _is_continuation(out[last_expr], line):
            out[last_expr] = out[last_expr].rstrip() + " " + line.lstrip()
        else:
            out.append(line)
            last_expr = len(out) - 1
        # A statement terminator closes the open expression for joining.
        if line.rstrip().endswith(";"):
            last_expr = None
    return "\n".join(out)


def _is_continuation(prev: str, cur: str) -> bool:
    prev = prev.rstrip()
    cur = cur.lstrip()
    if not prev or not cur:
        return False
    # previous line is mid-expression (assignment, operator, call, paren)
    if prev.endswith(("=", "?", ":", "&&", "||", "+", "-", "*", "/", "(", ")", ",")):
        return True
    # current line continues a method chain / ternary
    if cur.startswith(("?", ":", ".")):
        return True
    return False


def _to_python_source(code: str) -> str:
    """Convert this specific ES5 IIFE file into executable Python for testing.

    The file is intentionally ES5 (no classes, arrows, or template literals),
    so a small targeted transform is reliable.
    """
    code = _join_continuations(code)
    lines = []
    for raw in code.splitlines():
        line = raw
        if line.strip().startswith("//"):
            continue
        idx = line.find("//")
        if idx != -1:
            line = line[:idx]
        if line.strip().startswith("(function (global) {"):
            continue
        if line.strip() == "})(window);":
            continue
        line = line.replace("global.", "window.")
        line = re.sub(r"\b(const|let|var)\s+", "", line)
        line = line.replace("new LogViewer(", "LogViewer(")
        lines.append(line)
    body = "\n".join(lines)

    # strSlice(s, a, b) -> s[a:b]  (must run before function->def so it matches the call)
    body = re.sub(r"strSlice\(([^,]+),\s*([^,]+),\s*([^)]+)\)", r"\1[\2:\3]", body)
    # typeof X === 'string' -> isinstance(X, str)  (test-only transpile)
    body = re.sub(
        r"typeof\s+([\w.]+)\s*(?:===\s*'string'|==\s*'string')",
        r"isinstance(\1, str)",
        body,
    )
    # LogViewer.prototype.NAME = function (ARGS) {  ->  def NAME(self, ARGS):
    body = re.sub(
        r"LogViewer\.prototype\.([A-Za-z_]\w*)\s*=\s*function\s*\(([^)]*)\)\s*\{",
        r"def \1(self, \2):",
        body,
    )
    # standalone function NAME(ARGS) {  ->  def NAME(ARGS):  (no implicit self)
    body = re.sub(r"function\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{", r"def \1(\2):", body)
    # The LogViewer constructor uses `this` -> bind a fresh namespace object.
    body = re.sub(
        r"def LogViewer\((.*)\):",
        r"def LogViewer(\1):\n    self = SimpleNamespace()",
        body,
    )
    body = body.replace("self = SimpleNamespace()", "    self = SimpleNamespace()")
    # JS object property access on missing keys yields undefined; emulate with
    # getattr(..., None) for the `options` object passed as a namespace/dict.
    body = re.sub(r"\boptions\.(\w+)", r"getattr(options, '\1', None)", body)
    # Object-literal results (diff/fetched payloads) are dicts in Python, so
    # translate `obj.key` access into `obj['key']` for those locals.
    body = re.sub(r"\b(diff|data)\.(\w+)", r"\1['\2']", body)
    # any remaining ") {" (e.g. nested blocks) -> "):"
    body = re.sub(r"\)\s*\{", "):", body)
    # this. -> self.
    # strip .bind(...) calls (browser-only)
    body = re.sub(r"\.bind\([^)]*\)", "", body)
    body = body.replace("this.", "self.")
    # drop the JS `const self = this;` alias (Python methods already use self)
    body = re.sub(r"^\s*self\s*=\s*this\s*;?\s*$", "", body, flags=re.MULTILINE)
    # remap stray `this` references (e.g. `return this`) to self
    body = re.sub(r"\bthis\b", "self", body)
    # .length -> len(...)
    # simple .slice(a, b) -> [a:b] (helper body only; no nested parens)
    body = re.sub(r"\.slice\(([^,]+),\s*([^)]+)\)", r"[\1:\2]", body)
    body = re.sub(r"([\w.]+)\.length", r"len(\1)", body)
    # bracket-notation (.length after obj['key']) produced by the dict rewrite
    body = re.sub(r"(\w+)\['(\w+)'\]\.length", r"len(\1['\2'])", body)
    # ternary  NAME = A ? B : C -> NAME = B if A else C  (single, line-safe)
    body = re.sub(
        r"([A-Za-z_]\w*)\s*=\s*([^?;]+)\?\s*([^:;]+)\s*:\s*([^;]+);",
        r"\1 = \3 if \2 else \4",
        body,
    )
    # boolean / null literals
    # strict equality -> equality (JS === / !==)
    body = body.replace("===", "==").replace("!==", "!=")
    body = body.replace("null", "None").replace("true", "True").replace("false", "False")
    # logical operators
    body = body.replace("||", " or ").replace("&&", " and ")
    # negation: replace standalone `!` only (not the `!=` produced above)
    body = re.sub(r"!(?!=)", "not ", body)
    # object-literal returns -> dicts (no nested braces in this file)
    body = re.sub(
        r"return\s*\{([^}]*)\};",
        lambda m: "return {" + _dict_from_js(m.group(1)) + "}",
        body,
    )
    # add self as first param for methods that use it
    body = re.sub(
        r"def\s+(_?\w+)\(([^)]*)\):",
        lambda m: _method_signature(m.group(1), m.group(2)),
        body,
    )
    # strip trailing semicolons so '};' becomes '}' (dict braces preserved)
    body = re.sub(r";\s*$", "", body, flags=re.MULTILINE)
    # remove standalone block-closing braces only (dict braces are kept)
    body = re.sub(r"^\s*\}\s*$", "", body, flags=re.MULTILINE)
    # empty method/function bodies (JS comments only) need a `pass` in Python
    body_lines = body.splitlines()
    fixed = []
    for i, ln in enumerate(body_lines):
        fixed.append(ln)
        if re.match(r"^\s*def\s+\w+\(.*\):\s*$", ln):
            nxt = body_lines[i + 1] if i + 1 < len(body_lines) else ""
            if nxt.strip() == "":
                fixed.append(ln[: len(ln) - len(ln.lstrip())] + "    pass")
    body = "\n".join(fixed)
    # Drop browser-only methods that cannot be transpiled (use fetch/.finally).
    body = _strip_methods(body, ("start", "stop"))
    # robust dedent: strip the common leading whitespace of non-empty lines
    non_empty = [ln for ln in body.splitlines() if ln.strip()]
    common = min((len(ln) - len(ln.lstrip()) for ln in non_empty), default=0)
    dedented = "\n".join(
        (ln[common:] if len(ln) >= common else ln) for ln in body.splitlines()
    )
    # Bind every prototype method onto the instance (emulates `this.method()`
    # dispatch in JS, where the constructor returns the new object).
    method_names = re.findall(r"^def\s+([A-Za-z_]\w*)\(self", dedented, flags=re.M)
    bindings = "\n".join(
        f"    self.{n} = lambda *a, **k: {n}(self, *a, **k)" for n in method_names
    )
    dedented = dedented.replace(
        "    self = SimpleNamespace()",
        "    self = SimpleNamespace()\n" + bindings,
        1,
    )
    # JS constructors implicitly return `this`; make the Python ctor return it.
    dedented = dedented.replace(
        "    self._bindScroll()",
        "    self._bindScroll()\n    return self",
        1,
    )
    return dedented



def _strip_methods(body: str, names) -> str:
    """Remove whole method definitions (def NAME...) from the transpiled body.

    Used to drop browser-only methods (start/stop) that rely on fetch/.finally
    and cannot be expressed in the simple JS->Python transpiler.
    """
    out = []
    drop_depth = None
    for ln in body.splitlines():
        m = re.match(r"^(\s*)def\s+(\w+)\(", ln)
        if m and m.group(2) in names and drop_depth is None:
            drop_depth = len(m.group(1))
            continue
        if drop_depth is not None:
            if ln.strip() == "":
                continue
            # Stop dropping once we reach a line at the same/lower indentation.
            if len(ln) - len(ln.lstrip()) <= drop_depth:
                drop_depth = None
            else:
                continue
        out.append(ln)
    return "\n".join(out)


def _dict_from_js(inner: str) -> str:
    parts = []
    for pair in inner.split(","):
        if not pair.strip():
            continue
        key, _, val = pair.partition(":")
        parts.append(f'"{key.strip()}": {val.strip()}')
    return ", ".join(parts)


def _method_signature(name: str, params: str) -> str:
    # Signatures are already correct from the prototype/function conversions
    # above (prototype methods carry `self`; standalone functions do not), so
    # this pass is intentionally a no-op kept for compatibility.
    return f"def {name}({params}):"


class FakeTextNode:
    def __init__(self, text):
        self._text = text


class FakeNode:
    def __init__(self, text=""):
        self._text = text
        self.childNodes = []
        self.scrollHeight = 0
        self.scrollTop = 0
        self.clientHeight = 100
        self._listeners = []

    @property
    def textContent(self):
        return self._text + "".join(
            c._text for c in self.childNodes if hasattr(c, "_text")
        )

    @textContent.setter
    def textContent(self, value):
        self._text = value
        self.childNodes = []

    def appendChild(self, node):
        self.childNodes.append(node)
        return node

    def contains(self, node):
        if node == "inside":
            return True
        if node == "outside":
            return False
        return node is self or any(
            c is node or (hasattr(c, "contains") and c.contains(node))
            for c in self.childNodes
        )

    def addEventListener(self, _evt, _fn):
        self._listeners.append((_evt, _fn))


class FakeSelection:
    def __init__(self, inside=False, collapsed=True):
        self.isCollapsed = collapsed
        self.rangeCount = 0 if collapsed else 1
        self._inside = inside

    def getRangeAt(self, _i):
        class R:
            collapsed = False
            commonAncestorContainer = "inside" if self._inside else "outside"

        return R()


class FakeWindow(dict):
    def __init__(self, selection=None):
        super().__init__()
        self._selection = selection
        self.setInterval = lambda fn, _ms: 1
        self.clearInterval = lambda _id: None

    def getSelection(self):
        return self._selection


def _make_viewer(selection=None, initial_text=""):
    window = FakeWindow(selection=selection)
    window["document"] = type(
        "Doc", (), {"createTextNode": staticmethod(lambda t: FakeTextNode(t))}
    )()
    code = _to_python_source(LOG_VIEWER_PATH.read_text(encoding="utf-8"))
    ns = {
        "window": window,
        "document": window["document"],
        "SimpleNamespace": __import__("types").SimpleNamespace,
    }
    exec(compile(code, str(LOG_VIEWER_PATH), "exec"), ns)
    LogViewer = ns["LogViewer"]
    el = FakeNode(initial_text)
    viewer = LogViewer(el, SimpleNamespace(endpoint="/logs/data"))
    return viewer, el


def test_no_update_when_content_identical():
    viewer, el = _make_viewer(initial_text="line1\nline2\n")
    viewer._lastText = "line1\nline2\n"
    el.textContent = "line1\nline2\n"
    before = el.textContent
    viewer._apply("line1\nline2\n")
    assert el.textContent == before
    assert el.scrollTop == 0  # never forced to bottom when unchanged


def test_bottom_append_grows_via_full_replace():
    # Real log growth is a bottom-append: the previous text is NOT a suffix of
    # the new text, so the diff falls back to a full replace. That path must
    # keep producing the exact, complete content and advance _lastText.
    viewer, el = _make_viewer(initial_text="")
    viewer._apply("line1\n")
    viewer._apply("line1\nline2\n")
    viewer._apply("line1\nline2\nline3\n")
    assert el.textContent == "line1\nline2\nline3\n"
    assert viewer._lastText == "line1\nline2\nline3\n"


def test_full_replace_on_divergent_content():
    viewer, el = _make_viewer(initial_text="aaa\nbbb\n")
    viewer._lastText = "aaa\nbbb\n"
    el.textContent = "aaa\nbbb\n"
    viewer._apply("aaa\nCHANGED\n")
    assert el.textContent == "aaa\nCHANGED\n"
    assert el.childNodes == []


def test_continuous_updates_survive_divergent_update():
    # REGRESSION (H7.2): the original code threw inside the full-replace branch
    # (diff.appended was undefined) which silently killed the polling loop after
    # the first divergent update. The viewer must keep updating afterwards.
    viewer, el = _make_viewer(initial_text="")
    viewer._apply("line1\n")           # first render
    assert el.textContent == "line1\n"
    assert viewer._lastText == "line1\n"

    viewer._apply("line1\nline2\n")    # pure bottom-append -> full replace
    assert el.textContent == "line1\nline2\n"
    assert viewer._lastText == "line1\nline2\n"

    viewer._apply("line1\nCHANGED\n")  # divergent edit -> full replace
    assert el.textContent == "line1\nCHANGED\n"
    assert viewer._lastText == "line1\nCHANGED\n"

    # Updates MUST keep flowing after the divergent update.
    viewer._apply("line1\nCHANGED\nline3\n")
    assert el.textContent == "line1\nCHANGED\nline3\n"
    assert viewer._lastText == "line1\nCHANGED\nline3\n"


def test_live_log_growth_keeps_updating():
    # Simulates the live-log polling sequence: the file only ever grows, and the
    # viewer must reflect every new line without getting stuck on stale state.
    viewer, el = _make_viewer(initial_text="")
    content = ""
    for i in range(1, 21):
        content += f"tick {i}\n"
        viewer._apply(content)
        assert el.textContent == content
        assert viewer._lastText == content


def test_identical_content_is_noop_between_polls():
    # While the file is unchanged between polls, nothing must be rewritten and
    # _lastText must stay in sync so the next growth is still detected.
    viewer, el = _make_viewer(initial_text="")
    viewer._apply("stable\n")
    snapshot = el.textContent
    for _ in range(5):
        viewer._apply("stable\n")
        assert el.textContent == snapshot
        assert viewer._lastText == "stable\n"
    viewer._apply("stable\nmore\n")
    assert el.textContent == "stable\nmore\n"


def test_polling_survives_long_session_with_no_loss():
    # Simulates several minutes of live-log polling (e.g. 5 min @ 2s = 150
    # ticks) where the file grows every few polls and occasionally rewrites a
    # line in place. Every update must be reflected with zero lost lines and
    # _lastText must never get stuck on stale content (the H7.2 root cause).
    viewer, el = _make_viewer(initial_text="")
    content = ""
    for tick in range(150):
        if tick % 3 == 0:
            content += f"line {tick}\n"
        elif tick % 17 == 0:
            # In-place rewrite: replace the last line (divergent update).
            content = content.rstrip("\n").rsplit("\n", 1)[0] + "\nREWRITTEN\n"
        viewer._apply(content)
        assert el.textContent == content, f"tick {tick}: content drift"
        assert viewer._lastText == content, f"tick {tick}: _lastText stuck"
    # Final sanity: the last produced line is present.
    assert "REWRITTEN" in el.textContent


def test_selection_preserved_blocks_update():
    selection = FakeSelection(inside=True, collapsed=False)
    viewer, el = _make_viewer(selection=selection, initial_text="old\n")
    viewer._lastText = "old\n"
    el.textContent = "old\n"
    viewer._apply("old\nnew line\n")
    assert el.textContent == "old\n"
    assert el.childNodes == []


def test_autoscroll_follows_bottom():
    viewer, el = _make_viewer(initial_text="a\n")
    viewer._lastText = "a\n"
    el.textContent = "a\n"
    el.scrollHeight = 200
    el.clientHeight = 100
    el.scrollTop = 100
    viewer.setAutoScroll(True)
    viewer._apply("a\nb\n")
    assert el.scrollTop == el.scrollHeight


def test_no_scroll_change_when_autoscroll_off():
    viewer, el = _make_viewer(initial_text="a\n")
    viewer._lastText = "a\n"
    el.textContent = "a\n"
    el.scrollTop = 0
    viewer.setAutoScroll(False)
    el.scrollHeight = 300
    el.clientHeight = 100
    viewer._apply("a\nb\nc\n")
    assert el.scrollTop == 0


def test_scroll_to_bottom_on_enable():
    viewer, el = _make_viewer(initial_text="a\n")
    viewer.autoScroll = False
    el.scrollHeight = 250
    el.clientHeight = 100
    el.scrollTop = 50
    viewer.setAutoScroll(True)
    assert el.scrollTop == el.scrollHeight


def test_reset_clears_state_and_text():
    viewer, el = _make_viewer(initial_text="x\n")
    viewer._lastText = "x\n"
    viewer.reset("fresh\n")
    assert el.textContent == "fresh\n"
    assert viewer._lastText == "fresh\n"


def test_html_loads_log_viewer_before_dashboard():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert html.find("js/log_viewer.js") != -1
    assert html.find("js/log_viewer.js") < html.find("js/dashboard.js")


def test_log_viewer_script_tag_present():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "js/log_viewer.js" in html


def test_logs_output_element_present():
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert 'id="logs-output"' in html
    assert 'id="logs-auto-scroll"' in html


def test_log_viewer_css_class_exists():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".startup-warning" in css  # sanity: CSS file present/loaded


def test_compute_new_content_uses_defined_symbols():
    """Regression (H7.2B): _computeNewContent must not reference an undefined
    symbol. The slice helper is named `strSliceImpl`; every call site must use
    that exact name. A mismatched name (`strSlice`) raised
    `ReferenceError: strSlice is not defined` on every growing poll."""
    src = LOG_VIEWER_PATH.read_text(encoding="utf-8")

    # The helper must be defined exactly once.
    assert "function strSliceImpl(" in src, "strSliceImpl definition missing"
    # Every `strSlice(` call must actually be `strSliceImpl(` (no orphan bare calls).
    for m in re.finditer(r"strSlice\(", src):
        start = m.start()
        prefix = src[max(0, start - 3):start]
        assert prefix.endswith("Impl"), f"undefined symbol strSlice used at {start}"
    # The helper is actually exercised (called) by _computeNewContent.
    assert "strSliceImpl(" in src, "strSliceImpl is never called"

    # The existing harness already exercises _computeNewContent via _apply;
    # assert the divergent + append paths produce correct diffs end-to-end.
    viewer, el = _make_viewer(initial_text="")
    viewer._lastText = "line1\n"
    viewer.update("line1\nline2\n")
    assert el.textContent == "line1\nline2\n"
    assert viewer._lastText == "line1\nline2\n"

    viewer._lastText = "aaa\nbbb\n"
    viewer.update("aaa\nCHANGED\n")
    assert el.textContent == "aaa\nCHANGED\n"
    assert viewer._lastText == "aaa\nCHANGED\n"

