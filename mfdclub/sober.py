"""Sober (Roblox on Linux) profiles.

Sober keeps everything in ~/.var/app/org.vinegarhq.Sober and has no built-in
multi-account support. We emulate "separate spaces" by keeping one directory per
profile and swapping the active one into place while Sober is closed. Each
profile keeps its own session, so switching never logs anybody out.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from . import paths
from .config import Config, data_dir

APP_ID = "org.vinegarhq.Sober"


class SoberError(RuntimeError):
    pass


def live_dir() -> Path:
    return Path(os.environ.get("MFDCLUB_SOBER_DIR") or paths.home() / ".var" / "app" / APP_ID)


def profiles_dir() -> Path:
    return data_dir() / "sober-profiles"


def _state_path() -> Path:
    return data_dir() / "sober-state.json"


def active_profile() -> str | None:
    try:
        return json.loads(_state_path().read_text()).get("active")
    except FileNotFoundError:
        return None


def _set_active(name: str | None) -> None:
    _state_path().parent.mkdir(parents=True, exist_ok=True)
    _state_path().write_text(json.dumps({"active": name}))


def _check_name(name: str) -> None:
    if not name or "/" in name or name.startswith(".") or name != name.strip():
        raise SoberError(f"invalid profile name: {name!r}")


def running() -> bool:
    if shutil.which("flatpak") is None:
        return False
    r = subprocess.run(["flatpak", "ps", "--columns=application"], capture_output=True, text=True)
    return APP_ID in r.stdout


def _has_data(p: Path) -> bool:
    return p.is_dir() and any(p.iterdir())


def profile_names() -> list[str]:
    d = profiles_dir()
    names = {p.name for p in d.iterdir() if p.is_dir()} if d.is_dir() else set()
    if (a := active_profile()):
        names.add(a)
    return sorted(names)


def profile_path(name: str) -> Path:
    return live_dir() if name == active_profile() else profiles_dir() / name


def has_session_data(name: str) -> bool:
    return _has_data(profile_path(name))


def init(name: str) -> None:
    """Declare the current Sober directory to be profile `name`."""
    _check_name(name)
    if active_profile():
        raise SoberError(f"already initialised (active profile: {active_profile()})")
    if (profiles_dir() / name).exists():
        raise SoberError(f"profile {name!r} already exists")
    _set_active(name)


def new(name: str) -> None:
    _check_name(name)
    if name in profile_names():
        raise SoberError(f"profile {name!r} already exists")
    (profiles_dir() / name).mkdir(parents=True)


def use(name: str) -> None:
    """Make `name` the live profile. Sober must not be running."""
    _check_name(name)
    cur = active_profile()
    if name == cur:
        return
    if cur is None:
        raise SoberError("run `mfdclub sober init <name>` first to name your current Sober data")
    if name not in profile_names():
        raise SoberError(f"no such profile: {name!r} (create it with `sober new`)")
    if running():
        raise SoberError("Sober is running; close it first")
    stash = profiles_dir() / cur
    stash.parent.mkdir(parents=True, exist_ok=True)
    if stash.exists():
        raise SoberError(f"{stash} already exists; refusing to overwrite")
    if live_dir().exists():
        shutil.move(str(live_dir()), str(stash))
    else:
        stash.mkdir()
    live_dir().parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(profiles_dir() / name), str(live_dir()))
    _set_active(name)


def run(name: str | None = None) -> int:
    if name:
        use(name)
    return subprocess.call(["flatpak", "run", APP_ID])


def reset_non_club(cfg: Config, dry_run: bool) -> list[str]:
    """Wipe every non-club profile's data (this drops its Roblox session)."""
    doomed = [n for n in profile_names() if n != cfg.sober_club_profile and has_session_data(n)]
    if dry_run or not doomed:
        return doomed
    if running() and active_profile() in doomed:
        raise SoberError("Sober is running with a non-club profile; close it first")
    for n in doomed:
        p = profile_path(n)
        shutil.rmtree(p)
        if n != active_profile():
            p.mkdir()
    return doomed
