# Dokumentacioni i projektit

Ky projekt analizon të dhëna të publikuara të prokurimit në Kosovë dhe
paraqet sinjale për shqyrtim. Paneli përdor një version të ruajtur të të
dhënave; rezultatet statistikore nuk janë prova shkeljesh.

## Nga të filloni

| Nëse dëshironi të… | Lexoni |
|---|---|
| Kuptoni projektin, ta instaloni ose ta nisni | [README kryesor](../README.md) |
| Përdorni panelin dhe kuptoni grafikët | [Udhëzuesi i përdorimit](user_guide.md) |
| Kuptoni si duhen përdorur rezultatet | [Përdorimi i përgjegjshëm](responsible_use.md) |
| Shqyrtoni metodën dhe pretendimet e punimit | [Metodologjia](methodology.md) |
| Kuptoni llogaritjen dhe shpjegimin e pikëve | [Si shpjegohen pikët](explainability.md) |
| Kuptoni organizimin e të dhënave dhe përbërësve | [Arkitektura](architecture.md) |
| Rindërtoni analizën ose zgjidhni probleme gjatë ekzekutimit | [Udhëzuesi i operimit](operations.md) |
| Verifikoni tenderë duke lexuar dokumentet burimore | [Protokolli i shqyrtimit manual](manual_audit_protocol.md) |
| Shihni përmbledhjen numerike të versionit të të dhënave | [Gjetjet e gjeneruara](findings.md) |
| Shihni vlerësimin e projektit dhe kontrollet e kryera | [Rishikimi i projektit — shtator 2026](project_review_2026_09.md) |

Udhëzuesi i përdorimit është për lexuesin pa njohuri teknike. Dokumentet
metodologjike dhe teknike përfshijnë edhe materiale në anglisht, emrat
origjinalë të fushave dhe komandat për riprodhimin e analizës.

## Çfarë përmban secili grup dokumentesh?

**Përdorimi dhe interpretimi.** [Udhëzuesi](user_guide.md) përshkruan nëntë
faqet reale të panelit, filtrat, shkarkimin dhe kuptimin e treguesve.
[Përdorimi i përgjegjshëm](responsible_use.md) shpjegon kufijtë e interpretimit
kur rezultatet lidhen me institucione ose furnizues konkretë.

**Metoda dhe zbatimi.** [Metodologjia](methodology.md) dokumenton burimin,
transformimet, rregullat, modelet, shpjegimin e pikëve dhe kufizimet.
[Shpjegimi i pikëve](explainability.md) jep formulën e kombinimit, një shembull
të verifikuar dhe dallimin mes shpjegimit të pikëve të kombinuara dhe SHAP-it.
[Arkitektura](architecture.md) shpjegon shtresat e të dhënave dhe lidhjen mes
tyre. [Udhëzuesi i operimit](operations.md) mbulon rindërtimin, kontrollet e
publikimeve, problemet e zakonshme dhe rikthimin e të dhënave.

**Rezultatet dhe vlerësimi.** [Gjetjet](findings.md) gjenerohen nga skedarët
e analizës; koha dhe gjurmët e hyrjeve shënohen në krye të dokumentit.
Mos i ndryshoni shifrat me dorë. Komanda për rigjenerim, pas përgatitjes dhe
verifikimit të rezultateve, është:

```bash
python -m thesis report findings
```

[Rishikimi i projektit](project_review_2026_09.md) është një vlerësim me datë:
ndan kontrollet e kryera nga punët që nuk janë kryer. Nuk është raport që
përditësohet vetvetiu. [Protokolli i shqyrtimit manual](manual_audit_protocol.md)
përcakton si të mblidhen vlerësime njerëzore me dëshmi. Një fushë vlerësimi e
zbrazët do të thotë rast i pashqyrtuar, jo rast pa probleme.

## Vendimet arkitekturore (ADR)

Këto dokumente ruajnë arsyetimin, alternativat dhe pasojat e zgjedhjeve teknike.

| Dokumenti | Vendimi |
|---|---|
| [ADR-0001](adr/0001-medallion-architecture.md) | Ndarja e të dhënave në shtresat bronze, silver dhe gold |
| [ADR-0002](adr/0002-multi-model-anomaly-ensemble.md) | Kombinimi i modeleve me shtresën e rregullave |
| [ADR-0003](adr/0003-parquet-storage.md) | Përdorimi i formatit Parquet për ruajtje |
| [ADR-0004](adr/0004-streamlit-as-frontend.md) | Përdorimi i Streamlit për panelin |
| [ADR-0005](adr/0005-cautious-anomaly-framing.md) | Paraqitja e anomalive si sinjale, jo si prova mashtrimi |
| [ADR-0006](adr/0006-airflow-as-prod-orchestrator.md) | Rruga e propozuar drejt orkestrimit me Airflow |

Shembulli me Airflow dhe dokumentimi i një rruge për përdorim të zgjeruar
nuk nënkuptojnë se paketa funksionon si shërbim i vazhdueshëm në prodhim.
