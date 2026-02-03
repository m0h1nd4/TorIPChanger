# ⚡ TorIPChanger

**Automatischer IP-Wechsel über das Tor-Netzwerk.**

Fordert in konfigurierbaren Intervallen eine neue Tor-Identity an und rotiert damit die öffentliche Exit-IP. Gedacht für Security-Research, Penetration-Testing und Privacy-Anwendungen auf Linux-Systemen.

```
  ┌──────────────────────────────────────────────────────────┐
  │  ▄▄▄   ▄▄  ▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄ ▄▄▄▄▄▄  ▄▄▄▄▄▄  │
  │  █   █ █  █   █   █       █ █       █   ▄  ██   ▄  █ │
  │  █   █ █  █   █   █   ▄   █ █▄     ▄█  █ █ ██  █ █ █ │
  │  █   █▄█  █   █   █  █ █  █   █   █ █   █▄▄█▄█   █▄█ █│
  │  █       █   █   █  █▄█  █   █   █ █    ▄▄  █    ▄▄  █│
  │  █   ▄   █   █   █       █   █   █ █   █  █ █   █  █ █│
  │  █▄▄█ █▄▄█▄▄▄█▄▄▄█▄▄▄▄▄▄▄█   █▄▄▄█ █▄▄▄█  █▄█▄▄▄█  █▄│
  │                                                          │
  │  ╔═══════════════════════════════════════════════════╗    │
  │  ║  >> TOR IP CHANGER // v3.0 // IDENTITY ROTATION  ║    │
  │  ╚═══════════════════════════════════════════════════╝    │
  └──────────────────────────────────────────────────────────┘
```

---

## Inhaltsverzeichnis

- [Features](#features)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Nutzung](#nutzung)
- [Wie der Code funktioniert](#wie-der-code-funktioniert)
- [Architektur](#architektur)
- [Sicherheitsrisiken und Hinweise](#sicherheitsrisiken-und-hinweise)
- [Konfiguration](#konfiguration)
- [Troubleshooting](#troubleshooting)
- [Lizenz](#lizenz)

---

## Features

| Feature | Beschreibung |
|---|---|
| **DNS-Leak-Schutz** | `socks5h://` leitet DNS-Auflösung über Tor – verhindert, dass der ISP sieht welche Domains aufgelöst werden |
| **Tor-Verifizierung** | Prüft über die offizielle Tor-Project-API, ob der Traffic tatsächlich über das Tor-Netzwerk läuft |
| **Fallback IP-Check** | Drei unabhängige Dienste (Tor-Project, ipify, AWS) als Fallback-Kette zur IP-Ermittlung |
| **Graceful Shutdown** | Signal-Handler für `SIGINT`/`SIGTERM` – sauberes Beenden nach dem aktuellen Zyklus |
| **CLI & Interaktiv** | Vollständige argparse-CLI mit Flags *oder* interaktive Abfrage – flexibel einsetzbar |
| **Dependency-Check** | Prüft Root-Rechte, Tor-Installation und Python-Pakete *vor* dem Start |
| **Systemd + SysV** | Automatischer Fallback von `systemctl` auf `service` für ältere Systeme |
| **Port-Readiness** | Wartet aktiv auf den Tor-SOCKS-Port statt blindem `sleep` |

---

## Voraussetzungen

| Komponente | Minimum | Empfohlen |
|---|---|---|
| **OS** | Debian/Ubuntu-basiertes Linux | Kali Linux, Parrot OS, Ubuntu 22.04+ |
| **Python** | 3.10+ | 3.12+ |
| **Tor** | Beliebige Version aus den Paketquellen | Aktuelle Version |
| **Rechte** | Root (`sudo`) | Root |

---

## Installation

### Schnellstart (manuell)

```bash
# 1. Repository klonen
git clone https://github.com/m0h1nd4/TorIPChanger.git
cd TorIPChanger

# 2. Abhängigkeiten installieren
sudo apt update && sudo apt install tor -y
pip3 install requests requests[socks]

# 3. Direkt ausführen
sudo python3 autotor.py
```

### Systemweite Installation

```bash
# Installiert 'autotor' als systemweiten Befehl
sudo python3 install.py install

# Danach einfach:
sudo autotor
```

### Deinstallation

```bash
sudo python3 install.py uninstall
```

---

## Nutzung

### Interaktiver Modus

```bash
sudo autotor
```

Das Script fragt nach dem Intervall (Sekunden zwischen Wechseln) und der Anzahl der gewünschten Wechsel.

### CLI-Modus (für Scripting & Automation)

```bash
# 10 Wechsel im 90-Sekunden-Takt
sudo autotor --interval 90 --count 10

# Endlose Rotation im 60-Sekunden-Takt
sudo autotor --interval 60 --infinite

# Mit Debug-Ausgabe
sudo autotor -i 60 --infinite -v

# Hilfe anzeigen
sudo autotor --help
```

### Beispielausgabe

```
14:32:01 [INFO] ✓ Tor gefunden: /usr/bin/tor
14:32:01 [INFO] ✓ Python-Abhängigkeiten vorhanden
14:32:01 [INFO] Starte Tor-Dienst …
14:32:01 [INFO] Warte auf Tor-SOCKS-Proxy (127.0.0.1:9050) …
14:32:03 [INFO] ✓ Tor-Proxy erreichbar
14:32:04 [INFO] Aktuelle Tor-Exit-IP: 185.220.101.42
14:32:04 [INFO] Starte IP-Rotation: Intervall=60s, Wechsel=unendlich (Ctrl+C zum Beenden)
14:33:04 [INFO] --- Wechsel #1 ---
14:33:07 [INFO] ✓ Neue IP: 104.244.76.13
14:34:07 [INFO] --- Wechsel #2 ---
14:34:10 [INFO] ✓ Neue IP: 199.249.230.87
```

---

## Wie der Code funktioniert

### Überblick

Das Tool steuert den lokal laufenden Tor-Daemon. Tor öffnet einen SOCKS5-Proxy auf `127.0.0.1:9050`. Jedes `service tor reload` veranlasst Tor, neue Circuits (Verbindungsketten über drei Relays) aufzubauen – und damit eine neue Exit-Node mit neuer IP zu verwenden.

### Ablaufdiagramm

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  START       │────►│ check_root()    │────►│ check_deps()     │
└─────────────┘     │ euid == 0?      │     │ tor installiert? │
                    │ Ja → weiter     │     │ requests da?     │
                    │ Nein → exit(1)  │     │ socks da?        │
                    └─────────────────┘     └────────┬─────────┘
                                                     │
                    ┌─────────────────┐              │
                    │ tor_service()   │◄─────────────┘
                    │ "start"         │
                    │ systemctl → svc │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ wait_for_tor()  │
                    │ Socket-Connect  │
                    │ auf :9050       │
                    │ max 30s Timeout │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ get_current_ip()│
                    │ Request über    │
                    │ Tor-Proxy an    │
                    │ IP-Check-APIs   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐      ┌──────────────────┐
                    │ run_changer()   │─────►│ change_identity()│
                    │ Hauptschleife   │      │ tor reload       │
                    │ sleep(interval) │◄─────│ + get_current_ip │
                    │ bis count oder  │      └──────────────────┘
                    │ SIGINT/SIGTERM  │
                    └─────────────────┘
```

### Detaillierte Code-Erklärung

#### `autotor.py` – Hauptscript

**Konstanten und Proxy-Konfiguration**

```python
TOR_PROXIES = {
    "http":  f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
    "https": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
}
```

Das `h` in `socks5h://` ist entscheidend: Es sorgt dafür, dass auch DNS-Anfragen über den SOCKS-Proxy (und damit über Tor) aufgelöst werden. Ohne das `h` würde der lokale DNS-Resolver des Systems genutzt – der ISP könnte sehen welche Domains aufgerufen werden (DNS-Leak).

Drei IP-Check-URLs sind als Fallback-Kette definiert. Die Tor-Project-API hat Priorität, weil sie zusätzlich meldet ob der Traffic wirklich über Tor läuft (`IsTor: true/false`).

**Signal-Handling**

```python
_shutdown_requested = False

def _signal_handler(signum, _frame):
    global _shutdown_requested
    _shutdown_requested = True
```

Statt `KeyboardInterrupt` in einer Endlosschleife zu fangen (was zu unvollständigen Zyklen führen kann), setzt der Handler ein globales Flag. Die Hauptschleife prüft dieses Flag in jedem 1-Sekunden-Tick und beendet sich sauber nach dem aktuellen Zyklus. Das verhindert, dass ein `tor reload` halb ausgeführt wird.

**Root-Check und Dependency-Prüfung**

`check_root()` prüft `os.geteuid() == 0`. Ohne Root kann weder der Tor-Service gesteuert noch der SOCKS-Port gebunden werden. `check_dependencies()` verifiziert die Tor-Binary via `shutil.which()` und die Python-Pakete per Import-Versuch. Im Fehlerfall gibt es klare Installationsanweisungen statt kryptischer Tracebacks.

**Tor-Service-Steuerung**

```python
def tor_service(action: str) -> bool:
    for cmd in (
        ["systemctl", action, "tor"],
        ["service", "tor", action],
    ):
        ...
```

Versucht zuerst `systemctl` (moderne systemd-basierte Systeme), fällt auf `service` zurück (SysV-Init). Jeder Aufruf nutzt `subprocess.run()` mit `check=True`, Timeout und Fehlerbehandlung – im Gegensatz zum Original das `os.system()` ohne jede Prüfung verwendete.

**Tor-Readiness-Check**

```python
def wait_for_tor(max_wait=30):
    with socket.create_connection((TOR_SOCKS_HOST, TOR_SOCKS_PORT), timeout=2):
        ...
```

Versucht in einer Schleife eine TCP-Verbindung zum SOCKS-Port. Erst wenn die Verbindung steht, ist Tor bereit. Das Original wartete blind 3 Sekunden – was auf langsamen Systemen zu früh und auf schnellen unnötig lang war.

**IP-Ermittlung**

`get_current_ip()` iteriert über die drei Check-URLs. Für die Tor-Project-API wird zusätzlich das `IsTor`-Feld geprüft. Wenn dieses `false` ist, gibt es eine explizite Warnung – der Traffic läuft dann nicht über Tor, obwohl der Proxy konfiguriert ist (z.B. wenn Tor noch alte Circuits nutzt). HTTP-Fehler und Timeouts werden pro URL gefangen, sodass ein ausgefallener Dienst die Funktion nicht zum Absturz bringt.

**Identity-Rotation**

```python
def change_identity():
    tor_service("reload")  # Neue Circuits aufbauen
    time.sleep(TOR_RELOAD_WAIT)
    return get_current_ip()
```

`tor reload` sendet ein `SIGHUP` an den Tor-Prozess, der daraufhin neue Circuits aufbaut. Die kurze Wartezeit gibt Tor Zeit die neuen Circuits zu etablieren bevor die IP geprüft wird.

**Hauptschleife**

```python
def run_changer(interval, count):
    while not _shutdown_requested:
        for _ in range(interval):
            if _shutdown_requested:
                break
            time.sleep(1)
        change_identity()
```

Das Intervall wird in 1-Sekunden-Schritten abgewartet. So reagiert das Script innerhalb einer Sekunde auf Shutdown-Signale, statt bis zum Ende eines möglicherweise 5-Minuten-Intervalls blockiert zu sein.

#### `install.py` – Installer

Der Installer kopiert `autotor.py` nach `/usr/share/autotor/` und erstellt einen Shell-Wrapper in `/usr/bin/autotor`. Der Wrapper ist ein minimales Shell-Script das `python3` mit dem installierten Script aufruft und alle CLI-Argumente weiterreicht (`"$@"`). Vor jeder destruktiven Aktion (Überschreiben, Löschen) wird eine Bestätigung abgefragt. Berechtigungen werden explizit via `stat`-Konstanten gesetzt statt mit `chmod 777`.

---

## Architektur

```
TorIPChanger/
├── autotor.py       # Hauptscript – IP-Rotation über Tor
├── install.py       # Systemweiter Installer/Uninstaller
├── README.md        # Dokumentation
└── LICENSE          # MIT License
```

### Abhängigkeitsgraph

```
autotor.py
├── argparse      (stdlib)  CLI-Parsing
├── logging       (stdlib)  Strukturierte Ausgabe
├── os            (stdlib)  Root-Check (geteuid)
├── shutil        (stdlib)  Binary-Lookup (which)
├── signal        (stdlib)  Graceful Shutdown
├── socket        (stdlib)  Tor Port-Check
├── subprocess    (stdlib)  Tor-Service-Steuerung
├── sys           (stdlib)  Exit-Codes
├── time          (stdlib)  Sleep / Timing
├── requests      (PyPI)    HTTP-Requests über Proxy
└── PySocks       (PyPI)    SOCKS5-Proxy-Support für requests
```

---

## Sicherheitsrisiken und Hinweise

### ⚠️ Kritisch: Was AutoTor NICHT tut

AutoTor routet **ausschließlich seine eigenen IP-Check-Requests** über Tor. Der restliche System-Traffic (Browser, andere Anwendungen, DNS außerhalb des Scripts) geht **direkt über die echte IP**. AutoTor ist kein Ersatz für eine vollständige Tor-Konfiguration.

### Risiko-Matrix

| Risiko | Schwere | Beschreibung | Gegenmaßnahme |
|---|---|---|---|
| **Kein systemweiter Tor-Proxy** | 🔴 Hoch | Nur das Script selbst nutzt Tor. Alle anderen Programme nutzen die echte IP. | `torsocks` für einzelne Programme, oder transparenten Tor-Proxy einrichten (siehe unten) |
| **WebRTC / Browser Leaks** | 🔴 Hoch | Browser können die echte IP über WebRTC, Canvas Fingerprinting oder Browser-Plugins leaken – selbst wenn der SOCKS-Proxy konfiguriert ist. | Tor Browser verwenden statt normaler Browser + Proxy |
| **Root-Ausführung** | 🟡 Mittel | Script läuft als Root, da es den Tor-Service steuern muss. Ein Bug oder eine kompromittierte Dependency könnte Root-Zugriff ermöglichen. | Script-Quelle prüfen. Nur vertrauenswürdige Pakete installieren. |
| **IP-Check über Drittanbieter** | 🟡 Mittel | Die IP-Check-Dienste sehen jeden Request und könnten Nutzungsprofile erstellen (Timing, Häufigkeit). | Intervall nicht zu kurz wählen (>30s). Dienste loggen erfahrungsgemäß nicht, aber Garantie gibt es nicht. |
| **Timing-Korrelation** | 🟡 Mittel | Ein Angreifer der sowohl den Entry-Node als auch das Ziel kontrolliert, kann über Timing-Analyse Traffic korrelieren – besonders bei regelmäßigen Rotation-Mustern. | Für hochsensitive Anwendungen: Tails OS oder Whonix nutzen. |
| **Exit-Node Sniffing** | 🟡 Mittel | Der letzte Knoten im Tor-Circuit (Exit-Node) kann unverschlüsselten Traffic mitlesen. | Nur HTTPS verwenden. Sensible Daten nie über unverschlüsselte Verbindungen senden. |
| **Tor-Circuit Aufbauzeit** | 🟢 Niedrig | Nach `tor reload` brauchen neue Circuits 1–5 Sekunden. Anfragen in dieser Zeit können fehlschlagen. | `TOR_RELOAD_WAIT` erhöhen falls nötig. |
| **Rate-Limiting der IP-Check-APIs** | 🟢 Niedrig | Bei zu häufigen Requests (Intervall <10s) können die Check-Dienste blocken. | Minimum-Intervall von 5 Sekunden ist im Script eingebaut. |

### Empfehlungen für verschiedene Einsatz-Szenarien

**Web-Scraping / OSINT Research:**
AutoTor reicht als IP-Rotator, wenn die Requests ebenfalls über den SOCKS-Proxy geroutet werden. Beispiel mit `requests`:

```python
import requests
proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
resp = requests.get("https://example.com", proxies=proxies)
```

**Anonymes Browsing:**
AutoTor allein ist dafür **nicht geeignet**. Nutze stattdessen den Tor Browser oder Tails OS. Ein normaler Browser mit SOCKS-Proxy leakt zu viele Metadaten.

**Penetration Testing:**
Für Tools wie `nmap`, `nikto`, `sqlmap` den Traffic über `proxychains` oder `torsocks` leiten:

```bash
# proxychains konfigurieren (/etc/proxychains.conf):
# socks5 127.0.0.1 9050

proxychains nmap -sV target.com
torsocks curl https://target.com
```

**Maximale Anonymität:**
AutoTor ist dafür nicht das richtige Tool. Verwende Whonix (VM-basierte Tor-Isolation) oder Tails (Live-OS das allen Traffic über Tor routet).

### Transparenter Tor-Proxy (systemweit)

Wer den gesamten System-Traffic über Tor leiten möchte, kann einen transparenten Proxy mit `iptables` einrichten. **Achtung:** Das ist ein komplexes Setup mit Risiken – nur für erfahrene Admins.

```bash
# Grundidee (vereinfacht, NICHT produktionsreif):
iptables -t nat -A OUTPUT -m owner --uid-owner debian-tor -j RETURN
iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports 9040
```

Eine vollständige Anleitung findet sich in der [Tor-Dokumentation zu TransPort](https://community.torproject.org/relay/setup/bridge/debian-ubuntu/).

---

## Konfiguration

### Konstanten in `autotor.py`

| Konstante | Default | Beschreibung |
|---|---|---|
| `TOR_SOCKS_HOST` | `127.0.0.1` | Host des Tor-SOCKS-Proxy |
| `TOR_SOCKS_PORT` | `9050` | Port des Tor-SOCKS-Proxy |
| `IP_CHECK_URLS` | 3 URLs | Fallback-Kette zur IP-Ermittlung |
| `REQUEST_TIMEOUT` | `15` | Timeout in Sekunden für IP-Check-Requests |
| `TOR_RELOAD_WAIT` | `2` | Wartezeit nach `tor reload` in Sekunden |

### Tor-Konfiguration (`/etc/tor/torrc`)

Relevante Einstellungen für die Nutzung mit AutoTor:

```bash
# SOCKS-Port (Standard, normalerweise bereits gesetzt)
SocksPort 9050

# Neuen Circuit erzwingen nach X Sekunden (Standard: 600)
MaxCircuitDirtiness 60

# Bestimmte Länder als Exit-Node ausschließen
ExcludeExitNodes {ru},{cn},{ir}

# Nur bestimmte Länder als Exit erlauben
# ExitNodes {de},{nl},{ch},{se}
```

Nach Änderungen: `sudo systemctl restart tor`

---

## Troubleshooting

**"Tor-Proxy nicht erreichbar nach 30 Sekunden"**
Tor braucht beim ersten Start Zeit um Circuits aufzubauen. Prüfe den Status mit `sudo systemctl status tor` und die Logs mit `sudo journalctl -u tor -f`. Firewall-Regeln können den Aufbau blockieren.

**"Tor-Project meldet: Traffic läuft NICHT über Tor!"**
Der SOCKS-Proxy ist erreichbar, aber die Tor-Project-API erkennt den Traffic nicht als Tor-Traffic. Mögliche Ursachen: Tor hat noch keine gültigen Circuits, oder ein HTTP-Proxy zwischen Client und Tor fängt den Traffic ab. Warte einige Sekunden und versuche es erneut.

**IP ändert sich nicht nach Reload**
Tor garantiert nicht bei jedem Reload eine neue Exit-Node. Bei wenigen verfügbaren Exit-Nodes kann dieselbe IP mehrfach zugewiesen werden. `MaxCircuitDirtiness` in der `torrc` auf einen niedrigeren Wert setzen kann helfen.

**"Permission denied" trotz sudo**
Einige Container-Umgebungen (Docker, LXC) erlauben kein `systemctl`. Tor muss dann manuell gestartet werden: `tor &` und das Script mit `--interval` und `--infinite` aufrufen.

---

## Lizenz

[MIT](LICENSE) – Nutzung auf eigene Verantwortung. Dieses Tool ist für legale Zwecke wie Security-Research, Penetration-Testing (mit Genehmigung) und Privacy-Schutz gedacht. Der Autor übernimmt keine Haftung für missbräuchliche Verwendung.
