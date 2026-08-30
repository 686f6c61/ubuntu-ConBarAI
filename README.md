# ConBarAI

**Tu agente de IA en la barra de Ubuntu.** A un atajo de teclado, siempre
a mano, y con una misión extra: convertir los crashes de Linux en informes
con causa y arreglo.

**Web**: https://conbarai.686f6c61.dev

[English](README.en.md) · Español

---

**ConBarAI** (**Con**sole **Bar** **A**rtificial **I**ntelligence) integra
[OpenCode](https://opencode.ai) en el escritorio: un panel flotante estilo
Omarchy que aparece bajo la barra de GNOME al pulsar `Súper+Intro` y se
aparta al volver a pulsar. Sin ventanas nuevas, sin perder el flujo.

![Panel de ConBarAI con OpenCode](screenshots/captura-panel.png)

## Por qué ConBarAI

**Siempre a una tecla.** El panel vive en `tmux`: ocúltalo, ciérralo o
reinicia el equipo — OpenCode sigue ahí y retoma la conversación donde
estaba (`opencode -c`). Cada carpeta de trabajo tiene su propia sesión.

**Los crashes dejan de ser un infierno.** Un programa que se cierra solo,
la sesión que se reinicia, el equipo que se apaga sin avisar... averiguar
el porqué significa bucear en journals, dmesg, apport y volcados. ConBarAI
lo hace por ti: detecta el crash, lo analiza con IA en modo solo lectura y
te entrega un informe en claro con causa y arreglo.

**Tuyo y local.** Todo corre en tu espacio de usuario, sin sudo, sin
telemetría y sin tocar nada del sistema sin que lo pidas. La IA es tu
propio OpenCode.

## El agente del día a día

Pídele cosas del sistema: instalar programas, configurar servicios,
revisar logs, liberar disco... El panel carga la skill `ubuntu-operator`,
una guía de operación de Ubuntu con una regla fija: **diagnosticar antes
de tocar, y saber deshacer cada cambio**.

- Multi-sesión: un panel por carpeta (sesiones tmux `oc`, `oc-<carpeta>`).
- Alertas: cuando OpenCode pide atención suena una notificación, el icono
  pasa a ámbar y el punto de la cabecera a amarillo.
- Consumo a la vista: tokens y coste de la carpeta en la cabecera, leídos
  de la base de datos de OpenCode en modo solo lectura.
- Portapapeles de verdad: `Ctrl+V` pega, `Ctrl+C` copia si hay selección
  (si no, interrumpe al agente); además `Ctrl+Mayús+C/V`, `Mayús+Insert`
  y menú de clic derecho. Arrastra archivos y se insertan como rutas.
- Temas Tokyo Night, Catppuccin, Dracula y Gruvbox; JetBrains Mono Nerd
  con detección automática.

## Crashes: de infierno a informe

![Crash analizándose en la consola de diagnóstico](screenshots/captura-crash.png)

1. Un **vigía** (`oc-crash-watch`, servicio de usuario systemd) lee el
   journal del kernel — sin sudo, el usuario está en `adm` — y detecta
   segfaults, OOM-kills, resets de GPU, tareas colgadas y reinicios
   inesperados. Dedupe por programa y mute individual.
2. Te avisa con una **notificación** y guarda la evidencia.
3. Un agente con permisos de **SOLO LECTURA** (lista cerrada de comandos
   de diagnóstico; edición y red denegadas) escribe un informe en
   español: qué pasó, evidencia, causa probable — separando lo **probado**
   de lo **inferido** —, arreglo con su reversión y cómo evitarlo.
4. Con el panel a la vista, el análisis se ve **en directo** en una
   consola junto al panel (al lado o debajo, tú eliges); con el panel
   oculto, el informe se genera en segundo plano y se anuncia al acabar.

Las evidencias e informes quedan en `~/.local/state/oc-drop/crash/`
(`<fecha>-<programa>-<tipo>.md` la evidencia,
`<fecha>-<programa>-report.md` el informe). También a mano:

```bash
oc-crash-watch --once                 # una pasada de detección
oc-crash-run --pack <evidencia>.md    # analizar una evidencia guardada
systemctl --user status oc-crash-watch
```

## Todo desde el icono de la barra

<img src="screenshots/captura-menu.png" alt="Menú del tray" width="420" align="right">

- **Abrir / ocultar OpenCode** — lo mismo que el atajo.
- **Nueva sesión…** — panel con sesión propia para la carpeta que elijas.
- **Carpeta de trabajo…** — cambia la carpeta por defecto; el panel se
  reinicia y OpenCode pasa a trabajar desde ahí.
- **Terminal del sistema** — tu terminal (Ghostty u otro) en la carpeta
  de trabajo.
- **Cerrar paneles** — cierra las ventanas; tmux y OpenCode siguen vivos.
- **Sesiones** y **Carpetas recientes** — vuelve a cualquiera con un clic.
- **Tamaño**, **Transparencia**, **Tema**, **Tecla de apertura** —
  presets del panel.
- **Diagnóstico de crashes** — posición de la consola, vigía y análisis
  activables, y acceso a la carpeta de informes.
- **Abrir continuando la última sesión (-c)** — retomar contexto al
  arrancar, o empezar siempre de cero.
- **Ocultar al perder el foco** y **Arrancar al iniciar el sistema**.
- **Ayuda** — manual completo integrado, con estética de página `man`.
- **ConBarAI x.y.z** — la versión instalada abre este repositorio.

<br clear="right">

## Ayuda integrada

<img src="screenshots/captura-ayuda.png" alt="Ventana de ayuda" width="560">

La entrada **Ayuda** abre `conbarai(1)`: un manual de consola con la
tipografía y los colores del tema activo que documenta cada entrada del
menú, cada atajo, cada comando y cada ajuste.

## Instalación

```bash
git clone https://github.com/686f6c61/ubuntu-ConBarAI.git
cd ubuntu-ConBarAI
./install.sh
```

El instalador es interactivo: comprueba dependencias y ofrece instalarlas
con apt; ofrece Ghostty, OpenCode (instalador oficial) y JetBrains Mono
Nerd; **pregunta la carpeta de trabajo**; enlaza los binarios en
`~/.local/bin`; instala la skill como copia canónica (el panel la enlaza
como skill de proyecto SOLO en su carpeta de ejecución); y registra
autostart, atajo global y el servicio del vigía.

Después, cierra sesión y entra de nuevo (o ejecuta `oc-tray`) para ver el
icono en la barra.

### Requisitos

- GNOME en Wayland (probado en GNOME 50 / Ubuntu; la ventana usa XWayland)
- `python3-gi` + `gir1.2-vte-2.91` + `gir1.2-ayatanaappindicator3-0.1`
- `wmctrl`, `xdotool`, `tmux`, `libnotify-bin`
- `opencode` en el PATH
- Para el vigía: usuario en el grupo `adm` (el de Ubuntu por defecto)

## Uso

| Acción | Resultado |
| --- | --- |
| `Súper+Intro` (o el atajo configurado) | Abre u oculta el panel |
| Icono del tray | Menú completo (ver arriba) |
| Botón de recarga en la cabecera | Nueva sesión (OpenCode de cero, sin `-c`) |
| Botón de cierre en la cabecera | Oculta el panel |
| Clic fuera del panel | Se oculta solo (autohide, configurable) |
| `oc-drop --workdir RUTA` | Panel con sesión propia en esa carpeta |
| `oc-drop --quit` | Cierra todos los paneles (tmux sigue vivo) |

La cabecera muestra un punto verde (sesión viva), rojo (muerta) o ámbar
(pide atención), la carpeta de trabajo y el consumo.

## Ajustes

`~/.config/oc-drop/settings.json` (el menú del icono lo escribe por ti):

```json
{
  "autohide": true,
  "autostart": true,
  "workdir": "/home/usuario/Documentos/ConBarAI",
  "width": 0.34,
  "height": 0.62,
  "opacity": 0.97,
  "keybinding": "<Super>Return",
  "terminal": "auto",
  "theme": "tokyo-night",
  "font": "auto",
  "font_size": 10,
  "continue_session": true,
  "diag_pos": "side",
  "crash_watch": true,
  "crash_analyze": true,
  "crash_dedupe": 60,
  "crash_poll": 8
}
```

| Clave | Significado | Rango |
| --- | --- | --- |
| `autohide` | Ocultar el panel cuando pierde el foco | true / false |
| `autostart` | Arranca el tray al iniciar sesión (también en el menú del tray) | true / false |
| `workdir` | Carpeta de ejecución de OpenCode. Vacío = `~/Documentos/ConBarAI`. La pregunta el instalador y se cambia desde el tray ("Carpeta de trabajo…", reinicia el panel) | ruta |
| `width` | Ancho del panel (fracción del área de trabajo) | 0.15 - 0.90 |
| `height` | Alto del panel (fracción del área de trabajo) | 0.20 - 0.95 |
| `opacity` | Opacidad del panel | 0.50 - 1.00 |
| `keybinding` | Atajo global de apertura. `""` = desactivado | `<Super>Return`, `<Super>a`, ... |
| `terminal` | Terminal del sistema (menú del tray). `auto` = Ghostty si está, si no el que haya | `auto` o nombre del binario |
| `theme` | Tema del panel | `tokyo-night`, `catppuccin`, `dracula`, `gruvbox` |
| `font` | Tipografía de la terminal. `auto` = JetBrains Mono Nerd si está | `auto` o familia |
| `font_size` | Tamaño de la tipografía | 7 - 16 |
| `continue_session` | OpenCode arranca con `-c` (retoma la última sesión). El botón "Nueva sesión" siempre empieza de cero | true / false |
| `diag_pos` | Posición de la consola de diagnóstico de crashes | `side` (al lado) / `below` (debajo) |
| `crash_watch` | Vigilar crashes del sistema (journal del kernel) | true / false |
| `crash_analyze` | Analizar los crashes con IA | true / false |
| `crash_dedupe` | Ventana de deduplicación por programa (segundos) | entero |
| `crash_poll` | Intervalo de sondeo del vigía (segundos) | entero |

Los cambios de tamaño y transparencia se aplican la próxima vez que se
abre el panel.

## Seguridad y confianza

Todo es local, en el espacio del usuario:

- Los nombres de sesión se validan con charset cerrado
  (`^[a-z0-9][a-z0-9_-]{0,47}$`) antes de usarse en rutas, hooks de tmux
  o notificaciones.
- Los hooks de tmux solo crean un marcador en
  `~/.local/state/oc-drop/alerts/` (directorio 0700) y lanzan
  `notify-send`. No ejecutan nada del contenido del terminal.
- El análisis de crashes corre con permisos de solo lectura (lista
  cerrada de comandos de diagnóstico; edición, red y el resto del bash
  denegados) y la skill se carga solo en la carpeta de ejecución del
  panel, no en tu OpenCode general.
- Ajustes y registros con permisos 0600 en directorios 0700.
- La base de datos de OpenCode se abre en modo solo lectura.
- Ninguna función propia hace peticiones de red (la IA es tu OpenCode).
- `install.sh` puede instalar OpenCode con el instalador oficial
  (`curl ... | bash`): revisa el guion si prefieres otro método.

## Limitaciones conocidas

- La ventana usa XWayland (así se puede posicionar en GNOME); con varios
  monitores se ancla al borde derecho del espacio virtual combinado.
- La detección de "trabajando" es una heurística de CPU (~10%).
- El nombre de la sesión sale del nombre de la carpeta: dos carpetas con
  el mismo nombre comparten sesión.
- La detección de crashes es por journal del kernel: crashes que no dejan
  rastro ahí no se anuncian.

## Probado en

- Ubuntu 26.04, GNOME Shell 50 (Wayland), tmux 3.6, Ghostty 1.3, VTE 2.91.

## Estructura

```
ConBarAI/
├── oc-drop        Panel flotante y consola de diagnóstico (GTK3 + VTE)
├── oc-tray        Icono de la barra, menú y ayuda (AppIndicator)
├── oc-crash-watch Vigía de crashes (journal del kernel, servicio systemd)
├── oc-crash-run   Análisis headless de un crash con IA
├── oc_common.py   Módulo compartido (ajustes, crashes, tmux, consumo)
├── skills/        Skill ubuntu-operator (operación y forense de Ubuntu)
├── systemd/       Unidad de usuario oc-crash-watch.service
├── tests/         Tests unitarios (pytest)
├── icons/         Iconos del tray
├── autostart/     Plantilla de entrada de autostart
├── applications/  Plantilla de entrada del menú de Aplicaciones
├── screenshots/   Capturas del README
├── install.sh     Instalador interactivo
├── uninstall.sh   Desinstalador
└── pyproject.toml Configuración de ruff y pytest
```

## Changelog

Historial de cambios en [CHANGELOG.md](CHANGELOG.md). Versión actual:
**1.4.0**.

## Licencia

MIT — ver [LICENSE](LICENSE).

## Desarrollo

```bash
ruff check .        # análisis estático
python3 -m pytest   # tests unitarios
```

## Desinstalación

```bash
./uninstall.sh
```
