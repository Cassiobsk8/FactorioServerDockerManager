from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.config import BASE_DIR, INSTALL_DIR, SAVE_DIR
from backend.services.factorio_service import is_server_installed
from backend.services.world_config import WorldConfig
from backend.services.world_builder_schema import get_field_by_id

logger = logging.getLogger("fsm.world_builder")

WORLD_BUILDER_DIR = BASE_DIR / "data" / "world-builder"
PREVIEWS_DIR = WORLD_BUILDER_DIR / "previews"

DEFAULT_PLANETS = ["nauvis", "vulcanus", "fulgora", "gleba", "aquilo"]

_MAP_GEN_SETTINGS_DEFAULTS_PATH = INSTALL_DIR / "data" / "map-gen-settings.example.json"
_MAP_SETTINGS_DEFAULTS_PATH = INSTALL_DIR / "data" / "map-settings.example.json"


def _load_official_defaults(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to load official defaults from %s: %s", path, exc)
        return {}


_factorio_paths_logged = False


def _log_factorio_paths() -> None:
    global _factorio_paths_logged
    if _factorio_paths_logged:
        return
    _factorio_paths_logged = True

    factorio_bin = INSTALL_DIR / "bin" / "x64" / "factorio"
    data_dir = INSTALL_DIR / "data"

    logger.info("Factorio executable: %s", factorio_bin)
    logger.info("Factorio installation: %s", INSTALL_DIR)
    logger.info("Factorio data directory: %s", data_dir)

    if not is_server_installed():
        logger.info("Factorio installation not found.")
        logger.info("Official defaults not loaded.")
        return

    logger.info("Factorio installation found.")
    logger.info("Loading official defaults...")
    logger.info("Loading official defaults: %s", _MAP_GEN_SETTINGS_DEFAULTS_PATH)
    logger.info("Loading official defaults: %s", _MAP_SETTINGS_DEFAULTS_PATH)


def _get_map_gen_settings_defaults() -> dict[str, Any]:
    _log_factorio_paths()
    if not is_server_installed():
        return {}
    defaults = _load_official_defaults(_MAP_GEN_SETTINGS_DEFAULTS_PATH)
    if defaults:
        logger.info("map-gen-settings.example.json loaded.")
    else:
        logger.error("Factorio installation detected, but official example files could not be found.")
    return defaults


def _get_map_settings_defaults() -> dict[str, Any]:
    _log_factorio_paths()
    if not is_server_installed():
        return {}
    defaults = _load_official_defaults(_MAP_SETTINGS_DEFAULTS_PATH)
    if defaults:
        logger.info("map-settings.example.json loaded.")
    else:
        logger.error("Factorio installation detected, but official example files could not be found.")
    return defaults


_MAP_SETTINGS_FALLBACK: dict[str, Any] = {
    "difficulty_settings": {
        "technology_price_multiplier": 1,
        "spoil_time_modifier": 1,
    },
    "pollution": {
        "enabled": True,
        "diffusion_ratio": 0.02,
        "min_to_diffuse": 15,
        "ageing": 1,
        "expected_max_per_chunk": 150,
        "min_to_show_per_chunk": 50,
        "min_pollution_to_damage_trees": 60,
        "pollution_with_max_forest_damage": 150,
        "pollution_per_tree_damage": 50,
        "pollution_restored_per_tree_damage": 10,
        "max_pollution_to_restore_trees": 20,
        "enemy_attack_pollution_consumption_modifier": 1,
    },
    "enemy_evolution": {
        "enabled": True,
        "time_factor": 0.000004,
        "destroy_factor": 0.002,
        "pollution_factor": 0.0000009,
    },
    "enemy_expansion": {
        "enabled": True,
        "max_expansion_distance": 7,
        "friendly_base_influence_radius": 2,
        "enemy_building_influence_radius": 2,
        "building_coefficient": 0.1,
        "other_base_coefficient": 2.0,
        "neighbouring_chunk_coefficient": 0.5,
        "neighbouring_base_chunk_coefficient": 0.4,
        "max_colliding_tiles_coefficient": 0.9,
        "settler_group_min_size": 5,
        "settler_group_max_size": 20,
        "min_expansion_cooldown": 14400,
        "max_expansion_cooldown": 216000,
    },
    "unit_group": {
        "min_group_gathering_time": 3600,
        "max_group_gathering_time": 36000,
        "max_wait_time_for_late_members": 7200,
        "max_group_radius": 30.0,
        "min_group_radius": 5.0,
        "max_member_speedup_when_behind": 1.4,
        "max_member_slowdown_when_ahead": 0.6,
        "max_group_slowdown_factor": 0.3,
        "max_group_member_fallback_factor": 3,
        "member_disown_distance": 10,
        "tick_tolerance_when_member_arrives": 60,
        "max_gathering_unit_groups": 30,
        "max_unit_group_size": 200,
    },
    "steering": {
        "default": {
            "radius": 1.2,
            "separation_force": 0.005,
            "separation_factor": 1.2,
            "force_unit_fuzzy_goto_behavior": False,
        },
        "moving": {
            "radius": 3,
            "separation_force": 0.01,
            "separation_factor": 3,
            "force_unit_fuzzy_goto_behavior": False,
        },
    },
    "path_finder": {
        "fwd2bwd_ratio": 5,
        "goal_pressure_ratio": 2,
        "max_steps_worked_per_tick": 1000,
        "max_work_done_per_tick": 8000,
        "use_path_cache": True,
        "short_cache_size": 5,
        "long_cache_size": 25,
        "short_cache_min_cacheable_distance": 10,
        "short_cache_min_algo_steps_to_cache": 50,
        "long_cache_min_cacheable_distance": 30,
        "cache_max_connect_to_cache_steps_multiplier": 100,
        "cache_accept_path_start_distance_ratio": 0.2,
        "cache_accept_path_end_distance_ratio": 0.15,
        "negative_cache_accept_path_start_distance_ratio": 0.3,
        "negative_cache_accept_path_end_distance_ratio": 0.3,
        "cache_path_start_distance_rating_multiplier": 10,
        "cache_path_end_distance_rating_multiplier": 20,
        "stale_enemy_with_same_destination_collision_penalty": 30,
        "ignore_moving_enemy_collision_distance": 5,
        "enemy_with_different_destination_collision_penalty": 30,
        "general_entity_collision_penalty": 10,
        "general_entity_subsequent_collision_penalty": 3,
        "extended_collision_penalty": 3,
        "max_clients_to_accept_any_new_request": 10,
        "max_clients_to_accept_short_new_request": 100,
        "direct_distance_to_consider_short_request": 100,
        "short_request_max_steps": 1000,
        "short_request_ratio": 0.5,
        "min_steps_to_check_path_find_termination": 2000,
        "start_to_goal_cost_multiplier_to_terminate_path_find": 2000.0,
        "overload_levels": [0, 100, 500],
        "overload_multipliers": [2, 3, 4],
        "negative_path_cache_delay_interval": 20,
    },
    "asteroids": {
        "spawning_rate": 1,
        "max_ray_portals_expanded_per_tick": 100,
    },
    "max_failed_behavior_count": 3,
}

PLANET_AUTOPLACE_CONTROLS: dict[str, list[str]] = {
    "nauvis": [
        "coal",
        "stone",
        "iron-ore",
        "copper-ore",
        "uranium-ore",
        "crude-oil",
        "water",
        "trees",
        "rocks",
        "enemy-base",
        "starting_area_moisture",
        "nauvis_cliff",
    ],
    "vulcanus": [
        "vulcanus_coal",
        "calcite",
        "sulfuric_acid_geyser",
        "tungsten_ore",
        "vulcanus_volcanism",
    ],
    "gleba": [
        "gleba_water",
        "gleba_plants",
        "gleba_stone",
        "gleba_enemy_base",
        "gleba_cliff",
    ],
    "fulgora": [
        "scrap",
        "fulgora_islands",
        "fulgora_cliff",
    ],
    "aquilo": [
        "aquilo_crude_oil",
    "fluorine_vent",
    "lithium_brine",
    ],
}


def _prepare_preview_config(config: WorldConfig) -> WorldConfig:
    allowed_controls = set(PLANET_AUTOPLACE_CONTROLS.get(config.planet or "nauvis", []))
    if not allowed_controls or not isinstance(config.settings, dict):
        return config

    filtered_settings = deepcopy(config.settings)
    if isinstance(filtered_settings.get("autoplace_controls"), dict):
        filtered_settings["autoplace_controls"] = {
            key: value
            for key, value in filtered_settings["autoplace_controls"].items()
            if key in allowed_controls
        }

    from dataclasses import replace
    return replace(config, settings=filtered_settings)


def _get_factorio_bin() -> Optional[Path]:
    factorio_bin = INSTALL_DIR / "bin" / "x64" / "factorio"
    if not factorio_bin.exists():
        return None
    return factorio_bin


def validate_factorio_binary() -> dict[str, Any]:
    factorio_bin = _get_factorio_bin()
    if factorio_bin is None:
        return {
            "valid": False,
            "reason": "not_installed",
            "message": "World Builder preview unavailable. Factorio installation is not complete.",
        }

    try:
        with open(factorio_bin, "rb") as f:
            magic = f.read(4)
    except OSError as exc:
        return {
            "valid": False,
            "reason": "placeholder",
            "message": f"Factorio binary not readable: {exc}",
        }

    if magic != b"\x7fELF":
        return {
            "valid": False,
            "reason": "placeholder",
            "message": "World Builder Preview indisponível. Instalação do Factorio não concluída.",
        }

    return {"valid": True, "reason": "ok"}


def _ensure_dirs() -> None:
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)


def _compute_config_hash(config: WorldConfig) -> str:
    payload = json.dumps(
        {
            "world_name": config.world_name,
            "seed": config.seed,
            "random_seed": config.random_seed,
            "planet": config.planet,
            "settings": config.settings,
            "map_settings": config.map_settings,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _write_map_gen_settings(config: WorldConfig, directory: Path) -> Optional[Path]:
    official_defaults = deepcopy(_get_map_gen_settings_defaults())

    user_settings = deepcopy(config.settings) if config.settings else {}
    merged = official_defaults

    if isinstance(user_settings.get("autoplace_controls"), dict) and isinstance(merged.get("autoplace_controls"), dict):
        for control_id, values in user_settings["autoplace_controls"].items():
            if control_id in merged["autoplace_controls"] and isinstance(values, dict):
                merged["autoplace_controls"][control_id].update(values)
            else:
                merged["autoplace_controls"][control_id] = values
        del user_settings["autoplace_controls"]

    for key, value in user_settings.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value

    if isinstance(merged.get("autoplace_controls"), dict):
        autoplace_controls = merged["autoplace_controls"]
        official_autoplace = official_defaults.get("autoplace_controls", {})
        for control_id, values in autoplace_controls.items():
            if not isinstance(values, dict):
                continue
            defaults = official_autoplace.get(control_id)
            if isinstance(defaults, dict):
                merged_values = {**defaults, **{k: v for k, v in values.items() if v is not None}}
                autoplace_controls[control_id] = merged_values
            else:
                merged_values = {**values}
                autoplace_controls[control_id] = merged_values
        for control_id, values in autoplace_controls.items():
            if not isinstance(values, dict):
                autoplace_controls[control_id] = {"frequency": 1, "size": 1, "richness": 1}
                continue
            for key in ("frequency", "size", "richness"):
                if key not in values:
                    values[key] = 1

    if config.seed and not config.random_seed:
        merged["seed"] = int(config.seed)

    path = directory / "map-gen-settings.json"
    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return path


def _write_map_settings(config: WorldConfig, directory: Path) -> Optional[Path]:
    official_defaults = deepcopy(_get_map_settings_defaults())
    if not official_defaults:
        official_defaults = deepcopy(_MAP_SETTINGS_FALLBACK)

    user_settings = deepcopy(config.map_settings) if config.map_settings else {}
    merged = _deep_merge(official_defaults, user_settings)

    path = directory / "map-settings.json"
    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return path


def list_planets() -> list[str]:
    return list(DEFAULT_PLANETS)


def _run_factorio(cmd: list[str], tmpdir: Path) -> dict[str, Any]:
    start = time.time()
    cliff_continuity = None
    map_settings_path = tmpdir / "map-settings.json"
    if map_settings_path.exists():
        try:
            with map_settings_path.open(encoding="utf-8") as handle:
                map_settings_data = json.load(handle)
            cliff_value = (((map_settings_data.get("cliff_settings") or {}).get("richness")))
            if cliff_value is not None:
                cliff_continuity = str(cliff_value)
        except (OSError, json.JSONDecodeError):
            pass

    result = subprocess.run(
        cmd,
        cwd=str(tmpdir),
        capture_output=True,
        text=True,
        timeout=300,
    )
    elapsed = time.time() - start
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    return_code = getattr(result, "returncode", 0)

    if cliff_continuity is not None:
        print(f"CLIFF_CONTINUITY={cliff_continuity}", flush=True)

    return {
        "command": cmd,
        "stdout": stdout,
        "stderr": stderr,
        "return_code": return_code,
        "elapsed_seconds": round(elapsed, 3),
    }


def _cleanup_tempdir(tmpdir: Path) -> None:
    try:
        if tmpdir.exists():
            shutil.rmtree(tmpdir)
    except OSError as exc:
        logger.warning("Failed to cleanup temp directory %s: %s", tmpdir, exc)


def _read_input_files(tmpdir: Path, cmd: list[str]) -> str:
    input_files = []

    known_files = [
        "map-gen-settings.json",
        "map-settings.json",
    ]

    additional_files = set()
    for arg in cmd:
        if arg.startswith("--") and "=" in arg:
            value = arg.split("=", 1)[1]
            if not Path(value).is_absolute() and (tmpdir / value).exists():
                additional_files.add(value)

    all_files = sorted(set(known_files) | additional_files)

    sections = []
    for filename in all_files:
        filepath = tmpdir / filename
        if filepath.exists() and filepath.is_file():
            sections.append(f"===== {filename} =====")
            try:
                sections.append(filepath.read_text(encoding="utf-8"))
            except OSError:
                sections.append(f"<falha ao ler {filename}>")
        else:
            sections.append(f"===== {filename} =====")
            sections.append(f"<arquivo inexistente>")

    if not sections:
        return ""

    separator = "=" * 50
    return (
        f"{separator}\nARQUIVOS UTILIZADOS NA GERAÇÃO\n{separator}\n\n"
        + "\n\n".join(sections)
        + f"\n{separator}\n"
    )


def clear_preview_cache() -> dict[str, Any]:
    if not PREVIEWS_DIR.exists():
        return {"status": "cleared", "previews_dir": str(PREVIEWS_DIR), "removed": 0}

    removed = 0
    for path in PREVIEWS_DIR.iterdir():
        try:
            if path.is_file():
                path.unlink()
                removed += 1
            elif path.is_dir():
                shutil.rmtree(path)
                removed += 1
        except OSError as exc:
            logger.warning("Failed to remove preview cache entry %s: %s", path, exc)

    logger.info("Preview cache cleared. removed=%s dir=%s", removed, PREVIEWS_DIR)
    return {"status": "cleared", "previews_dir": str(PREVIEWS_DIR), "removed": removed}


def _move_generated_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    if not destination.exists():
        raise RuntimeError(f"File move failed: {source} -> {destination}")


def generate_preview(config: WorldConfig) -> dict[str, Any]:
    _ensure_dirs()

    validation = validate_factorio_binary()
    if not validation.get("valid"):
        raise RuntimeError(validation.get("message", "Invalid Factorio installation."))

    factorio_bin = _get_factorio_bin()
    config_hash = _compute_config_hash(config)
    preview_path = PREVIEWS_DIR / f"{config_hash}.png"

    if preview_path.exists():
        return {
            "preview_url": f"/api/world-builder/preview-image/{config_hash}.png",
            "preview_hash": config_hash,
            "status": "ready",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    tmpdir = Path(tempfile.mkdtemp(prefix="world-builder-"))
    map_gen_settings_path = None
    map_settings_path = None

    def _list_directory(path: Path) -> list[str]:
        if not path.exists():
            return ["<diretório não existe>"]
        return sorted(p.name for p in path.iterdir())

    def _png_files(path: Path) -> list[str]:
        return sorted(p.name for p in path.glob("*.png")) if path.exists() else []

    try:
        preview_config = _prepare_preview_config(config)
        map_gen_settings_path = _write_map_gen_settings(preview_config, tmpdir)
        map_settings_path = _write_map_settings(config, tmpdir)

        cmd = [str(factorio_bin), "--generate-map-preview", "preview.png"]
        if map_gen_settings_path:
            cmd.append(f"--map-gen-settings={map_gen_settings_path.name}")
        if map_settings_path:
            cmd.append(f"--map-settings={map_settings_path.name}")
        if config.seed and not config.random_seed:
            cmd.append(f"--map-gen-seed={config.seed}")
        cmd.extend(["--map-preview-size", "2048"])
        if config.planet:
            cmd.append(f"--map-preview-planet={config.planet}")

        exec_info = _run_factorio(cmd, tmpdir)
        logger.info(
            "Preview generation completed. Command: %s | Return code: %s | Time: %ss",
            " ".join(exec_info["command"]),
            exec_info["return_code"],
            exec_info["elapsed_seconds"],
        )
        if exec_info["stdout"]:
            logger.debug("Preview stdout: %s", exec_info["stdout"])
        if exec_info["stderr"]:
            logger.debug("Preview stderr: %s", exec_info["stderr"])

        generated = tmpdir / "preview.png"
        if exec_info["return_code"] != 0:
            files = _list_directory(tmpdir)
            pngs = _png_files(tmpdir)
            details = (
                f"Comando: {' '.join(exec_info['command'])}\n"
                f"cwd: {tmpdir}\n"
                f"stdout: {exec_info['stdout']}\n"
                f"stderr: {exec_info['stderr']}\n"
                f"return code: {exec_info['return_code']}\n"
                f"tempo: {exec_info['elapsed_seconds']}s\n"
                f"preview.png existe: {generated.exists()}\n"
                f"PNGs encontrados: {pngs if pngs else 'nenhum'}\n"
                f"arquivos no diretório temporário:\n"
                + "\n".join(f"  {f}" for f in files)
            )
            logger.error("Factorio failed to generate preview. Details:\n%s", details)
            raise RuntimeError(
                "Factorio falhou ao gerar preview.\n" + details + _read_input_files(tmpdir, exec_info["command"])
            )

        if not generated.exists():
            files = _list_directory(tmpdir)
            pngs = _png_files(tmpdir)
            details = (
                f"Comando: {' '.join(exec_info['command'])}\n"
                f"cwd: {tmpdir}\n"
                f"stdout: {exec_info['stdout']}\n"
                f"stderr: {exec_info['stderr']}\n"
                f"return code: {exec_info['return_code']}\n"
                f"tempo: {exec_info['elapsed_seconds']}s\n"
                f"preview.png existe: False\n"
                f"PNGs encontrados: {pngs if pngs else 'nenhum'}\n"
                f"arquivos no diretório temporário:\n"
                + "\n".join(f"  {f}" for f in files)
            )
            logger.error("Preview generation failed. Details:\n%s", details)
            raise RuntimeError(
                "Factorio executou com sucesso mas não gerou preview.png.\n"
                + details
                + _read_input_files(tmpdir, exec_info["command"])
            )

        _move_generated_file(generated, preview_path)

        logger.info(
            "DIAGNOSTIC preview generated: path=%s exists=%s size=%s hash=%s",
            preview_path,
            preview_path.exists(),
            preview_path.stat().st_size if preview_path.exists() else None,
            config_hash,
        )
    except subprocess.CalledProcessError as exc:
        files = _list_directory(tmpdir)
        pngs = _png_files(tmpdir)
        logger.error(
            "Failed to generate preview. Command: %s | Return code: %s | Stderr: %s | Files: %s | PNGs: %s",
            " ".join(exc.cmd) if exc.cmd else "unknown",
            exc.returncode,
            exc.stderr,
            files,
            pngs,
        )
        raise RuntimeError(
            "Failed to generate preview.\n"
            f"Comando: {' '.join(exc.cmd) if exc.cmd else 'unknown'}\n"
            f"cwd: {tmpdir}\n"
            f"stdout: {getattr(exc, 'stdout', '')}\n"
            f"stderr: {exc.stderr}\n"
            f"return code: {exc.returncode}\n"
            f"arquivos no diretório temporário:\n"
            + "\n".join(f"  {f}" for f in files)
            + _read_input_files(tmpdir, exc.cmd if exc.cmd else [])
        ) from exc
    except subprocess.TimeoutExpired as exc:
        files = _list_directory(tmpdir)
        pngs = _png_files(tmpdir)
        logger.error(
            "Preview generation timed out after 300s. Files: %s | PNGs: %s",
            files,
            pngs,
        )
        raise RuntimeError(
            "Preview generation timed out.\n"
            f"cwd: {tmpdir}\n"
            f"arquivos no diretório temporário:\n"
            + "\n".join(f"  {f}" for f in files)
            + _read_input_files(tmpdir, exc.cmd if exc.cmd else [])
        )
    except Exception as exc:
        logger.error("Unexpected error during preview generation: %s", exc, exc_info=True)
        raise
    finally:
        _cleanup_tempdir(tmpdir)

    return {
        "preview_url": f"/api/world-builder/preview-image/{config_hash}.png",
        "preview_hash": config_hash,
        "status": "ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def create_world(config: WorldConfig, preview_hash: str) -> dict[str, Any]:
    validation = validate_factorio_binary()
    if not validation.get("valid"):
        raise RuntimeError(validation.get("message", "Invalid Factorio installation."))

    factorio_bin = _get_factorio_bin()
    config_hash = _compute_config_hash(config)

    if preview_hash != config_hash:
        raise ValueError("Preview hash does not match current configuration. Update preview first.")

    if not config.world_name.endswith(".zip"):
        save_name = f"{config.world_name}.zip"
    else:
        save_name = config.world_name

    target = SAVE_DIR / save_name
    if target.exists():
        raise FileExistsError(f"Save already exists: {save_name}")

    tmpdir = Path(tempfile.mkdtemp(prefix="world-builder-"))
    map_gen_settings_path = None
    map_settings_path = None
    temp_save = tmpdir / save_name

    try:
        map_gen_settings_path = _write_map_gen_settings(config, tmpdir)
        map_settings_path = _write_map_settings(config, tmpdir)

        cmd = [str(factorio_bin), f"--create={temp_save}"]
        if map_gen_settings_path:
            cmd.append(f"--map-gen-settings={map_gen_settings_path.name}")
        if map_settings_path:
            cmd.append(f"--map-settings={map_settings_path.name}")
        if config.seed and not config.random_seed:
            cmd.append(f"--map-gen-seed={config.seed}")

        exec_info = _run_factorio(cmd, tmpdir)
        logger.info(
            "World creation completed. Command: %s | Return code: %s | Time: %ss",
            " ".join(exec_info["command"]),
            exec_info["return_code"],
            exec_info["elapsed_seconds"],
        )
        if exec_info["stdout"]:
            logger.debug("World creation stdout: %s", exec_info["stdout"])
        if exec_info["stderr"]:
            logger.debug("World creation stderr: %s", exec_info["stderr"])

        if not temp_save.exists():
            raise RuntimeError("Factorio did not create the save file")

        _move_generated_file(temp_save, target)
    except subprocess.CalledProcessError as exc:
        logger.error(
            "Failed to create world. Command: %s | Return code: %s | Stderr: %s",
            " ".join(exc.cmd) if exc.cmd else "unknown",
            exc.returncode,
            exc.stderr,
        )
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass
        raise RuntimeError("Failed to create world. Check server logs for details.") from exc
    except subprocess.TimeoutExpired:
        logger.error("World creation timed out after 300s")
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass
        raise RuntimeError("World creation timed out.")
    except Exception as exc:
        logger.error("Unexpected error during world creation: %s", exc, exc_info=True)
        raise
    finally:
        _cleanup_tempdir(tmpdir)

    logger.info("Created new world save: %s", save_name)
    return {
        "save_file": save_name,
        "save_path": str(target),
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }



