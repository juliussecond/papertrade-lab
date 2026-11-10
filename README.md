# PaperTrade Lab – iPad-freundliche Demo

Eine kleine Paper-Trading-Web-App. Sie zeigt Kursdaten von Twelve Data und verwaltet ein virtuelles Portfolio lokal in SQLite. **Es werden keine echten Orders versendet und es gibt keine Echtgeld-Funktion.**

## Auf dem iPad verwenden

Das iPad kann die App im Safari-Browser bedienen. Für die erste Veröffentlichung ist ein Hosting-Dienst nötig, damit die App eine Webadresse bekommt. Ein einfacher Weg:

1. Lade diesen ZIP-Ordner auf einen Computer oder in einen GitHub-Account hoch.
2. Lege ein privates GitHub-Repository an und lade `app.py` und `requirements.txt` hoch.
3. Öffne [Streamlit Community Cloud](https://share.streamlit.io/) und verbinde das Repository.
4. Wähle `app.py` als Hauptdatei und veröffentliche die App.
5. In den App-Einstellungen unter **Secrets** kannst du später API-Zugangsdaten als Secret hinterlegen. Diese Starterversion fragt den Key zunächst im Seitenmenü ab.
6. Öffne die erzeugte Webadresse auf dem iPad in Safari.

**Wichtig:** Lass einen Erziehungsberechtigten bei Konten, Veröffentlichungen und API-Schlüsseln mithelfen und prüft die Alters- und Nutzungsbedingungen der Anbieter. Veröffentliche niemals einen API-Key in einem öffentlichen GitHub-Repository.

## Lokal starten (Mac/PC)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Daten

Die App nutzt Twelve Data `time_series` mit Tagesintervallen. Das ist **kein garantierter tick-genauer Live-Feed**. Datenumfang, Verzögerung und API-Limits hängen vom gewählten Tarif und der Börse ab.

## Demo-Regeln

- Startguthaben: 10.000 US-Dollar virtuell
- Simulierte Gebühr: 0,10 %
- Simulierte Slippage-Annahme: 0,05 %
- Käufe/Verkäufe verändern nur die lokale Demo-Datenbank
- Kein Broker, keine echten Orders, keine automatische Echtgeld-Ausführung

Die Demo-Datenbank liegt in `papertrade.db`. Bei manchen Cloud-Hostings kann lokaler Speicher nach Neustarts oder Redeployments zurückgesetzt werden. Für dauerhafte Speicherung wäre später eine externe Datenbank nötig.
