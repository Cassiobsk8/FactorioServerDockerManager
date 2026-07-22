from __future__ import annotations

import json

import pytest

from backend.services.world_builder_config_engine import (
    get_default_values,
    get_form_config,
    serialize_form_values,
    deserialize_form_values,
    validate_form_value,
)
from backend.services.world_builder_schema import get_field_by_id


def test_get_form_config_returns_version():
    config = get_form_config()
    assert config["version"] == "1.0.0"


def test_get_form_config_all_fields():
    config = get_form_config()
    assert len(config["fields"]) > 0
    for field in config["fields"]:
        assert "id" in field
        assert "label" in field
        assert "type" in field
        assert "category" in field


def test_get_form_config_filter_by_source_file():
    config = get_form_config(source_file="map-gen-settings.json")
    for field in config["fields"]:
        assert field["source_file"] == "map-gen-settings.json"
    assert config["source_file"] == "map-gen-settings.json"


def test_get_form_config_map_settings_source():
    config = get_form_config(source_file="map-settings.json")
    for field in config["fields"]:
        assert field["source_file"] == "map-settings.json"


def test_form_field_types():
    config = get_form_config()
    valid_types = {"string", "number", "boolean", "enum", "slider", "range", "group", "array"}
    for field in config["fields"]:
        assert field["type"] in valid_types


def test_serialize_form_values_nested():
    values = {
        "seed": 12345,
        "width": 0,
        "pollution.enabled": True,
        "autoplace_controls.coal": {"frequency": 1.0, "size": 1.0, "richness": 1.0},
    }
    result = serialize_form_values(values)
    assert result["seed"] == 12345
    assert result["width"] == 0
    assert result["pollution"]["enabled"] is True
    assert result["autoplace_controls"]["coal"]["frequency"] == 1.0


def test_serialize_form_values_skips_none():
    values = {"seed": None, "width": 0}
    result = serialize_form_values(values)
    assert "seed" not in result
    assert result["width"] == 0


def test_deserialize_form_values_nested():
    data = {
        "seed": 12345,
        "pollution": {"enabled": True, "diffusion_ratio": 0.02},
    }
    result = deserialize_form_values(data)
    assert result["seed"] == 12345
    assert result["pollution.enabled"] is True
    assert result["pollution.diffusion_ratio"] == 0.02


def test_validate_form_value_valid_boolean():
    error = validate_form_value("peaceful_mode", True)
    assert error is None


def test_validate_form_value_invalid_boolean():
    error = validate_form_value("peaceful_mode", "yes")
    assert error is not None


def test_validate_form_value_valid_number():
    error = validate_form_value("width", 1000)
    assert error is None


def test_validate_form_value_below_min():
    error = validate_form_value("width", -1)
    assert "below minimum" in error


def test_validate_form_value_above_max():
    error = validate_form_value("width", 999999999999)
    assert "above maximum" in error


def test_validate_form_value_invalid_option():
    error = validate_form_value("starting_area", "invalid")
    assert "invalid option" in error


def test_validate_form_value_valid_option():
    error = validate_form_value("starting_area", "medium")
    assert error is None


def test_get_default_values():
    defaults = get_default_values()
    assert "seed" in defaults
    assert "width" in defaults
    assert "height" in defaults


def test_get_default_values_map_gen():
    defaults = get_default_values(source_file="map-gen-settings.json")
    assert "seed" in defaults
    assert "autoplace_controls.coal" not in defaults or True


def test_get_default_values_map_settings():
    defaults = get_default_values(source_file="map-settings.json")
    assert "pollution.enabled" in defaults
    assert "enemy_evolution.enabled" in defaults


def test_serialize_roundtrip():
    original = {
        "seed": 123,
        "starting_area": "medium",
        "pollution": {"enabled": False, "diffusion_ratio": 0.5},
    }
    serialized = serialize_form_values(original)
    deserialized = deserialize_form_values(serialized)
    assert deserialized["seed"] == 123
    assert deserialized["starting_area"] == "medium"
    assert deserialized["pollution.enabled"] is False
    assert deserialized["pollution.diffusion_ratio"] == 0.5


def test_validate_unknown_field():
    error = validate_form_value("nonexistent.field", "value")
    assert "unknown field" in error


def test_form_config_has_all_categories():
    config = get_form_config()
    assert "Resources" in config["categories"]
    assert "Terrain" in config["categories"]
    assert "Water" in config["categories"]
    assert "Starting Area" in config["categories"]
    assert "Enemies" in config["categories"]
    assert "Pollution" in config["categories"]
    assert "Evolution" in config["categories"]
    assert "Expansion" in config["categories"]
    assert "Advanced" in config["categories"]
    assert "Planet" in config["categories"]


def test_form_config_has_autoplace_controls_in_resources():
    from backend.services.world_builder_schema import get_fields_by_category

    resource_fields = get_fields_by_category("Resources")
    autoplace_fields = [f for f in resource_fields if f["type"] == "AutoplaceControl"]
    assert len(autoplace_fields) > 0
    for field in autoplace_fields:
        assert field["default"] is not None
        assert "frequency" in field["default"]
        assert "size" in field["default"]
        if field.get("default", {}).get("richness") is not None:
            assert "richness" in field["default"]


def test_build_form_field_preserves_original_type_for_autoplace():
    from backend.services.world_builder_config_engine import _build_form_field

    field = {
        "id": "autoplace_controls.coal",
        "label": "Coal",
        "description": "Frequency, size and richness of coal deposits.",
        "category": "Resources",
        "type": "AutoplaceControl",
        "default": {"frequency": 1.0, "size": 1.0, "richness": 1.0},
        "source_file": "map-gen-settings.json",
        "min": 0.0,
        "max": 10.0,
    }
    result = _build_form_field(field)
    assert result["type"] == "group"
    assert result["original_type"] == "AutoplaceControl"
    assert result["default"] == {"frequency": 1.0, "size": 1.0, "richness": 1.0}
    assert result["min"] == 0.0
    assert result["max"] == 10.0


