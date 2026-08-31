#!/usr/bin/env bash
# ConBarAI (Console Bar Artificial Intelligence) - instalación en Ubuntu GNOME
# Comprueba dependencias (ofreciendo instalarlas), resuelve el terminal del
# sistema (Ghostty o el que tenga el usuario), pregunta la carpeta de trabajo
# y enlaza todo en ~/.local. El atajo global lo gestiona oc-tray.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd || pwd)"

# Guion suelto (bash <(curl …) o curl | bash): descarga la última release
# publicada y sigue la instalación desde ella.
if [ ! -f "$DIR/oc-drop" ]; then
  echo "[i] Descargando la última release de ConBarAI..."
  TMPD="$(mktemp -d)"
  TAG="$(curl -fsSL https://api.github.com/repos/686f6c61/ubuntu-ConBarAI/releases/latest | grep -m1 '"tag_name"' | cut -d'"' -f4)"
  if [ -z "$TAG" ]; then
    echo "[!] No se pudo resolver la última release; clona el repositorio e instala desde ahí."
    exit 1
  fi
  echo "[i] Release $TAG"
  curl -fsSL "https://github.com/686f6c61/ubuntu-ConBarAI/archive/refs/tags/$TAG.tar.gz" | tar -xz -C "$TMPD"
  exec bash "$TMPD"/ubuntu-ConBarAI-*/install.sh "$@"
fi

BIN="$HOME/.local/bin"
SHARE="$HOME/.local/share/oc-drop"
CONFIG="$HOME/.config/oc-drop"
AUTOSTART="$HOME/.config/autostart"
VERSION="$(grep -m1 '^version' "$DIR/pyproject.toml" 2>/dev/null | cut -d'"' -f2 || true)"
VERSION="${VERSION:-?}"

# --- presentación (colores solo con TTY) ---
if [ -t 1 ]; then
  ACC=$'\033[1;34m'; VER=$'\033[1;32m'; AVI=$'\033[1;33m'
  DIM=$'\033[2m'; NEG=$'\033[1m'; RST=$'\033[0m'
else
  ACC=""; VER=""; AVI=""; DIM=""; NEG=""; RST=""
fi

ok()   { echo "${VER}[OK]${RST} $*"; }
info() { echo "${ACC}[i]${RST}  $*"; }
warn() { echo "${AVI}[!]${RST}  $*"; }
paso() { echo; echo "${NEG}${ACC}[$1/7]${RST} ${NEG}$2${RST}"; }

echo "${ACC}"
cat <<'BANNER'
 ██████╗ ██████╗ ███╗   ██╗██████╗  █████╗ ██████╗  █████╗ ██╗
██╔════╝██╔═══██╗████╗  ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║
██║     ██║   ██║██╔██╗ ██║██████╔╝███████║██████╔╝███████║██║
██║     ██║   ██║██║╚██╗██║██╔══██╗██╔══██║██╔══██╗██╔══██║██║
╚██████╗╚██████╔╝██║ ╚████║██████╔╝██║  ██║██║  ██║██║  ██║██║
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝
BANNER
echo "${RST}${DIM}Console Bar Artificial Intelligence · v${VERSION}${RST}"
echo "${DIM}OpenCode en la barra de Ubuntu, con vigía y forense de crashes${RST}"

mkdir -p "$BIN" "$SHARE" "$CONFIG" "$AUTOSTART"

# --- [1/7] dependencias del panel ---
paso 1 "Dependencias del panel"
DEPS=(python3-gi gir1.2-vte-2.91 gir1.2-ayatanaappindicator3-0.1 wmctrl xdotool tmux libnotify-bin)
MISSING=()
for dep in "${DEPS[@]}"; do
  dpkg -s "$dep" >/dev/null 2>&1 || MISSING+=("$dep")
done
if [ ${#MISSING[@]} -gt 0 ]; then
  warn "Faltan dependencias: ${MISSING[*]}"
  if [ -t 0 ]; then
    read -r -p "¿Instalarlas con apt? [s/N] " resp
    if [[ "$resp" =~ ^[sS]$ ]]; then
      sudo apt-get update -qq && sudo apt-get install -y "${MISSING[@]}"
    fi
  else
    warn "Instálalas a mano: sudo apt install ${MISSING[*]}"
  fi
else
  ok "Todas presentes (${#DEPS[@]})"
fi

# --- [2/7] terminal del sistema: Ghostty o el que tenga el usuario ---
paso 2 "Terminal del sistema"
FALLBACKS=(gnome-terminal konsole alacritty kitty xterm x-terminal-emulator)
TERMINAL="none"
if command -v ghostty >/dev/null 2>&1; then
  TERMINAL="ghostty"
  ok "Ghostty detectado"
else
  warn "Ghostty no está instalado."
  if [ -t 0 ]; then
    read -r -p "¿Instalar Ghostty? [s/N] " resp
    if [[ "$resp" =~ ^[sS]$ ]]; then
      sudo apt-get update -qq && sudo apt-get install -y ghostty && TERMINAL="ghostty"
    fi
  fi
  if [ "$TERMINAL" = "none" ]; then
    for t in "${FALLBACKS[@]}"; do
      if command -v "$t" >/dev/null 2>&1; then
        TERMINAL="$t"
        break
      fi
    done
    if [ "$TERMINAL" = "none" ]; then
      warn "Sin terminal del sistema disponible (el panel funciona igual)."
    else
      info "Se usará $TERMINAL como terminal del sistema."
    fi
  fi
fi

# --- [3/7] OpenCode ---
paso 3 "OpenCode"
if command -v opencode >/dev/null 2>&1; then
  ok "OpenCode en el PATH"
else
  warn "OpenCode no está instalado."
  if [ -t 0 ]; then
    read -r -p "¿Instalar OpenCode ahora? [s/N] " resp
    if [[ "$resp" =~ ^[sS]$ ]]; then
      curl -fsSL https://opencode.ai/install | bash
      export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$PATH"
    fi
  else
    info "Instálalo después: curl -fsSL https://opencode.ai/install | bash"
  fi
  if ! command -v opencode >/dev/null 2>&1; then
    warn "Sin OpenCode, el panel abrirá sin sesión funcional."
  fi
fi

# --- [4/7] tipografía (look Omarchy): JetBrains Mono Nerd Font ---
paso 4 "Tipografía JetBrains Mono Nerd"
if fc-list 2>/dev/null | grep -qi "jetbrainsmono nerd font" \
   || compgen -G "$HOME/.local/share/fonts/JetBrainsMonoNerdFont-*" >/dev/null; then
  ok "Ya instalada"
else
  info "No encontrada (~90 MB de descarga)."
  if [ -t 0 ]; then
    read -r -p "¿Descargar e instalar? [s/N] " resp
    if [[ "$resp" =~ ^[sS]$ ]]; then
      mkdir -p "$HOME/.local/share/fonts"
      if curl -fL --max-time 240 -o /tmp/JetBrainsMono-Nerd.zip \
           https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip; then
        python3 - <<'EOF'
import os, re, zipfile
dest = os.path.expanduser("~/.local/share/fonts")
pat = re.compile(r"JetBrainsMonoNerdFont-[A-Za-z]+\.ttf$")
with zipfile.ZipFile("/tmp/JetBrainsMono-Nerd.zip") as zf:
    for name in zf.namelist():
        if pat.search(name):
            data = zf.read(name)
            with open(os.path.join(dest, os.path.basename(name)), "wb") as fh:
                fh.write(data)
EOF
        fc-cache -f >/dev/null 2>&1
        ok "JetBrains Mono Nerd Font instalada"
      else
        warn "Descarga fallida; opcional: sudo apt install fonts-jetbrains-mono"
      fi
      rm -f /tmp/JetBrainsMono-Nerd.zip
    fi
  fi
fi

# --- [5/7] carpeta de trabajo de OpenCode ---
paso 5 "Carpeta de trabajo"
CURRENT_WD=""
if [ -f "$CONFIG/settings.json" ]; then
  CURRENT_WD="$(python3 -c "import json;print(json.load(open('$CONFIG/settings.json')).get('workdir') or '')" 2>/dev/null || true)"
fi
DEFAULT_WD="$HOME/Documentos/ConBarAI"
if [ -d "$HOME/Documents" ] && [ ! -d "$HOME/Documentos" ]; then
  DEFAULT_WD="$HOME/Documents/ConBarAI"
fi
[ -n "$CURRENT_WD" ] && DEFAULT_WD="$CURRENT_WD"
WORKDIR="$DEFAULT_WD"
if [ -t 0 ]; then
  read -r -p "Carpeta de trabajo de OpenCode [$DEFAULT_WD]: " resp
  WORKDIR="${resp:-$DEFAULT_WD}"
fi
WORKDIR="${WORKDIR/#\~/$HOME}"
mkdir -p "$WORKDIR"
ok "Carpeta de trabajo: $WORKDIR ${DIM}(cambiable en el tray: Carpeta de trabajo…)${RST}"

# --- [6/7] enlaces, skill, escritorio y ajustes ---
paso 6 "Enlaces, skill y ajustes"
ln -sf "$DIR/conbarai" "$BIN/conbarai"
ln -sf "$DIR/oc-drop" "$BIN/oc-drop"
ln -sf "$DIR/oc-tray" "$BIN/oc-tray"
ln -sf "$DIR/oc-crash-watch" "$BIN/oc-crash-watch"
ln -sf "$DIR/oc-crash-run" "$BIN/oc-crash-run"
install -m 644 "$DIR/icons/oc-drop.svg" "$SHARE/icon.svg"
ok "Binarios enlazados en $BIN"

# Skills empaquetadas: copia canónica en la app; el panel la enlaza como
# skill de proyecto en su workdir, así solo la carga ESE OpenCode.
if [ -d "$DIR/skills" ]; then
  rm -rf "$SHARE/skills"
  cp -r "$DIR/skills" "$SHARE/skills"
  ok "Skills instaladas en $SHARE/skills: $(ls "$SHARE/skills" | tr '\n' ' ')"
fi

mkdir -p "$HOME/.local/share/applications"
sed "s|__HOME__|$HOME|g" "$DIR/applications/conbarai.desktop" \
  > "$HOME/.local/share/applications/conbarai.desktop"

# Ajustes iniciales (conservando los existentes)
if [ -f "$CONFIG/settings.json" ]; then
  python3 - "$TERMINAL" "$WORKDIR" <<'EOF'
import json, sys
from pathlib import Path
p = Path.home() / ".config/oc-drop/settings.json"
data = json.loads(p.read_text())
data.setdefault("terminal", sys.argv[1] if sys.argv[1] != "none" else "auto")
data.setdefault("autostart", True)
data["workdir"] = sys.argv[2]
p.write_text(json.dumps(data, indent=2) + "\n")
EOF
  ok "Ajustes existentes conservados ($CONFIG/settings.json)"
else
  python3 - "$TERMINAL" "$WORKDIR" <<'EOF'
import json, sys
from pathlib import Path
p = Path.home() / ".config/oc-drop/settings.json"
p.write_text(json.dumps({
    "autohide": True,
    "autostart": True,
    "workdir": sys.argv[2],
    "width": 0.34,
    "height": 0.62,
    "opacity": 0.97,
    "keybinding": "<Super>Return",
    "terminal": sys.argv[1],
}, indent=2) + "\n")
EOF
  ok "Ajustes creados ($CONFIG/settings.json)"
fi

# Autostart solo si el ajuste lo pide (desactivable desde el tray)
if python3 -c "import json,sys; sys.exit(0 if json.load(open('$CONFIG/settings.json')).get('autostart', True) else 1)"; then
  sed "s|__HOME__|$HOME|g" "$DIR/autostart/oc-tray.desktop" > "$AUTOSTART/oc-tray.desktop"
  ok "Autostart del tray registrado"
else
  rm -f "$AUTOSTART/oc-tray.desktop"
  info "Autostart desactivado por ajuste"
fi

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

# --- [7/7] vigía de crashes: servicio de usuario ---
paso 7 "Vigía de crashes (servicio de usuario)"
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
if command -v systemctl >/dev/null 2>&1; then
  install -m 644 "$DIR/systemd/oc-crash-watch.service" "$UNIT_DIR/oc-crash-watch.service"
  systemctl --user daemon-reload >/dev/null 2>&1 || true
  if python3 -c "import json,sys; sys.exit(0 if json.load(open('$CONFIG/settings.json')).get('crash_watch', True) else 1)"; then
    systemctl --user enable --now oc-crash-watch.service >/dev/null 2>&1 || true
    ok "Vigía ACTIVO ${DIM}(systemctl --user status oc-crash-watch)${RST}"
  else
    systemctl --user disable --now oc-crash-watch.service >/dev/null 2>&1 || true
    info "Vigía en pausa (crash_watch=false)."
  fi
else
  warn "Sin systemctl: el vigía no se registró."
fi

# --- resumen ---
echo
echo "${DIM}──────────────────────────────────────────────────────────────${RST}"
ok "${NEG}ConBarAI v${VERSION} instalado${RST}"
echo
echo "  ${NEG}App${RST}        conbarai           ${DIM}también en el menú de Aplicaciones${RST}"
echo "  ${NEG}Panel${RST}      oc-drop            ${DIM}atajo según settings.json (Súper+Intro)${RST}"
echo "  ${NEG}Tray${RST}       oc-tray            ${DIM}icono en la barra; Ayuda en su menú${RST}"
echo "  ${NEG}Vigía${RST}      oc-crash-watch     ${DIM}crashes del sistema, avisa y analiza${RST}"
echo "  ${NEG}Terminal${RST}   $TERMINAL"
echo "  ${NEG}Carpeta${RST}    $WORKDIR"
echo "  ${NEG}Ajustes${RST}    $CONFIG/settings.json"
echo "  ${NEG}Informes${RST}   $HOME/.local/state/oc-drop/crash/"
echo
echo "  Cierra sesión y vuelve a entrar (o ejecuta ${NEG}oc-tray${RST}) para ver el icono."
echo "${DIM}──────────────────────────────────────────────────────────────${RST}"
