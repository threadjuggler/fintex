# Pilot-Akquise: Web-Agenturen (Entwurf)

Ziel der Woche-1-Gate: **5 zahlende Piloten.** Diese Datei: Ansprache-Text + Vorgehen,
um die erste Welle rauszubekommen. Bau dient nur dazu, etwas Vorführbares zu haben.

## Positionierung (der Aufhänger)

> XRechnung **validieren und erzeugen** per API — **gehostet in Deutschland**, ohne
> US-Subdienstleister im Datenpfad, **Zero-Retention** (Rechnungen werden nur im
> Speicher verarbeitet, nie gespeichert). Validierung über den offiziellen
> KoSIT-Validator, also dieselben Ergebnisse wie das amtliche Prüftool.

Warum Agenturen: Sie bauen Shops/Portale/Branchensoftware für KMU, Handwerk und
öffentliche Auftraggeber — alle seit 2025 verpflichtet, E-Rechnungen zu **empfangen**,
zunehmend zu **senden**. Die Agentur will das nicht selbst bauen → eine deutsche API
mit klarer Rechtslage ist ein einfaches „Ja".

## ⚠️ Rechtlicher Hinweis zur Kaltansprache

Kalte Werbe-E-Mails an Unternehmen sind in DE über **§7 UWG** stark eingeschränkt
(grundsätzlich Einwilligung nötig; mutmaßliche Einwilligung ist eng). Sicherer als
Massen-Kaltmail:

- **Warme Kanäle zuerst:** eigenes Netzwerk, LinkedIn-Direktnachricht, Empfehlungen,
  Branchen-Slacks/Foren, Meetups/Events.
- Nur Kontakte anschreiben, bei denen ein **konkreter sachlicher Bezug** plausibel ist.
- Kein gekaufter Verteiler, keine generische Massensendung.

Der Text unten funktioniert genauso als LinkedIn-Nachricht / warme Intro.

## Ansprache-Entwurf (kurz, DE)

**Betreff-Optionen**
- „XRechnung-API – validieren & erzeugen, gehostet in Deutschland"
- „E-Rechnung für Ihre Kundenprojekte – ohne eigenes XRechnung-Modul"

**Text**

> Hallo [Name],
>
> kurze Frage als [Agentur]: Bauen Sie für Kund:innen Projekte, in denen E-Rechnungen
> (XRechnung/ZUGFeRD) anfallen — Empfang oder Erstellung?
>
> Ich biete dafür eine schlanke API:
> - **/validate** – XML oder ZUGFeRD-PDF rein, sauberer Prüfbericht raus (offizieller
>   KoSIT-Validator, mit Regelcodes).
> - **/generate** – JSON rein, geprüfte XRechnung raus (nur gültige Rechnungen verlassen
>   die API).
>
> Gehostet **in Deutschland**, ohne US-Subdienstleister, Zero-Retention (Rechnungen
> werden nicht gespeichert). Spart Ihnen das eigene XRechnung-Modul.
>
> Ich suche gerade **5 Pilotkund:innen** zu vergünstigten Konditionen. 15 Minuten, ob es
> für ein aktuelles Projekt passt? Hier ein Live-Beispiel zum Selbst-Ausprobieren:
>
> ```sh
> curl -H "X-API-Key: <pilot-key>" -F "file=@rechnung.xml" https://api.codedbyme.de/validate
> ```
>
> Viele Grüße
> [Dein Name]

**Prinzipien:** kurz, konkreter Bezug, ein klarer CTA (15 Min), sofort selbst testbar.
Pro Empfänger 1–2 Sätze personalisieren (welche Projekte, welche Branche).

## Zielliste aufbauen (15–20)

Keine echten Firmen erfunden — selbst recherchieren. Kriterien:

- DE-Agentur, baut Webshops/Portale/Branchen- oder Verwaltungssoftware.
- Kundschaft: KMU, Handwerk, **öffentliche Auftraggeber** (höchster XRechnung-Druck).
- Stack passt zu API-Integration (nicht reine Design-Boutique).

Quellen: eigenes Netzwerk; LinkedIn (Suche „Agentur" + „TYPO3/Shopware/Magento/öffentliche
Hand"); Shopware/Shopify/TYPO3-Partnerverzeichnisse; GovTech-/Verwaltungs-Digitalisierungs-Communities;
lokale IT-/Gründer-Meetups.

| # | Agentur | Kontakt/Rolle | Kanal | Bezug (1 Satz) | Status |
|---|---|---|---|---|---|
| 1 | | | LinkedIn/Mail/warm | | offen |
| 2 | | | | | |
| … | | | | | |

## Cadence

1. Erstkontakt (personalisiert).
2. Nach ~4 Werktagen ein kurzer Follow-up („oben nochmal, falls untergegangen").
3. Danach Ruhe. Antworten → 15-Min-Call → Pilot-Key ausgeben → erstes echtes Projekt.

Gate-Tracking: Ziel **5 zahlende Piloten**. Pipeline hier oder im CRM pflegen.
