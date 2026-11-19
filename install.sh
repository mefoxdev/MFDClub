#!/bin/sh
# MFDClub installer.
#   curl -fsSL https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install.sh | sh
#   wget -qO- https://raw.githubusercontent.com/mefoxdev/MFDClub/main/install.sh | sh
# Uninstall: ... | sh -s -- --uninstall
# Env: MFDCLUB_REF (branch/tag, default main), MFDCLUB_BIN_DIR, MFDCLUB_APP_DIR,
#      MFDCLUB_TARBALL_URL (override download URL).
set -eu

REPO="mefoxdev/MFDClub"
REF="${MFDCLUB_REF:-main}"
BIN_DIR="${MFDCLUB_BIN_DIR:-$HOME/.local/bin}"
APP_DIR="${MFDCLUB_APP_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/mfdclub-app}"
URL="${MFDCLUB_TARBALL_URL:-https://github.com/$REPO/archive/$REF.tar.gz}"

die() { echo "mfdclub installer: $*" >&2; exit 1; }

if [ "${1:-}" = "--uninstall" ]; then
    rm -rf "$APP_DIR" "$BIN_DIR/mfdclub"
    echo "Removed $APP_DIR and $BIN_DIR/mfdclub (your config and data were left in place)."
    exit 0
fi

command -v python3 >/dev/null 2>&1 || die "python3 is required"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || die "Python 3.10+ is required"
command -v tar >/dev/null 2>&1 || die "tar is required"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT INT TERM

echo "Downloading $URL"
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

# Replace the previous install atomically-ish.
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR"
cp -R "$TMP/src/mfdclub" "$APP_DIR/mfdclub"
cp "$TMP/src/LICENSE" "$APP_DIR/" 2>/dev/null || true

cat > "$BIN_DIR/mfdclub" <<LAUNCHER
#!/bin/sh
PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m mfdclub "\$@"
LAUNCHER
chmod +x "$BIN_DIR/mfdclub"

echo "Installed: $BIN_DIR/mfdclub"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "Note: $BIN_DIR is not in your PATH. Add it, e.g.: export PATH=\"$BIN_DIR:\$PATH\"" ;;
esac
echo "Try: mfdclub list"
