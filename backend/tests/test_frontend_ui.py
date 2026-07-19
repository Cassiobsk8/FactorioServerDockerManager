from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "frontend" / "templates" / "index.html"

EXPECTED_MODULES = [
    'data-list="admins"',
    'data-list="whitelist"',
    'data-list="banlist"',
    'data-i18n="config.map_settings_title"',
    'data-i18n="config.server_id_title"',
]


def _read_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def test_all_settings_modules_use_settings_module_card():
    html = _read_template()
    for marker in EXPECTED_MODULES:
        segment = html.split(marker)[0]
        tag = segment.split("<section")[-1]
        assert "settings-module-card" in tag, f"settings-module-card missing for {marker}"


def test_settings_module_card_css_exists():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".settings-module-card" in css


def test_old_card_classes_removed():
    html = _read_template()
    assert "placeholder-card" not in html
    assert "access-control-card" not in html

    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".placeholder-card" not in css
    assert ".access-control-card" not in css
