from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from backend.config import BASE_DIR, INSTALL_DIR, LOG_DIR, PID_PATH, SAVE_DIR


def get_process_metrics(pid: Optional[int] = None) -> dict:
    metrics: dict = {
        "cpu_percent": 0.0,
        "ram_mb": 0,
        "uptime_seconds": 0,
        "disk_usage_mb": 0,
    }

    if pid is None:
        pid = _read_pid()

    if pid is None or not _is_process_running(pid):
        return metrics

    stat_path = Path(f"/proc/{pid}/stat")
    status_path = Path(f"/proc/{pid}/status")

    if stat_path.exists():
        try:
            raw = stat_path.read_text(encoding="utf-8").split()
            utime = int(raw[13])
            stime = int(raw[14])
            starttime = int(raw[21])
            clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

            with open("/proc/uptime", encoding="utf-8") as f:
                system_uptime = float(f.read().split()[0])

            process_start = system_uptime - (starttime / clk_tck)
            metrics["uptime_seconds"] = max(0, int(system_uptime - process_start))

            try:
                with open(f"/proc/{pid}/stat", encoding="utf-8") as f1:
                    t1 = f1.read().split()
                utime1 = int(t1[13])
                stime1 = int(t1[14])
                time.sleep(0.1)
                with open(f"/proc/{pid}/stat", encoding="utf-8") as f2:
                    t2 = f2.read().split()
                utime2 = int(t2[13])
                stime2 = int(t2[14])
                total_time = (utime2 + stime2) - (utime1 + stime1)
                total_time_seconds = total_time / clk_tck
                interval = 0.1
                cpu_cores = os.cpu_count() or 1
                metrics["cpu_percent"] = round((total_time_seconds / interval) * 100.0 / cpu_cores, 1)
            except Exception:
                pass
        except Exception:
            pass

    if status_path.exists():
        try:
            with status_path.open(encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            metrics["ram_mb"] = round(int(parts[1]) / 1024, 1)
                        break
        except Exception:
            pass

    try:
        usage = shutil.disk_usage(str(BASE_DIR))
        metrics["disk_usage_mb"] = round(usage.used / (1024 * 1024), 1)
    except Exception:
        pass

    return metrics


def get_factorio_version() -> str:
    version_file = INSTALL_DIR / "data" / "base" / "info.json"
    if version_file.exists():
        try:
            import json
            data = json.loads(version_file.read_text(encoding="utf-8"))
            return data.get("version", "unknown")
        except Exception:
            pass

    changelog = INSTALL_DIR / "data" / "base" / "changelog.txt"
    if changelog.exists():
        try:
            first_line = changelog.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            match = re.search(r"(\d+\.\d+\.\d+)", first_line)
            if match:
                return match.group(1)
        except Exception:
            pass

    return "unknown"


def get_active_save() -> str:
    if not SAVE_DIR.exists():
        return "none"
    saves = sorted(SAVE_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return saves[0].name if saves else "none"


def _read_pid() -> Optional[int]:
    if not PID_PATH.exists():
        return None
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
