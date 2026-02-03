# AutoTor IP Changer v3.0

Automatischer IP-Wechsel über das Tor-Netzwerk. Fordert in konfigurierbaren Intervallen eine neue Tor-Identity an und rotiert damit die öffentliche Exit-IP.

## Features

- **DNS-Leak-Schutz** – Nutzt `socks5h://` für DNS-Auflösung über Tor
- **Tor-Verifizierung** – Prüft über die Tor-Project-API, ob Traffic tatsächlich über Tor läuft
- **Graceful Shutdown** – Sauberes Beenden via `Ctrl+C` / `SIGTERM`
- **Fallback IP-Check** – Mehrere Dienste als Fallback zur IP-Ermittlung
- **CLI & Interaktiv** – Nutzbar mit Argumenten oder im interaktiven Modus
- **Dependency-Check** – Prüft alle Voraussetzungen vor dem Start

## Voraussetzungen

- Linux (Debian/Ubuntu-basiert)
- Python 3.10+
- Root-Rechte (`sudo`)

## Installation

```bash
# Abhängigkeiten installieren
sudo apt install tor
pip3 install requests requests[socks]

# AutoTor systemweit installieren
sudo python3 install.py install
```

## Nutzung

### Interaktiver Modus
```bash
sudo autotor
```

### CLI-Modus
```bash
# 10 Wechsel, alle 90 Sekunden
sudo autotor --interval 90 --count 10

# Endlose Rotation, alle 60 Sekunden
sudo autotor --interval 60 --infinite

# Debug-Ausgabe
sudo autotor -i 60 --infinite -v
```

### Hilfe
```bash
sudo autotor --help
```

## Deinstallation

```bash
sudo python3 install.py uninstall
```

## Sicherheitshinweise

> **Wichtig:** AutoTor routet nur den eigenen IP-Check-Traffic über Tor.
> Für vollständige Anonymisierung muss der gesamte System-Traffic über Tor
> geleitet werden (z.B. via `torsocks` oder transparentem Tor-Proxy).

- Der SOCKS5-Proxy ist unter `127.0.0.1:9050` erreichbar
- Anwendungen müssen einzeln für den Proxy konfiguriert werden
- `socks5h://` stellt sicher, dass DNS-Anfragen ebenfalls über Tor laufen

## Lizenz

MIT
