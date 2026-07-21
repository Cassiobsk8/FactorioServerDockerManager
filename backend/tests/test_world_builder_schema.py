from __future__ import annotations

import json

import pytest

from backend.services.world_builder_schema import (
    MAP_GEN_SETTINGS_SCHEMA,
    MAP_SETTINGS_SCHEMA,
    get_categories,
    get_field_by_id,
    get_fields_by_category,
    load_schema_metadata,
    validate_schema_integrity,
)


def test_load_schema_metadata_returns_version():
    metadata = load_schema_metadata()
    assert "version" in metadata
    assert metadata["version"] == "1.0.0"


def test_load_schema_metadata_counts():
    metadata = load_schema_metadata()
    assert metadata["map_gen_settings_count"] == len(MAP_GEN_SETTINGS_SCHEMA)
    assert metadata["map_settings_count"] == len(MAP_SETTINGS_SCHEMA)
    assert metadata["map_gen_settings_count"] > 0
    assert metadata["map_settings_count"] > 0


def test_load_schema_metadata_categories():
    metadata = load_schema_metadata()
    assert "categories" in metadata
    assert isinstance(metadata["categories"], list)
    assert len(metadata["categories"]) > 0


def test_load_schema_metadata_fields_are_dicts():
    metadata = load_schema_metadata()
    for field in metadata["fields"]:
        assert isinstance(field, dict)
        assert "id" in field
        assert "label" in field
        assert "description" in field
        assert "category" in field
        assert "type" in field
        assert "source_file" in field


def test_validate_schema_integrity_no_duplicates():
    errors = validate_schema_integrity()
    duplicate_errors = [e for e in errors if "duplicate" in e]
    assert len(duplicate_errors) == 0


def test_validate_schema_integrity_valid_categories():
    errors = validate_schema_integrity()
    category_errors = [e for e in errors if "invalid category" in e]
    assert len(category_errors) == 0


def test_validate_schema_integrity_source_files():
    errors = validate_schema_integrity()
    source_errors = [e for e in errors if "source_file" in e]
    assert len(source_errors) == 0


def test_get_categories_returns_non_empty_list():
    categories = get_categories()
    assert isinstance(categories, list)
    assert len(categories) > 0
    assert "Resources" in categories
    assert "Terrain" in categories
    assert "Water" in categories
    assert "Starting Area" in categories
    assert "Enemies" in categories
    assert "Pollution" in categories
    assert "Evolution" in categories
    assert "Expansion" in categories
    assert "Advanced" in categories
    assert "Planet" in categories


def test_get_fields_by_category_resources():
    fields = get_fields_by_category("Resources")
    assert len(fields) > 0
    for field in fields:
        assert field["category"] == "Resources"


def test_get_fields_by_category_invalid():
    fields = get_fields_by_category("InvalidCategory")
    assert len(fields) == 0


def test_get_field_by_id_existing():
    field = get_field_by_id("seed")
    assert field is not None
    assert field["id"] == "seed"
    assert field["label"] == "Seed"
    assert field["source_file"] == "map-gen-settings.json"


def test_get_field_by_id_map_settings():
    field = get_field_by_id("pollution.enabled")
    assert field is not None
    assert field["id"] == "pollution.enabled"
    assert field["label"] == "Pollution Enabled"
    assert field["source_file"] == "map-settings.json"


def test_get_field_by_id_nonexistent():
    field = get_field_by_id("nonexistent.field")
    assert field is None


def test_map_gen_schema_has_required_fields():
    required = ["seed", "width", "height", "starting_area", "peaceful_mode"]
    for req in required:
        field = get_field_by_id(req)
        assert field is not None, f"Missing required field: {req}"


def test_map_settings_schema_has_required_fields():
    required = [
        "difficulty_settings.technology_price_multiplier",
        "pollution.enabled",
        "enemy_evolution.enabled",
        "enemy_expansion.enabled",
    ]
    for req in required:
        field = get_field_by_id(req)
        assert field is not None, f"Missing required field: {req}"


def test_space_age_fields_marked():
    space_age_fields = [f for f in MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA if f.get("space_age_exclusive")]
    assert len(space_age_fields) > 0
    for field in space_age_fields:
        assert field["space_age_exclusive"] is True


def test_planet_exclusive_fields():
    planet_fields = [f for f in MAP_GEN_SETTINGS_SCHEMA if f.get("planet_exclusive")]
    assert len(planet_fields) > 0
    for field in planet_fields:
        assert "planet_exclusive" in field
        assert isinstance(field["planet_exclusive"], list)


def test_schema_serializable():
    metadata = load_schema_metadata()
    serialized = json.dumps(metadata, default=str)
    assert isinstance(serialized, str)
    assert len(serialized) > 0


def test_map_gen_schema_field_types():
    valid_types = {
        "boolean", "uint32", "int32", "double", "string", "array",
        "AutoplaceControl", "MapGenSize", "uint32|null",
    }
    for field in MAP_GEN_SETTINGS_SCHEMA:
        assert field["type"] in valid_types, f"Invalid type '{field['type']}' for {field['id']}"


def test_map_settings_schema_field_types():
    valid_types = {
        "boolean", "uint32", "int32", "double", "string", "array",
    }
    for field in MAP_SETTINGS_SCHEMA:
        assert field["type"] in valid_types, f"Invalid type '{field['type']}' for {field['id']}"


def test_no_duplicate_labels():
    labels = [f["label"] for f in MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA]
    assert len(labels) == len(set(labels))


def test_all_fields_have_description():
    for field in MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA:
        assert len(field["description"]) > 0
