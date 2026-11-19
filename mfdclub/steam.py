"""Steam accounts remembered on this device (config/loginusers.vdf)."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from . import vdf
from . import paths
from .config import Config


@dataclass
class SteamAccount:
    steamid: str
    account_name: str
    persona_name: str
    most_recent: bool
    remember_password: bool
    timestamp: int
    club: bool = False


def candidate_roots() -> list[Path]:
    if os.environ.get("MFDCLUB_STEAM_DIR"):
        return [Path(os.environ["MFDCLUB_STEAM_DIR"])]
    h = paths.home()
    return [
        h / ".local/share/Steam",
        h / ".steam/steam",
        h / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]


def find_loginusers() -> Path | None:
    for root in candidate_roots():
        p = root / "config" / "loginusers.vdf"
        if p.is_file():
            return p
    return None


def _load(path: Path) -> dict:
    return vdf.loads(path.read_text(encoding="utf-8", errors="replace")).get("users", {})


def list_accounts(cfg: Config, path: Path | None = None) -> list[SteamAccount]:
    path = path or find_loginusers()
    if not path:
        return []
    out = []
    for sid, u in _load(path).items():
        name = u.get("AccountName", "")
        out.append(SteamAccount(
            sid, name, u.get("PersonaName", ""),
            u.get("MostRecent", u.get("mostrecent", "0")) == "1",
            u.get("RememberPassword", "0") == "1",
            int(u.get("Timestamp", "0") or 0),
            cfg.is_club_steam(sid, name),
        ))
    return sorted(out, key=lambda a: -a.timestamp)


def steam_running() -> bool:
    for name in ("steam", "steamwebhelper"):
        if subprocess.run(["pgrep", "-u", str(os.geteuid()), "-x", name], capture_output=True).returncode == 0:
            return True
    return False


def logout_non_club(cfg: Config, dry_run: bool, path: Path | None = None) -> list[SteamAccount]:
    """Forget all non-club accounts. Returns the accounts that were (or would be) removed.

    The caller must make sure Steam is closed: Steam rewrites the file on exit.
    """
    path = path or find_loginusers()
    if not path:
        return []
    accounts = list_accounts(cfg, path)
    doomed = [a for a in accounts if not a.club]
    if dry_run or not doomed:
        return doomed
    shutil.copy2(path, path.with_name(f"loginusers.vdf.bak-{int(time.time())}"))
    users = _load(path)
    for a in doomed:
        users.pop(a.steamid, None)
    club = [a for a in accounts if a.club]
    for sid, u in users.items():
        u["MostRecent"] = "0"
    if club:
        users[club[0].steamid]["MostRecent"] = "1"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(vdf.dumps({"users": users}), encoding="utf-8")
    tmp.replace(path)
    return doomed
