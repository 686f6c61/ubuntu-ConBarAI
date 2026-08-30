"""oc_common: recursos compartidos de ConBarAI (oc-drop y oc-tray)."""

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
SETTINGS_FILE = HOME / ".config/oc-drop/settings.json"
STATE_DIR = HOME / ".local/state/oc-drop"
ALERTS_DIR = STATE_DIR / "alerts"
SESSIONS_FILE = STATE_DIR / "sessions.json"
ICON_DIR = HOME / ".local/share/oc-drop"
OPENCODE_DB = HOME / ".local/share/opencode/opencode.db"
AUTOSTART_FILE = HOME / ".config/autostart/oc-tray.desktop"
DESKTOP_FILE = HOME / ".local/share/applications/conbarai.desktop"

DEFAULT_SESSION = "oc"

DEFAULTS = {
    "autohide": True,
    "autostart": True,
    "workdir": "",  # vacío = carpeta de ejecución (~/Documentos o ~/Documents + ConBarAI)
    "width": 0.34,
    "height": 0.62,
    "opacity": 0.97,
    "keybinding": "<Super>Return",
    "terminal": "auto",
    "theme": "tokyo-night",
    "font": "auto",
    "font_size": 10,
}

AUTOSTART_TEMPLATE = """[Desktop Entry]
Type=Application
Name=OpenCode tray
Comment=Icono de OpenCode en la barra superior (ConBarAI)
Exec={home}/.local/bin/oc-tray
Terminal=false
X-GNOME-Autostart-enabled=true
Categories=Utility;
"""


def set_autostart(enabled):
    """Registra o retira el arranque automático del tray al iniciar sesión."""
    try:
        if enabled:
            AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
            AUTOSTART_FILE.write_text(AUTOSTART_TEMPLATE.format(home=str(HOME)))
        else:
            AUTOSTART_FILE.unlink(missing_ok=True)
        return enabled
    except OSError as e:
        log("no se pudo ajustar el autostart:", e)
        return autostart_enabled()


def autostart_enabled():
    return AUTOSTART_FILE.exists()


# Los nombres de sesión terminan interpolados en rutas y hooks de tmux:
# charset cerrado, sin shell metacharacters.
SESSION_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")

THEMES = {
    "tokyo-night": {
        "bg": "#1a1b26",
        "bg_head": "#16161e",
        "fg": "#c0caf5",
        "fg_dim": "#565f89",
        "green": "#9ece6a",
        "red": "#f7768e",
        "accent": "#7aa2f7",
        "yellow": "#e0af68",
        "border": "rgba(192, 202, 245, 0.10)",
        "palette": [
            "#15161e",
            "#f7768e",
            "#9ece6a",
            "#e0af68",
            "#7aa2f7",
            "#bb9af7",
            "#7dcfff",
            "#a9b1d6",
            "#414868",
            "#f7768e",
            "#9ece6a",
            "#e0af68",
            "#7aa2f7",
            "#bb9af7",
            "#7dcfff",
            "#c0caf5",
        ],
    },
    "catppuccin": {
        "bg": "#1e1e2e",
        "bg_head": "#181825",
        "fg": "#cdd6f4",
        "fg_dim": "#6c7086",
        "green": "#a6e3a1",
        "red": "#f38ba8",
        "accent": "#89b4fa",
        "yellow": "#f9e2af",
        "border": "rgba(205, 214, 244, 0.10)",
        "palette": [
            "#45475a",
            "#f38ba8",
            "#a6e3a1",
            "#f9e2af",
            "#89b4fa",
            "#f5c2e7",
            "#94e2d5",
            "#bac2de",
            "#585b70",
            "#f38ba8",
            "#a6e3a1",
            "#f9e2af",
            "#89b4fa",
            "#f5c2e7",
            "#94e2d5",
            "#a6adc8",
        ],
    },
    "dracula": {
        "bg": "#282a36",
        "bg_head": "#21222c",
        "fg": "#f8f8f2",
        "fg_dim": "#6272a4",
        "green": "#50fa7b",
        "red": "#ff5555",
        "accent": "#bd93f9",
        "yellow": "#f1fa8c",
        "border": "rgba(248, 248, 242, 0.10)",
        "palette": [
            "#21222c",
            "#ff5555",
            "#50fa7b",
            "#f1fa8c",
            "#bd93f9",
            "#ff79c6",
            "#8be9fd",
            "#f8f8f2",
            "#6272a4",
            "#ff5555",
            "#50fa7b",
            "#f1fa8c",
            "#bd93f9",
            "#ff79c6",
            "#8be9fd",
            "#ffffff",
        ],
    },
    "gruvbox": {
        "bg": "#282828",
        "bg_head": "#1d2021",
        "fg": "#ebdbb2",
        "fg_dim": "#928374",
        "green": "#b8bb26",
        "red": "#fb4934",
        "accent": "#83a598",
        "yellow": "#fabd2f",
        "border": "rgba(235, 219, 178, 0.10)",
        "palette": [
            "#3c3836",
            "#fb4934",
            "#b8bb26",
            "#fabd2f",
            "#83a598",
            "#d3869b",
            "#8ec07c",
            "#ebdbb2",
            "#504945",
            "#fb4934",
            "#b8bb26",
            "#fabd2f",
            "#83a598",
            "#d3869b",
            "#8ec07c",
            "#fbf1c7",
        ],
    },
}


def log(*parts):
    """Diagnóstico a stderr: los lanzadores lo redirigen al log de sesión."""
    print("[conbarai]", *parts, file=sys.stderr, flush=True)


def validate_session(name):
    """Valida el nombre de sesión tmux (charset cerrado). Lanza ValueError."""
    if not SESSION_RE.match(name or ""):
        raise ValueError(f"Nombre de sesión no válido: {name!r}")
    return name


def _private_dir(path, mode=0o700):
    """Crea (y ajusta) un directorio privado del usuario."""
    try:
        path.mkdir(parents=True, exist_ok=True, mode=mode)
        os.chmod(path, mode)
    except OSError as e:
        log("no se pudo preparar", path, ":", e)
    return path


def load_settings():
    data = dict(DEFAULTS)
    try:
        raw = json.loads(SETTINGS_FILE.read_text())
        if isinstance(raw, dict):
            data.update({k: v for k, v in raw.items() if v is not None})
    except (OSError, ValueError) as e:
        if SETTINGS_FILE.exists():
            log("ajustes ilegibles, uso valores por defecto:", e)
    try:
        data["width"] = min(0.90, max(0.15, float(data["width"])))
    except (TypeError, ValueError):
        data["width"] = DEFAULTS["width"]
    try:
        data["height"] = min(0.95, max(0.20, float(data["height"])))
    except (TypeError, ValueError):
        data["height"] = DEFAULTS["height"]
    try:
        data["opacity"] = min(1.0, max(0.50, float(data["opacity"])))
    except (TypeError, ValueError):
        data["opacity"] = DEFAULTS["opacity"]
    try:
        data["font_size"] = min(16, max(7, int(data["font_size"])))
    except (TypeError, ValueError):
        data["font_size"] = DEFAULTS["font_size"]
    return data


def save_settings(data):
    _private_dir(SETTINGS_FILE.parent)
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2) + "\n")
        os.chmod(SETTINGS_FILE, 0o600)
    except OSError as e:
        log("no se pudieron guardar los ajustes:", e)


def slug(name):
    clean = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    return clean or "sesion"


def default_workdir(settings=None):
    """Carpeta de ejecución: ajuste explícito o ~/Documentos|Documents/ConBarAI."""
    s = settings or load_settings()
    wd = s.get("workdir", "")
    if wd:
        wd = os.path.expanduser(wd)
        return wd if os.path.isdir(wd) else str(HOME)
    for base in ("Documentos", "Documents"):
        cand = HOME / base / "ConBarAI"
        if cand.is_dir():
            return str(cand)
    return str(HOME)


def session_for_workdir(workdir):
    if os.path.realpath(str(workdir)) == os.path.realpath(default_workdir()):
        return DEFAULT_SESSION
    return f"{DEFAULT_SESSION}-{slug(os.path.basename(str(workdir).rstrip('/')))}"


# ---------- tmux ----------


def managed_sessions():
    try:
        out = subprocess.check_output(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return [s for s in out.splitlines() if s.startswith(DEFAULT_SESSION)]
    except (OSError, subprocess.SubprocessError):
        return []


def pane_pid(session):
    validate_session(session)
    try:
        out = subprocess.check_output(
            ["tmux", "display-message", "-p", "-t", session, "#{pane_pid}"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return int(out.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


_TICK_CACHE = {}


def busy(session):
    """True/False según CPU del proceso del panel; None si aún no hay dato."""
    pid = pane_pid(session)
    now = time.monotonic()
    if not pid:
        _TICK_CACHE.pop(session, None)
        return False
    try:
        with open(f"/proc/{pid}/stat", "r") as fh:
            fields = fh.read().rsplit(") ", 1)[1].split()
        ticks = int(fields[11]) + int(fields[12])  # utime + stime
    except (OSError, ValueError, IndexError):
        _TICK_CACHE.pop(session, None)
        return False
    prev = _TICK_CACHE.get(session)
    _TICK_CACHE[session] = (ticks, now)
    if not prev:
        return None
    dt = now - prev[1]
    if dt < 0.5:
        return None
    return (ticks - prev[0]) / dt > 10  # ~10% de CPU


def ensure_hooks(session):
    """Campana del panel -> marcador de alerta + notificación del escritorio."""
    validate_session(session)
    try:
        _private_dir(ALERTS_DIR)
        marker = ALERTS_DIR / f"{session}.alert"
        hook = (
            f"run-shell 'touch {marker}; "
            f'notify-send -a OpenCode -t 3500 "OpenCode: {session}" '
            f'"Necesita tu atención"\''
        )
        subprocess.run(
            ["tmux", "set-option", "-t", session, "monitor-bell", "on"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["tmux", "set-hook", "-t", session, "alert-bell", hook],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError) as e:
        log("no se pudieron registrar los hooks de", session, ":", e)


def record_session(session, workdir):
    validate_session(session)
    try:
        _private_dir(STATE_DIR)
        data = {}
        if SESSIONS_FILE.exists():
            try:
                data = json.loads(SESSIONS_FILE.read_text())
            except (OSError, json.JSONDecodeError) as e:
                log("registro de sesiones ilegible, lo recreo:", e)
        data[session] = workdir
        SESSIONS_FILE.write_text(json.dumps(data, indent=2))
        os.chmod(SESSIONS_FILE, 0o600)
    except OSError as e:
        log("no se pudo registrar la sesión:", e)


def session_workdirs():
    try:
        data = json.loads(SESSIONS_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


# ---------- alertas (marcadores por sesión, dir privado) ----------


def alerts_present():
    try:
        markers = list(ALERTS_DIR.glob("*.alert"))
        for p in markers:
            # tmux crea el marcador con su umask; lo ajustamos a privado
            if p.stat().st_mode & 0o077:
                os.chmod(p, 0o600)
        return {p.stem for p in markers}
    except OSError:
        return set()


def clear_alert(session):
    validate_session(session)
    try:
        (ALERTS_DIR / f"{session}.alert").unlink(missing_ok=True)
    except OSError as e:
        log("no se pudo limpiar la alerta de", session, ":", e)


# ---------- consumo (tokens / coste) ----------


def usage(workdir):
    """(coste, tokens) acumulados de las sesiones de OpenCode de un directorio."""
    if not OPENCODE_DB.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{OPENCODE_DB}?mode=ro", uri=True)
        try:
            row = con.execute(
                "SELECT ifnull(sum(cost),0), "
                "ifnull(sum(tokens_input+tokens_output+tokens_reasoning+tokens_cache_write),0) "
                "FROM session WHERE directory=?",
                (str(workdir),),
            ).fetchone()
        finally:
            con.close()
        return row[0], row[1]
    except (OSError, sqlite3.Error) as e:
        log("no se pudo leer el consumo:", e)
        return None


def format_usage(cost, tokens):
    if not tokens:
        return ""
    if tokens >= 1_000_000:
        tok = f"{tokens / 1_000_000:.1f}M tok"
    elif tokens >= 1_000:
        tok = f"{tokens / 1_000:.1f}k tok"
    else:
        tok = f"{int(tokens)} tok"
    if cost:
        return f"${cost:.2f} · {tok}"
    return tok


# ---------- tipografía ----------


def detect_font(settings=None):
    s = settings or load_settings()
    want = s.get("font", "auto")
    if want and want != "auto":
        return want
    try:
        out = subprocess.check_output(
            ["fc-list", ":", "family"], text=True, stderr=subprocess.DEVNULL
        ).lower()
    except (OSError, subprocess.SubprocessError):
        return "DejaVu Sans Mono"
    if "jetbrainsmono nerd font" in out:
        return "JetBrainsMono Nerd Font"
    if "jetbrains mono" in out:
        return "JetBrains Mono"
    return "DejaVu Sans Mono"
