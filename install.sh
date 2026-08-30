#!/usr/bin/env bash
# ConBarAI - instalación en Ubuntu GNOME
# Comprueba dependencias (ofreciendo instalarlas), resuelve el terminal del
# sistema (Ghostty o el que tenga el usuario) y enlaza todo en ~/.local.
# El atajo global lo gestiona oc-tray según settings.json.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
SHARE="$HOME/.local/share/oc-drop"
CONFIG="$HOME/.config/oc-drop"
AUTOSTART="$HOME/.config/autostart"

mkdir -p "$BIN" "$SHARE" "$CONFIG" "$AUTOSTART"

# --- dependencias del panel ---
DEPS=(python3-gi gir1.2-vte-2.91 gir1.2-ayatanaappindicator3-0.1 wmctrl xdotool tmux libnotify-bin)
MISSING=()
for dep in "${DEPS[@]}"; do
  dpkg -s "$dep" >/dev/null 2>&1 || MISSING+=("$dep")
done
if [ ${#MISSING[@]} -gt 0 ]; then
  echo "[!] Faltan dependencias: ${MISSING[*]}"
  if [ -t 0 ]; then
    read -r -p "¿Instalarlas con apt? [s/N] " resp
    if [[ "$resp" =~ ^[sS]$ ]]; then
      sudo apt-get update -qq && sudo apt-get install -y "${MISSING[@]}"
    fi
  else
    echo "[!] Instálalas a mano: sudo apt install ${MISSING[*]}"
  fi
fi

# --- terminal del sistema: Ghostty o el que tenga el usuario ---
FALLBACKS=(gnome-terminal konsole alacritty kitty xterm x-terminal-emulator)
TERMINAL="none"
if command -v ghostty >/dev/null 2>&1; then
  TERMINAL="ghostty"
else
  echo "[!] Ghostty no está instalado."
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
      echo "[!] Sin terminal del sistema disponible (el panel funciona igual)."
    else
      echo "[i] Se usará $TERMINAL como terminal del sistema."
    fi
  fi
fi

# --- OpenCode ---
if ! command -v opencode >/dev/null 2>&1; then
  echo "[!] OpenCode no está instalado."
  if [ -t 0 ]; then
    read -r -p "¿Instalar OpenCode ahora? [s/N] " resp
    if [[ "$resp" =~ ^[sS]$ ]]; then
      curl -fsSL https://opencode.ai/install | bash
      export PATH="$HOME/.local/bin:$HOME/.opencode/bin:$PATH"
    fi
  else
    echo "[i] Instálalo después: curl -fsSL https://opencode.ai/install | bash"
  fi
  if ! command -v opencode >/dev/null 2>&1; then
    echo "[!] Sin OpenCode, el panel abrirá sin sesión funcional."
  fi
fi

# --- tipografía (look Omarchy): JetBrains Mono Nerd Font ---
if ! fc-list 2>/dev/null | grep -qi "jetbrainsmono nerd font" \
   && ! ls "$HOME/.local/share/fonts" 2>/dev/null | grep -qi "^JetBrainsMonoNerdFont-"; then
  echo "[i] Tipografía JetBrains Mono Nerd no encontrada (~90 MB de descarga)."
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
        echo "[OK] JetBrains Mono Nerd Font instalada"
      else
        echo "[!] Descarga fallida; opcional: sudo apt install fonts-jetbrains-mono"
      fi
      rm -f /tmp/JetBrainsMono-Nerd.zip
    fi
  fi
fi

# --- enlaces, icono y entradas de escritorio ---
ln -sf "$DIR/oc-drop" "$BIN/oc-drop"
ln -sf "$DIR/oc-tray" "$BIN/oc-tray"
install -m 644 "$DIR/icons/oc-drop.svg" "$SHARE/icon.svg"
mkdir -p "$HOME/.local/share/applications"
sed "s|__HOME__|$HOME|g" "$DIR/applications/conbarai.desktop" \
  > "$HOME/.local/share/applications/conbarai.desktop"

# --- ajustes iniciales (conservando los existentes) ---
if [ -f "$CONFIG/settings.json" ]; then
  python3 - "$TERMINAL" <<'EOF'
import json, sys
from pathlib import Path
p = Path.home() / ".config/oc-drop/settings.json"
data = json.loads(p.read_text())
data.setdefault("terminal", sys.argv[1] if sys.argv[1] != "none" else "auto")
data.setdefault("autostart", True)
p.write_text(json.dumps(data, indent=2) + "\n")
EOF
else
  cat > "$CONFIG/settings.json" <<EOF
{
  "autohide": true,
  "autostart": true,
  "workdir": "",
  "width": 0.34,
  "height": 0.62,
  "opacity": 0.97,
  "keybinding": "<Super>Return",
  "terminal": "${TERMINAL}"
}
EOF
fi

# Autostart solo si el ajuste lo pide (desactivable desde el tray)
if python3 -c "import json,sys; sys.exit(0 if json.load(open('$CONFIG/settings.json')).get('autostart', True) else 1)"; then
  sed "s|__HOME__|$HOME|g" "$DIR/autostart/oc-tray.desktop" > "$AUTOSTART/oc-tray.desktop"
else
  rm -f "$AUTOSTART/oc-tray.desktop"
fi

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "[OK] ConBarAI instalado"
echo "     Panel:      $BIN/oc-drop  (atajo según settings.json, por defecto Super+Intro)"
echo "     Tray:       $BIN/oc-tray  (arranca al iniciar sesión y registra el atajo)"
echo "     Terminal:   $TERMINAL (opción 'Terminal del sistema' del tray)"
echo "     Ajustes:    $CONFIG/settings.json"
