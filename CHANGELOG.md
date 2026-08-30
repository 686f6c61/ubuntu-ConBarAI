# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y adherido al [Versionado Semántico](https://semver.org/lang/es/).

## [1.0.2] - 2026-08-30

### Añadido

- Copiar y pegar en el panel: atajos `Ctrl+Shift+C` / `Ctrl+Shift+V`,
  `Ctrl+Insert` / `Shift+Insert` y menú en el clic derecho con Copiar y
  Pegar (esta compilación de VTE GTK3 no los traía de serie).
- Arrastrar y soltar archivos y carpetas dentro del panel: se insertan
  como rutas entrecomilladas listas para el comando; el texto suelto
  también se pega.

### Corregido

- El autohide se ocultaba con robos de foco de popups. En lugar de fiarse
  de un grab de GTK (que XWayland no siempre expone), ahora solo se
  oculta cuando la ventana activa de X11 pasa a ser otra ventana real.

## [1.0.1] - 2026-08-30

### Corregido

- El panel se ocultaba al intentar pegar con el menú contextual de VTE
  (clic derecho) o al interactuar con popups: el menú roba el foco y el
  autohide lo interpretaba como una pérdida de foco definitiva. Ahora el
  ocultado se difiere mientras haya un menú activo y, al cerrarse, solo
  se oculta si el foco quedó en otra ventana.

## [1.0.0] - 2026-08-30

Primera versión estable, lista para la comunidad de Ubuntu.

### Añadido

- Panel flotante estilo Omarchy (GTK3 + VTE sobre XWayland) con OpenCode
  corriendo en tmux: esquinas redondeadas, sombra, tema Tokyo Night y
  anclado en la esquina superior derecha, justo bajo la barra de GNOME.
- Icono en el tray de la barra superior: abrir/ocultar, nueva sesión,
  terminal del sistema y cerrar paneles, con iconos simbólicos.
- Multi-sesión: un panel por carpeta de trabajo (sesiones tmux `oc`,
  `oc-<carpeta>`), menú de sesiones y carpetas recientes.
- Alertas: la campana de la TUI lanza notificación de escritorio, icono
  ámbar en el tray y punto ámbar en la cabecera; se limpia al abrir.
- Spinner en la cabecera e icono animado mientras el agente trabaja
  (heurística de CPU del proceso del panel).
- Contador de tokens y coste de la carpeta en la cabecera, leído en modo
  solo lectura de la base de datos de OpenCode.
- Temas: Tokyo Night, Catppuccin, Dracula y Gruvbox.
- Botón de maximizar/restaurar el panel en la cabecera.
- Entrada en el menú de Aplicaciones de GNOME y autostart configurable
  (ajuste `autostart` y casilla en el menú del tray).
- Atajo global configurable (por defecto Super+Intro) y desactivable,
  registrado vía gsettings por el propio tray.
- Presets de tamaño y transparencia; ajustes completos en
  `~/.config/oc-drop/settings.json`.
- Terminal del sistema: Ghostty si está o el terminal disponible del
  usuario (gnome-terminal, konsole, alacritty, kitty, xterm).
- Instalador interactivo: dependencias por apt, Ghostty opcional,
  OpenCode opcional (instalador oficial) y tipografía JetBrains Mono
  Nerd opcional.
- Desinstalador que conserva los atajos de teclado personalizados ajenos
  al proyecto.

### Seguridad

- Validación de nombres de sesión con charset cerrado antes de
  interpolarlos en hooks de tmux, rutas y notificaciones.
- Alertas como marcadores por sesión en directorio privado 0700,
  normalizados a 0600; ajustes y registros 0600 en directorios 0700.
- Base de datos de OpenCode abierta en modo solo lectura.
- Filtrado de entradas de media-keys ajenas al editar atajos globales.
- `.gitignore` que impide entrar artefactos de herramientas de IA.

### Desarrollo

- 31 tests unitarios (pytest) en verde y análisis estático limpio (ruff).
- `pyproject.toml` con configuración de ruff y pytest y metadatos del
  proyecto bajo licencia MIT.
- README con guía de ajustes, sección de seguridad, limitaciones y
  versiones probadas, más capturas del panel.
- Localización de la carpeta de ejecución por defecto
  (`~/Documentos` o `~/Documents`).

[1.0.2]: https://github.com/686f6c61/ubuntu-ConBarAI/releases/tag/v1.0.2
[1.0.1]: https://github.com/686f6c61/ubuntu-ConBarAI/releases/tag/v1.0.1
[1.0.0]: https://github.com/686f6c61/ubuntu-ConBarAI/releases/tag/v1.0.0
