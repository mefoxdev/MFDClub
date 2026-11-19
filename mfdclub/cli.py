from __future__ import annotations

import argparse
import os
import pwd
import sys

from . import __version__, paths, sober, steam
from .config import Config, system_config_path


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


def _show(user: str | None) -> None:
    paths.set_home(paths.home_of(user) if user else None)
    try:
        cfg = Config.load()  # per-user config of the inspected user (system config wins)
        _print_steam(cfg)
        _print_sober(cfg)
    except PermissionError as e:
        print(f"  no access to {e.filename} (run with sudo to inspect other users)")
    finally:
        paths.set_home(None)


def _become(name: str) -> None:
    """Act as another local user (root only): drop privileges so files keep the right owner."""
    try:
        pw = pwd.getpwnam(name)
    except KeyError:
        raise LookupError(f"no such user: {name}") from None
    if os.geteuid() == pw.pw_uid:
        return
    if os.geteuid() != 0:
        raise PermissionError(f"administering user {name} requires root (use sudo)")
    os.initgroups(pw.pw_name, pw.pw_gid)
    os.setgid(pw.pw_gid)
    os.setuid(pw.pw_uid)
    os.environ.update(HOME=pw.pw_dir, USER=pw.pw_name, LOGNAME=pw.pw_name)
    paths.set_home(None)  # Path.home() now resolves to the target user's home


def cmd_list(args, cfg):
    if args.all_users:
        for u in paths.local_users():
            print(f"=== {u} ===")
            _show(u)
    else:
        if args.user:
            paths.home_of(args.user)  # fail early on unknown user
            print(f"=== {args.user} ===")
        _show(args.user)


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
    target = None
    if args.system:
        if os.geteuid() != 0:
            print("error: --system requires root (use sudo)", file=sys.stderr)
            return 1
        target = system_config_path()
        cfg = Config.load(target)
    if args.action == "add-steam":
        if args.value not in cfg.steam_club:
            cfg.steam_club.append(args.value)
    elif args.action == "rm-steam":
        cfg.steam_club = [x for x in cfg.steam_club if x.lower() != args.value.lower()]
    elif args.action == "set-sober":
        cfg.sober_club_profile = args.value
    elif args.action == "clear-sober":
        cfg.sober_club_profile = None
    if args.action != "show":
        try:
            cfg.save(target)
            if target:
                target.chmod(0o644)
        except PermissionError:
            print(f"error: club settings are managed by the administrator ({cfg.path()}); "
                  "re-run with sudo mfdclub club --system ...", file=sys.stderr)
            return 1
    where = target or cfg.path()
    print(f"[{where}] Club Steam accounts: {cfg.steam_club or '-'}; "
          f"club Sober profile: {cfg.sober_club_profile or '-'}")


def cmd_sober(args, cfg):
    a = args.action
    if a == "init":
        sober.init(args.name)
    elif a == "new":
        sober.new(args.name)
    elif a == "use":
        sober.use(args.name)
    elif a == "run":
        if args.user:
            raise sober.SoberError("`sober run` launches a GUI app; run it from that user's own session")
        return sober.run(args.name)
    elif a == "list":
        _print_sober(cfg)
        return
    print("OK")


def _user_opt(sp) -> None:
    sp.add_argument("-u", "--user", default=argparse.SUPPRESS, help="administer another local user (needs sudo)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mfdclub", description="Manage Steam/Sober accounts on this device")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("-u", "--user", help="administer another local user (needs sudo)")
    p.set_defaults(user=None, all_users=False, system=False)
    sub = p.add_subparsers(dest="cmd", required=True)
    li = sub.add_parser("list", help="show accounts present on this device")
    _user_opt(li)
    li.add_argument("--all-users", action="store_true", help="inspect every local user (needs sudo)")
    li.set_defaults(fn=cmd_list)
    lo = sub.add_parser("logout", help="log out of every non-club account (dry run unless --yes)")
    lo.add_argument("--yes", action="store_true", help="actually do it")
    _user_opt(lo)
    lo.set_defaults(fn=cmd_logout)
    cl = sub.add_parser("club", help="configure which accounts belong to the club")
    cl.add_argument("action", choices=["show", "add-steam", "rm-steam", "set-sober", "clear-sober"])
    cl.add_argument("value", nargs="?", help="SteamID64 / login name, or Sober profile name")
    cl.add_argument("--system", action="store_true",
                    help="edit the machine-wide config (/etc/mfdclub, root only) that applies to all users")
    _user_opt(cl)
    cl.set_defaults(fn=cmd_club)
    so = sub.add_parser("sober", help="separate Sober spaces (profiles)")
    so.add_argument("action", choices=["init", "new", "use", "run", "list"])
    so.add_argument("name", nargs="?")
    _user_opt(so)
    so.set_defaults(fn=cmd_sober)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "sober" and args.action in ("init", "new", "use") and not args.name:
        print("profile name required", file=sys.stderr)
        return 2
    if args.cmd == "club" and args.action in ("add-steam", "rm-steam", "set-sober") and not args.value:
        print("value required", file=sys.stderr)
        return 2
    try:
        # read-only `list` inspects other users without changing identity; everything
        # else runs as the target user so created/changed files keep the right owner.
        acts_as_user = args.user and args.cmd in ("logout", "sober", "club") \
            and not (args.cmd == "club" and args.system) \
            and not (args.cmd == "sober" and args.action == "list") \
            and not (args.cmd == "club" and args.action == "show")
        if acts_as_user:
            _become(args.user)
        elif args.user and args.cmd != "list":
            paths.set_home(paths.home_of(args.user))
        return args.fn(args, Config.load()) or 0
    except LookupError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except sober.SoberError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
