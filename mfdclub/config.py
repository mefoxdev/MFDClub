"""Club configuration: which accounts belong to the club."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from . import paths
from pathlib import Path


def config_dir() -> Path:
    return Path(os.environ.get("MFDCLUB_CONFIG_DIR") or paths.home() / ".config" / "mfdclub")


def data_dir() -> Path:
    return Path(os.environ.get("MFDCLUB_DATA_DIR") or paths.home() / ".local" / "share" / "mfdclub")


def system_config_path() -> Path:
    return Path(os.environ.get("MFDCLUB_SYSTEM_CONFIG") or "/etc/mfdclub/config.json")


@dataclass
class Config:
    # SteamID64 or account login name (case-insensitive) of club Steam accounts.
    steam_club: list[str] = field(default_factory=list)
    # Name of the Sober profile that holds the club's Roblox session.
    sober_club_profile: str | None = None

    @staticmethod
    def path() -> Path:
        """System-wide config (admin-managed) wins over the per-user one."""
        sys_path = system_config_path()
        return sys_path if sys_path.is_file() else config_dir() / "config.json"

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        try:
            raw = json.loads((path or cls.path()).read_text())
        except FileNotFoundError:
            return cls()
        return cls(list(raw.get("steam_club", [])), raw.get("sober_club_profile"))

    def save(self, path: Path | None = None) -> None:
        p = path or self.path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(
            {"steam_club": self.steam_club, "sober_club_profile": self.sober_club_profile},
            indent=2) + "\n")

    def is_club_steam(self, steamid: str, account_name: str) -> bool:
        keys = {k.lower() for k in self.steam_club}
        return steamid.lower() in keys or account_name.lower() in keys
