from __future__ import annotations

import argparse
import sys

from . import __version__, sober, steam
from .config import Config


def _print_steam(cfg: Config) -> None:
    print("Steam")
    accs = steam.list_accounts(cfg)
    if not accs:
        print("  (no accounts found)")
    for a in accs:
        tags = [t for t, on in (("club", a.club), ("last used", a.most_recent),
                                ("remembered", a.remember_password)) if on]
        print(f"  {a.account_name:<20} {a.persona_name:<20} {a.steamid}  [{', '.join(tags)}]")


def _print_sober(cfg: Config) -> None:
    print("Roblox (Sober)")
    names = sober.profile_names()
    if not names:
        print("  (no profiles; run `mfdclub sober init <name>` to name your current Sober data)")
    for n in names:
        tags = [t for t, on in (("club", n == cfg.sober_club_profile),
                                ("active", n == sober.active_profile()),
                                ("has session data", sober.has_session_data(n))) if on]
        print(f"  {n:<20} [{', '.join(tags)}]")


def cmd_list(args, cfg):
    _print_steam(cfg)
    _print_sober(cfg)


def cmd_logout(args, cfg):
    dry = not args.yes
    if not cfg.steam_club and not cfg.sober_club_profile:
        print("No club accounts configured; refusing to log everyone out. See `mfdclub club`.")
        return 2
    if not dry and steam.steam_running():
        print("Steam is running; close it first (it rewrites its login list on exit).")
        return 2
    removed = steam.logout_non_club(cfg, dry)
    wiped = sober.reset_non_club(cfg, dry)
    verb = "Would log out" if dry else "Logged out"
    for a in removed:
        print(f"{verb} Steam: {a.account_name} ({a.steamid})")
    for n in wiped:
        print(f"{verb} Sober profile (data wiped): {n}")
    if not removed and not wiped:
        print("Nothing to log out.")
    if dry and (removed or wiped):
        print("Dry run. Re-run with --yes to apply.")


def cmd_club(args, cfg):
    if args.action == "add-steam":
        if args.value not in cfg.steam_club:
            cfg.steam_club.append(args.value)
    elif args.action == "rm-steam":
        cfg.steam_club = [x for x in cfg.steam_club if x.lower() != args.value.lower()]
    elif args.action == "set-sober":
        cfg.sober_club_profile = args.value
    try:
        cfg.save()
    except PermissionError:
        print(f"error: club settings are managed by the administrator ({cfg.path()}); "
              "re-run with sudo", file=sys.stderr)
        return 1
    print(f"Club Steam accounts: {cfg.steam_club or '-'}; club Sober profile: {cfg.sober_club_profile or '-'}")


def cmd_sober(args, cfg):
    a = args.action
    if a == "init":
        sober.init(args.name)
    elif a == "new":
        sober.new(args.name)
    elif a == "use":
        sober.use(args.name)
    elif a == "run":
        return sober.run(args.name)
    elif a == "list":
        _print_sober(cfg)
        return
    print("OK")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mfdclub", description="Manage Steam/Sober accounts on this device")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="show accounts present on this device").set_defaults(fn=cmd_list)
    lo = sub.add_parser("logout", help="log out of every non-club account (dry run unless --yes)")
    lo.add_argument("--yes", action="store_true", help="actually do it")
    lo.set_defaults(fn=cmd_logout)
    cl = sub.add_parser("club", help="configure which accounts belong to the club")
    cl.add_argument("action", choices=["add-steam", "rm-steam", "set-sober"])
    cl.add_argument("value", help="SteamID64 / login name, or Sober profile name")
    cl.set_defaults(fn=cmd_club)
    so = sub.add_parser("sober", help="separate Sober spaces (profiles)")
    so.add_argument("action", choices=["init", "new", "use", "run", "list"])
    so.add_argument("name", nargs="?")
    so.set_defaults(fn=cmd_sober)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "sober" and args.action in ("init", "new", "use") and not args.name:
        print("profile name required", file=sys.stderr)
        return 2
    try:
        return args.fn(args, Config.load()) or 0
    except sober.SoberError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
