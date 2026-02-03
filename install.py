#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoTor Installer / Uninstaller
================================
Installiert oder entfernt AutoTor systemweit.

Usage:
    sudo python3 install.py install
    sudo python3 install.py uninstall

Nach der Installation kann AutoTor mit 'autotor' aufgerufen werden.

License: MIT
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
INSTALL_DIR = Path("/usr/share/autotor")
BIN_LINK = Path("/usr/bin/autotor")
SOURCE_FILE = Path(__file__).parent / "autotor.py"

SHELL_WRAPPER = f"""#!/bin/sh
# AutoTor IP Changer – Wrapper
exec python3 {INSTALL_DIR / 'autotor.py'} "$@"
"""

REQUIRED_PIP_PACKAGES = ["requests", "requests[socks]"]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def check_root() -> None:
    """Prüft Root-Rechte."""
    if os.geteuid() != 0:
        print("[✗] Dieses Script benötigt Root-Rechte (sudo).", file=sys.stderr)
        sys.exit(1)


def confirm(prompt: str) -> bool:
    """Fragt den Benutzer nach Bestätigung.

    Args:
        prompt: Anzuzeigende Frage.

    Returns:
        True bei 'y'/'yes', False sonst.
    """
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in ("y", "yes", "j", "ja")


def check_tor_installed() -> bool:
    """Prüft ob Tor installiert ist."""
    return shutil.which("tor") is not None


def install_system_dependencies() -> None:
    """Installiert Tor über den Paketmanager, falls nicht vorhanden."""
    if check_tor_installed():
        print("[✓] Tor ist bereits installiert.")
        return

    if not confirm("[?] Tor ist nicht installiert. Jetzt installieren?"):
        print("[!] Ohne Tor kann AutoTor nicht funktionieren.")
        sys.exit(1)

    print("[*] Installiere Tor …")
    try:
        subprocess.run(
            ["apt", "update"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["apt", "install", "-y", "tor"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("[✓] Tor erfolgreich installiert.")
    except subprocess.CalledProcessError as exc:
        print(f"[✗] Tor-Installation fehlgeschlagen: {exc}", file=sys.stderr)
        sys.exit(1)


def install_pip_packages() -> None:
    """Installiert benötigte Python-Pakete."""
    print("[*] Prüfe Python-Abhängigkeiten …")
    try:
        import requests  # noqa: F401
        import socks  # noqa: F401
        print("[✓] Python-Abhängigkeiten vorhanden.")
        return
    except ImportError:
        pass

    print("[*] Installiere Python-Pakete …")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", *REQUIRED_PIP_PACKAGES],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("[✓] Python-Pakete installiert.")
    except subprocess.CalledProcessError as exc:
        print(
            f"[✗] Paket-Installation fehlgeschlagen: {exc}\n"
            f"    Manuell installieren mit: pip3 install {' '.join(REQUIRED_PIP_PACKAGES)}",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Install / Uninstall
# ---------------------------------------------------------------------------


def install() -> None:
    """Installiert AutoTor systemweit."""
    check_root()

    if not SOURCE_FILE.exists():
        print(
            f"[✗] Quelldatei nicht gefunden: {SOURCE_FILE}\n"
            "    Bitte aus dem Projektverzeichnis ausführen.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- System-Abhängigkeiten ---
    install_system_dependencies()
    install_pip_packages()

    # --- Vorherige Installation prüfen ---
    if INSTALL_DIR.exists():
        if not confirm(
            f"[?] {INSTALL_DIR} existiert bereits. Überschreiben?"
        ):
            print("[!] Installation abgebrochen.")
            sys.exit(0)
        shutil.rmtree(INSTALL_DIR)

    # --- Dateien kopieren ---
    print(f"[*] Erstelle {INSTALL_DIR} …")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    target = INSTALL_DIR / "autotor.py"
    shutil.copy2(SOURCE_FILE, target)

    # Berechtigungen: rwxr-xr-x
    target.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    print(f"[✓] {SOURCE_FILE.name} → {target}")

    # --- Shell-Wrapper erstellen ---
    print(f"[*] Erstelle Wrapper: {BIN_LINK} …")
    BIN_LINK.write_text(SHELL_WRAPPER)
    BIN_LINK.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    print(f"[✓] Wrapper erstellt: {BIN_LINK}")

    # --- Abschluss ---
    print(
        f"\n{'='*50}\n"
        f"[✓] AutoTor erfolgreich installiert!\n"
        f"\n"
        f"    Aufruf:  sudo autotor\n"
        f"    Hilfe:   sudo autotor --help\n"
        f"{'='*50}"
    )


def uninstall() -> None:
    """Entfernt AutoTor vom System."""
    check_root()

    found_something = False

    if INSTALL_DIR.exists():
        found_something = True
        print(f"[*] Gefunden: {INSTALL_DIR}")

    if BIN_LINK.exists():
        found_something = True
        print(f"[*] Gefunden: {BIN_LINK}")

    if not found_something:
        print("[!] AutoTor ist nicht installiert – nichts zu entfernen.")
        return

    if not confirm("[?] AutoTor wirklich deinstallieren?"):
        print("[!] Deinstallation abgebrochen.")
        return

    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR)
        print(f"[✓] Entfernt: {INSTALL_DIR}")

    if BIN_LINK.exists():
        BIN_LINK.unlink()
        print(f"[✓] Entfernt: {BIN_LINK}")

    print("\n[✓] AutoTor erfolgreich deinstalliert.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Einstiegspunkt."""
    parser = argparse.ArgumentParser(
        description="AutoTor Installer / Uninstaller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  sudo python3 install.py install     # Installieren\n"
            "  sudo python3 install.py uninstall   # Deinstallieren\n"
        ),
    )
    parser.add_argument(
        "action",
        choices=["install", "uninstall"],
        help="'install' zum Installieren, 'uninstall' zum Entfernen",
    )

    args = parser.parse_args()

    if args.action == "install":
        install()
    elif args.action == "uninstall":
        uninstall()


if __name__ == "__main__":
    main()
