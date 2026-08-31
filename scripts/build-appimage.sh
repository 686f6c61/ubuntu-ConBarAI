#!/usr/bin/env bash
# Construye la AppImage de ConBarAI.
# La AppImage lleva la app completa como carga útil; al ejecutarla, copia
# la app a ~/.local/share/conbarai/app, corre install.sh (no interactivo)
# y lanza la app. Ejecutarla de nuevo actualiza la instalación.
# Uso: scripts/build-appimage.sh [directorio-salida]   (por defecto dist/)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$DIR/dist}"
VERSION="$(grep -m1 '^version' "$DIR/pyproject.toml" | cut -d'"' -f2)"
WORK="$(mktemp -d)"
APPDIR="$WORK/AppDir"
trap 'rm -rf "$WORK"' EXIT

echo "[i] ConBarAI v$VERSION -> AppImage"

# --- carga útil: la app tal cual la usa install.sh ---
PAYLOAD="$APPDIR/usr/share/conbarai"
mkdir -p "$PAYLOAD"
cp "$DIR"/conbarai "$DIR"/oc-drop "$DIR"/oc-tray \
   "$DIR"/oc-crash-watch "$DIR"/oc-crash-run "$DIR"/oc_common.py \
   "$DIR"/install.sh "$DIR"/uninstall.sh "$DIR"/pyproject.toml "$PAYLOAD/"
cp -r "$DIR"/skills "$DIR"/icons "$DIR"/applications "$DIR"/autostart \
      "$DIR"/systemd "$PAYLOAD/"

# --- AppRun: instala/actualiza y lanza ---
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/usr/bin/env bash
# ConBarAI AppImage: instala o actualiza la app en el espacio del usuario
# y la lanza. CONBARAI_INSTALL_ONLY=1 instala sin lanzar (pruebas/CI).
set -u
HERE="$(dirname "$(readlink -f "$0")")"
PAYLOAD="$HERE/usr/share/conbarai"
DEST="$HOME/.local/share/conbarai/app"

avisa() {
  zenity --error --title "ConBarAI" --text "$1" 2>/dev/null \
    || notify-send "ConBarAI" "$1" 2>/dev/null \
    || echo "[!] $1" >&2
}

if ! python3 -c "import gi" 2>/dev/null; then
  avisa "Faltan dependencias del sistema. Instálalas con:
sudo apt install python3-gi gir1.2-vte-2.91 gir1.2-ayatanaappindicator3-0.1 tmux libnotify-bin"
  exit 1
fi

mkdir -p "$DEST"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "$PAYLOAD/" "$DEST/"
else
  rm -rf "$DEST"; mkdir -p "$DEST"; cp -a "$PAYLOAD/." "$DEST/"
fi
chmod +x "$DEST"/conbarai "$DEST"/oc-* "$DEST"/install.sh "$DEST"/uninstall.sh

if ! bash "$DEST/install.sh" </dev/null; then
  avisa "La instalación no terminó bien; ejecuta a mano: bash $DEST/install.sh"
  exit 1
fi

if [ "${CONBARAI_INSTALL_ONLY:-0}" = "1" ]; then
  exit 0
fi
exec "$HOME/.local/bin/conbarai" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# --- desktop + icono (lo que appimagetool exige en la raíz) ---
cat > "$APPDIR/conbarai.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ConBarAI
GenericName=Panel de OpenCode
Comment=OpenCode en la barra de Ubuntu, con vigia y forense de crashes
Exec=conbarai
Icon=conbarai
Terminal=false
Categories=Development;Utility;
EOF
cp "$DIR/icons/oc-drop.svg" "$APPDIR/conbarai.svg"
# .DirIcon es lo que muestran los gestores de archivos: siempre presente
ln -sf conbarai.svg "$APPDIR/.DirIcon"

# --- appimagetool ---
TOOL="${APPIMAGETOOL:-}"
if [ -z "$TOOL" ]; then
  if command -v appimagetool >/dev/null 2>&1; then
    TOOL=appimagetool
  else
    TOOL="$WORK/appimagetool"
    echo "[i] Descargando appimagetool..."
    curl -fsSL -o "$TOOL" \
      "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
  fi
fi

mkdir -p "$OUT"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run -n "$APPDIR" \
  "$OUT/ConBarAI-x86_64.AppImage" >/dev/null 2>&1 \
  || ARCH=x86_64 "$TOOL" -n "$APPDIR" "$OUT/ConBarAI-x86_64.AppImage"
echo "[OK] $OUT/ConBarAI-x86_64.AppImage ($(du -h "$OUT/ConBarAI-x86_64.AppImage" | cut -f1))"
