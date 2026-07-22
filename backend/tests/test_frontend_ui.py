from pathlib import Path
import json


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


def test_startup_preview_modal_exists():
    html = _read_template()
    assert 'id="startup-preview-modal"' in html
    assert 'data-i18n="startup_preview.modal_title"' in html
    assert 'id="startup-preview-command"' in html
    assert 'id="startup-preview-copy"' in html


def test_startup_preview_not_embedded_in_card():
    html = _read_template()
    assert 'id="startup-preview"' not in html


def test_startup_preview_css_exists():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".modal-overlay" in css
    assert ".modal-card" in css
    assert ".startup-preview-command" in css


def test_startup_preview_i18n_keys_exist():
    i18n_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "i18n"
    required_keys = {
        "startup_preview.modal_title",
        "startup_preview.subtitle",
        "startup_preview.show",
        "startup_preview.copy",
        "startup_preview.copied",
    }
    for lang in ["en.json", "pt_BR.json", "es.json", "zh_CN.json"]:
        data = json.loads((i18n_dir / lang).read_text(encoding="utf-8"))
        missing = required_keys - data.keys()
        assert not missing, f"Missing keys in {lang}: {missing}"


def test_factorio_account_section_exists():
    html = _read_template()
    assert 'id="factorio-account-card"' in html
    assert 'id="factorio-account-form"' in html
    assert 'id="factorio-username"' in html
    assert 'id="factorio-token"' in html
    assert 'id="factorio-account-toggle-token"' in html
    assert 'id="factorio-account-status"' in html


def test_factorio_account_i18n_keys_exist():
    i18n_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "i18n"
    required_keys = {
        "settings.group.factorio_account",
        "factorio_account.title",
        "factorio_account.username",
        "factorio_account.token",
        "factorio_account.show_token",
        "factorio_account.hide_token",
        "factorio_account.save",
        "factorio_account.status.not_configured",
        "factorio_account.status.authenticated",
        "factorio_account.status.invalid",
    }
    for lang in ["en.json", "pt_BR.json", "es.json", "zh_CN.json"]:
        data = json.loads((i18n_dir / lang).read_text(encoding="utf-8"))
        missing = required_keys - data.keys()
        assert not missing, f"Missing keys in {lang}: {missing}"


def test_factorio_account_css_exists():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".factorio-token-row" in css
    assert ".badge-factorio" in css


def test_world_builder_tab_exists():
    html = _read_template()
    assert 'data-tab="world-builder"' in html
    assert 'id="world-builder-panel"' in html


def test_world_builder_panel_has_split_layout():
    html = _read_template()
    assert 'class="world-builder-layout"' in html
    assert 'class="panel card config-card world-builder-config"' in html
    assert 'class="panel card config-card world-builder-preview-card"' in html


def test_world_builder_form_fields_exist():
    html = _read_template()
    assert 'id="wb-world-name"' in html
    assert 'id="wb-seed"' in html
    assert 'id="wb-generate-seed"' in html
    assert 'id="wb-planet"' in html
    assert 'id="wb-update-preview"' in html
    assert 'id="wb-create-world"' in html


def test_world_builder_create_hint_exists():
    html = _read_template()
    assert 'id="wb-create-hint"' in html
    assert 'world_builder.error.outdated_preview' in html


def test_world_builder_status_banner_exists():
    html = _read_template()
    assert 'id="wb-status-banner"' in html
    assert 'data-i18n="world_builder.status.unavailable"' in html
    assert 'data-i18n="world_builder.status.unavailable_detail"' in html


def test_world_builder_preview_status_and_image():
    html = _read_template()
    assert 'id="wb-preview-status"' in html
    assert 'id="wb-preview-image"' in html
    assert 'id="wb-preview-container"' in html


def test_world_builder_css_exists():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".world-builder-layout" in css
    assert ".world-builder-preview" in css
    assert ".world-builder-preview-image" in css
    assert ".world-builder-preview-card" in css
    assert ".world-builder-status-banner" in css
    assert ".world-builder-create-hint" in css


def test_world_builder_js_exists():
    js_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "world_builder.js"
    assert js_path.exists()
    js = js_path.read_text(encoding="utf-8")
    assert "updatePreview" in js
    assert "createWorld" in js
    assert "markPreviewOutdated" in js
    assert "generateRandomSeed" in js
    assert "checkWorldBuilderStatus" in js
    assert "refreshPreviewStatus" in js
    assert "wbState" in js
    assert "worldConfig" in js
    assert "preview" in js
    assert "/api/world-builder/preview" in js
    assert "/api/world-builder/create" in js
    assert "/api/world-builder/status" in js
    assert "/api/world-builder/config-hash" in js
    assert "preview_url" in js


def test_world_builder_i18n_keys_exist():
    i18n_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "i18n"
    required_keys = {
        "menu.world_builder",
        "world_builder.title",
        "world_builder.configuration",
        "world_builder.preview",
        "world_builder.world_name",
        "world_builder.seed",
        "world_builder.generate_seed",
        "world_builder.planet",
        "world_builder.update_preview",
        "world_builder.create_world",
        "world_builder.preview.status.updated",
        "world_builder.preview.status.outdated",
        "world_builder.preview.status.generating",
        "world_builder.preview.status.error",
        "world_builder.preview.placeholder",
        "world_builder.error.preview_failed",
        "world_builder.error.create_failed",
        "world_builder.error.create_exception",
        "world_builder.error.outdated_preview",
        "world_builder.status.unavailable",
        "world_builder.status.unavailable_detail",
    }
    for lang in ["en.json", "pt_BR.json", "es.json", "zh_CN.json"]:
        data = json.loads((i18n_dir / lang).read_text(encoding="utf-8"))
        missing = required_keys - data.keys()
        assert not missing, f"Missing keys in {lang}: {missing}"


def test_bootstrap_cache_exists_in_utils():
    utils_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "utils.js"
    js = utils_path.read_text(encoding="utf-8")
    assert "const BootstrapCache" in js
    assert "async get(" in js
    assert "invalidate(" in js
    assert "isStale(" in js


def test_template_loads_app_state_before_app():
    html = _read_template()
    assert "url_for('static', filename='js/core/app_state.js')" in html
    app_state_pos = html.index("app_state.js")
    app_js_pos = html.index("js/app.js")
    assert app_state_pos < app_js_pos


def test_app_js_uses_app_state_bootstrap():
    app_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "app.js"
    js = app_path.read_text(encoding="utf-8")
    assert "AppState.bootstrap()" in js
    assert "Promise.all" not in js


def test_dashboard_prefers_app_state():
    dashboard_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "dashboard.js"
    js = dashboard_path.read_text(encoding="utf-8")
    assert "AppState.get('runtime')" in js
    assert "AppState.get('saves')" in js


def test_config_prefers_app_state():
    config_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "config.js"
    js = config_path.read_text(encoding="utf-8")
    assert "AppState.get('serverSettings')" in js
    assert "BootstrapCache.invalidate('server-settings')" in js


def test_i18n_prefers_app_state():
    i18n_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "i18n.js"
    js = i18n_path.read_text(encoding="utf-8")
    assert "AppState.get('settings')" in js
    assert "BootstrapCache.invalidate('app-settings')" in js


def test_rcon_prefers_app_state():
    rcon_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "rcon.js"
    js = rcon_path.read_text(encoding="utf-8")
    assert "AppState.get('rcon')" in js


def test_world_builder_prefers_app_state():
    wb_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "world_builder.js"
    js = wb_path.read_text(encoding="utf-8")
    assert "AppState.get('worldBuilderStatus')" in js
    assert "AppState.get('worldBuilderOptions')" in js


def test_saves_prefers_app_state():
    saves_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "saves.js"
    js = saves_path.read_text(encoding="utf-8")
    assert "AppState.get('saves')" in js


def test_world_builder_uses_bootstrap_cache():
    wb_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "world_builder.js"
    js = wb_path.read_text(encoding="utf-8")
    assert "BootstrapCache.get('world-builder-status'" in js
    assert "BootstrapCache.get('world-builder-options'" in js


def test_world_builder_init_avoids_duplicate_bootstrap_calls():
    js_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "world_builder.js"
    js = js_path.read_text(encoding="utf-8")
    init_start = js.index("function initWorldBuilder()")
    init_body = js[init_start:]
    assert "loadWorldBuilderOptions()" not in init_body
    assert "checkWorldBuilderStatus()" not in init_body


def test_app_state_exists():
    app_state_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "core" / "app_state.js"
    js = app_state_path.read_text(encoding="utf-8")
    assert "const AppState" in js
    assert "async bootstrap()" in js
    assert "Promise.allSettled" in js
    assert "server-settings" in js
    assert "/api/status" in js
    assert "/api/world-builder/status" in js
    assert "/api/world-builder/options" in js
    assert "/api/settings" in js
    assert "/api/saves" in js
    assert "/api/rcon/status" in js


def test_rcon_uses_bootstrap_cache():
    rcon_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "rcon.js"
    js = rcon_path.read_text(encoding="utf-8")
    assert "BootstrapCache.get('rcon-status'" in js


def test_saves_uses_bootstrap_cache():
    saves_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "saves.js"
    js = saves_path.read_text(encoding="utf-8")
    assert "BootstrapCache.get('saves'" in js


def test_config_uses_bootstrap_cache():
    config_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "config.js"
    js = config_path.read_text(encoding="utf-8")
    assert "BootstrapCache.get('server-settings'" in js


def test_i18n_uses_bootstrap_cache():
    i18n_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "i18n.js"
    js = i18n_path.read_text(encoding="utf-8")
    assert "BootstrapCache.get('app-settings'" in js


def test_favicon_links_exist():
    html = _read_template()
    assert "url_for('static', filename='icons/favicon.ico')" in html
    assert 'type="image/x-icon"' in html
    assert 'rel="icon"' in html


def test_logo_img_in_sidebar():
    html = _read_template()
    assert "url_for('static', filename='img/logo.png')" in html
    assert 'class="brand-logo"' in html
    assert 'alt="Factorio Server Manager"' in html


def test_old_brand_svg_removed():
    html = _read_template()
    assert 'class="brand-icon"' not in html
    assert 'viewBox="0 0 48 48"' not in html


def test_about_hero_uses_logo():
    html = _read_template()
    assert 'class="about-hero-icon"' in html
    assert '<img' in html
    assert '⚙️' not in html


def test_logo_css_responsive():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".brand-logo" in css
    assert "object-fit: contain" in css


def test_settings_save_invalidates_cache():
    config_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "config.js"
    js = config_path.read_text(encoding="utf-8")
    assert "BootstrapCache.invalidate('server-settings')" in js


def test_language_change_invalidates_cache():
    i18n_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "i18n.js"
    js = i18n_path.read_text(encoding="utf-8")
    assert "BootstrapCache.invalidate('app-settings')" in js
