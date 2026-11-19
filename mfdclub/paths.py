"""Which user's files we look at (defaults to the current user)."""
from __future__ import annotations

import pwd
from pathlib import Path

_override: Path | None = None


def home() -> Path:
    return _override or Path.home()


def set_home(path: Path | None) -> None:
    global _override
    _override = path


def home_of(name: str) -> Path:
    try:
        return Path(pwd.getpwnam(name).pw_dir)
    except KeyError:
        raise LookupError(f"no such user: {name}") from None


def local_users() -> list[str]:
    """Regular login users (uid 1000-59999, real shell)."""
    return sorted(p.pw_name for p in pwd.getpwall()
                  if 1000 <= p.pw_uid < 60000 and not p.pw_shell.endswith(("nologin", "false")))
