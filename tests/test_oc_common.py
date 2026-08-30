"""Tests unitarios de oc_common (sin tocar los ajustes reales del usuario)."""

import json
import sys
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
