# einvoice-core — Internes Handbuch: Produkt, Vertrieb, Preise, Recht

> **Vertraulich / nur intern.** Dieses Dokument enthält Geschäftsgeheimnisse,
> Preislogik und Strategie. Liegt absichtlich in `instructions/` (vom Deploy
> ausgeschlossen). Nicht an Kunden weitergeben.
>
> **Kein Rechts-/Steuer-/Finanzrat.** Kapitel 4 (Preise) sind Markt-Startwerte zum
> Testen, Kapitel 5 ist eine Vorbereitung fürs Anwaltsgespräch — beides ersetzt
> keine fachliche Beratung. Gesetzliche Fristen/Stände vor Kundengesprächen prüfen.

## Inhalt

1. Produkt-Handbuch (Kundengespräche vorbereiten) + FAQ
2. Was du dem Kunden **nicht** sagst (Know-how schützen)
3. Selbstmarketing & Vertriebsstrategie
4. Preisgestaltung (konkret, pro Leistung)
5. Fragenkatalog für den Anwalt

---

# 1. Produkt-Handbuch

## 1.1 Was ist einvoice-core (in einem Satz)

Eine in Deutschland gehostete HTTP-API, die elektronische Rechnungen (XRechnung /
EN 16931, ZUGFeRD/Factur-X) **prüft** und **erzeugt** — mit dem offiziellen
KoSIT-Validator und ohne dass Rechnungen gespeichert werden (Zero-Retention).

## 1.2 Der gesetzliche Anlass (dein Verkaufsfenster)

E-Rechnungspflicht im inländischen B2B (Wachstumschancengesetz, § 14 UStG) —
**Stand vor jedem Gespräch kurz gegenprüfen**:

- **Seit 01.01.2025:** Jedes inländische Unternehmen muss E-Rechnungen **empfangen**
  können. Das ist der heute schon akute, unausweichliche Bedarf.
- **Übergangsfrist bis 31.12.2026:** Beim **Versand** sind andere Formate (Papier/PDF)
  noch erlaubt.
- **Ab 01.01.2027:** Versandpflicht für Unternehmen mit Vorjahresumsatz > 800.000 €.
- **Ab 01.01.2028:** Versandpflicht für alle.

Botschaft an Kunden: „Empfang müssen Ihre Kunden schon heute, Versand kommt 2027/2028 —
wer jetzt integriert, ist vorbereitet statt unter Druck."

## 1.3 Was die API kann

- **`POST /validate`** — XML **oder** ZUGFeRD/Factur-X-**PDF** rein → sauberer
  JSON-Prüfbericht: gültig/ungültig, Format (UBL/CII), Profil, Version, Regelverstöße
  mit Code (z. B. `BR-DE-15`), Klartext-Meldung und XPath-Position.
- **`POST /generate`** — normalisiertes JSON rein → **XRechnung-CII-XML** raus. Der
  Output wird **vor der Rückgabe intern selbst geprüft** — nur gültige Rechnungen
  verlassen die API.
- `GET /health` für Monitoring.

Beide Endpunkte brauchen einen API-Key (`X-API-Key`).

## 1.4 Wie es technisch aufgebaut ist (für technische Kunden, grob)

```
Internet ──▶ Caddy (TLS) ──▶ App (FastAPI) ──▶ KoSIT-Validator (Sidecar)
                                  ├──▶ PostgreSQL (nur Metadaten)
                                  └──▶ Redis (Rate-Limit)
```

- Gehostet auf einem deutschen Server (Hetzner, DE-Rechenzentrum). **Keine
  US-Subdienstleister im Datenpfad.**
- Validierung über den **offiziellen KoSIT-Validator** → dieselben Ergebnisse wie das
  amtliche Prüfwerkzeug. Validator- und Konfigurationsversion sind fest gepinnt.
- **Zero-Retention:** Rechnungen werden nur im Arbeitsspeicher verarbeitet, **nie**
  auf Platte/DB geschrieben. Gespeichert werden ausschließlich Metadaten: Zeitstempel,
  Dokumenttyp, Ergebnis, Byte-Zahl, **SHA-256-Hashes** von Ein-/Ausgabe und die
  Validator-/Regelwerk-Version.

## 1.5 Integration beim Kunden (so einfach ist es)

1. Kunde bekommt einen API-Key.
2. HTTPS-Request gegen `https://api.snapvoice.de/validate` bzw. `/generate`.
3. Antwort als JSON (validate) bzw. als XML-Datei (generate).

Selbst-Test, den du jedem geben kannst:

```sh
curl -H "X-API-Key: <key>" -F "file=@rechnung.xml" https://api.snapvoice.de/validate
```

## 1.6 FAQ — typische Kundenfragen + gute Antworten

**„Ist das rechtssicher / amtlich anerkannt?"**
Die Prüfung läuft über den offiziellen KoSIT-Validator mit der offiziellen
XRechnung-Konfiguration — also identische Ergebnisse wie das amtliche Tool. Wir liefern
das Ergebnis sauber als API. (Ehrlich bleiben: *wir* sind keine Behörde; wir führen das
amtliche Prüfwerkzeug zuverlässig aus.)

**„Wo liegen meine Daten?"**
In Deutschland, ohne US-Subdienstleister im Datenpfad. Und: Rechnungen werden gar nicht
gespeichert (Zero-Retention) — nur Metadaten/Hashes. Das ist der DSGVO-Vorteil.

**„Was, wenn sich das Gesetz / die XRechnung ändert?"**
Wir aktualisieren die KoSIT-Konfiguration und halten die Version nachvollziehbar. Du
musst nichts tun, die API bleibt aktuell. (Versionspflege ist Teil des Werts.)

**„Was passiert bei einem Ausfall?"**
Hier brauchst du eine ehrliche, klare Linie: angestrebte Verfügbarkeit, Statusseite,
Reaktionszeit. Lieber konservativ versprechen und halten. SLA-Details → Anwalt/AGB.

**„Können wir auch ZUGFeRD-**PDF**s erzeugen?"**
Aktuell erzeugen wir die XRechnung-**XML** (CII), die sich später in ein ZUGFeRD-PDF
einbetten lässt; PDF-Erzeugung ist auf der Roadmap. Validieren können wir ZUGFeRD-PDFs
schon heute. (Nicht mehr versprechen, als gebaut ist.)

**„Wieso nicht einfach selbst den KoSIT-Validator betreiben?"**
Können sie — dann betreiben sie aber Java-Sidecar, Updates, Hosting, Monitoring,
DSGVO-Dokumentation und bauen die Erzeugungs-Seite selbst. Wir liefern das als fertigen,
gepflegten, deutschen Dienst inkl. `/generate`. (Mehr dazu in Kap. 3.)

**„DSGVO / AVV?"**
AVV (Auftragsverarbeitungsvertrag) stellen wir bereit; Zero-Retention macht ihn schlank.
(Vorlage → Anwalt, Kap. 5.)

**Grenzen offen ansprechen (schafft Vertrauen):** Standard-Steuerfall (Regelsatz) ist
abgedeckt; Sonderfälle (Steuerbefreiung, Rabatte/Zuschläge, Anzahlungen), `/parse` und
PDF-Erzeugung kommen. Lieber ehrlich „kommt" als falsch „haben wir".

---

# 2. Was du dem Kunden NICHT sagst (Know-how schützen)

Ziel: Der Kunde kauft den **Dienst**, nicht die Bauanleitung. Schützenswert ist nicht
„geheime Technik" (der KoSIT-Validator ist offen) — sondern **dass die Wertschöpfung
leicht aussieht**. Wer deine Architektur, Margen und Abhängigkeiten kennt, baut es nach
oder drückt den Preis.

**Nicht herausgeben / nicht betonen:**

- **Dass der Kern „nur" ein gehosteter offener Validator ist.** Technisch korrekt, aber
  es entwertet dich im Kopf des Kunden. Rede über Ergebnis, Verfügbarkeit, Rechtslage,
  Pflege, Integration — nicht über „ist ja bloß ein Wrapper".
- **Deine Kostenbasis** (Server kostet ~10–20 €/Monat). Niemals nennen — sonst ankert
  der Kunde den Preis an deinen Kosten statt an seinem Nutzen.
- **Interne Architekturdetails, Quellcode, das JSON→CII-Mapping, der Golden-File-Ansatz,
  exakte Bibliotheken/Versionen** über das hinaus, was eine Integration braucht. Für die
  Integration reichen Endpunkte, Auth, Formate.
- **Andere Kundennamen, deren Preise, deine Pipeline, deine Roadmap-Interna.**
- **Betriebsdetails, die Bus-Faktor verraten.** Tritt als Firma/Marke auf, nicht als
  „ich allein bastle das". Support über eine Rollenadresse (`support@…`). Lüge aber
  nicht über die Unternehmensgröße, wenn direkt gefragt — das ist Vertrauens- und
  ggf. Rechtsrisiko; antworte stattdessen über Substanz (Verfügbarkeit, Backups,
  Vertretung/Notfallplan).

**Aktiv schützen:**

- **NDA** vor tieferen technischen Gesprächen (Vorlage → Anwalt). Das
  Geschäftsgeheimnisgesetz (GeschGehG) schützt nur, wer **angemessene
  Geheimhaltungsmaßnahmen** trifft — NDA + Zugriffsbeschränkung sind genau das.
- **Demo statt Doku:** zeig die laufende API (Selbst-Test-curl), nicht das Repo.
- **Wenn „könnten wir nicht selbst…?" kommt:** auf Gesamtkosten lenken (Betrieb,
  Updates, Haftung, Pflege, `/generate`), nicht defensiv werden.

---

# 3. Selbstmarketing & Vertriebsstrategie

## 3.1 Warum dir jemand Geld + Vertrauen gibt

Du verkaufst **Risiko-Abnahme**, nicht XML. Der Kunde (bzw. dessen Endkunde) hat ein
gesetzliches Muss und Angst vor Fehlern (abgelehnte Rechnung → verspätete Zahlung,
Ärger mit Behörde/Finanzamt). Dein Job: diese Angst glaubwürdig wegnehmen.

## 3.2 Deine drei Vertrauensanker (immer zuerst nennen)

1. **„In Deutschland gehostet, keine US-Subdienstleister, DSGVO-freundlich."**
2. **„Offizieller KoSIT-Validator — gleiche Ergebnisse wie das amtliche Tool."**
3. **„Zero-Retention — Ihre Rechnungen werden nicht gespeichert."**

Diese drei sind genau das, was große, austauschbare SaaS-Anbieter **nicht** sauber
behaupten können. Das ist dein Graben.

## 3.3 Vertrauen trotz „neu & klein" aufbauen

- **Live-Beweis:** der curl-Selbsttest. „Probieren Sie's jetzt mit Ihrer eigenen
  Rechnung." Funktionierende Software schlägt jedes Versprechen.
- **Status-/Uptime-Seite**, sobald deployt.
- **AVV + Datenschutz griffbereit** — signalisiert Professionalität.
- **Pilot-Referenzen:** die ersten 5 sind Gold. Hol dir explizit das Recht, sie (anonym
  oder benannt) als Referenz zu nennen — Teil des Pilot-Deals.
- **Klare, ehrliche Grenzen.** Wer sagt „das kann ich, das noch nicht", wirkt
  vertrauenswürdiger als wer alles verspricht.
- **Inhalt zeigt Kompetenz:** ein, zwei gute Erklärartikel („XRechnung empfangen — was
  Agenturen jetzt wissen müssen") ziehen genau die Richtigen an und belegen Expertise.

## 3.4 Wer ist der beste Erstkunde

**Web-/Software-Agenturen**, die für KMU, Handwerk und **öffentliche Auftraggeber**
bauen. Sie haben den Bedarf bei *ihren* Kunden, wollen kein eigenes XRechnung-Modul
bauen, und ein Verkauf bringt dir gleich mehrere Endkunden (Hebel). Siehe
[outreach-agenturen.md](outreach-agenturen.md).

## 3.5 Verkaufsprozess (schlank)

1. **Discovery (15 Min):** „Bauen Sie Projekte mit E-Rechnung? Empfang oder Versand?
   Wie lösen Sie's heute?"
2. **Demo:** Selbst-Test mit *ihrer* Datei.
3. **Pilot-Angebot:** vergünstigt/kostenlos auf Zeit gegen Feedback + Referenz.
4. **Conversion:** vom Pilot in ein bezahltes Abo, wenn ein echtes Projekt läuft.
5. **Expand:** Einstieg über `/validate` (Empfang, akuter Bedarf) → später `/generate`
   dazuverkaufen (Versandpflicht 2027/2028 als Anlass).

## 3.6 Einwände + Antworten

- **„Zu teuer."** → Gegenrechnung: Was kostet ein eigenes XRechnung-Modul in
  Entwicklertagen? Was kostet *eine* abgelehnte Rechnung in Verzug/Aufwand?
- **„Warum nicht selbst bauen?"** → Betrieb + Updates + Haftung + `/generate` +
  DSGVO-Doku. Dein Preis < ihre internen Vollkosten.
- **„Warum Ihnen vertrauen?"** → Live-Demo, deutsche Hosting-/Datenschutzlage, AVV,
  Referenzen, Statusseite.
- **„Was, wenn Sie ausfallen?"** → Notfall-/Vertretungsplan, Backups, Datenexport,
  und: portabel (Docker-Compose) → kein Lock-in-Drama.

---

# 4. Preisgestaltung

> **Startwerte zum Testen, keine Finanzberatung.** Den echten Preis findest du nur in
> Gesprächen (Preis-Discovery). Anker = **Nutzen des Kunden**, nie deine Kosten.

## 4.1 Logik

- **Wertbasiert, nicht kostenbasiert.** Du nimmst Compliance-Risiko ab.
- **Hybrid:** Abo (planbare Einnahme) **+** Volumenstaffel (skaliert mit Nutzung).
- **`/generate` ist mehr wert als `/validate`** (~2–3×): es ersetzt Entwicklungsarbeit
  und erzeugt ein verkaufsfähiges Artefakt, nicht nur ein Urteil.
- **Agenturen brauchen Marge:** White-Label/Mandantenfähigkeit gegen Aufpreis, damit
  sie an *ihre* Kunden weiterverkaufen.

## 4.2 Vorgeschlagene Pakete (mtl., netto)

| Paket | Preis/Monat | inkl. Dokumente* | Overage | Für wen |
|---|---|---|---|---|
| **Pilot** | 0 € für 6–8 Wochen **oder** −50 % | begrenzt | – | Erste 5, gegen Feedback + Referenz |
| **Starter** | 39 € | 250 | 0,08 €/Dok | Einzelne KMU / kleines Projekt |
| **Pro** | 129 € | 2.000 | 0,05 €/Dok | Aktive Agentur / mehr Volumen, Support 1 Werktag |
| **Business/Agentur** | 349 € | 10.000 | 0,03 €/Dok | White-Label, mehrere Mandanten/Keys, Prio-Support |
| **Enterprise / On-Prem** | ab ~1.000 € o. Lizenz | individuell | – | Eigenbetrieb, eigene SLAs |

\* „Dokument" = ein validiertes **oder** erzeugtes Dokument. Optional `/generate` höher
gewichten (z. B. 1 generate = 3 Dokumente).

## 4.3 Ohne Abo (Pay-as-you-go)

- `/validate`: **0,05 €/Dokument**
- `/generate`: **0,15 €/Dokument**
(Einstieg für Zögernde; Abo ist günstiger pro Dokument → Upgrade-Anreiz.)

## 4.4 Einmalige Leistungen (Dienstleistung)

- **Integrations-/Onboarding-Paket:** 750 – 2.500 € (Anbindung, Beratung, Test).
- **Individuelle Mappings/Sonderfälle:** nach Aufwand, Tagessatz.

## 4.5 Taktik

- **Jährlich −2 Monate** (10 statt 12) → bindet + verbessert Cashflow.
- **Pilot-Rabatt ausdrücklich gegen Gegenleistung** (Referenz, Logo, Testimonial,
  Feedback) — nicht „einfach billig".
- **Drei Stufen anbieten** (Anker-Effekt): die mittlere soll gewählt werden.
- **Preise testen:** Wenn niemand „zu teuer" sagt, bist du zu billig.

---

# 5. Fragenkatalog für den Anwalt

> Mitnehmen zum **Fachanwalt für IT-Recht** (idealerweise mit Datenschutz- und
> Steuerbezug). Vorab: Kapitel 1–4 dieses Dokuments + die Architektur-/Memory-Notiz zu
> Zero-Retention (Beweis durch Reproduzierbarkeit statt Speicherung).

## 5.1 AGB / Nutzungsbedingungen (B2B-SaaS)

- Saubere **Leistungsbeschreibung** (was die API tut — und was nicht).
- **Haftungsbegrenzung** + Klarstellung: „Werkzeug, kein Steuerberater / keine
  Rechtsberatung". Höchstbetrag/Deckelung?
- **Gewährleistung für Validierungsergebnisse:** Wir führen den offiziellen KoSIT-Validator
  in einer **genannten Version** aus — haften wir für dessen inhaltliche Richtigkeit?
  Wie formuliere ich „faithful execution at stated version" rechtssicher?
- **Verfügbarkeit/SLA:** Was kann ich als Solo realistisch zusichern? Wartungsfenster,
  Haftung bei Ausfall, Service-Gutschriften statt Schadensersatz?
- Laufzeit, **Kündigung**, Preisanpassungsklausel, Datenexport bei Vertragsende.

## 5.2 Haftung & Versicherung

- Wer haftet, wenn eine **erzeugte** Rechnung doch fehlerhaft ist und beim Kunden Schaden
  entsteht? Wie grenze ich das ab (Kunde verantwortet Eingabedaten + steuerliche
  Richtigkeit)?
- Sinnvolle **Versicherungen**: Berufs-/Betriebshaftpflicht, **Cyber-/Vermögensschaden**?
- Beweislast im Streitfall — reicht meine **Reproduzierbarkeit** (Input-/Output-Hash +
  Versionspins) als Nachweis „diese Eingabe ergab dieses Ergebnis"?

### 5.2.1 Arbeitsthese zur Haftung (anwaltlich gegenzuprüfen)

> Eigene Argumentation, **noch nicht** rechtlich bestätigt. Ziel der Prüfung: Hält die
> Konstruktion „treue Ausführung statt Richtigkeitsgarantie" vor Gericht und in den AGB?

- **Kernidee — zwei Bedeutungen von „Richtigkeit" trennen:**
  1. *Inhaltliche Richtigkeit der Regeln* („das Urteil des Validators ist juristisch
     korrekt") → **niemals garantieren**. Das sind die offiziellen Regeln des Bundes
     (KoSIT/EN 16931), nicht meine; selbst die KoSIT schließt dafür jede Gewähr aus.
     Diese Pflicht wäre unbegrenzt und faktisch unversicherbar.
  2. *Korrekte Ausführung* („ich habe den offiziellen KoSIT-Validator vX mit Config vY
     gegen genau diese Eingabe ausgeführt, das ist das Ergebnis") → **garantierbar und
     beweisbar**. Begrenzte, prüfbare, versicherbare Pflicht.
  → Vertraglich auf **(2)** festlegen, **(1)** ausdrücklich ausschließen.
- **Warum (2) risikoarm ist:**
  - KoSIT-Validator ist die **offizielle Referenzimplementierung** — Behörde/Empfänger
    prüfen gegen dieselbe Norm, bekommen dasselbe Ergebnis. Kein eigenes, divergierendes
    Urteil → gegenüber dem Standard kaum „falsch" möglich.
  - **Reproduzierbarkeit als Haftungsschild** (Input-/Output-Hash + gepinnte Validator-/
    Config-Version): verschiebt die Frage von „War die Antwort richtig?" (unbegrenzt) zu
    „Wurde das offizielle Tool treu ausgeführt?" (begrenzt, beweisbar). Vgl. 5.2 oben.
  - Geprüft wird **Format** (EN 16931 / XRechnung-Konformität), **nicht** die steuerliche/
    materielle Richtigkeit (z. B. Vorsteuerabzug). Muss in Leistungsbeschreibung + AGB
    explizit stehen (Anknüpfung an 5.1).
- **Hebel fürs Restrisiko:**
  - **Leistung eng definieren:** „konforme Ausführung des offiziellen Validators in
    Version X/Config Y", *keine* Rechtskonformitäts- oder Akzeptanzgarantie.
  - **Disclaimer:** keine Steuer-/Rechtsberatung; Aufbewahrung + Datenrichtigkeit bleiben
    Kundenpflicht (Anknüpfung an 5.4).
  - **Haftungsbegrenzung (B2B):** Cap z. B. auf Jahresgebühr, Ausschluss Folge-/indirekter
    Schäden + entgangenem Gewinn. Grenzen (nicht ausschließbar): Vorsatz, grobe
    Fahrlässigkeit, Leben/Körper/Gesundheit, ProdHaftG (§§ 276, 307, 309 Nr. 7 BGB); bei
    leichter Fahrlässigkeit an Kardinalpflichten nur Begrenzung auf vertragstypisch
    vorhersehbaren Schaden. **← Hauptpunkt der anwaltlichen Prüfung.**
  - **Versicherung:** Vermögensschaden-/Berufshaftpflicht für Restrisiko nach Cap (vgl.
    5.2). Cap + PI ist Standard-Setup eines IT-Dienstleisters.
  - **Versionstransparenz im Response:** verwendete Validator-/Config-Version stets
    mitliefern → Kunde/Empfänger kann reproduzieren.
- **Realistisches Schadensszenario:** Worst Case „gültig gemeldet, war's nicht" → Empfänger
  lehnt ab → Neuausstellung, Verzug. Bei treuer Ausführung kaum möglich (Empfänger prüft
  gegen dieselbe Norm). False-Negative → Zeitverlust, geringer Schaden.
- **Fazit (zu bestätigen):** Die Pflicht „treue Ausführung an gepinnten Versionen +
  Nachweis" ist begrenzt, beweisbar und durch die Architektur bereits abgedeckt. Mit
  B2B-Haftungscap + PI-Versicherung normales IT-Service-Risiko — **nicht** das große Risiko
  der naiven „Richtigkeitsgarantie".

## 5.3 Datenschutz (DSGVO)

- **AVV (Art. 28 DSGVO)** als Vorlage — passend zu Zero-Retention (so schlank wie möglich).
- **TOMs** (technisch-organisatorische Maßnahmen) dokumentieren.
- **Subunternehmer-Liste** (Hetzner; ggf. später Sentry/Stripe — nur EU).
- **Datenschutzerklärung** für Website/Dienst.
- Bestätigung, dass **transiente Verarbeitung** (keine Speicherung) die DSGVO-Last
  minimiert.

## 5.4 Steuer / GoBD (Zero-Retention absichern)

- Bestätigung: **transientes Validieren/Erzeugen löst keine GoBD-/§-147-AO-
  Archivierungspflicht** bei mir aus (ich bin kein revisionssicheres Archiv).
- Klarstellung in den AGB: **Aufbewahrung bleibt Pflicht des Kunden** (8–10 Jahre).
- Falls ich je Archivierung anbiete: dann zwingend DE/EU-Speicherung — welche Pflichten
  kämen dann?

## 5.5 Lizenzen / IP

- **Lizenz des KoSIT-Validators** und der **XRechnung-Konfiguration** prüfen: erlauben
  sie kommerzielle Nutzung, Hosting und Weitergabe der Prüfergebnisse über eine bezahlte
  API? (Lizenztext gegenprüfen lassen.)
- Eigene spätere **OSS-Veröffentlichung** der Library — welche Lizenz, welche Pflichten?
- Wem gehört der Code, wenn ich Auftragsentwicklung/Integration mache?

## 5.6 Marke / Name

- **„XRechnung" ist eine geschützte Bezeichnung des Bundes** — beschreibende Nutzung ist
  ok, aber **nicht als Produktname/Marke**. Was darf ich wie nennen?
- Eigenen Produktnamen prüfen (Marken-/Domainrecherche) vor Veröffentlichung.

## 5.7 Verträge / Gesellschaft / Sonstiges

- **Pilotvereinbarung** (kurz): Leistung, Laufzeit, Referenzrecht, Preis danach.
- **NDA-Vorlage** für technische Gespräche (GeschGehG-konform).
- Rechtsform/Gewerbe, **Kleinunternehmer vs. USt** für meine eigene Rechnungsstellung.
- Impressum/TMG-Pflichten für die Website.

---

*Stand: 2026-06-14. Vor Kundengesprächen gesetzliche Fristen + Versionsstände kurz
gegenprüfen.*
