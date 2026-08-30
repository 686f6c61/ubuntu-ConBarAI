---
name: ubuntu-operator
description: >-
  Operate Ubuntu end-to-end — terminal administration, package management
  (apt, dpkg, snap, flatpak, AppImage), services (systemd), network, drivers,
  system triage (journalctl, AppArmor, ufw), crash forensics (segfaults, OOM
  kills, gnome-shell/XWayland restarts, apport and coredump reports), recovery
  playbooks and desktop GUI control — under one safety-first loop: diagnose,
  plan, execute defensively, verify, roll back. Use whenever managing,
  debugging, installing, configuring, or automating anything on an Ubuntu
  system, and whenever something on Ubuntu crashes, dies, restarts, or a
  program/kernel is killed and the cause must be worked out.
---

# Ubuntu Operator

One operating discipline for everything on Ubuntu: terminal, services, packages, hardware, and desktop GUI.

> Scope note: this skill is bundled with the ConBarAI panel and is loaded
> only by the OpenCode instance that runs inside it (via `OPENCODE_CONFIG`).
> It diagnoses **Ubuntu system crashes** from Ubuntu's own records (journald,
> dmesg, apport, coredump): kernel faults, OOM kills, the desktop/display
> server dying, or any program being killed. Read the evidence first; never
> fix before diagnosing.

## The loop (always)

**OBSERVE → DIAGNOSE → PLAN → EXECUTE → VERIFY**

- Never fix before diagnosing. State a hypothesis, apply the minimal change, verify it.
- Before every change, know the undo command. If it cannot be undone, ask the user first.
- When a fix fails, restore the prior state before trying the next hypothesis — never stack half-applied fixes.
- After every change, run the check that proves it worked (service active, port listening, config parses, exit code 0).

## 0. First contact — know the system

Before advising or acting on an unfamiliar machine, gather facts in one pass:

```bash
lsb_release -a; uname -r; echo "session: $XDG_SESSION_TYPE, desktop: $XDG_CURRENT_DESKTOP"
df -h /; free -h; lscpu | grep 'Model name'; lspci | grep -Ei 'vga|3d'
```

- **X11 vs Wayland decides your tooling**: `xdotool`, `scrot`, and global input simulation only work on X11; AT-SPI accessibility and `gnome-screenshot`/`grim` work on both. Check `$XDG_SESSION_TYPE` before any GUI automation.
- Release and kernel versions gate which commands and package names exist — never give version-specific advice without them.

## 1. Safety rules (non-negotiable)

- **Never run destructive or irreversible commands without explicit user confirmation**: `rm -rf`, `dd`, `mkfs`, partition changes, `chmod -R`/`chown -R` on system paths, dropping data, killing processes you haven't investigated.
- **Dry-run first when risk is non-trivial**: `apt-get --dry-run`, `rm -i`, echo the command before executing it.
- **Backup before editing any config**: `cp file file.bak.$(date +%Y%m%d%H%M%S)` — rollback stays one command away.
- **sudo discipline**: use only when required, one command at a time, never pipe a downloaded script into sudo without reading it, never edit sudoers except through `visudo`.
- **Investigate before touching**: unfamiliar files, locks, mounts, or processes may be someone's in-progress work.
- **Scripts you write are defensive**:
  - Start with `set -Eeuo pipefail`; trap errors and cleanup (`trap 'rm -rf "$TMPDIR"' EXIT`, `TMPDIR=$(mktemp -d)`).
  - Quote every expansion (`"$var"`), use `[[ ]]`, fail fast on missing inputs (`: "${VAR:?required}"`).
  - Write atomically (temp file + `mv`), design for idempotency (safe to re-run), support `--dry-run` for risky operations.
  - Validate dependencies up front (`command -v jq || exit 1`) and log with timestamps to stderr.

## 2. Package management

Preference order on Ubuntu: **apt (official repos) → snap → flatpak → AppImage → .deb download → PPA → build from source**. Higher in the list means better integration and updates; go lower only when the app isn't packaged above.

| Task | Command |
|------|---------|
| Search | `apt search <name>`, `snap find <name>`, `flatpak search <name>` |
| Install | `sudo apt install <pkg>`, `sudo snap install <pkg>`, `flatpak install flathub <id>` |
| Info before installing | `apt show <pkg>`, `snap info <pkg>` |
| Remove cleanly | `sudo apt purge <pkg> && sudo apt autoremove`, `sudo snap remove <pkg>` |
| .deb file | `sudo apt install ./file.deb` (resolves deps; plain `dpkg -i` doesn't) |
| AppImage | `chmod +x file.AppImage`, keep in `~/Applications`, integrate with a `.desktop` file |
| List what's installed | `apt list --installed`, `snap list`, `flatpak list` |
| Holds / pins | `apt-mark showhold`, `sudo apt-mark hold <pkg>` |

Rules:

- Fix broken state first: `sudo dpkg --configure -a`, then `sudo apt --fix-broken install`.
- Never force `dpkg --force-*` or remove essential packages (`apt` warns — believe it).
- PPAs: check they support this Ubuntu release (`lsb_release -cs`) before adding; removing = `sudo add-apt-repository --remove ppa:...` + purge its packages.
- Snap confinement and AppArmor denials explain many "app can't see my files" issues.

## 3. Terminal triage toolkit

Diagnose with the right tool before touching anything:

| Area | First commands |
|------|----------------|
| Packages | `apt policy <pkg>`, `dpkg -l \| grep <pkg>`, `apt list --upgradable`; holds: `apt-mark showhold` |
| Services | `systemctl status <svc>`, `systemctl --failed`, `journalctl -u <svc> -b --no-pager`, `journalctl -p err -b` |
| Boot/system | `systemd-analyze blame`, `journalctl -b -1` (previous boot), `dmesg -T \| tail -50` |
| Disk | `df -h`, `du -xh --max-depth=1 / 2>/dev/null \| sort -h`, `lsblk -f`, `smartctl -a /dev/sdX` |
| CPU/RAM | `free -h`, `ps aux --sort=-%mem \| head`, `vmstat 1 5` |
| Network | `ip a`, `ip r`, `ss -tulpn`, `resolvectl status`, `nmcli device status` |
| Permissions | `namei -l <path>`, `ls -la` along the whole path |
| Security | AppArmor: `aa-status`, `journalctl -b \| grep DENIED`; firewall: `sudo ufw status verbose` |

Notes:

- Logs live in `/var/log/` — grep before guessing.
- When a service "should work but doesn't", check AppArmor denials and `ufw` before reconfiguring anything.

## 4. Services and scheduled tasks (systemd)

- User services (no sudo, preferred when possible): unit in `~/.config/systemd/user/x.service`, then `systemctl --user daemon-reload && systemctl --user enable --now x`.
- System services: unit in `/etc/systemd/system/`, `sudo systemctl enable --now x`.
- Minimal unit: `[Service]` with `ExecStart=`, `Restart=on-failure`; `[Install]` with `WantedBy=default.target` (user) or `multi-user.target` (system).
- Recurring tasks: prefer a `.timer` over cron — `systemctl --user list-timers` shows schedule and last run, logs land in the journal.
- Verify: `systemctl status x`, `journalctl --user-unit x -f`.

## 5. Network and firewall

- Wi-Fi: `nmcli device wifi list`, `nmcli device wifi connect "SSID" password "..."`, `nmcli connection show`.
- DNS problems: `resolvectl status`, test with `dig example.com` vs `ping -c3 1.1.1.1` (IP works + DNS fails = resolver issue).
- Firewall (deny-by-default posture): `sudo ufw default deny incoming && sudo ufw default allow outgoing`, then allow per service: `sudo ufw allow ssh`, `sudo ufw allow 8080/tcp`. Enable with `sudo ufw enable`; verify `sudo ufw status verbose`. Undo a rule: `sudo ufw delete allow ssh`.
- "Port already in use": `ss -tulpn | grep :<port>` to find the owner before killing anything.

## 6. Users, groups, and permissions

- Add user to a group (docker, dialout, plugdev...): `sudo usermod -aG <group> <user>` — never omit `-a` (without it you strip every other group). Takes effect on next login; verify with `id <user>`.
- Permissions quick read: `rwx` per user/group/other; `chmod u+x file` style relative changes beat absolute modes for safety.
- Default ACLs on shared dirs: `setfacl -d -m g:<group>:rwX <dir>`.

## 7. Hardware and drivers

- GPU: `ubuntu-drivers devices` then `sudo ubuntu-drivers autoinstall` (reversible: pick the previous driver in "Software & Updates"); NVIDIA status: `nvidia-smi`.
- USB/ports: `lsusb`, `lsblk`, `dmesg -T | tail` right after plugging in.
- Audio: `pactl list sinks short`, `pavucontrol` for GUI routing.
- Printing: CUPS at `http://localhost:631`, `lpstat -p -d`.
- Laptop battery/thermal: `upower -i /org/freedesktop/UPower/devices/battery_BAT0`, `sensors`.

## 8. Maintenance and disk-space recovery

- Routine update: `sudo apt update && sudo apt upgrade`, then `sudo apt autoremove --purge`.
- Biggest space hogs, in order of safety to clean:
  1. Journal: `journalctl --disk-usage`, trim `sudo journalctl --vacuum-size=200M`.
  2. APT cache: `sudo apt clean`.
  3. Old snap revisions: `snap list --all | awk '/disabled/{print $1, $3}'` (remove disabled revisions only).
  4. User cache: `du -xh ~/.cache --max-depth=1 | sort -h`.
  5. Old kernels: handled by `apt autoremove`; never delete `/boot` files by hand.

## 9. Recovery playbooks

- **APT/DPKG broken**: `sudo dpkg --configure -a` → `sudo apt --fix-broken install` → `sudo apt update`. Only then consider removing the offending package.
- **Disk 100% full and system unusable**: clean journal + apt cache (section 8), check deleted-but-open files with `sudo lsof +L1` (restart the holding process to free space).
- **Broken after update**: boot the previous kernel from GRUB ("Advanced options"), verify, then pin or report the regression.
- **Forgotten password / unbootable system**: recovery mode or live USB + chroot — walk the user through it interactively; never automate blindly.
- **GUI broken but TTY works**: Ctrl+Alt+F3, check `journalctl -b -p err`, `systemctl status gdm`.

## 10. GUI operation (desktop)

Prefer the `computer-use` skill (orca CLI) when installed — it provides the accessibility-tree tooling. Whether using it or raw AT-SPI/OCR, apply the same principles:

- **Check the session first**: `$XDG_SESSION_TYPE` — on Wayland, coordinate tools like `xdotool`/`scrot` don't work; use AT-SPI/OCR or portal-based screenshots.
- **Semantic first**: target elements by name/role via the accessibility tree (AT-SPI), never by raw coordinates unless nothing else works.
- **OCR fallback**: when the a11y tree doesn't expose an element (canvas, images, legacy apps), locate its text with OCR (tesseract).
- **Wait, don't sleep**: poll for elements to appear/disappear with timeout + backoff; fixed `sleep` is fragile.
- **Verify critical actions**: screenshot or re-read the UI tree before and after any consequential click.
- **Read before acting**: list windows/apps and dump the UI tree first; act on what is actually on screen, not on what should be.
- **Never launch GUI apps the user didn't ask for**; opening an app is a visible, session-altering action — confirm first when in doubt.

## 11. Escalate to the user when

- The action is irreversible, touches disk partitioning, credentials, or system-wide state.
- Installing or removing software outside official repos (PPAs, random .deb/AppImage, curl|bash installers).
- Diagnosis is uncertain between two risky paths.
- Permissions, passwords, or hardware access are missing.
- A command requires interactive sudo and no password was provided.

## 12. Crash forensics (the Ubuntu system crashed something)

A "crash" is a kernel fault, an OOM kill, the desktop/display server dying, or
a program being killed. Diagnose from **Ubuntu's own records**, evidence first,
then name a cause. Method mirrors Omarchy's `diagnose-crash`: **read, never
fix** — a diagnosis changes nothing on the machine except a mute the user asked
for.

### Who captures cores here — find out first

```bash
cat /proc/sys/kernel/core_pattern
```

- Starts with `|/usr/share/apport/apport` → **Ubuntu default: apport**. Crashes
  land in `/var/crash/*.crash`; `coredumpctl` is usually absent. This section's
  apport path applies.
- Empty or `core` / handled by `systemd-coredump` → use `coredumpctl` instead
  (`coredumpctl list`, `info <PID>`, `dump <PID>`).
- Apport crash files are `root:whoopsie 0640`: your user typically **cannot read
  the file** (listing the directory is fine). Read a report without sudo via
  `apport-cli '<path>.crash'` or its `-x`; the trigger needs no privilege (a new
  file mtime is enough).

### Where an Ubuntu crash is recorded

| Signal | Where to look (no sudo unless noted) |
|--------|---------------|
| A program segfaulted / aborted | new `/var/crash/<exe>.<uid>.crash`; fields `ProblemType, ExecutablePath, Signal, StacktraceTop, ProcCmdline, Date, Package`. Read via `apport-cli` (sudo for raw file) |
| apport processed it | `journalctl -b | grep -iE 'apport|whoopsie|update-notifier-crash'`; `/var/log/apport.log` |
| OOM killer picked a victim | `journalctl -k -b | grep -Ei 'Out of memory|Killed process|oom-kill|memory cgroup out of memory'` |
| Kernel segfault / GP fault / traps | `journalctl -k -b | grep -Ei 'segfault|general protection|traps:'`; `dmesg -T | grep -i segfault` |
| Kernel panic / hardware / thermal / reboot | `journalctl -k -b -1 | tail -60`, `last -x reboot shutdown`, `journalctl --list-boots`, `/proc/sys/kernel/random/boot_id`, `/var/crash/kexec_cmd` (kdump) |
| GPU reset / driver fault | `journalctl -k -b | grep -Ei 'NVRM|Xid|amdgpu|i915|drm.*reset'` |
| GNOME Shell / mutter / XWayland restart | `journalctl -b | grep -iE 'gnome-shell|mutter|Xwayland'`, `journalctl -u gdm`; `~/.local/share/xorg/Xorg.*.log*` |
| Hung task / disk dying | `journalctl -k -b | grep -Ei 'hung task|blocked for more than|I/O error|nvme.*timeout'`; `smartctl -a /dev/nvme0n1` (sudo) |

### Establish the facts (one pass)

```bash
echo "== handler =="; cat /proc/sys/kernel/core_pattern
echo "== boot =="; uptime -s; cat /proc/sys/kernel/random/boot_id; last -x reboot shutdown 2>/dev/null | head -3
echo "== crash reports =="; ls -lt /var/crash/ 2>/dev/null | head
echo "== kernel faults =="; journalctl -k -b --no-pager | grep -Ei 'segfault|oom|killed process|general protection|hung task|Xid' | tail -20
echo "== prev boot tail =="; journalctl -k -b -1 --no-pager 2>/dev/null | tail -40
echo "== RAM =="; free -h
```

### Work the evidence (the discipline)

- **Rule out resource exhaustion first**: `free -h` + OOM lines. A process killed
  by the OOM killer is *not* a bug in that process — the symptom (a window that
  vanished) is the killed PID; the cause is memory pressure.
- **Correlate the timestamp** (the most underused fact): compare the crash time
  against file/directory mtimes, adjacent journal warnings, and recent package
  upgrades (`journalctl --since <upgrade-time>`). A crash that starts right
  after an update points at the update.
- **Read the whole report, not just the top frame**: `ProcCmdline` shows what it
  was working on; `StacktraceTop` names the faulting library. Flag third-party
  code in the address space (browser/Nautilus extensions, out-of-tree drivers
  like virtualbox-dkms) but **do not blame it without evidence**.
- **Symbolize only if the machine can**: Ubuntu has `apport-retrace` /
  `debuginfod` only if enabled. When frames stay unresolved, **say so** — never
  invent function names to fill the gap; describe the shape instead (signal
  handler? main loop? worker thread? which `.so`?).
- **Separate what the evidence proves from what you infer**, and state the
  confidence. If it is genuinely ambiguous, say that; do not assemble certainty
  out of guesswork.

### Cause → action (decision tree)

- **Whole machine reset**, `journalctl -k -b -1` ends abruptly / shows a panic →
  read the last lines + MCE/thermal; suspect hardware (PSU, RAM, overheating via
  `sensors`, disk via `smartctl`). Do not reinstall to "fix" an unidentified
  fault.
- **`Out of memory: Killed process X`** → memory pressure; find the hog (the OOM
  line lists the task table), then fix the leak or add swap / raise the limit.
  Reversible moves only.
- **A named program + a `/var/crash` entry** → read `Signal`
  (6=SIGABRT, 11=SIGSEGV, 9=SIGKILL/OOM, 4=SIGILL) and `StacktraceTop`; match to
  a recent upgrade or an AppArmor denial (`aa-status`, `journalctl | grep DENIED`).
- **Desktop flashed back to login** → GPU reset (`Xid`/`drm`), shell OOM, or a
  bad GNOME extension. Bisect safely; test the previous driver (section 7).
- **Only a stray process died, session intact** → OOM or an upstream app bug;
  hand the user `ubuntu-bug <pkg>` rather than patching system files.

### Leave the system as you found it

Diagnosis is read-only. It does not "tidy", reconfigure, delete crash files, or
apply fixes unprompted. If the same program keeps crashing, **offer** to silence
ConBarAI's notice for that one program (see the mute in section 13) and say in
the same breath how to undo it — never a one-way door. Anything that would
actually change the system is a separate, confirmed step (section 11).

## 13. ConBarAI auto-analysis protocol

ConBarAI copies Omarchy's crash flow, adapted to **Ubuntu (apport + journald)**:
a crash happens → a watcher notices from Ubuntu's logs → an AI analyses it →
the user gets findings + fix options, **without ever interrupting work already
running**.

- **Watcher = a user service** (`oc-crash-watch.service`, `PartOf=` graphical
  session, `Restart=always`), like Omarchy's. Poll every few seconds
  (apport has no single journal `MESSAGE_ID` like systemd-coredump, so watch):
  - `boot_id` changed → machine rebooted (panic/power loss): analyse
    `journalctl -k -b -1`;
  - a **new/updated file** under `/var/crash/` (by mtime; listing needs no
    sudo): an apport crash — read it via `apport-cli`/sudo for content;
  - `journalctl -k --since <watermark>` matching
    `segfault|general protection|oom-kill|Killed process|hung task|Xid`;
  - never announce our own tooling (`oc-drop`, `oc-tray`, `oc-crash-watch`,
    `oc-crash-run`).
- **Filters (as Omarchy does):** only the current user's crashes (apport file
  carries the uid; kernel lines need matching), a dedupe window per program
  (crash loops), a per-program mute, and a global off switch.
- **Runner:** analyse with a headless `opencode run "<context pack>"` (a *new*
  session, never `--continue`). The run gets `OPENCODE_CONFIG` with read-only
  bash permissions and `skills.paths`, so it already carries this skill.
- **Never disturb running work:** the analysis opens in its **own diagnostic
  window** (beside or below the panel, setting `diag_pos`), streaming the
  agent live; the main panel's session is never touched or resized. A desktop
  notification announces the crash.
- **Be brief — the run has a hard timeout:** the report must arrive within
  minutes. At most 3-4 read-only commands; if the evidence in the context
  pack already tells the story, answer without executing anything.
- **Artifacts on disk** (`~/.local/state/oc-drop/crash/`): evidence packs
  `<ts>-<program>-<kind>.md`, finished reports `<ts>-<program>-report.md`,
  watcher state `watch.json`, mutes in `ignore/`.
- **Mute:** per-program flag in `~/.local/state/oc-drop/crash/ignore/<name>`
  (list = that dir; removing the file unmutes). Sanitise `<name>` to a single
  path component so a hostile `comm`/path can't escape the dir. The global
  switches live in the tray menu "Diagnóstico de crashes" (vigía y análisis).
- **Required report shape** (Spanish, user's language):
  1. **Qué pasó** — one sentence: what died, when, signal/event.
  2. **Evidencia** — the exact log/report lines, verbatim (redact any secrets).
  3. **Causa probable** — ranked; state what is *proved* vs *inferred* and how
     to confirm each; admit ambiguity honestly.
  4. **Arreglo** — options safest→invasive, each with its **rollback**; nothing
     irreversible run automatically (ask first, section 11).
  5. **Cómo evitarlo** — the durable fix, and offer the per-program mute.

## Worked examples (the loop in practice)

**"El Wi-Fi no conecta tras actualizar."**

1. **Observe**: `nmcli device status`, `journalctl -u NetworkManager -b --no-pager | tail -30`, `apt list --installed | grep -i firmware`.
2. **Diagnose**: hypothesis — kernel update broke the driver; evidence in `dmesg -T | grep -i firmware`.
3. **Plan**: boot the previous kernel (reversible) vs reinstall firmware (reversible). Rollback: reboot into the newer kernel.
4. **Execute**: one change only.
5. **Verify**: `nmcli device status` shows `connected`; `ping -c3 1.1.1.1`. If not, revert and try the next hypothesis.

**"Instala la app X."**

1. **Observe**: `apt search x` → ¿existe en repos? `snap find x` → `flatpak search x`. Check the app's official docs for the recommended Linux channel.
2. **Diagnose**: prefer the channel highest in the preference order (section 2) that is officially maintained.
3. **Plan**: state install command + its undo (`apt purge`, `snap remove`...). If only a PPA/curl-script exists, ask the user first (section 11).
4. **Execute**, then **verify**: binary runs (`command -v x`, `x --version`), app appears in the launcher.
