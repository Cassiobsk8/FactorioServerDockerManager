from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WorldConfig:
    world_name: str
    seed: Optional[str] = None
    random_seed: bool = True
    planet: str = "nauvis"
    settings: dict[str, Any] = field(default_factory=dict)
    map_settings: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors = []
        if not self.world_name or not self.world_name.strip():
            errors.append("world_name is required")
        if self.planet not in ("nauvis", "vulcanus", "fulgora", "gleba", "aquilo"):
            errors.append(f"unsupported planet: {self.planet}")
        return errors
