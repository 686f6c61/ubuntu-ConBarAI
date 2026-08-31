"""Tests unitarios de oc_common (sin tocar los ajustes reales del usuario)."""

import json
import py_compile
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oc_common as OC


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Home aislado: ajustes, estado y carpetas base fuera del usuario real."""
    home = tmp_path / "home"
    (home / ".config/oc-drop").mkdir(parents=True)
    (home / ".local/state/oc-drop").mkdir(parents=True)
    (home / "Documentos/ConBarAI").mkdir(parents=True)
    monkeypatch.setattr(OC, "HOME", home)
    monkeypatch.setattr(OC, "SETTINGS_FILE", home / ".config/oc-drop/settings.json")
    monkeypatch.setattr(OC, "STATE_DIR", home / ".local/state/oc-drop")
    monkeypatch.setattr(OC, "ALERTS_DIR", home / ".local/state/oc-drop/alerts")
    monkeypatch.setattr(OC, "SESSIONS_FILE", home / ".local/state/oc-drop/sessions.json")
    return home


# ---------- validate_session ----------


def test_validate_session_acepta_nombres_normales():
    for name in ("oc", "oc-mi-proyecto", "oc-test_1", "a"):
        assert OC.validate_session(name) == name


@pytest.mark.parametrize(
    "bad",
    [
        "",
        None,
        "Oc-mayuscula",
        "con espacios",
        "con/punto",
        "con:punto",
        "-empieza-guion",
        "a" * 50,
        "con'comilla",
        "con;punto_y_coma",
        "injection'; rm -rf ~; '",
        "con$variable",
        "con\\barra",
    ],
)
def test_validate_session_rechaza_invalidos(bad):
    with pytest.raises(ValueError):
        OC.validate_session(bad)


# ---------- slug / session_for_workdir ----------


def test_slug_basico():
    assert OC.slug("Mi Proyecto!") == "mi-proyecto"
    assert OC.slug("") == "sesion"
    assert OC.slug("---") == "sesion"


def test_session_for_workdir_default(fake_home):
    assert OC.session_for_workdir(str(fake_home / "Documentos/ConBarAI")) == "oc"


def test_session_for_workdir_otra_carpeta(fake_home):
    assert OC.session_for_workdir("/tmp/x/Mi Proyecto") == "oc-mi-proyecto"


# ---------- format_usage ----------


def test_format_usage_vacio():
    assert OC.format_usage(0, 0) == ""
    assert OC.format_usage(0, None) == ""


def test_format_usage_tokens():
    assert OC.format_usage(0, 10342) == "10.3k tok"
    assert OC.format_usage(0, 999) == "999 tok"
    assert OC.format_usage(0, 1_500_000) == "1.5M tok"


def test_format_usage_con_coste():
    assert OC.format_usage(0.42, 1_500_000) == "$0.42 · 1.5M tok"


# ---------- load_settings: límites ----------


def test_load_settings_clamps(fake_home):
    OC.SETTINGS_FILE.write_text(
        json.dumps({"width": 5, "height": 0.01, "opacity": 0.1, "font_size": 100})
    )
    s = OC.load_settings()
    assert s["width"] == 0.90
    assert s["height"] == 0.20
    assert s["opacity"] == 0.50
    assert s["font_size"] == 16


def test_load_settings_json_roto_devuelve_defaults(fake_home):
    OC.SETTINGS_FILE.write_text("{esto no es json")
    s = OC.load_settings()
    assert s["width"] == OC.DEFAULTS["width"]
    assert s["theme"] == "tokyo-night"


def test_load_settings_archivo_inexistente_devuelve_defaults(fake_home):
    s = OC.load_settings()
    assert s == OC.DEFAULTS


# ---------- save_settings: permisos ----------


def test_save_settings_permisos_0600(fake_home):
    OC.save_settings({"theme": "dracula"})
    s = OC.load_settings()
    assert s["theme"] == "dracula"
    assert (OC.SETTINGS_FILE.stat().st_mode & 0o777) == 0o600


# ---------- alertas por sesión ----------


def test_alertas_ciclo_completo(fake_home):
    OC.clear_alert("oc")
    assert "oc" not in OC.alerts_present()
    # marcador directo (ensure_hooks lo crea el hook de tmux vía touch)
    OC._private_dir(OC.ALERTS_DIR)
    (OC.ALERTS_DIR / "oc.alert").write_text("x")
    assert "oc" in OC.alerts_present()
    OC.clear_alert("oc")
    assert "oc" not in OC.alerts_present()


def test_clear_alert_valida_nombre(fake_home):
    with pytest.raises(ValueError):
        OC.clear_alert("mal; nombre")


# ---------- record / session_workdirs ----------


def test_record_session_y_lectura(fake_home):
    OC.record_session("oc-x", "/tmp/x")
    assert OC.session_workdirs() == {"oc-x": "/tmp/x"}


def test_record_session_rechaza_nombre(fake_home):
    with pytest.raises(ValueError):
        OC.record_session("mal nombre", "/tmp")


# ---------- default_workdir ----------


def test_default_workdir_localizado(fake_home):
    assert OC.default_workdir({}) == str(fake_home / "Documentos/ConBarAI")


def test_default_workdir_respet_ajuste(fake_home, tmp_path):
    other = tmp_path / "otro"
    other.mkdir()
    assert OC.default_workdir({"workdir": str(other)}) == str(other)


# ---------- autostart ----------


def test_set_autostart_crea_y_retira(fake_home, monkeypatch):
    autostart = fake_home / ".config/autostart/oc-tray.desktop"
    monkeypatch.setattr(OC, "AUTOSTART_FILE", autostart)
    assert OC.set_autostart(True)
    assert OC.autostart_enabled()
    assert "oc-tray" in autostart.read_text()
    assert not OC.set_autostart(False)
    assert not OC.autostart_enabled()
    assert not autostart.exists()


# ---------- ensure_project_skill ----------


def test_ensure_project_skill_siembra_enlace(fake_home, tmp_path, monkeypatch):
    canon = tmp_path / "appskills" / "ubuntu-operator"
    canon.mkdir(parents=True)
    (canon / "SKILL.md").write_text("---\nname: ubuntu-operator\n---\nx\n")
    monkeypatch.setattr(OC, "APP_SKILLS_DIR", tmp_path / "appskills")
    work = fake_home / "Documentos/ConBarAI"
    assert OC.ensure_project_skill(str(work)) is True
    dst = work / ".opencode/skills/ubuntu-operator/SKILL.md"
    assert dst.is_symlink()
    assert dst.resolve() == (canon / "SKILL.md").resolve()
    # idempotente: no falla al repetir
    assert OC.ensure_project_skill(str(work)) is True


def test_ensure_project_skill_sin_canonica_no_crea(fake_home, tmp_path, monkeypatch):
    monkeypatch.setattr(OC, "APP_SKILLS_DIR", tmp_path / "vacio")
    work = fake_home / "Documentos/ConBarAI"
    assert OC.ensure_project_skill(str(work)) is False
    assert not (work / ".opencode").exists()


# ---------- deteccion de crashes ----------


def test_parse_line_oom():
    ev = OC.parse_journal_crash_line(
        "kernel: Out of memory: Killed process 4242 (firefox) total-vm:1"
    )
    assert ev == {
        "kind": "oom",
        "program": "firefox",
        "pid": "4242",
        "raw": "kernel: Out of memory: Killed process 4242 (firefox) total-vm:1",
    }


def test_parse_line_segfault():
    ev = OC.parse_journal_crash_line("host kernel: gimp[3001]: segfault at 0 ip 0x0")
    assert ev is not None
    assert ev["kind"] == "segfault" and ev["program"] == "gimp" and ev["pid"] == "3001"


def test_parse_line_no_crash():
    assert OC.parse_journal_crash_line("kernel: usb 1-1: new high-speed device") is None


def test_parse_block_filtra_maquinaria_propia():
    sample = (
        "kernel: gimp[1]: segfault at 0\n"
        "kernel: oc-drop[9]: segfault at 0\n"
        "kernel: Out of memory: Killed process 5 (xterm)\n"
    )
    progs = {e["program"] for e in OC.parse_journal_crash(sample)}
    assert progs == {"gimp", "xterm"}
    assert "oc-drop" not in progs


def test_crash_mute_roundtrip(tmp_path, monkeypatch):
    ignore = tmp_path / "ignore"
    ignore.mkdir(parents=True)
    monkeypatch.setattr(OC, "CRASH_IGNORE_DIR", ignore)
    assert OC.crash_muted("firefox") is False
    assert OC.crash_mute("firefox", True) is True
    assert OC.crash_muted("firefox") is True
    assert "firefox" in OC.crash_muted_list()
    assert OC.crash_mute("firefox", False) is True
    assert OC.crash_muted("firefox") is False


# ---------- versión de la instalación ----------


def test_app_version_coincide_con_pyproject():
    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    assert f'version = "{OC.app_version()}"' in text
    assert OC.app_version() != ""


def test_app_version_sin_pyproject_devuelve_vacio(monkeypatch, tmp_path):
    monkeypatch.setattr(OC, "__file__", str(tmp_path / "oc_common.py"))
    assert OC.app_version() == ""


# ---------- ajustes de la 1.4.0 ----------


def test_defaults_incluyen_ajustes_140():
    assert OC.DEFAULTS["diag_pos"] == "side"
    assert OC.DEFAULTS["continue_session"] is True
    assert OC.DEFAULTS["crash_watch"] is True
    assert OC.DEFAULTS["crash_analyze"] is True


def test_diag_pos_persiste_en_ajustes(fake_home):
    data = OC.load_settings()
    data["diag_pos"] = "below"
    OC.save_settings(data)
    assert OC.load_settings()["diag_pos"] == "below"


def test_scripts_compilan(tmp_path):
    root = Path(__file__).resolve().parents[1]
    for name in ("oc-drop", "oc-tray", "oc-crash-watch", "oc-crash-run"):
        py_compile.compile(
            str(root / name), cfile=str(tmp_path / f"{name}.pyc"), doraise=True
        )


# ---------- petición de análisis pendiente (watcher -> panel) ----------


def test_scripts_bash_validos():
    root = Path(__file__).resolve().parents[1]
    for name in ("conbarai", "install.sh", "uninstall.sh", "scripts/build-appimage.sh"):
        subprocess.run(["bash", "-n", str(root / name)], check=True)


def test_crash_pending_roundtrip(tmp_path, monkeypatch):
    crash = tmp_path / "crash"
    monkeypatch.setattr(OC, "CRASH_DIR", crash)
    monkeypatch.setattr(OC, "CRASH_PENDING", crash / "pending.json")
    monkeypatch.setattr(OC, "CRASH_IGNORE_DIR", crash / "ignore")
    ev = {"program": "gimp", "kind": "segfault", "pid": "123", "raw": "linea"}
    assert OC.write_crash_pending(ev) is True
    data, ts = OC.take_crash_pending(0.0)
    assert data["program"] == "gimp"
    assert ts > 0
    otra, ts2 = OC.take_crash_pending(ts)
    assert otra is None
    assert ts2 == ts
    OC.clear_crash_pending()
    assert not (crash / "pending.json").exists()


def test_crash_prompt_contiene_evidencia_y_formato():
    ev = {"kind": "oom", "program": "firefox", "pid": "42", "raw": "Killed process"}
    prompt = OC.crash_prompt(ev)
    assert "firefox" in prompt
    assert "Killed process" in prompt
    for seccion in ("Qué pasó", "Evidencia", "Causa probable", "Arreglo", "Cómo evitarlo"):
        assert seccion in prompt


def test_take_stale_pending_reciente_no_la_consume(tmp_path, monkeypatch):
    crash = tmp_path / "crash"
    monkeypatch.setattr(OC, "CRASH_DIR", crash)
    monkeypatch.setattr(OC, "CRASH_PENDING", crash / "pending.json")
    monkeypatch.setattr(OC, "CRASH_IGNORE_DIR", crash / "ignore")
    OC.write_crash_pending({"program": "gimp", "kind": "segfault", "raw": "x"})
    assert OC.take_stale_pending(20) is None
    assert (crash / "pending.json").exists()


def test_take_stale_pending_huerfana_la_consume(tmp_path, monkeypatch):
    crash = tmp_path / "crash"
    crash.mkdir()
    pending = crash / "pending.json"
    monkeypatch.setattr(OC, "CRASH_PENDING", pending)
    pending.write_text(json.dumps({"program": "gimp", "ts": time.time() - 100}))
    data = OC.take_stale_pending(20)
    assert data["program"] == "gimp"
    assert not pending.exists()
    assert OC.take_stale_pending(20) is None


# ---------- apagado ordenado vs de golpe ----------


class _FakeRun:
    def __init__(self, stdout, returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_previous_boot_clean_apagado_ordenado(monkeypatch):
    tail = (
        "Reached target poweroff.target - System Power Off.\n"
        "Shutting down.\n"
        "Journal stopped\n"
    )
    monkeypatch.setattr(OC.subprocess, "run", lambda *a, **k: _FakeRun(tail))
    assert OC.previous_boot_clean() is True


def test_previous_boot_clean_solo_reached_target(monkeypatch):
    tail = "Reached target shutdown.target - System Shutdown.\n"
    monkeypatch.setattr(OC.subprocess, "run", lambda *a, **k: _FakeRun(tail))
    assert OC.previous_boot_clean() is True


def test_previous_boot_clean_corte_de_golpe(monkeypatch):
    tail = (
        "gnome-shell[2412]: meta_window_actor...\n"
        "kernel: snap-store[1241]: segfault at 58875 ip 000075c1\n"
        "NetworkManager[988]: <info> dhcp4: state changed\n"
    )
    monkeypatch.setattr(OC.subprocess, "run", lambda *a, **k: _FakeRun(tail))
    assert OC.previous_boot_clean() is False


def test_previous_boot_clean_journal_ilegible(monkeypatch):
    monkeypatch.setattr(OC.subprocess, "run", lambda *a, **k: _FakeRun("", 1))
    assert OC.previous_boot_clean() is None
