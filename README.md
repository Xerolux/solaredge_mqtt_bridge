
# SolarEdge MQTT Bridge

Ein Python-Skript, das Daten von einem SolarEdge-EnergiezÃ¤hler Ã¼ber Modbus liest und an einen MQTT-Broker sendet. Dies ermÃ¶glicht die Integration von SolarEdge-Energiedaten in IoT-Systeme und Energiemanagement-Plattformen.

---

## Funktionen / Features

- Liest Daten wie Energieverbrauch, Leistung und Netzparameter von einem SolarEdge-ZÃ¤hler.
- Publiziert Daten in einem strukturierten Format Ã¼ber MQTT.
- Konfigurierbare Einstellungen Ã¼ber eine YAML-Datei.
- Automatische Wiederverbindung fÃ¼r Modbus und MQTT, falls die Verbindung unterbrochen wird.
- **Inkrementelles Modelltraining**: Erlaubt die schrittweise Anpassung des Vorhersagemodells basierend auf neuen Daten, ohne vorherige Daten erneut zu trainieren.
- **Wetterintegration**: Optionaler Abruf von Wetterdaten (z. B. Temperatur und BewÃ¶lkungsgrad) zur Verbesserung der Vorhersagegenauigkeit.
- **Speicher- und Wiederverwendung des Modells**: Trainierte Modelle kÃ¶nnen gespeichert und wiederverwendet werden, um die Ladezeit zu optimieren.
- **API-Dashboard**: Webinterface fÃ¼r die Visualisierung von Echtzeitdaten und Vorhersagen.
- **Anomalie-Erkennung**: Identifikation von abnormalen DatenÃ¤nderungen.

---

## Voraussetzungen / Prerequisites

- **Python 3.7+ (kompatibel mit Python 3.12)**
- SolarEdge-EnergiezÃ¤hler mit aktiviertem Modbus TCP
- MQTT-Broker zum Publizieren der Daten

---

## Erforderliche Python-Bibliotheken / Required Python Libraries

Installiere die notwendigen Bibliotheken Ã¼ber pip:

```bash
pip install pymodbus paho-mqtt pyyaml influxdb-client scikit-learn requests matplotlib flask
```

---

## Installation und Einrichtung / Installation and Setup

### KompatibilitÃ¤t mit Python 3.12 / Python 3.12 Compatibility

Dieses Skript ist mit Python 3.12 kompatibel. Um sicherzustellen, dass alles funktioniert:

1. Installiere Python 3.12 und erstelle eine virtuelle Umgebung:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

2. Installiere die AbhÃ¤ngigkeiten:
   ```bash
   pip install -r requirements.txt
   ```

3. Starte das Skript:
   ```bash
   python main.py
   ```

---

### AusfÃ¼hren als Systemd-Dienst / Running as a Systemd Service

Um das Skript als Systemd-Dienst auszufÃ¼hren:

1. Erstelle eine Systemd-Service-Datei:
   ```bash
   sudo nano /etc/systemd/system/solaredge_mqtt.service
   ```

2. FÃ¼ge die folgende Konfiguration hinzu (ersetze `/path/to/venv` und `/path/to/project` durch die tatsÃ¤chlichen Pfade):

   ```ini
   [Unit]
   Description=SolarEdge MQTT Bridge Service
   After=network.target

   [Service]
   ExecStart=/path/to/venv/bin/python /path/to/main.py
   WorkingDirectory=/path/to/project
   Restart=always
   User=your-username
   Environment="PYTHONUNBUFFERED=1"

   [Install]
   WantedBy=multi-user.target
   ```

3. Aktivieren und starten des Dienstes:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable solaredge_mqtt.service
   sudo systemctl start solaredge_mqtt.service
   ```

4. Status des Dienstes prÃ¼fen:
   ```bash
   sudo systemctl status solaredge_mqtt.service
   ```

5. Dienst stoppen, neu starten oder Logs anzeigen:
   ```bash
   sudo systemctl stop solaredge_mqtt.service
   sudo systemctl restart solaredge_mqtt.service
   journalctl -u solaredge_mqtt.service
   ```

---

## Nutzung / Usage

Das Skript starten, um Daten zu lesen und an MQTT zu senden:

```bash
python main.py
```

---

## Konfigurationsdatei (`config.yaml`) / Configuration File (`config.yaml`)

Die Konfiguration erfolgt Ã¼ber die `config.yaml` Datei:

- **Modbus-Einstellungen**: IP, Port und Unit-ID fÃ¼r die Verbindung mit dem SolarEdge-ZÃ¤hler.
- **MQTT-Einstellungen**: IP des Brokers, Port, Topic und optional Benutzerdaten.
- **Allgemeine Einstellungen**: Intervall fÃ¼r die Datenerfassung und Parameter fÃ¼r Wiederverbindung.
- **Vorhersageeinstellungen**: 
  - **Modelltraining**: Optionales inkrementelles Training des Modells, bei dem neue Daten mit dem bestehenden Modell kombiniert werden.
  - **Speichern und Laden des Modells**: Das trainierte Modell kann gespeichert und bei Bedarf wiederverwendet werden.
  - **Wetterintegration**: Optionaler Abruf von Wetterdaten wie Temperatur und BewÃ¶lkung, mit Standort- und API-SchlÃ¼ssel-Einstellungen.
- **API-Dashboard**: Aktivierung eines Web-Interfaces zur Visualisierung der aktuellen und vorhergesagten Werte.
- **Anomalie-Erkennung**: Schwellwertbasierte Erkennung von ungewÃ¶hnlichen Ã„nderungen.

---

## Fehlerbehebung / Troubleshooting

- Stelle sicher, dass Modbus TCP auf dem SolarEdge-ZÃ¤hler aktiviert ist.
- ÃœberprÃ¼fe die MQTT-Broker-Anmeldedaten und die Netzwerkverbindung.
- PrÃ¼fe die `config.yaml` auf korrekte IP-Adressen und Ports.

---

## Lizenz / License

Dieses Projekt steht unter der MIT-Lizenz. Siehe die [LICENSE](LICENSE) Datei fÃ¼r mehr Details.

---

## Beitrag / Contribution

BeitrÃ¤ge sind willkommen! Bitte Ã¶ffne ein Issue, um Ã„nderungen oder Verbesserungen zu besprechen.
