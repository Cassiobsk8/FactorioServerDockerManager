from __future__ import annotations

import json
from typing import Any

from backend.services.world_builder_schema import (
    MAP_GEN_SETTINGS_SCHEMA,
    MAP_SETTINGS_SCHEMA,
    get_field_by_id,
    get_fields_by_category,
    load_schema_metadata,
)


def _infer_form_type(field: dict[str, Any]) -> str:
    type_ = field.get("type", "string")
    if type_ in {"boolean"}:
        return "boolean"
    if type_ in {"uint32", "int32", "double", "number", "uint32|null"}:
        if field.get("options"):
            return "enum"
        if field.get("min") is not None and field.get("max") is not None:
            return "range"
        return "number"
    if type_ in {"string"}:
        if field.get("options"):
            return "enum"
        return "string"
    if type_ in {"array"}:
        return "array"
    if type_ in {"AutoplaceControl"}:
        return "group"
    return "string"


def _build_form_field(field: dict[str, Any]) -> dict[str, Any]:
    form_type = _infer_form_type(field)
    data: dict[str, Any] = {
        "id": field["id"],
        "label": field["label"],
        "description": field["description"],
        "type": form_type,
        "category": field["category"],
        "source_file": field["source_file"],
        "default": field.get("default"),
        "visible": True,
        "enabled": True,
    }
    if field.get("options"):
        data["options"] = field["options"]
    if field.get("min") is not None:
        data["min"] = field["min"]
    if field.get("max") is not None:
        data["max"] = field["max"]
    if field.get("unit"):
        data["unit"] = field["unit"]
    if field.get("planet_exclusive"):
        data["planet_exclusive"] = field["planet_exclusive"]
    if field.get("space_age_exclusive"):
        data["space_age_exclusive"] = True
    return data


def get_form_config(source_file: str | None = None) -> dict[str, Any]:
    fields = MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA
    if source_file in {"map-gen-settings.json", "map-settings.json"}:
        fields = [f for f in fields if f["source_file"] == source_file]
    form_fields = [_build_form_field(f) for f in fields]
    categories = sorted({f["category"] for f in form_fields})
    return {
        "version": "1.0.0",
        "source_file": source_file,
        "categories": categories,
        "fields": form_fields,
    }


def serialize_form_values(values: dict[str, Any], source_file: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        parts = key.split(".", 1)
        if len(parts) == 2:
            section, prop = parts
            if section not in result:
                result[section] = {}
            result[section][prop] = value
        else:
            result[key] = value
    return result


def deserialize_form_values(data: dict[str, Any], source_file: str | None = None) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for section, props in data.items():
        if isinstance(props, dict):
            for prop, value in props.items():
                values[f"{section}.{prop}"] = value
        else:
            values[section] = props
    return values


def validate_form_value(field_id: str, value: Any) -> str | None:
    field = get_field_by_id(field_id)
    if not field:
        return f"unknown field: {field_id}"
    type_ = field.get("type", "string")
    if type_ == "boolean" and not isinstance(value, bool):
        return "must be boolean"
    if type_ in {"uint32", "int32"}:
        if not isinstance(value, int) or isinstance(value, bool):
            return "must be integer"
        if field.get("min") is not None and value < field["min"]:
            return f"below minimum {field['min']}"
        if field.get("max") is not None and value > field["max"]:
            return f"above maximum {field['max']}"
    if type_ == "double":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "must be number"
        if field.get("min") is not None and value < field["min"]:
            return f"below minimum {field['min']}"
        if field.get("max") is not None and value > field["max"]:
            return f"above maximum {field['max']}"
    if field.get("options") and value not in field["options"]:
        return f"invalid option: {value}"
    return None


def get_default_values(source_file: str | None = None) -> dict[str, Any]:
    fields = MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA
    if source_file in {"map-gen-settings.json", "map-settings.json"}:
        fields = [f for f in fields if f["source_file"] == source_file]
    defaults: dict[str, Any] = {}
    for field in fields:
        defaults[field["id"]] = field.get("default")
    return defaults
