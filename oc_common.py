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
APP_SKILLS_DIR = ICON_DIR / "skills"  # copia canónica instalada por install.sh
BUNDLED_SKILL = "ubuntu-operator"
OPENCODE_DB = HOME / ".local/share/opencode/opencode.db"
AUTOSTART_FILE = HOME / ".config/autostart/oc-tray.desktop"
DESKTOP_FILE = HOME / ".local/share/applications/conbarai.desktop"

DEFAULT_SESSION = "oc"

REPO_URL = "https://github.com/686f6c61/ubuntu-ConBarAI"


def app_version():
    """Versión instalada, leída del pyproject.toml que acompaña al código
    (la instalación enlaza los binarios al repo, así que viaja junto)."""
    try:
        text = (Path(__file__).resolve().parent / "pyproject.toml").read_text()
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
        if m:
            return m.group(1)
    except OSError:
        pass
    return ""

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
    "crash_watch": True,
    "crash_dedupe": 60,
    "crash_poll": 8,
    "crash_analyze": True,
    "diag_pos": "side",  # "side" = al lado del panel; "below" = debajo
    # True: opencode arranca con -c (continúa la última sesión, p. ej. tras
    # un reinicio); False: siempre empieza sin contexto arrastrado
    "continue_session": True,
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


def ensure_project_skill(workdir, skill=BUNDLED_SKILL):
    """Enlaza la skill canónica de la app en <workdir>/.opencode/skills/<skill>/
    para que SOLO el OpenCode que arranca en ese workdir la cargue (skill de
    proyecto). Fuera de esa carpeta, ningún otro OpenCode la ve."""
    src = APP_SKILLS_DIR / skill / "SKILL.md"
    if not src.is_file():
        return False
    dst_dir = Path(workdir) / ".opencode" / "skills" / skill
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "SKILL.md"
        if dst.is_symlink():
            if os.path.realpath(dst) != os.path.realpath(src):
                dst.unlink()
                dst.symlink_to(src)
        elif not dst.exists():
            dst.symlink_to(src)
        return True
    except OSError as e:
        log("skill no sembrada en workdir:", e)
        return False


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


# ---------- detección de crashes del sistema (Ubuntu / journald) ----------
#
# El usuario está en el grupo `adm`, así que puede leer el journal del kernel
# sin sudo. Detectamos por `journalctl -k` (no por /var/crash, que apport deja
# root:whoopsie 0640 y no se lee sin privilegios).

CRASH_DIR = STATE_DIR / "crash"
CRASH_STATE = CRASH_DIR / "watch.json"
CRASH_IGNORE_DIR = CRASH_DIR / "ignore"

# Señales de crash en el journal del kernel -> (tipo, regex).
_CRASH_PATTERNS = [
    ("oom", re.compile(r"Killed process (\d+) \(([^)]+)\)")),
    (
        "segfault",
        re.compile(
            r"\b([A-Za-z0-9_.+\-]{1,64})\[(\d+)\]: "
            r"(segfault|general protection fault|traps:|int3|Code: [0-9a-f])"
        ),
    ),
    ("gpu", re.compile(r"(NVRM:.*Xid|drm.*(?:reset|hang)|amdgpu.*reset)")),
    (
        "hung",
        re.compile(r"task:([A-Za-z0-9_.+\-]{1,64}).*blocked for more than"),
    ),
]

# Nada de announcear nuestra propia maquinaria; opencode SÍ es una víctima
# reportable (puede caer y querer saber por qué).
_SELF_TOOLS = ("oc-drop", "oc-tray", "oc-crash-watch", "oc-crash-run")


def is_own_tool(name):
    return str(name or "").split("/")[-1] in _SELF_TOOLS


def parse_journal_crash_line(line):
    """Devuelve dict(kind, program, pid, raw) o None si no es un crash."""
    for kind, rx in _CRASH_PATTERNS:
        m = rx.search(line)
        if not m:
            continue
        g = m.groups()
        if kind == "oom":
            pid, program = g[0], g[1]
        elif kind == "hung":
            pid, program = "", g[0]
        elif kind == "segfault":
            program, pid = g[0], g[1]
        else:  # gpu: sin programa concreto
            pid, program = "", "kernel/gpu"
        return {"kind": kind, "program": program, "pid": pid, "raw": line.rstrip()}
    return None


def parse_journal_crash(text):
    events = []
    for line in text.splitlines():
        ev = parse_journal_crash_line(line)
        if ev and not is_own_tool(ev["program"]):
            events.append(ev)
    return events


# Marcadores de un apagado ordenado al final del journal del arranque
# anterior (systemd los escribe siempre en inglés). Si no aparece ninguno,
# el arranque terminó de golpe (panic, corte de luz, cuelgue).
CLEAN_SHUTDOWN_RE = re.compile(
    r"Journal stopped"
    r"|Shutting down\."
    r"|systemd-shutdow"
    r"|Reached target (?:[a-z-]+\.target - )?(?:System )?"
    r"(?:Shutdown|Power-?Off|Reboot|Halt)",
    re.I,
)


def previous_boot_clean():
    """True si el arranque anterior terminó con un apagado ordenado,
    False si acabó de golpe, None si el journal no permite saberlo."""
    try:
        out = subprocess.run(
            ["journalctl", "-b", "-1", "-n", "60", "-o", "cat", "--no-pager"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        return bool(CLEAN_SHUTDOWN_RE.search(out.stdout))
    except (OSError, subprocess.SubprocessError):
        return None


def boot_id():
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return ""


def load_crash_state():
    try:
        return json.loads(CRASH_STATE.read_text())
    except (OSError, ValueError):
        return {"boot_id": "", "watermark": ""}


def save_crash_state(state):
    try:
        _private_dir(CRASH_DIR)
        _private_dir(CRASH_IGNORE_DIR)
        CRASH_STATE.write_text(json.dumps(state))
        CRASH_STATE.chmod(0o600)
        return True
    except OSError as e:
        log("estado de crashes no guardado:", e)
        return False


def crash_muted(program):
    try:
        safe = re.sub(r"[^A-Za-z0-9_.+-]", "_", str(program))[:64] or "unknown"
        return (CRASH_IGNORE_DIR / safe).exists()
    except OSError:
        return False


def crash_mute(program, on=True):
    safe = re.sub(r"[^A-Za-z0-9_.+-]", "_", str(program))[:64] or "unknown"
    _private_dir(CRASH_DIR)
    _private_dir(CRASH_IGNORE_DIR)
    flag = CRASH_IGNORE_DIR / safe
    try:
        if on:
            flag.write_text("")
            flag.chmod(0o600)
        elif flag.exists():
            flag.unlink()
        return True
    except OSError:
        return False


def crash_muted_list():
    try:
        return (
            sorted(p.name for p in CRASH_IGNORE_DIR.iterdir()) if CRASH_IGNORE_DIR.is_dir() else []
        )
    except OSError:
        return []


def journal_since(kernel_only, watermark, extra_args=()):
    """journalctl --since <watermark> (vacío = desde arranque) como texto."""
    args = ["journalctl", "--no-pager", "-o", "short-iso"]
    if kernel_only:
        args.append("-k")
    if watermark:
        args += ["--since", watermark]
    else:
        args += ["-b"]
    args += list(extra_args)
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        log("journalctl falló:", e)
        return ""


def detect_new_crashes(watermark):
    """Crashes del kernel/journal posteriores a `watermark`."""
    text = journal_since(True, watermark)
    return parse_journal_crash(text)


CRASH_PENDING = CRASH_DIR / "pending.json"

# Recetas (prompt) para el agente, en español, formato Omarchy.
CRASH_PROMPT = """Se ha detectado un crash en este equipo Ubuntu y quiero saber por qué.

Hechos recogidos por ConBarAI desde el journal del kernel:
- tipo: {kind}
- programa: {program}
- pid: {pid}

Evidencia:
```
{evidence}
```

Usa la skill `ubuntu-operator` (sección de *crash forensics* de Ubuntu):
evidencia primero, contrasta `journalctl -k` y, si aporta, `/var/crash`.
DIAGNÓSTICO SOLO: no modifiques nada. Sé breve: como mucho 3 o 4 comandos de
lectura; si con la evidencia ya está claro, respóndeme sin ejecutar nada.

Devuelve el informe en ESPAÑOL, corto, con este formato:
1. Qué pasó — una frase (qué murió, cuándo, señal/evento).
2. Evidencia — solo las líneas clave (tacha secretos).
3. Causa probable — 1-3 frases; di qué es PROBADO y qué INFERIDO.
4. Arreglo — hasta 2 opciones (más segura primero) con su reversión.
5. Cómo evitarlo — una línea."""


def crash_prompt(ev):
    return CRASH_PROMPT.format(
        kind=ev.get("kind", "desconocido"),
        program=ev.get("program", "desconocido"),
        pid=ev.get("pid") or "n/d",
        evidence=(ev.get("raw") or "(sin evidencia)").strip(),
    )


def write_crash_pending(ev):
    """Deja una petición para que un panel visible lance al agente en directo."""
    try:
        _private_dir(CRASH_DIR)
        CRASH_PENDING.write_text(
            json.dumps(
                {
                    "program": ev.get("program"),
                    "kind": ev.get("kind"),
                    "pid": ev.get("pid"),
                    "raw": ev.get("raw"),
                    "ts": time.time(),
                }
            )
        )
        CRASH_PENDING.chmod(0o600)
        return True
    except OSError as e:
        log("no se pudo dejar la petición de análisis:", e)
        return False


def take_crash_pending(seen_ts):
    """Devuelve la petición si es más nueva que `seen_ts`; no la borra."""
    try:
        data = json.loads(CRASH_PENDING.read_text())
    except (OSError, ValueError):
        return None, seen_ts
    ts = float(data.get("ts", 0))
    if ts > seen_ts:
        return data, ts
    return None, seen_ts


def clear_crash_pending():
    try:
        if CRASH_PENDING.exists():
            CRASH_PENDING.unlink()
    except OSError:
        pass


def take_stale_pending(max_age_s):
    """Petición que ningún panel visible recogió en `max_age_s`: la consume
    y la devuelve para que el vigía la analice en headless. None si no hay
    petición o aún es reciente (un panel visible puede estar a punto de
    recogerla)."""
    try:
        data = json.loads(CRASH_PENDING.read_text())
        ts = float(data.get("ts", 0))
    except (OSError, ValueError, TypeError):
        return None
    if time.time() - ts < max_age_s:
        return None
    clear_crash_pending()
    return data


CRASH_CONFIG = ICON_DIR / "conbarai-crash.json"

# Herramientas de SOLO LECTURA que el análisis de crash puede ejecutar.
_CRASH_RO_CMDS = [
    "journalctl",
    "coredumpctl",
    "apport-cli",
    "apport-retrace",
    "whoopsie",
    "dmesg",
    "free",
    "uptime",
    "last",
    "who",
    "ls",
    "cat",
    "grep",
    "head",
    "tail",
    "awk",
    "sort",
    "uniq",
    "wc",
    "smartctl",
    "sensors",
    "systemctl",
    "loginctl",
    "nvidia-smi",
    "lscpu",
    "ip",
    "nmcli",
    "resolvectl",
    "opencode",
    "uname",
    "id",
    "dpkg",
    "apt-mark",
    "basename",
    "dirname",
    "readlink",
    "stat",
    "du",
    "find",
]


def crash_config():
    """Config de opencode para el análisis: carga la skill y deniega todo lo
    que escriba; solo permite lecturas de diagnóstico."""
    bash = {f"{c} *": "allow" for c in _CRASH_RO_CMDS}
    bash["*"] = "deny"
    data = {
        "$schema": "https://opencode.ai/config.json",
        "skills": {"paths": [str(APP_SKILLS_DIR)]},
        "permission": {
            "edit": "deny",
            "bash": bash,
            "webfetch": "deny",
            "external_directory": {"*": "allow"},
        },
    }
    try:
        _private_dir(ICON_DIR)
        CRASH_CONFIG.write_text(json.dumps(data, indent=2))
        CRASH_CONFIG.chmod(0o600)
        return str(CRASH_CONFIG)
    except OSError as e:
        log("no se pudo escribir la config de crash:", e)
        return None
