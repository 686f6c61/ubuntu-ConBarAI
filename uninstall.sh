#!/usr/bin/env bash
# ConBarAI - desinstalación
set -uo pipefail

pkill -f "oc-dr[o]p" 2>/dev/null
pkill -f "oc-crash-wat[c]h" 2>/dev/null
# Detira el servicio de usuario antes de borrar sus ficheros
if command -v systemctl >/dev/null 2>&1; then
  systemctl --user disable --now oc-crash-watch.service >/dev/null 2>&1 || true
  rm -f "$HOME/.config/systemd/user/oc-crash-watch.service"
  systemctl --user daemon-reload >/dev/null 2>&1 || true
fi
rm -f "$HOME/.local/bin/oc-drop" "$HOME/.local/bin/oc-tray" "$HOME/.local/bin/oc-crash-watch"
rm -rf "$HOME/.local/share/oc-drop" "$HOME/.config/oc-drop" "$HOME/.local/state/oc-drop"
rm -f "$HOME/.config/autostart/oc-tray.desktop"

# Retira solo la entrada custom0 de ConBarAI, conservando otros atajos
python3 - <<'EOF'
import subprocess

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
CHILD = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
KEY = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0/"


def gset(schema, key, value):
    subprocess.run(["gsettings", "set", schema, key, value], check=False)


def gget(schema, key):
    out = subprocess.run(["gsettings", "get", schema, key], capture_output=True, text=True)
    return out.stdout.strip()


import re

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

echo "[OK] ConBarAI desinstalado"
