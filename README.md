# MFDClub

CLI to see which Steam and Roblox (Sober) accounts are present on this device,
log out of everything that is not a club account, and keep a separate Sober
"space" for personal play without touching the club session.

Python 3.10+, no dependencies.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install.sh | sh
# or
wget -qO- https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install.sh | sh
```

Installs to `~/.local/share/mfdclub-app` with a launcher in `~/.local/bin/mfdclub`.
Re-run the same command to update. Uninstall (config and data are kept):

```bash
curl -fsSL https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install.sh | sh -s -- --uninstall
```

Options via env: `MFDCLUB_REF` (branch/tag), `MFDCLUB_BIN_DIR`, `MFDCLUB_APP_DIR`.

### Shared PC (admin account + restricted accounts)

Run as the admin; the installer asks which local users may use `mfdclub`, and which
accounts belong to the club:

```bash
curl -fsSL https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install-system.sh | sudo sh
# or: wget -qO- https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install-system.sh | sudo sh
```

Non-interactive: `... | sudo sh -s -- --users elev,bob --club-steam club_login --club-sober club`
(`--all` for everyone, `--uninstall` to remove, `--dry-run` to preview).

It installs root-owned files to `/opt/mfdclub-app` and `/usr/local/bin/mfdclub`, puts the chosen
users in the `mfdclub` group (they need to log in again), and writes the club list to
`/etc/mfdclub/config.json`. That file takes priority over per-user config and only root can edit it
(`sudo mfdclub club add-steam ...`), so restricted users cannot un-mark club accounts.
Steam and Sober data stay per user: each user sees and logs out only their own accounts.

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

## GUI (Fyne, read-only)

`gui/` is a small Go/Fyne window with two tabs: Steam accounts and Sober profiles
(club accounts are marked). It reads the same files and config as the CLI; use the
CLI to change anything.

```bash
# Debian/Ubuntu build deps: sudo apt install golang gcc libgl1-mesa-dev xorg-dev
cd gui && go build -o mfdclub-gui . && ./mfdclub-gui
```

Tests run without a display: `cd gui && go test -tags ci ./...`.

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
