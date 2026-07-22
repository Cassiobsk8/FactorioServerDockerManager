from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CATEGORY_RESOURCES = "Resources"
CATEGORY_TERRAIN = "Terrain"
CATEGORY_WATER = "Water"
CATEGORY_STARTING_AREA = "Starting Area"
CATEGORY_ENEMIES = "Enemies"
CATEGORY_POLLUTION = "Pollution"
CATEGORY_EVOLUTION = "Evolution"
CATEGORY_EXPANSION = "Expansion"
CATEGORY_ADVANCED = "Advanced"
CATEGORY_PLANET = "Planet"

WORLD_BUILDER_SCHEMA_VERSION = "1.0.0"


@dataclass
class FieldMetadata:
    id: str
    label: str
    description: str
    category: str
    type: str
    default: Any = None
    options: list[str] | None = None
    min: float | int | None = None
    max: float | int | None = None
    unit: str | None = None
    source_file: str | None = None
    parent: str | None = None
    planet_exclusive: list[str] | None = None
    space_age_exclusive: bool = False
    can_be_disabled: bool = True


def _autoplace(
    control_id: str,
    label: str,
    description: str,
    default: float = 1.0,
    min_val: float = 0.0,
    max_val: float = 10.0,
    planet_exclusive: list[str] | None = None,
    richness: bool = True,
    order_: str | None = None,
    can_be_disabled: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": f"autoplace_controls.{control_id}",
        "label": label,
        "description": description,
        "category": CATEGORY_RESOURCES,
        "type": "AutoplaceControl",
        "default": {"frequency": default, "size": default},
        "min": min_val,
        "max": max_val,
        "source_file": "map-gen-settings.json",
        "can_be_disabled": can_be_disabled,
    }
    if richness:
        data["default"]["richness"] = default
    if planet_exclusive is not None:
        data["planet_exclusive"] = planet_exclusive
    if order_ is not None:
        data["order"] = order_
    return data


def _field(
    field_id: str,
    label: str,
    description: str,
    category: str,
    type_: str,
    default: Any = None,
    options: list[str] | None = None,
    min_: float | int | None = None,
    max_: float | int | None = None,
    unit: str | None = None,
    source_file: str = "map-gen-settings.json",
    parent: str | None = None,
    planet_exclusive: list[str] | None = None,
    space_age_exclusive: bool = False,
    order_: str | None = None,
    can_be_disabled: bool = True,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": field_id,
        "label": label,
        "description": description,
        "category": category,
        "type": type_,
        "default": default,
        "source_file": source_file,
        "can_be_disabled": can_be_disabled,
    }
    if options is not None:
        data["options"] = options
    if min_ is not None:
        data["min"] = min_
    if max_ is not None:
        data["max"] = max_
    if unit is not None:
        data["unit"] = unit
    if parent is not None:
        data["parent"] = parent
    if planet_exclusive is not None:
        data["planet_exclusive"] = planet_exclusive
    if space_age_exclusive:
        data["space_age_exclusive"] = True
    if order_ is not None:
        data["order"] = order_
    return data


MAP_GEN_SETTINGS_SCHEMA = [
    _field("width", "Width", "Width of the map in tiles. If 0, the map has 'infinite' width.", CATEGORY_ADVANCED, "uint32", default=0, min_=0, max_=1_000_000, unit="tiles", source_file="map-gen-settings.json"),
    _field("height", "Height", "Height of the map in tiles. If 0, the map has 'infinite' height.", CATEGORY_ADVANCED, "uint32", default=0, min_=0, max_=1_000_000, unit="tiles", source_file="map-gen-settings.json"),
    _field("starting_area", "Starting Area", "Multiplier for 'biter free zone radius'.", CATEGORY_STARTING_AREA, "MapGenSize", default=1, options=["none", "poor", "small", "medium", "good", "none"], min_=0, max_=10, source_file="map-gen-settings.json"),
    _field("peaceful_mode", "Peaceful Mode", "If true, enemy creatures will not attack unless the player first attacks them.", CATEGORY_ENEMIES, "boolean", default=False, source_file="map-gen-settings.json"),
    _field("no_enemies_mode", "No Enemies Mode", "If true, enemy creatures will not naturally spawn.", CATEGORY_ENEMIES, "boolean", default=False, source_file="map-gen-settings.json"),
    _field("default_enable_all_autoplace_controls", "Default Enable All Autoplace Controls", "Whether undefined autoplace_controls should fall back to the default controls.", CATEGORY_ADVANCED, "boolean", default=True, source_file="map-gen-settings.json"),
    _autoplace("coal", "Coal", "Frequency, size and richness of coal deposits.", order_="a-d"),
    _autoplace("stone", "Stone", "Frequency, size and richness of stone deposits.", order_="a-c"),
    _autoplace("copper-ore", "Copper Ore", "Frequency, size and richness of copper ore deposits.", order_="a-b"),
    _autoplace("iron-ore", "Iron Ore", "Frequency, size and richness of iron ore deposits.", order_="a-a"),
    _autoplace("uranium-ore", "Uranium Ore", "Frequency, size and richness of uranium ore deposits.", order_="a-f"),
    _autoplace("crude-oil", "Crude Oil", "Frequency, size and richness of crude oil patches.", order_="a-e"),
    _field("autoplace_controls.water", "Water", "Frequency and size of water patches.", CATEGORY_WATER, "AutoplaceControl", default={"frequency": 1.0, "size": 1.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", order_="c-a"),
    _autoplace("trees", "Trees", "Frequency and size of tree clusters.", order_="c-x"),
    _autoplace("enemy-base", "Enemy Bases", "Frequency and size of enemy bases.", order_="c-z", can_be_disabled=False),
    _field("autoplace_controls.rocks", "Rocks", "Frequency and size of rock patches.", CATEGORY_RESOURCES, "AutoplaceControl", default={"frequency": 1.0, "size": 1.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", order_="c-y"),
    _field("autoplace_controls.starting_area_moisture", "Starting Area Moisture", "Moisture setting for the starting area.", CATEGORY_RESOURCES, "AutoplaceControl", default={"frequency": 1.0, "size": 1.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", order_="c-z"),
    _field("autoplace_controls.nauvis_cliff", "Nauvis Cliffs", "Frequency, size and richness of cliffs on Nauvis.", CATEGORY_PLANET, "AutoplaceControl", default={"frequency": 1.0, "size": 2.0, "richness": 0.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", order_="c-z"),
    _autoplace("vulcanus_coal", "Vulcanus Coal", "Frequency, size and richness of coal deposits on Vulcanus.", planet_exclusive=["vulcanus"], order_="b-a"),
    _autoplace("calcite", "Calcite", "Frequency, size and richness of calcite deposits.", planet_exclusive=["vulcanus"], order_="b-c"),
    _autoplace("sulfuric-acid-geyser", "Sulfuric Acid Geyser", "Frequency, size and richness of sulfuric acid geysers.", planet_exclusive=["vulcanus"], order_="b-c"),
    _autoplace("tungsten-ore", "Tungsten Ore", "Frequency, size and richness of tungsten ore deposits.", planet_exclusive=["vulcanus"], order_="b-d"),
    _autoplace("gleba_stone", "Gleba Stone", "Frequency, size and richness of stone deposits on Gleba.", planet_exclusive=["gleba"], order_="c-a"),
    _field("autoplace_controls.gleba_water", "Gleba Water", "Frequency and size of water patches on Gleba.", CATEGORY_RESOURCES, "AutoplaceControl", default={"frequency": 1.0, "size": 1.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", planet_exclusive=["gleba"], order_="c-z-b", can_be_disabled=False),
    _field("autoplace_controls.gleba_plants", "Gleba Plants", "Frequency and size of plant life on Gleba.", CATEGORY_RESOURCES, "AutoplaceControl", default={"frequency": 1.0, "size": 1.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", planet_exclusive=["gleba"], order_="c-z-c", can_be_disabled=False),
    _autoplace("scrap", "Scrap", "Frequency, size and richness of scrap piles.", planet_exclusive=["fulgora"], order_="d-a"),
    _field("autoplace_controls.fulgora_islands", "Fulgora Islands", "Frequency and size of islands on Fulgora.", CATEGORY_RESOURCES, "AutoplaceControl", default={"frequency": 1.0, "size": 1.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", planet_exclusive=["fulgora"], order_="c-z-d", can_be_disabled=False),
    _autoplace("aquilo_crude_oil", "Aquilo Crude Oil", "Frequency, size and richness of crude oil patches on Aquilo.", planet_exclusive=["aquilo"], order_="e-a"),
    _autoplace("fluorine_vent", "Fluorine Vent", "Frequency, size and richness of fluorine vents.", planet_exclusive=["aquilo"], order_="e-c"),
    _autoplace("lithium_brine", "Lithium Brine", "Frequency, size and richness of lithium brine deposits.", planet_exclusive=["aquilo"], order_="e-b"),
    _field("autoplace_controls.vulcanus_volcanism", "Vulcanus Volcanism", "Frequency and size of volcanic activity on Vulcanus.", CATEGORY_RESOURCES, "AutoplaceControl", default={"frequency": 1.0, "size": 1.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", planet_exclusive=["vulcanus"], order_="c-z-a", can_be_disabled=False),
    _field("autoplace_controls.gleba_enemy_base", "Gleba Enemy Bases", "Frequency and size of enemy bases on Gleba.", CATEGORY_RESOURCES, "AutoplaceControl", default={"frequency": 1.0, "size": 1.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", planet_exclusive=["gleba"], order_="z", can_be_disabled=False),
    _field("autoplace_controls.fulgora_cliff", "Fulgora Cliffs", "Frequency, size and richness of cliffs on Fulgora.", CATEGORY_PLANET, "AutoplaceControl", default={"frequency": 1.0, "size": 2.0, "richness": 0.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", planet_exclusive=["fulgora"], space_age_exclusive=True, order_="c-z-c"),
    _field("autoplace_controls.gleba_cliff", "Gleba Cliffs", "Frequency, size and richness of cliffs on Gleba.", CATEGORY_PLANET, "AutoplaceControl", default={"frequency": 1.0, "size": 2.0, "richness": 0.0}, min_=0.0, max_=10.0, source_file="map-gen-settings.json", planet_exclusive=["gleba"], space_age_exclusive=True, order_="c-z-b"),
    _field("cliff_settings.name", "Cliff Prototype Name", "Name of the cliff prototype.", CATEGORY_TERRAIN, "string", default="cliff", source_file="map-gen-settings.json"),
    _field("cliff_settings.cliff_elevation_0", "Cliff Elevation 0", "Elevation of first row of cliffs.", CATEGORY_TERRAIN, "double", default=10, min_=0, max_=100, source_file="map-gen-settings.json"),
    _field("cliff_settings.cliff_elevation_interval", "Cliff Elevation Interval", "Elevation difference between successive rows of cliffs.", CATEGORY_TERRAIN, "double", default=40, min_=1, max_=200, source_file="map-gen-settings.json"),
    _field("cliff_settings.cliff_smoothing", "Cliff Smoothing", "Smoothing applied to cliff edges.", CATEGORY_TERRAIN, "double", default=1, min_=0, max_=10, source_file="map-gen-settings.json", space_age_exclusive=True),
    _field("cliff_settings.richness", "Cliff Richness", "Called 'cliff continuity' in the map generator GUI. 0 = no cliffs, 10 = solid cliff rows.", CATEGORY_TERRAIN, "double", default=1, min_=0, max_=10, source_file="map-gen-settings.json"),
    _field("property_expression_names.elevation", "Elevation Expression", "Overrides for the elevation property value generator.", CATEGORY_TERRAIN, "string", default="", source_file="map-gen-settings.json"),
    _field("property_expression_names.control:moisture:frequency", "Moisture Frequency", "Inverse of the 'moisture scale' in the map generator GUI.", CATEGORY_TERRAIN, "string", default="1", source_file="map-gen-settings.json"),
    _field("property_expression_names.control:moisture:bias", "Moisture Bias", "The 'moisture bias' in the map generator GUI.", CATEGORY_TERRAIN, "string", default="0", source_file="map-gen-settings.json"),
    _field("property_expression_names.control:aux:frequency", "Terrain Type Frequency", "Inverse of the 'terrain type scale' in the map generator GUI.", CATEGORY_TERRAIN, "string", default="1", source_file="map-gen-settings.json"),
    _field("property_expression_names.control:aux:bias", "Terrain Type Bias", "The 'terrain type bias' in the map generator GUI.", CATEGORY_TERRAIN, "string", default="0", source_file="map-gen-settings.json"),
    _field("starting_points", "Starting Points", "Positions of the starting areas.", CATEGORY_STARTING_AREA, "array", default=[{"x": 0, "y": 0}], source_file="map-gen-settings.json"),
    _field("seed", "Seed", "Use null for a random seed, or a number for a specific seed.", CATEGORY_ADVANCED, "uint32|null", default=None, min_=0, max_=4294967295, source_file="map-gen-settings.json"),
    _field("territory_settings.enabled", "Territory Enabled", "Whether territory system is enabled.", CATEGORY_PLANET, "boolean", default=True, source_file="map-gen-settings.json", space_age_exclusive=True),
    _field("territory_settings.force", "Territory Force", "Force index for territory ownership.", CATEGORY_PLANET, "uint32", default=1, min_=0, max_=255, source_file="map-gen-settings.json", space_age_exclusive=True),
    _field("territory_settings.chunk_padding", "Territory Chunk Padding", "Padding in chunks around territory boundaries.", CATEGORY_PLANET, "uint32", default=0, min_=0, max_=10, source_file="map-gen-settings.json", space_age_exclusive=True),
]


MAP_SETTINGS_SCHEMA = [
    _field("difficulty_settings.technology_price_multiplier", "Technology Price Multiplier", "Multiplier for technology research costs.", CATEGORY_ADVANCED, "double", default=1.0, min_=0.0, max_=100.0, source_file="map-settings.json"),
    _field("difficulty_settings.spoil_time_modifier", "Spoil Time Modifier", "Modifier for spoil time of items.", CATEGORY_ADVANCED, "double", default=1.0, min_=0.0, max_=100.0, source_file="map-settings.json", space_age_exclusive=True),
    _field("pollution.enabled", "Pollution Enabled", "Whether pollution is enabled at all.", CATEGORY_POLLUTION, "boolean", default=True, source_file="map-settings.json"),
    _field("pollution.diffusion_ratio", "Pollution Diffusion Ratio", "The amount of pollution diffused to neighboring chunk per second.", CATEGORY_POLLUTION, "double", default=0.02, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("pollution.min_to_diffuse", "Min Pollution to Diffuse", "Pollution units needed on a chunk to start diffusing.", CATEGORY_POLLUTION, "double", default=15, min_=0.0, source_file="map-settings.json"),
    _field("pollution.ageing", "Pollution Ageing", "Modifier of pollution eaten by a chunk's tiles.", CATEGORY_POLLUTION, "double", default=1.0, min_=0.0, max_=10.0, source_file="map-settings.json"),
    _field("pollution.expected_max_per_chunk", "Expected Max Pollution Per Chunk", "Pollution amount above this is visualized as this value.", CATEGORY_POLLUTION, "double", default=150, min_=0.0, source_file="map-settings.json"),
    _field("pollution.min_to_show_per_chunk", "Min Pollution to Show Per Chunk", "Pollution below this is visualized as this value.", CATEGORY_POLLUTION, "double", default=50, min_=0.0, source_file="map-settings.json"),
    _field("pollution.min_pollution_to_damage_trees", "Min Pollution to Damage Trees", "Pollution above this starts damaging trees.", CATEGORY_POLLUTION, "double", default=60, min_=0.0, source_file="map-settings.json"),
    _field("pollution.pollution_with_max_forest_damage", "Pollution With Max Forest Damage", "Pollution amount at which forest damage reaches maximum.", CATEGORY_POLLUTION, "double", default=150, min_=0.0, source_file="map-settings.json"),
    _field("pollution.pollution_per_tree_damage", "Pollution Per Tree Damage", "Pollution absorbed per tree damage.", CATEGORY_POLLUTION, "double", default=50, min_=0.0, source_file="map-settings.json"),
    _field("pollution.pollution_restored_per_tree_damage", "Pollution Restored Per Tree Damage", "Pollution restored when a damaged tree recovers.", CATEGORY_POLLUTION, "double", default=10, min_=0.0, source_file="map-settings.json"),
    _field("pollution.max_pollution_to_restore_trees", "Max Pollution to Restore Trees", "Maximum pollution at which trees can be restored.", CATEGORY_POLLUTION, "double", default=20, min_=0.0, source_file="map-settings.json"),
    _field("pollution.enemy_attack_pollution_consumption_modifier", "Enemy Attack Pollution Consumption Modifier", "Modifier for pollution consumed by enemy attacks.", CATEGORY_POLLUTION, "double", default=1.0, min_=0.0, source_file="map-settings.json"),
    _field("enemy_evolution.enabled", "Enemy Evolution Enabled", "Whether enemy evolution is enabled.", CATEGORY_EVOLUTION, "boolean", default=True, source_file="map-settings.json"),
    _field("enemy_evolution.time_factor", "Evolution Time Factor", "Natural evolution progress per second.", CATEGORY_EVOLUTION, "double", default=0.000004, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("enemy_evolution.destroy_factor", "Evolution Destroy Factor", "Evolution progress per destroyed spawner.", CATEGORY_EVOLUTION, "double", default=0.002, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("enemy_evolution.pollution_factor", "Evolution Pollution Factor", "Evolution progress per unit of pollution.", CATEGORY_EVOLUTION, "double", default=0.0000009, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("enemy_expansion.enabled", "Enemy Expansion Enabled", "Whether enemy expansion is enabled.", CATEGORY_EXPANSION, "boolean", default=True, source_file="map-settings.json"),
    _field("enemy_expansion.max_expansion_distance", "Max Expansion Distance", "Distance in chunks preventing expansions from reaching too far.", CATEGORY_EXPANSION, "uint32", default=5, min_=0, max_=255, unit="chunks", source_file="map-settings.json"),
    _field("enemy_expansion.min_expansion_distance", "Min Expansion Distance", "Distance in chunks preventing expansions from being too close to bases.", CATEGORY_EXPANSION, "uint32", default=3, min_=0, max_=255, unit="chunks", source_file="map-settings.json"),
    _field("enemy_expansion.friendly_base_influence_radius", "Friendly Base Influence Radius", "Radius around friendly bases influencing expansion scoring.", CATEGORY_EXPANSION, "uint32", default=6, min_=0, max_=50, unit="chunks", source_file="map-settings.json"),
    _field("enemy_expansion.enemy_building_influence_radius", "Enemy Building Influence Radius", "Radius around enemy buildings influencing expansion scoring.", CATEGORY_EXPANSION, "uint32", default=3, min_=0, max_=50, unit="chunks", source_file="map-settings.json"),
    _field("enemy_expansion.building_coefficient", "Building Coefficient", "Coefficient for player buildings in expansion scoring.", CATEGORY_EXPANSION, "double", default=0.5, min_=0.0, max_=100.0, source_file="map-settings.json"),
    _field("enemy_expansion.other_base_coefficient", "Other Base Coefficient", "Coefficient for other enemy bases in expansion scoring.", CATEGORY_EXPANSION, "double", default=3.0, min_=0.0, max_=100.0, source_file="map-settings.json"),
    _field("enemy_expansion.neighbouring_chunk_coefficient", "Neighbouring Chunk Coefficient", "Coefficient for neighbouring chunks in expansion scoring.", CATEGORY_EXPANSION, "double", default=0.5, min_=0.0, max_=100.0, source_file="map-settings.json"),
    _field("enemy_expansion.neighbouring_base_chunk_coefficient", "Neighbouring Base Chunk Coefficient", "Coefficient for neighbouring base chunks in expansion scoring.", CATEGORY_EXPANSION, "double", default=0.5, min_=0.0, max_=100.0, source_file="map-settings.json"),
    _field("enemy_expansion.max_colliding_tiles_coefficient", "Max Colliding Tiles Coefficient", "Max percentage of unbuildable tiles for expansion candidate.", CATEGORY_EXPANSION, "double", default=0.8, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("enemy_expansion.settler_group_min_size", "Settler Group Min Size", "Minimum size of a biter group building a new base.", CATEGORY_EXPANSION, "uint32", default=5, min_=1, max_=1000, source_file="map-settings.json"),
    _field("enemy_expansion.settler_group_max_size", "Settler Group Max Size", "Maximum size of a biter group building a new base.", CATEGORY_EXPANSION, "uint32", default=20, min_=1, max_=1000, source_file="map-settings.json"),
    _field("enemy_expansion.evolution_group_size_factor", "Evolution Group Size Factor", "Factor by which evolution affects group size.", CATEGORY_EXPANSION, "double", default=4.0, min_=0.0, max_=100.0, source_file="map-settings.json"),
    _field("enemy_expansion.min_expansion_cooldown", "Min Expansion Cooldown", "Minimum time between expansions in ticks.", CATEGORY_EXPANSION, "uint32", default=14400, min_=0, max_=1_000_000, unit="ticks", source_file="map-settings.json"),
    _field("enemy_expansion.max_expansion_cooldown", "Max Expansion Cooldown", "Maximum time between expansions in ticks.", CATEGORY_EXPANSION, "uint32", default=216000, min_=0, max_=10_000_000, unit="ticks", source_file="map-settings.json"),
    _field("unit_group.min_group_gathering_time", "Min Group Gathering Time", "Minimum time for a unit group to gather in ticks.", CATEGORY_ENEMIES, "uint32", default=3600, min_=0, max_=1_000_000, unit="ticks", source_file="map-settings.json"),
    _field("unit_group.max_group_gathering_time", "Max Group Gathering Time", "Maximum time for a unit group to gather in ticks.", CATEGORY_ENEMIES, "uint32", default=36000, min_=0, max_=10_000_000, unit="ticks", source_file="map-settings.json"),
    _field("unit_group.max_wait_time_for_late_members", "Max Wait Time For Late Members", "Maximum time to wait for late members in ticks.", CATEGORY_ENEMIES, "uint32", default=7200, min_=0, max_=1_000_000, unit="ticks", source_file="map-settings.json"),
    _field("unit_group.max_group_radius", "Max Group Radius", "Maximum radius in tiles for unit group formation.", CATEGORY_ENEMIES, "uint32", default=30, min_=1, max_=1000, unit="tiles", source_file="map-settings.json"),
    _field("unit_group.min_group_radius", "Min Group Radius", "Minimum radius in tiles for unit group formation.", CATEGORY_ENEMIES, "uint32", default=5, min_=1, max_=1000, unit="tiles", source_file="map-settings.json"),
    _field("unit_group.max_member_speedup_when_behind", "Max Member Speedup When Behind", "Max speed multiplier for members behind the group.", CATEGORY_ENEMIES, "double", default=1.4, min_=1.0, max_=10.0, source_file="map-settings.json"),
    _field("unit_group.max_member_slowdown_when_ahead", "Max Member Slowdown When Ahead", "Max speed multiplier for members ahead of the group.", CATEGORY_ENEMIES, "double", default=0.6, min_=0.1, max_=1.0, source_file="map-settings.json"),
    _field("unit_group.max_group_slowdown_factor", "Max Group Slowdown Factor", "Maximum slowdown factor applied to the whole group.", CATEGORY_ENEMIES, "double", default=0.3, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("unit_group.max_group_member_fallback_factor", "Max Group Member Fallback Factor", "Maximum fallback factor for group members.", CATEGORY_ENEMIES, "double", default=3.0, min_=1.0, max_=100.0, source_file="map-settings.json"),
    _field("unit_group.member_disown_distance", "Member Disown Distance", "Distance in tiles at which a member is disowned.", CATEGORY_ENEMIES, "uint32", default=10, min_=0, max_=1000, unit="tiles", source_file="map-settings.json"),
    _field("unit_group.tick_tolerance_when_member_arrives", "Tick Tolerance When Member Arrives", "Tick tolerance when a member arrives at gathering point.", CATEGORY_ENEMIES, "uint32", default=60, min_=0, max_=10000, unit="ticks", source_file="map-settings.json"),
    _field("unit_group.max_gathering_unit_groups", "Max Gathering Unit Groups", "Max groups gathering simultaneously.", CATEGORY_ENEMIES, "uint32", default=30, min_=0, max_=1000, source_file="map-settings.json"),
    _field("unit_group.max_unit_group_size", "Max Unit Group Size", "Max units in a single group.", CATEGORY_ENEMIES, "uint32", default=200, min_=1, max_=10000, source_file="map-settings.json"),
    _field("path_finder.fwd2bwd_ratio", "Forward to Backward Ratio", "Ratio of forward to backward pathfinding steps.", CATEGORY_ADVANCED, "uint32", default=5, min_=1, max_=100, source_file="map-settings.json"),
    _field("path_finder.goal_pressure_ratio", "Goal Pressure Ratio", "Ratio of goal pressure in pathfinding.", CATEGORY_ADVANCED, "uint32", default=2, min_=1, max_=100, source_file="map-settings.json"),
    _field("path_finder.max_steps_worked_per_tick", "Max Steps Worked Per Tick", "Max pathfinding steps per game tick.", CATEGORY_ADVANCED, "uint32", default=1000, min_=1, max_=100_000, source_file="map-settings.json"),
    _field("path_finder.max_work_done_per_tick", "Max Work Done Per Tick", "Max pathfinding work per game tick.", CATEGORY_ADVANCED, "uint32", default=8000, min_=1, max_=1_000_000, source_file="map-settings.json"),
    _field("path_finder.use_path_cache", "Use Path Cache", "Whether to use path caching.", CATEGORY_ADVANCED, "boolean", default=True, source_file="map-settings.json"),
    _field("path_finder.short_cache_size", "Short Cache Size", "Size of the short path cache.", CATEGORY_ADVANCED, "uint32", default=5, min_=0, max_=100, source_file="map-settings.json"),
    _field("path_finder.long_cache_size", "Long Cache Size", "Size of the long path cache.", CATEGORY_ADVANCED, "uint32", default=25, min_=0, max_=1000, source_file="map-settings.json"),
    _field("path_finder.short_cache_min_cacheable_distance", "Short Cache Min Cacheable Distance", "Min distance for short cache.", CATEGORY_ADVANCED, "uint32", default=10, min_=0, max_=10000, unit="tiles", source_file="map-settings.json"),
    _field("path_finder.short_cache_min_algo_steps_to_cache", "Short Cache Min Algo Steps To Cache", "Min algo steps for short cache.", CATEGORY_ADVANCED, "uint32", default=50, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.long_cache_min_cacheable_distance", "Long Cache Min Cacheable Distance", "Min distance for long cache.", CATEGORY_ADVANCED, "uint32", default=30, min_=0, max_=10000, unit="tiles", source_file="map-settings.json"),
    _field("path_finder.cache_max_connect_to_cache_steps_multiplier", "Cache Max Connect Steps Multiplier", "Multiplier for max steps connecting to cache.", CATEGORY_ADVANCED, "uint32", default=100, min_=1, max_=10000, source_file="map-settings.json"),
    _field("path_finder.cache_accept_path_start_distance_ratio", "Cache Accept Path Start Distance Ratio", "Max start distance ratio for cached paths.", CATEGORY_ADVANCED, "double", default=0.2, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("path_finder.cache_accept_path_end_distance_ratio", "Cache Accept Path End Distance Ratio", "Max end distance ratio for cached paths.", CATEGORY_ADVANCED, "double", default=0.15, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("path_finder.negative_cache_accept_path_start_distance_ratio", "Negative Cache Accept Path Start Distance Ratio", "Max start distance ratio for negative cache.", CATEGORY_ADVANCED, "double", default=0.3, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("path_finder.negative_cache_accept_path_end_distance_ratio", "Negative Cache Accept Path End Distance Ratio", "Max end distance ratio for negative cache.", CATEGORY_ADVANCED, "double", default=0.3, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("path_finder.cache_path_start_distance_rating_multiplier", "Cache Path Start Distance Rating Multiplier", "Rating multiplier for path start distance.", CATEGORY_ADVANCED, "uint32", default=10, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.cache_path_end_distance_rating_multiplier", "Cache Path End Distance Rating Multiplier", "Rating multiplier for path end distance.", CATEGORY_ADVANCED, "uint32", default=20, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.stale_enemy_with_same_destination_collision_penalty", "Stale Enemy Same Destination Collision Penalty", "Collision penalty for stale enemies with same destination.", CATEGORY_ADVANCED, "uint32", default=30, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.ignore_moving_enemy_collision_distance", "Ignore Moving Enemy Collision Distance", "Distance within which moving enemies are ignored.", CATEGORY_ADVANCED, "uint32", default=5, min_=0, max_=1000, unit="tiles", source_file="map-settings.json"),
    _field("path_finder.enemy_with_different_destination_collision_penalty", "Enemy Different Destination Collision Penalty", "Collision penalty for enemies with different destinations.", CATEGORY_ADVANCED, "uint32", default=30, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.general_entity_collision_penalty", "General Entity Collision Penalty", "General collision penalty for entities.", CATEGORY_ADVANCED, "uint32", default=10, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.general_entity_subsequent_collision_penalty", "General Entity Subsequent Collision Penalty", "Subsequent collision penalty.", CATEGORY_ADVANCED, "uint32", default=3, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.extended_collision_penalty", "Extended Collision Penalty", "Extended collision penalty.", CATEGORY_ADVANCED, "uint32", default=3, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.max_clients_to_accept_any_new_request", "Max Clients To Accept Any New Request", "Max clients accepting new pathfinding requests.", CATEGORY_ADVANCED, "uint32", default=10, min_=0, max_=10000, source_file="map-settings.json"),
    _field("path_finder.max_clients_to_accept_short_new_request", "Max Clients To Accept Short New Request", "Max clients accepting short pathfinding requests.", CATEGORY_ADVANCED, "uint32", default=100, min_=0, max_=100_000, source_file="map-settings.json"),
    _field("path_finder.direct_distance_to_consider_short_request", "Direct Distance To Consider Short Request", "Direct distance below which a request is short.", CATEGORY_ADVANCED, "uint32", default=1000, min_=0, max_=100_000, unit="tiles", source_file="map-settings.json"),
    _field("path_finder.short_request_max_steps", "Short Request Max Steps", "Max steps for short pathfinding requests.", CATEGORY_ADVANCED, "uint32", default=1000, min_=1, max_=100_000, source_file="map-settings.json"),
    _field("path_finder.short_request_ratio", "Short Request Ratio", "Ratio of short requests allowed.", CATEGORY_ADVANCED, "double", default=0.5, min_=0.0, max_=1.0, source_file="map-settings.json"),
    _field("path_finder.min_steps_to_check_path_find_termination", "Min Steps To Check Path Find Termination", "Min steps before checking termination.", CATEGORY_ADVANCED, "uint32", default=2000, min_=0, max_=100_000, source_file="map-settings.json"),
    _field("path_finder.start_to_goal_cost_multiplier_to_terminate_path_find", "Start To Goal Cost Multiplier To Terminate", "Cost multiplier to terminate pathfinding.", CATEGORY_ADVANCED, "uint32", default=2000, min_=1, max_=100_000, source_file="map-settings.json"),
    _field("path_finder.overload_levels", "Overload Levels", "Thresholds for pathfinding overload.", CATEGORY_ADVANCED, "array", default=[0, 100, 500], source_file="map-settings.json"),
    _field("path_finder.overload_multipliers", "Overload Multipliers", "Multipliers applied at overload levels.", CATEGORY_ADVANCED, "array", default=[2, 3, 4], source_file="map-settings.json"),
    _field("path_finder.negative_path_cache_delay_interval", "Negative Path Cache Delay Interval", "Delay interval for negative path cache.", CATEGORY_ADVANCED, "uint32", default=20, min_=0, max_=10000, source_file="map-settings.json"),
    _field("asteroids.spawning_rate", "Asteroid Spawning Rate", "Rate of asteroid spawning.", CATEGORY_ADVANCED, "double", default=1.0, min_=0.0, max_=100.0, source_file="map-settings.json", space_age_exclusive=True),
    _field("asteroids.max_ray_portals_expanded_per_tick", "Max Ray Portals Expanded Per Tick", "Maximum ray portals expanded per tick.", CATEGORY_ADVANCED, "uint32", default=100, min_=0, max_=10000, source_file="map-settings.json", space_age_exclusive=True),
    _field("max_failed_behavior_count", "Max Failed Behavior Count", "If a behavior fails this many times, the enemy is destroyed.", CATEGORY_ADVANCED, "uint32", default=3, min_=0, max_=1000, source_file="map-settings.json"),
]


CATEGORIES = sorted({f["category"] for f in MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA})


def get_categories() -> list[str]:
    return CATEGORIES


def get_fields_by_category(category: str) -> list[dict[str, Any]]:
    return [f for f in MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA if f["category"] == category]


def get_field_by_id(field_id: str) -> dict[str, Any] | None:
    for field in MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA:
        if field["id"] == field_id:
            return field
    return None


def load_schema_metadata() -> dict[str, Any]:
    return {
        "version": WORLD_BUILDER_SCHEMA_VERSION,
        "map_gen_settings_count": len(MAP_GEN_SETTINGS_SCHEMA),
        "map_settings_count": len(MAP_SETTINGS_SCHEMA),
        "categories": CATEGORIES,
        "fields": MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA,
    }


def validate_schema_integrity() -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    valid_categories = set(CATEGORIES)

    for field in MAP_GEN_SETTINGS_SCHEMA + MAP_SETTINGS_SCHEMA:
        if field["id"] in seen_ids:
            errors.append(f"duplicate field id: {field['id']}")
        seen_ids.add(field["id"])

        if field["category"] not in valid_categories:
            errors.append(f"invalid category '{field['category']}' for field {field['id']}")

        if not field.get("source_file"):
            errors.append(f"missing source_file for field {field['id']}")

    return errors


if __name__ == "__main__":
    metadata = load_schema_metadata()
    print(f"Schema version: {metadata['version']}")
    print(f"Map-gen settings fields: {metadata['map_gen_settings_count']}")
    print(f"Map settings fields: {metadata['map_settings_count']}")
    print(f"Categories: {metadata['categories']}")
    print(f"Total fields: {len(metadata['fields'])}")
    print(f"Integrity errors: {validate_schema_integrity()}")
