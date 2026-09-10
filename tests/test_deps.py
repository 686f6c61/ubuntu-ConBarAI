"""Regresión del issue #1: dependencias cairo y shebang del intérprete.

En Ubuntu 26.04 limpio faltaban `python3-cairo` y `python3-gi-cairo`
(`KeyError: 'could not find foreign type Region'`) y `#!/usr/bin/env
python3` cogía el Python de Homebrew, que no ve los paquetes apt."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EJECUTABLES = ["oc-drop", "oc-tray", "oc-crash-run", "oc-crash-watch"]
DEPS_CAIRO = ["python3-cairo", "python3-gi-cairo"]


@pytest.mark.parametrize("nombre", EJECUTABLES)
def test_shebang_usa_python_del_sistema(nombre):
    """Los paquetes apt solo los ve /usr/bin/python3; nada de env python3."""
    primera = (ROOT / nombre).read_text(encoding="utf-8").splitlines()[0]
    assert primera == "#!/usr/bin/python3", f"{nombre}: {primera!r}"


def _deps_install_sh():
    texto = (ROOT / "install.sh").read_text(encoding="utf-8")
    m = re.search(r"^DEPS=\((.*)\)$", texto, re.M)
    assert m, "install.sh sin línea DEPS=(...)"
    return m.group(1).split()


@pytest.mark.parametrize("paquete", DEPS_CAIRO)
def test_install_sh_exige_paquetes_cairo(paquete):
    assert paquete in _deps_install_sh()


@pytest.mark.parametrize("paquete", DEPS_CAIRO)
@pytest.mark.parametrize(
    "fichero", ["README.md", "README.en.md", "scripts/build-appimage.sh"]
)
def test_docs_y_appimage_nombran_paquetes_cairo(fichero, paquete):
    assert paquete in (ROOT / fichero).read_text(encoding="utf-8")


def test_apply_input_region_captura_keyerror():
    """Sin python3-gi-cairo PyGObject lanza KeyError; no debe escapar."""
    texto = (ROOT / "oc-drop").read_text(encoding="utf-8")
    cuerpo = texto.split("def apply_input_region(self):", 1)[1]
    cuerpo = cuerpo.split("def ", 1)[0]
    assert "KeyError" in cuerpo
