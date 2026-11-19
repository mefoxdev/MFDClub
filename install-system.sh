#!/bin/sh
# MFDClub system-wide installer for shared PCs (admin account + restricted accounts).
#   curl -fsSL https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install-system.sh | sudo sh
#   wget -qO- https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install-system.sh | sudo sh
#
# Installs to /opt/mfdclub-app + /usr/local/bin/mfdclub (root-owned, users cannot modify it),
# lets you choose which local users may run it, and writes an admin-managed club config
# (/etc/mfdclub/config.json) that restricted users cannot edit.
#
# Options (skip the questions):
#   --users a,b        only these users may run mfdclub (added to group "mfdclub")
#   --all              every user may run it
#   --club-steam a,b   club Steam logins / SteamID64s
#   --club-sober NAME  club Sober profile name
#   --uninstall        remove app, launcher and group (keeps /etc/mfdclub)
#   --dry-run          print privileged actions instead of doing them
# Env: MFDCLUB_REF, MFDCLUB_TARBALL_URL, MFDCLUB_BIN_DIR, MFDCLUB_APP_DIR, MFDCLUB_ETC_DIR
set -eu

REPO="mefoxdev/MFDClub"
REF="${MFDCLUB_REF:-main}"
BIN_DIR="${MFDCLUB_BIN_DIR:-/usr/local/bin}"
APP_DIR="${MFDCLUB_APP_DIR:-/opt/mfdclub-app}"
ETC_DIR="${MFDCLUB_ETC_DIR:-/etc/mfdclub}"
URL="${MFDCLUB_TARBALL_URL:-https://github.com/$REPO/archive/$REF.tar.gz}"
GROUP="mfdclub"

USERS="" ALL=0 STEAM="" SOBER="" UNINSTALL=0 DRY=0 STEAM_SET=0 SOBER_SET=0
die() { echo "mfdclub installer: $*" >&2; exit 1; }
say() { echo "$*"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --users) [ $# -ge 2 ] || die "--users needs a value"; USERS="$2"; shift 2 ;;
        --all) ALL=1; shift ;;
        --club-steam) [ $# -ge 2 ] || die "--club-steam needs a value"; STEAM="$2"; STEAM_SET=1; shift 2 ;;
        --club-sober) [ $# -ge 2 ] || die "--club-sober needs a value"; SOBER="$2"; SOBER_SET=1; shift 2 ;;
        --uninstall) UNINSTALL=1; shift ;;
        --dry-run) DRY=1; shift ;;
        -h|--help) sed -n '2,19p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown option: $1" ;;
    esac
done

priv() { if [ "$DRY" = 1 ]; then echo "[dry-run] $*"; else "$@"; fi; }

if [ "$DRY" = 0 ] && [ "$(id -u)" != 0 ]; then
    die "must run as root. Use: curl -fsSL <url> | sudo sh"
fi

if [ "$UNINSTALL" = 1 ]; then
    rm -rf "$APP_DIR" "$BIN_DIR/mfdclub"
    getent group "$GROUP" >/dev/null 2>&1 && priv groupdel "$GROUP" || true
    say "Removed $APP_DIR, $BIN_DIR/mfdclub and group $GROUP (kept $ETC_DIR and users' own data)."
    exit 0
fi

command -v python3 >/dev/null 2>&1 || die "python3 is required"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || die "Python 3.10+ is required"
command -v tar >/dev/null 2>&1 || die "tar is required"

# --- interactive questions (read from the terminal, since stdin is the script) ---
TTY=""
if ( : < /dev/tty > /dev/tty ) 2>/dev/null; then TTY=/dev/tty; fi
ask() { # ask "prompt" -> sets REPLY
    printf '%s' "$1" > "$TTY"
    IFS= read -r REPLY < "$TTY" || REPLY=""
}

local_users() {
    getent passwd | awk -F: '$3>=1000 && $3<60000 && $7 !~ /(nologin|false)$/ {print $1}' | sort
}

if [ "$ALL" = 0 ] && [ -z "$USERS" ]; then
    [ -n "$TTY" ] || die "no terminal for questions; pass --users a,b or --all"
    LIST="$(local_users)"
    [ -n "$LIST" ] || die "no regular users found; pass --users or --all"
    say "Local users:"
    i=1
    for u in $LIST; do say "  $i) $u"; i=$((i + 1)); done
    say "  a) all users"
    ask "Who may use mfdclub? Numbers separated by commas, or 'a': "
    case "$REPLY" in
        a|A|all) ALL=1 ;;
        *)
            for n in $(echo "$REPLY" | tr ',' ' '); do
                case "$n" in ''|*[!0-9]*) die "bad choice: $n" ;; esac
                u="$(echo "$LIST" | sed -n "${n}p")"
                [ -n "$u" ] || die "no user number $n"
                USERS="${USERS:+$USERS,}$u"
            done
            [ -n "$USERS" ] || die "nothing selected"
            ;;
    esac
fi

if [ "$STEAM_SET" = 0 ] && [ -n "$TTY" ]; then
    ask "Club Steam logins or SteamID64 (comma-separated, empty = configure later): "
    STEAM="$REPLY"; STEAM_SET=1
fi
if [ "$SOBER_SET" = 0 ] && [ -n "$TTY" ]; then
    ask "Club Sober profile name (empty = configure later): "
    SOBER="$REPLY"; SOBER_SET=1
fi

# validate users
CHOSEN=""
if [ "$ALL" = 0 ]; then
    for u in $(echo "$USERS" | tr ',' ' '); do
        case "$u" in *[!a-zA-Z0-9._-]*|'') die "invalid user name: $u" ;; esac
        id "$u" >/dev/null 2>&1 || die "no such user: $u"
        CHOSEN="$CHOSEN $u"
    done
fi

# --- download & install ---
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT INT TERM
say "Downloading $URL"
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" -o "$TMP/src.tar.gz" || die "download failed"
elif command -v wget >/dev/null 2>&1; then
    wget -q "$URL" -O "$TMP/src.tar.gz" || die "download failed"
else
    die "curl or wget is required"
fi
mkdir "$TMP/src"
tar -xzf "$TMP/src.tar.gz" -C "$TMP/src" --strip-components=1 || die "bad archive"
[ -d "$TMP/src/mfdclub" ] || die "archive does not contain the mfdclub package"

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR" "$ETC_DIR"
cp -R "$TMP/src/mfdclub" "$APP_DIR/mfdclub"
cp "$TMP/src/LICENSE" "$APP_DIR/" 2>/dev/null || true
find "$APP_DIR" -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true

cat > "$BIN_DIR/mfdclub" <<LAUNCHER
#!/bin/sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m mfdclub "\$@"
LAUNCHER

# permissions: root owns everything; either everyone or only group "mfdclub" may run it
if [ "$ALL" = 1 ]; then
    priv chown -R root:root "$APP_DIR" "$BIN_DIR/mfdclub"
    chmod -R u=rwX,go=rX "$APP_DIR"; chmod 755 "$BIN_DIR/mfdclub"
else
    getent group "$GROUP" >/dev/null 2>&1 || priv groupadd --system "$GROUP"
    priv chown -R "root:$GROUP" "$APP_DIR" "$BIN_DIR/mfdclub"
    chmod -R u=rwX,g=rX,o= "$APP_DIR"; chmod 750 "$BIN_DIR/mfdclub"
    for u in $CHOSEN; do
        priv usermod -aG "$GROUP" "$u"
        say "Added $u to group $GROUP (takes effect at next login)"
    done
fi

# admin-managed club config; restricted users cannot edit it
if [ -n "$STEAM$SOBER" ]; then
    python3 - "$ETC_DIR/config.json" "$STEAM" "$SOBER" <<'PY'
import json, sys
path, steam, sober = sys.argv[1:4]
cfg = {"steam_club": [s.strip() for s in steam.split(",") if s.strip()],
       "sober_club_profile": sober.strip() or None}
with open(path, "w") as f:
    json.dump(cfg, f, indent=2); f.write("\n")
PY
    priv chown root:root "$ETC_DIR" "$ETC_DIR/config.json"
    chmod 755 "$ETC_DIR"; chmod 644 "$ETC_DIR/config.json"
    say "Club config written to $ETC_DIR/config.json (edit it as root, or: sudo mfdclub club ...)"
fi

say "Installed: $BIN_DIR/mfdclub"
if [ "$ALL" = 1 ]; then say "Available to all users."; else say "Available to:${CHOSEN}"; fi
say "Next: log in as the user and run 'mfdclub list'."
