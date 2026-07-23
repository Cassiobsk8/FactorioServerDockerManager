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


def test_world_builder_resources_css_exists():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")
    assert ".wb-resource-label" in css
    assert ".wb-resource-slider" in css
    assert ".wb-resource-value" in css
    assert ".wb-resource-input" in css


def test_world_builder_resources_dom_structure():
    html = _read_template()
    assert 'id="wb-tab-resources"' in html
    assert 'id="wb-tab-terrain"' in html
    assert 'id="wb-tab-enemy"' in html
    assert 'id="wb-tab-advanced"' in html
    assert 'id="wb-preview-status"' in html
    assert 'id="wb-preview-image"' in html
    assert 'id="wb-preview-container"' in html


def test_world_builder_resources_js_resilient_filter():
    js_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "world_builder.js"
    js = js_path.read_text(encoding="utf-8")
    assert "original_type === 'AutoplaceControl'" in js
    assert "autoplace_controls." in js
    assert "renderResourcesError" in js


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
    assert "loadResourceFields" in js
    assert "renderResources" in js
    assert "handleResourceChange" in js
    assert "wbState" in js
    assert "worldConfig" in js
    assert "preview" in js
    assert "/api/world-builder/preview" in js
    assert "/api/world-builder/create" in js
    assert "/api/world-builder/status" in js
    assert "/api/world-builder/config-hash" in js
    assert "preview_url" in js


def test_world_builder_preview_centers_scroll_on_load():
    js_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "js" / "world_builder.js"
    js = js_path.read_text(encoding="utf-8")
    update_preview_start = js.index("async function updatePreview()")
    update_preview_body = js[update_preview_start:]
    assert "image.onload" in update_preview_body, "updatePreview must attach onload to center scroll after preview image loads"
    assert "scrollWidth" in update_preview_body, "Scroll centering logic must consider scrollWidth"
    assert "clientWidth" in update_preview_body, "Scroll centering logic must consider clientWidth"
    assert "scrollHeight" in update_preview_body, "Scroll centering logic must consider scrollHeight"
    assert "clientHeight" in update_preview_body, "Scroll centering logic must consider clientHeight"
    assert "scrollLeft" in update_preview_body, "Scroll centering logic must set scrollLeft"
    assert "scrollTop" in update_preview_body, "Scroll centering logic must set scrollTop"


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


def test_world_builder_preview_image_uses_intrinsic_size():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    preview_image_start = css.index(".world-builder-preview-image")
    preview_image_block = css[preview_image_start:]
    preview_image_block = preview_image_block.split("}")[0] + "}"

    assert "max-width: 100%" not in preview_image_block, "Preview image must not be constrained by max-width so overflow triggers scroll"
    assert "max-height: 100%" not in preview_image_block, "Preview image must not be constrained by max-height so overflow triggers scroll"
    assert "object-fit:" not in preview_image_block, "Preview image must not use object-fit when native scroll is expected"


def test_world_builder_preview_card_is_fixed_height():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    preview_card_start = css.index(".world-builder-preview-card")
    preview_card_block = css[preview_card_start:]
    preview_card_block = preview_card_block.split("}")[0] + "}"

    assert "height: 100%" in preview_card_block, "Preview card must have fixed height to prevent growth from large images"
    assert "overflow: hidden" in preview_card_block, "Preview card must hide overflow so scroll only happens inside inner container"


def test_world_builder_config_card_has_internal_scroll():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    wb_config_start = css.index(".world-builder-config {")
    wb_config_block = css[wb_config_start:]
    wb_config_block = wb_config_block.split("}")[0] + "}"

    assert "height: 100%" in wb_config_block, "World builder config card must have fixed height to avoid growing layout"
    assert "overflow: hidden" in wb_config_block, "World builder config card must hide outer overflow so only inner resource list scrolls"
    assert "overflow-y: auto" not in wb_config_block, "World builder config card must not have its own vertical scrollbar"
    assert "min-height: 0" in wb_config_block, "World builder config card must have min-height: 0 to shrink inside flex/grid"

    scroll_area_start = css.index(".wb-scroll-area {")
    scroll_area_block = css[scroll_area_start:]
    scroll_area_block = scroll_area_block.split("}")[0] + "}"

    assert "overflow: hidden" in scroll_area_block, "World builder scroll area must hide outer overflow so only inner resource list scrolls"

    resources_body_start = css.index(".wb-resources-body {")
    resources_body_block = css[resources_body_start:]
    resources_body_block = resources_body_block.split("}")[0] + "}"

    assert "overflow-y: auto" in resources_body_block, "World builder resource list must provide the only vertical scrollbar"


def test_world_builder_layout_has_fixed_height():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    layout_start = css.index(".world-builder-layout {")
    layout_block = css[layout_start:]
    layout_block = layout_block.split("}")[0] + "}"

    assert "height: 100%" in layout_block, "World builder layout must have fixed height so preview card does not grow"
    assert "flex: 1" in layout_block, "World builder layout must remain flexible to fill available space"
    assert "min-height: 0" in layout_block, "World builder layout must allow shrinking inside flex/grid parents"


def test_world_builder_preview_container_allows_scrolling():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    preview_start = css.index(".world-builder-preview {")
    preview_block = css[preview_start:]
    preview_block = preview_block.split("}")[0] + "}"

    assert "overflow: auto" in preview_block or "overflow: scroll" in preview_block, "Preview container must allow scrolling when image exceeds container"
    assert "align-items: center" not in preview_block, "Preview container must not force center alignment so large images can scroll from top-left"
    assert "justify-content: center" not in preview_block, "Preview container must not force center alignment so large images can scroll from top-left"


def test_world_builder_preview_image_centers_when_smaller():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    preview_image_start = css.index(".world-builder-preview-image")
    preview_image_block = css[preview_image_start:]
    preview_image_block = preview_image_block.split("}")[0] + "}"

    assert "margin: auto" in preview_image_block, "Preview image must use margin:auto so smaller images remain centered inside the scroll container"


def test_app_shell_uses_full_viewport_without_overflow():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    app_shell_start = css.index(".app-shell {")
    app_shell_block = css[app_shell_start:]
    app_shell_block = app_shell_block.split("}")[0] + "}"

    assert "height: 100vh" in app_shell_block, "App shell must use full viewport height"
    assert "overflow: hidden" in app_shell_block, "App shell must hide outer overflow so page never grows beyond viewport"


def test_content_and_tab_panel_have_fixed_height():
    css_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "css" / "app.css"
    css = css_path.read_text(encoding="utf-8")

    content_start = css.index(".content {")
    content_block = css[content_start:]
    content_block = content_block.split("}")[0] + "}"

    assert "height: 100%" in content_block, "Content must have fixed height to constrain world builder layout"
    assert "overflow: hidden" in content_block, "Content must hide overflow so page never grows beyond viewport"

    tab_start = css.index(".tab-panel.active {")
    tab_block = css[tab_start:]
    tab_block = tab_block.split("}")[0] + "}"

    assert "height: 100%" in tab_block, "Active tab panel must have fixed height to constrain world builder layout"
    assert "overflow: hidden" in tab_block, "Active tab panel must hide overflow so page never grows beyond viewport"

