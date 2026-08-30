#!/usr/bin/env bash
# ConBarAI (Console Bar Artificial Intelligence) - desinstalación
set -uo pipefail

if [ -t 1 ]; then
  ACC=$'\033[1;34m'; VER=$'\033[1;32m'; AVI=$'\033[1;33m'
  DIM=$'\033[2m'; NEG=$'\033[1m'; RST=$'\033[0m'
else
  ACC=""; VER=""; AVI=""; DIM=""; NEG=""; RST=""
fi

ok()   { echo "${VER}[OK]${RST} $*"; }
info() { echo "${ACC}[i]${RST}  $*"; }
warn() { echo "${AVI}[!]${RST}  $*"; }

echo "${ACC}"
cat <<'BANNER'
 ██████╗ ██████╗ ███╗   ██╗██████╗  █████╗ ██████╗  █████╗ ██╗
██╔════╝██╔═══██╗████╗  ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║
██║     ██║   ██║██╔██╗ ██║██████╔╝███████║██████╔╝███████║██║
██║     ██║   ██║██║╚██╗██║██╔══██╗██╔══██║██╔══██╗██╔══██║██║
╚██████╗╚██████╔╝██║ ╚████║██████╔╝██║  ██║██║  ██║██║  ██║██║
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝
BANNER
echo "${RST}${DIM}Console Bar Artificial Intelligence · desinstalación${RST}"
echo

warn "Se retirarán binarios, servicio, autostart, atajo, AJUSTES e"
warn "INFORMES de crash (~/.config/oc-drop y ~/.local/state/oc-drop)."
info "Las sesiones tmux y tu OpenCode general no se tocan."
if [ -t 0 ]; then
  read -r -p "¿Desinstalar ConBarAI? [s/N] " resp
  if [[ ! "$resp" =~ ^[sS]$ ]]; then
    info "Cancelado; no se ha tocado nada."
    exit 0
  fi
fi
echo

pkill -f "oc-dr[o]p" 2>/dev/null
pkill -f "oc-tra[y]" 2>/dev/null
pkill -f "oc-crash-wat[c]h" 2>/dev/null
ok "Procesos detenidos"

# Retira el servicio de usuario antes de borrar sus ficheros
if command -v systemctl >/dev/null 2>&1; then
  systemctl --user disable --now oc-crash-watch.service >/dev/null 2>&1 || true
  rm -f "$HOME/.config/systemd/user/oc-crash-watch.service"
  systemctl --user daemon-reload >/dev/null 2>&1 || true
  ok "Servicio oc-crash-watch retirado"
fi

rm -f "$HOME/.local/bin/oc-drop" "$HOME/.local/bin/oc-tray" \
      "$HOME/.local/bin/oc-crash-watch" "$HOME/.local/bin/oc-crash-run"
rm -rf "$HOME/.local/share/oc-drop" "$HOME/.config/oc-drop" "$HOME/.local/state/oc-drop"
rm -f "$HOME/.config/autostart/oc-tray.desktop"
rm -f "$HOME/.local/share/applications/conbarai.desktop"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
ok "Binarios, datos, autostart y entrada del menú retirados"

# Retira solo la entrada custom0 de ConBarAI, conservando otros atajos
python3 - <<'EOF'
import re
import subprocess

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
CHILD = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
KEY = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"


def gset(schema, key, value):
    subprocess.run(["gsettings", "set", schema, key, value], check=False)


def gget(schema, key):
    out = subprocess.run(["gsettings", "get", schema, key], capture_output=True, text=True)
    return out.stdout.strip()


raw = gget(SCHEMA, "custom-keybindings") or "@as []"
items = [
    i for i in re.findall(r"['\"]([^'\"]+)['\"]", raw)
    if re.match(r"^/org/gnome/settings-daemon/plugins/media-keys/", i)
]
if KEY in items:
    items = [i for i in items if i != KEY]
    gset(SCHEMA, "custom-keybindings", "[" + ", ".join(f"'{i}'" for i in items) + "]")
    for k in ("name", "command", "binding"):
        gset(f"{CHILD}:{KEY}", k, "")
    print("[OK] Atajo de teclado retirado")
EOF

echo
ok "${NEG}ConBarAI desinstalado${RST}. Hasta pronto."
