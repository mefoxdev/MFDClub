# MFDClub

CLI to see which Steam and Roblox (Sober) accounts are present on this device,
log out of everything that is not a club account, and keep a separate Sober
"space" for personal play without touching the club session.

Python 3.10+, no dependencies. Run `python -m mfdclub ...` or `pip install -e .` for `mfdclub`.

## Usage

```bash
mfdclub club add-steam <login name or SteamID64>   # mark club Steam accounts
mfdclub club set-sober club                        # name of the club Sober profile
mfdclub list                                       # Steam accounts + Sober profiles
mfdclub logout                                     # dry run
mfdclub logout --yes                               # apply (Steam must be closed)
```

### Separate Sober spaces

Sober has no multi-account support. `mfdclub` keeps one data directory per profile
and swaps the active one into `~/.var/app/org.vinegarhq.Sober` while Sober is closed,
so each profile keeps its own login.

```bash
mfdclub sober init club     # once: call your current Sober data "club"
mfdclub sober new me        # empty space for your own account
mfdclub sober run me        # switch to "me" and launch Sober (log in there)
mfdclub sober run club      # back to the club session, still logged in
```

## What it does and does not do

- **Steam**: reads `config/loginusers.vdf` (native and Flatpak Steam). Logout removes non-club
  entries (backup `loginusers.vdf.bak-*` is written) so they no longer appear in Steam's
  account list. Stored refresh tokens elsewhere in Steam's config are not deleted.
- **Sober**: Roblox account names are not shown; Sober's session storage location is not
  documented, so profiles are tracked as whole directories. Logout of a non-club profile
  **wipes that profile's data** (Roblox is re-downloaded on next launch).
- `logout` is a dry run unless `--yes`, and refuses to run with no club accounts configured.
- Not tested against a real Steam/Sober install (neither is present on the dev machine).

## License

AGPL-3.0-or-later, see `LICENSE`.
