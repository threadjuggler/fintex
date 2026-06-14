# Die Healthchecks.io-Geschichte — ein Solo-Lifestyle-SaaS als Vorbild

*Recherchiert + zusammengetragen am 2026-06-14. Zahlen mit Stand/Quelle markiert —
können sich seither geändert haben. Quellen unten.*

## Kurzprofil

- **Gründer:** Pēteris Caune — langjähriger Python-Entwickler aus **Valmiera, Lettland**.
- **Firma:** SIA „Monkey See Monkey Do" — ein **Ein-Mann**-Software-/Beratungsunternehmen,
  registriert in Lettland.
- **Produkt:** [Healthchecks.io](https://healthchecks.io) — Überwachung von Cron-Jobs und
  geplanten Tasks („Dead Man's Switch": ein Dienst pingt regelmäßig eine URL; bleibt der
  Ping aus, schlägt Healthchecks Alarm).
- **Start:** Juli **2015**.
- **Modell:** **Open Source** (Code auf GitHub) **und** gehosteter Bezahldienst —
  Kunden können selbst hosten oder die SaaS-Variante nehmen.
- **Hosting:** läuft auf **Hetzner (Deutschland)**.

## Die Geschichte (die „Legende")

Caune wollte 2015 vor allem **Neues ausprobieren**, nicht möglichst schnell Geld machen.
Er hatte selbst den Bedarf (ein zuverlässiges Cron-Monitoring) und baute genau das
Werkzeug — als Side-Project neben dem Job.

Der Start war bewusst **sparsam**: Alles lief anfangs auf einem einzigen
**5-$/Monat-Droplet** bei DigitalOcean — was bei anfangs sehr wenig Traffic völlig
reichte. Weil der Code offen war, nutzte er die „kostenlos für Open Source"-Pläne von
GitHub, Travis CI und Coveralls. Kosten quasi null, Risiko quasi null.

Dann **organisches Wachstum über Jahre** statt Raketenstart:

- **2018** (3. Geburtstag): ~**90 zahlende Kunden**, etwas über **700 $/Monat**.
- **Juli 2024** (9 Jahre): **652 zahlende Kunden**, **~14.043 $ MRR** — laut Gründer
  weiterhin ein **Ein-Mann-Geschäft**, das er bewusst so klein und genussvoll hält.

Aus dem Side-Project wurde so ein **tragfähiges Vollzeit-Solo-SaaS** — ohne Investoren,
ohne Team-Aufbau, ohne Hypergrowth. Der Blogpost dazu heißt sinngemäß „Running One-man
SaaS, 9 Years In".

## Warum das als Vorbild gilt

- **Open Source UND profitabel** — der seltene Beweis, dass beides zusammengeht: Offenheit
  schafft Vertrauen und Reichweite, der gehostete Dienst bringt das Geld.
- **Bewusst klein & nachhaltig:** Der Dienst „trägt sich", also optimiert der Gründer auf
  **Spaß und Work-Life-Balance** statt auf Maximalwachstum. Das ist der Kern eines
  *Lifestyle-Business*.
- **Radikale Einfachheit:** simpler Stack, **wenige Abhängigkeiten**, klassisches
  PostgreSQL statt hipper verteilter Datenbanken, **kein proprietärer Lock-in**.
- **Werte sichtbar gelebt:** Healthchecks.io **spendet 5 % des MRR** an die Open-Source-
  Projekte, auf denen es aufbaut.
- **Geduld:** von 700 $/Monat (2018) auf ~14 k $/Monat (2024) — solides, ruhiges Wachstum
  über fast ein Jahrzehnt.

## Was du daraus für einvoice-core mitnimmst

Die Parallelen sind fast unheimlich — nutze sie als Landkarte:

1. **Solo + bootstrapped ist machbar.** Ein Mensch, ein scharf umrissenes,
   „langweiliges" Infrastrukturproblem (Cron-Monitoring ↔ E-Rechnungs-Compliance) → ein
   tragfähiges Geschäft. Kein Team, kein VC nötig.
2. **Hetzner / Deutschland.** Healthchecks läuft genau dort, wo du auch bist. Günstig,
   solide, planbar — und bei dir zusätzlich ein **Verkaufsargument** (Datenstandort DE).
3. **Open Source als Hebel.** Deine geplante OSS-Library ist kein Widerspruch zum
   Bezahldienst, sondern Vertrauens- und Vertriebskanal — genau Caunes Modell
   (offener Kern + gehostete, gepflegte Variante).
4. **Einfach halten.** Wenige Abhängigkeiten, PostgreSQL, Docker/Compose, kein Lock-in —
   deckt sich 1:1 mit deinen Architektur-Entscheidungen (Portabilität).
5. **Geduld einplanen.** 90 → 652 Kunden in 6 Jahren. Dein Gate „5 zahlende Piloten" ist
   genau der richtige, kleine erste Schritt. Nicht auf den Raketenstart warten.
6. **Nachhaltigkeit > Hypergrowth.** Ziel darf „trägt sich gut und macht Spaß" sein.
   Das ist kein Kompromiss, das ist die Strategie.
7. **Selbst-hostbar anbieten** (wie Healthchecks) nimmt Kunden die Lock-in-Angst und
   passt zu deinem Compose-Setup.

**Der eine Satz zum Mitnehmen:** Ein langweiliges, echtes Problem, sauber und einfach
gelöst, offen und ehrlich betrieben, geduldig über Jahre — das reicht für ein gutes Leben
mit eigener Software.

## Zum Weiterlesen (Quellen)

- [Running One-man SaaS, 9 Years In (Blog, 2024)](https://blog.healthchecks.io/2024/07/running-one-man-saas-9-years-in/)
- [My One-person SaaS Side Project Celebrates its Third Birthday (Blog, 2018)](https://blog.healthchecks.io/2018/08/my-one-person-saas-side-project-celebrates-its-third-birthday/)
- [Indie Hackers: „Why I Don't Focus on Generating a Quick Profit"](https://www.indiehackers.com/interview/why-i-dont-focus-on-generating-a-quick-profit-160d4f87b6)
- [Healthchecks.io – About](https://healthchecks.io/about/)
- [Python Podcast.__init__: Folge mit Pēteris Caune](https://www.pythonpodcast.com/healthchecks-with-peteris-caune-episode-144)
- [GitHub: cuu508 (Pēteris Caune)](https://github.com/cuu508) · [Healthchecks.io auf Indie Hackers](https://www.indiehackers.com/product/healthchecks-io/revenue)

*Hinweis: Eine Drittseite (getlatka) nennt abweichende, höhere Zahlen (~111 k $ Umsatz /
15 k Kunden 2024). Verlässlicher sind die Eigenangaben des Gründers im Blog (652 zahlende
Kunden, ~14 k $ MRR, Stand Juli 2024) — die 15 k dürften alle Accounts inkl. Gratis sein.*
