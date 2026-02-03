#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoTor IP Changer v3.0
=======================
Automatischer IP-Wechsel über das Tor-Netzwerk.

Nutzt den lokalen Tor-SOCKS5-Proxy, um in konfigurierbaren
Intervallen eine neue Tor-Identity (und damit eine neue Exit-IP)
anzufordern.

Usage:
    sudo python3 autotor.py
    sudo python3 autotor.py --interval 90 --count 10
    sudo python3 autotor.py --interval 60 --infinite

Requires: tor, python3-requests, python3-requests[socks]

License: MIT
"""

import argparse
import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------
TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050
TOR_PROXIES = {
    "http": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
    "https": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
}
# socks5h = DNS-Auflösung über Tor (verhindert DNS-Leaks)

IP_CHECK_URLS = [
    "https://check.torproject.org/api/ip",
    "https://api.ipify.org",
    "https://checkip.amazonaws.com",
]

REQUEST_TIMEOUT = 15  # Sekunden
TOR_RELOAD_WAIT = 2   # Wartezeit nach Circuit-Reload
VERSION = "3.0"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("autotor")

# ---------------------------------------------------------------------------
# Globaler Shutdown-Flag
# ---------------------------------------------------------------------------
_shutdown_requested = False


def _signal_handler(signum: int, _frame) -> None:
    """Graceful Shutdown bei SIGINT / SIGTERM."""
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    log.info("Signal %s empfangen – beende nach aktuellem Zyklus …", sig_name)
    _shutdown_requested = True


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
_ESC = chr(27)
_R = f"{_ESC}[0m"         # Reset
_C = f"{_ESC}[1;36m"      # Cyan bold
_M = f"{_ESC}[1;35m"      # Magenta bold
_Y = f"{_ESC}[1;33m"      # Yellow bold
_G = f"{_ESC}[1;32m"      # Green bold
_D = f"{_ESC}[2;37m"      # Dim white
_RD = f"{_ESC}[1;31m"     # Red bold
_BG = f"{_ESC}[40m"       # Black background

BANNER = rf"""
{_BG}{_D}  ┌──────────────────────────────────────────────────────────┐{_R}
{_BG}{_D}  │{_R}{_BG}  {_RD}▄▄▄   ▄▄  ▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄ ▄▄▄▄▄▄  ▄▄▄▄▄▄  {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_RD}█   █ █  █   █   █       █ █       █   ▄  ██   ▄  █ {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_M}█   █ █  █   █   █   ▄   █ █▄     ▄█  █ █ ██  █ █ █ {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_M}█   █▄█  █   █   █  █ █  █   █   █ █   █▄▄█▄█   █▄█ █{_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_C}█       █   █   █  █▄█  █   █   █ █    ▄▄  █    ▄▄  █{_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_C}█   ▄   █   █   █       █   █   █ █   █  █ █   █  █ █{_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_C}█▄▄█ █▄▄█▄▄▄█▄▄▄█▄▄▄▄▄▄▄█   █▄▄▄█ █▄▄▄█  █▄█▄▄▄█  █▄{_D}│{_R}
{_BG}{_D}  │{_R}{_BG}                                                            {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_Y}╔═══════════════════════════════════════════════════╗  {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_Y}║{_R}{_BG}  {_G}>> TOR IP CHANGER {_D}// {_M}v{VERSION} {_D}// {_C}IDENTITY ROTATION  {_Y}║{_R}{_BG}  {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_Y}╚═══════════════════════════════════════════════════╝  {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}                                                            {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_D}  ░▒▓ {_C}github.com/m0h1nd4/TorIPChanger {_D}▓▒░             {_D}│{_R}
{_BG}{_D}  │{_R}{_BG}  {_D}  ░▒▓ {_M}SOCKS5 PROXY {_D}// {_G}127.0.0.1:9050 {_D}▓▒░             {_D}│{_R}
{_BG}{_D}  └──────────────────────────────────────────────────────────┘{_R}
"""


# ============================= Hilfsfunktionen =============================


def check_root() -> None:
    """Stellt sicher, dass das Script mit Root-Rechten läuft."""
    if os.geteuid() != 0:
        log.error("Dieses Script benötigt Root-Rechte (sudo).")
        sys.exit(1)


def check_dependencies() -> None:
    """Prüft, ob alle Abhängigkeiten vorhanden sind."""
    # --- Tor ---
    if not shutil.which("tor"):
        log.error(
            "Tor ist nicht installiert. Bitte installiere es mit:\n"
            "  sudo apt update && sudo apt install tor -y"
        )
        sys.exit(1)
    log.info("✓ Tor gefunden: %s", shutil.which("tor"))

    # --- Python-Pakete ---
    missing: list[str] = []
    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")

    try:
        import socks  # noqa: F401
    except ImportError:
        missing.append("requests[socks]")

    if missing:
        log.error(
            "Fehlende Python-Pakete: %s\n"
            "Installiere sie mit:\n  pip3 install %s",
            ", ".join(missing),
            " ".join(missing),
        )
        sys.exit(1)
    log.info("✓ Python-Abhängigkeiten vorhanden")


def tor_service(action: str) -> bool:
    """Führt eine systemctl/service-Aktion auf Tor aus.

    Args:
        action: start | stop | reload | restart | status

    Returns:
        True bei Erfolg, False bei Fehler.
    """
    # Versuche systemctl, fallback auf service
    for cmd in (
        ["systemctl", action, "tor"],
        ["service", "tor", action],
    ):
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            return True
        except FileNotFoundError:
            continue
        except subprocess.CalledProcessError as exc:
            log.warning("Kommando %s fehlgeschlagen: %s", " ".join(cmd), exc)
            return False
        except subprocess.TimeoutExpired:
            log.warning("Kommando %s Timeout", " ".join(cmd))
            return False
    log.error("Weder systemctl noch service verfügbar.")
    return False


def wait_for_tor(max_wait: int = 30) -> bool:
    """Wartet bis der Tor-SOCKS-Port erreichbar ist.

    Args:
        max_wait: Maximale Wartezeit in Sekunden.

    Returns:
        True wenn Tor bereit ist, False bei Timeout.
    """
    import socket

    log.info("Warte auf Tor-SOCKS-Proxy (%s:%d) …", TOR_SOCKS_HOST, TOR_SOCKS_PORT)
    start = time.monotonic()
    while time.monotonic() - start < max_wait:
        if _shutdown_requested:
            return False
        try:
            with socket.create_connection(
                (TOR_SOCKS_HOST, TOR_SOCKS_PORT), timeout=2
            ):
                log.info("✓ Tor-Proxy erreichbar")
                return True
        except OSError:
            time.sleep(1)
    log.error("Tor-Proxy nicht erreichbar nach %d Sekunden.", max_wait)
    return False


def get_current_ip() -> Optional[str]:
    """Ermittelt die aktuelle öffentliche IP über den Tor-Proxy.

    Versucht mehrere Check-URLs als Fallback.

    Returns:
        IP-Adresse als String oder None bei Fehler.
    """
    import requests

    for url in IP_CHECK_URLS:
        try:
            resp = requests.get(
                url,
                proxies=TOR_PROXIES,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()

            # Tor-Project API liefert JSON
            if "torproject.org" in url:
                data = resp.json()
                ip = data.get("IP", "").strip()
                is_tor = data.get("IsTor", False)
                if ip:
                    if not is_tor:
                        log.warning(
                            "⚠ Tor-Project meldet: Traffic läuft NICHT über Tor!"
                        )
                    return ip
            else:
                ip = resp.text.strip()
                if ip:
                    return ip

        except requests.RequestException as exc:
            log.debug("IP-Check via %s fehlgeschlagen: %s", url, exc)
            continue

    log.error("Konnte aktuelle IP über keinen Dienst ermitteln.")
    return None


def change_identity() -> Optional[str]:
    """Fordert eine neue Tor-Identity an und gibt die neue IP zurück.

    Returns:
        Neue IP-Adresse oder None bei Fehler.
    """
    if not tor_service("reload"):
        log.error("Tor-Reload fehlgeschlagen – IP nicht gewechselt.")
        return None

    time.sleep(TOR_RELOAD_WAIT)
    new_ip = get_current_ip()
    if new_ip:
        log.info("✓ Neue IP: %s", new_ip)
    else:
        log.warning("IP-Wechsel durchgeführt, aber neue IP konnte nicht ermittelt werden.")
    return new_ip


# =============================== Hauptlogik ================================


def run_changer(interval: int, count: int) -> None:
    """Hauptschleife für den IP-Wechsel.

    Args:
        interval: Pause zwischen Wechseln in Sekunden.
        count:    Anzahl der Wechsel (0 = unendlich).
    """
    mode = "unendlich" if count == 0 else f"{count}×"
    log.info(
        "Starte IP-Rotation: Intervall=%ds, Wechsel=%s (Ctrl+C zum Beenden)",
        interval,
        mode,
    )

    iteration = 0
    while not _shutdown_requested:
        # Warte das Intervall ab (in 1s-Schritten für schnelles Shutdown)
        for _ in range(interval):
            if _shutdown_requested:
                break
            time.sleep(1)

        if _shutdown_requested:
            break

        iteration += 1
        log.info("--- Wechsel #%d ---", iteration)
        change_identity()

        if count > 0 and iteration >= count:
            log.info("Gewünschte Anzahl (%d) erreicht.", count)
            break

    log.info("AutoTor beendet.")


def parse_args() -> argparse.Namespace:
    """CLI-Argumente parsen."""
    parser = argparse.ArgumentParser(
        description=f"AutoTor IP Changer v{VERSION} – Automatischer IP-Wechsel über Tor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  sudo python3 autotor.py                     # Interaktiver Modus\n"
            "  sudo python3 autotor.py -i 90 -c 10         # 10 Wechsel, alle 90s\n"
            "  sudo python3 autotor.py -i 60 --infinite     # Endlos, alle 60s\n"
        ),
    )
    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=None,
        help="Intervall in Sekunden zwischen IP-Wechseln (Standard: interaktiv)",
    )
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=None,
        help="Anzahl der IP-Wechsel (Standard: interaktiv)",
    )
    parser.add_argument(
        "--infinite",
        action="store_true",
        help="Endlose IP-Rotation (überschreibt --count)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Debug-Ausgabe aktivieren",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"AutoTor v{VERSION}",
    )
    return parser.parse_args()


def interactive_input() -> tuple[int, int]:
    """Fragt Intervall und Anzahl interaktiv ab.

    Returns:
        Tuple (interval, count) wobei count=0 für unendlich steht.
    """
    while True:
        try:
            raw = input("\n[?] Intervall in Sekunden zwischen IP-Wechseln [60]: ").strip()
            interval = int(raw) if raw else 60
            if interval < 5:
                log.warning("Intervall zu klein – Minimum ist 5 Sekunden.")
                continue
            break
        except ValueError:
            log.warning("Bitte eine gültige Zahl eingeben.")

    while True:
        try:
            raw = input(
                "[?] Anzahl der Wechsel (0 oder Enter = endlos): "
            ).strip()
            count = int(raw) if raw else 0
            if count < 0:
                log.warning("Bitte eine nicht-negative Zahl eingeben.")
                continue
            break
        except ValueError:
            log.warning("Bitte eine gültige Zahl eingeben.")

    return interval, count


def main() -> None:
    """Einstiegspunkt."""
    args = parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    print(BANNER)

    # --- Voraussetzungen ---
    check_root()
    check_dependencies()

    # --- Tor starten ---
    log.info("Starte Tor-Dienst …")
    if not tor_service("start"):
        log.error("Tor konnte nicht gestartet werden.")
        sys.exit(1)

    if not wait_for_tor():
        log.error("Tor-Proxy nicht verfügbar – Abbruch.")
        sys.exit(1)

    # --- Initiale IP anzeigen ---
    initial_ip = get_current_ip()
    if initial_ip:
        log.info("Aktuelle Tor-Exit-IP: %s", initial_ip)
    else:
        log.warning("Initiale IP konnte nicht ermittelt werden – fahre trotzdem fort.")

    # --- Parameter bestimmen ---
    if args.interval is not None:
        interval = max(args.interval, 5)
        count = 0 if args.infinite else (args.count if args.count is not None else 0)
    else:
        interval, count = interactive_input()
        if args.infinite:
            count = 0

    # --- Rotation starten ---
    run_changer(interval, count)


if __name__ == "__main__":
    main()
