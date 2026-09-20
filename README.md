# Prokurimet Publike të Kosovës — Zbulimi i Anomalive

Pipeline referencë i Inxhinierisë së të Dhënave për analizë retrospektive
të anomalive në rekordet e **Publikimit 115** të KRPP-së, të shpërndara
në format OCDS nga Open Contracting Partnership. Paketa e dorëzuar është
një **snapshot statik**: 75,710 rekorde dhe 118 muaj me të dhëna nga 121
muaj kalendarikë në intervalin 2016-03–2026-03. Nuk pretendohet se është
cens i plotë i çdo procedure prokurimi në Kosovë.

Objektet OCDS `award` në këtë snapshot trajtohen si **vendime dhënieje të
regjistruara**. Vlerat e tyre nuk dëshmojnë se një kontratë është nënshkruar,
ekzekutuar ose paguar; paneli dhe dokumentet i emërtojnë për këtë arsye
“vlera e vendimeve të dhënies”, jo “vlerë e kontraktuar”.

> 🎓 **Projekt diplome bachelor — jo mjet zyrtar qeveritar.** Shtresa e
> rregullave është baza heuristike e auditueshme; shtresa ML është
> **eksploruese dhe e pavaliduar** kundër së vërtetës bazë (etiketat proxy
> vijnë nga vetë rregullat dhe mbivendosen fort me veçoritë hyrëse, ndaj
> AUC afër 1.0 mat besnikëri ndaj proxy-t, jo saktësi zbulimi). Shih
> [`docs/methodology.md`](docs/methodology.md) dhe
> [`docs/responsible_use.md`](docs/responsible_use.md) për çfarë
> mund/nuk mund të pretendohet.
>
> **Temë e ndjeshme.** Shenjat e anomalive janë sinjale për rishikim nga
> një auditor me akses në dokumente — *jo* prova mashtrimi apo
> parregullsie. Lexo [`docs/responsible_use.md`](docs/responsible_use.md)
> para se të përdorësh ose publikosh çfarëdo rezultati.

---

## Pikat kryesore

- **Arkitekturë medallion** — bronze → silver → gold/`tender_features` →
  benchmark → ML/`tender_summary`, me kontrata skeme, kontrolle DQ dhe sidecar-e
  lineage për rindërtimin e snapshot-it.
- **Benchmark i dokumentuar shumë-modelësh** — 8 familje detektorësh të
  pambikëqyrur (Isolation Forest, LOF, Elliptic Envelope, One-Class SVM,
  PCA, GMM, KNN, HBOS) në **23 konfigurime** + 4 familje klasifikuesish të
  mbikëqyrur në **12 konfigurime**, me shumë seeds, stabilitet bootstrap
  dhe një **ndarje kohore të besnikërisë ndaj etiketave proxy** (trajno
  ≤ 2023, testo
  ≥ 2024). Meqë etiketa vjen nga rregullat dhe inputet mbivendosen fort
  me përbërësit e saj, kjo ndarje mat besnikëri ndaj proxy-t; nuk provon
  gjeneralizim ose zbulim. Rezultatet me
  checkpoint/resume në `data/models/benchmark/`.
- **Zgjedhje modeli e drejtuar nga benchmark-u** — `champions.json`
  regjistron konfigurimet fituese; pipeline-i ML i konsumon automatikisht.
- **Ansambël + XAI i lidhur me pikën reale** — 15 indikatorë transparentë
  (vetëm 4 me peshë), rank-percentilet e detektorëve kampionë dhe pika
  kontekstuale rindërtojnë ekzaktësisht `ensemble_score` për çdo rekord.
  Dashboard-i shfaq vlerën, peshën, kontributin dhe efektin ndaj bazës për
  secilin komponent. SHAP ruhet veçmas vetëm për modelin proxy të rregullave;
  nuk paraqitet si shpjegim i ansamblit unsupervised.
- **Kontrolle të brendshme** — CV k-fold kundër etiketave të rregullave,
  bootstrap stabiliteti, pajtim renditjesh (Spearman) dhe kalibrim/ECE
  ndaj proxy-t — të gjitha në
  `data/models/validation_report.json` dhe në faqen **Validimi**.
- **Gjurmim linje (lineage)** — çdo Parquet ka sidecar
  `<skedar>.lineage.json` me hash-e inputesh, gjurmë skeme, git SHA,
  run-id, kohëzgjatje.
- **Kontrata të dhënash** — Pydantic (rresht) + Pandera (DataFrame) +
  suita pritshmërish DQ; dështimet `ERROR` e ndalojnë gjithmonë publikimin,
  ndërsa `WARNING` bëhet bllokues kur `THESIS_FAIL_FAST_ON_DQ=true`.
- **Identitet furnizuesi me ndjeshmëri të dukshme** — ID-të sentinel
  normalizohen si të munguara. Raportohen veçmas çelësi ID-biznesi/emër,
  çelësi ID-biznesi/ID-palë-burimore/emër dhe pamja vetëm-me-ID. ID-ja e
  palës është identitet në publikim, jo ID juridike e verifikuar; asnjë
  pamje nuk pretendohet si zgjidhje e plotë e entitetit ose përkufizim tregu.
- **Mungesa e ofertuesve ruhet** — kur burimi nuk publikon listën/rolet e
  ofertuesve, `num_bidders` mbetet null dhe `bidder_data_observed=false`;
  mungesa nuk paraqitet më si zero ofertues.
- **Një CLI për rindërtim** — `python -m thesis ...` lokalisht; një DAG
  Airflow tregon si mund të orkestrohen të njëjtat faza. Paketa e dorëzuar
  mbetet snapshot statik, jo shërbim produksioni.
- **Panel Streamlit në shqip** — 9 faqe me grafikë, kërkim tenderësh,
  profile të autoriteteve dhe furnizuesve, krahasim modelesh dhe fjalor.
  Shënimi "Anomalia ≠ mashtrim" shfaqet në çdo faqe.
- **CI + Docker + pre-commit** — ruff, mypy, matricë pytest, testim
  integrimi, Dockerfile shumë-fazësh me përdorues jo-root.

---

## Si ta përdorni panelin

- **Ballina** jep pamjen e parë të vlerave dhe numrit të tenderëve.
- **Përmbledhja** paraqet ecurinë, kategoritë, procedurat dhe konkurrencën.
  Të gjithë grafikët ndjekin filtrat e zgjedhur. Kufijtë e vlerës vendosen
  në euro; mungesa e të dhënave ruhet si e tillë.
- **Kërko tenderë** gjen tenderë sipas titullit, autoritetit, furnizuesit
  ose identifikuesit. Zgjidhni një rezultat për të lexuar shifrat dhe sinjalet.
- **Sinjalet për shqyrtim** shpjegon arsyet përpara formulave. Llogaritjet
  dhe shpjegimet teknike hapen sipas nevojës.
- **Autoritetet dhe furnizuesit** krahason aktivitetin gjatë gjithë periudhës;
  kjo shtrirje shënohet në faqe. Faqet shpjeguese dhe fjalori janë në pjesën
  **Rreth analizës** të menysë.

Përmirësimet e paraqitjes gjenden te `streamlit_app/_charts.py` dhe
`streamlit_app/_narrative.py`; ato nuk ndryshojnë modelet, pikët ose
artefaktet e publikuara. Shih [rishikimin e projektit](docs/project_review_2026_09.md)
për kontrollet e kryera dhe kufizimet e mbetura të punimit.

---

## Nisja e shpejtë

Pas klonimit, riktheni skedarin burimor nga kopja e kompresuar e ruajtur në
repo. Skedari i zgjeruar nuk ruhet në Git për shkak të madhësisë:

```bash
gzip -dk data/raw/kosovo_ocds.jsonl.gz
```

Kjo komandë nevojitet vetëm kur `data/raw/kosovo_ocds.jsonl` mungon. Kopja e
kompresuar rikthen saktësisht të dhënat me të cilat janë ndërtuar rezultatet
e përfshira. Mos e zëvendësoni me një shkarkim më të ri pa rindërtuar analizën.

```bash
# 1. instalimi
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[dev,notebooks]
pre-commit install

# 2. pipeline-i i plotë (idempotent — anashkalon fazat e freskëta)
python -m thesis pipeline run

# 3. paneli
python -m thesis ui
```

### Ose me Docker:

```bash
docker compose up app          # paneli në http://localhost:8501
docker compose run pipeline    # pipeline i plotë një herë
```

### Objektivat Make:

```bash
make dev              # instalim + pre-commit
make all              # pipeline i plotë
make benchmark        # sweep-i i plotë i krahasimit të modeleve
make check_updates    # kontrollo për rekorde të reja të tenderëve
make app              # paneli Streamlit
make test             # suita e plotë e testeve
```

---

## CLI

```text
$ python -m thesis --help
  pipeline   Ekzekuto pipeline-in e të dhënave.
  dq         Komandat e cilësisë së të dhënave.
  report     Gjenero raporte dhe radhën e rishikimit manual.
  info       Përmbledhje e depos aktuale.
  version    Versioni i paketës.
  ui         Nis panelin Streamlit.

$ python -m thesis pipeline --help
  run            Ekzekuto DAG-un (me --only / --from / --force)
  status         Freskia e fazave
  bronze         Shkarko + ekstrakto OCDS
  check-updates  Kontrollo për rekorde të reja në burim (swap atomik)
  silver         Ndërto shtresën silver
  gold           Ndërto tender_features + përmbledhjet gold
  benchmark      Krahasimi rigoroz i modeleve (--quick për provë)
  ml             Shkruaj tender_summary + modelet, SHAP dhe validimin
```

---

## Struktura e projektit

```
.
├── pyproject.toml             # PEP 621, konfigurimi ruff/mypy/pytest
├── Dockerfile                 # shumë-fazësh, jo-root, healthcheck
├── docker-compose.yml         # stack-u lokal
├── Makefile                   # ekzekutuesi i detyrave
├── .github/workflows/ci.yml   # lint, type, matricë testesh, docker
│
├── src/thesis/
│   ├── config.py              # Pydantic Settings (12-factor, THESIS_*)
│   ├── logging.py             # structlog + run-id
│   ├── paths.py               # burimi i vetëm i rrugëve
│   ├── lineage.py             # sidecar-ët e linjës për artefakt
│   ├── cli.py                 # hyrja Typer
│   ├── domain/                # PURE: kontrata, skema, veçori
│   ├── io/                    # lexues + shkrues (me lineage)
│   ├── dq/                    # korniza + suitat e pritshmërive
│   ├── anomaly/
│   │   ├── rules.py           # 15 indikatorë + metadata/proveniencë
│   │   ├── models.py          # 4 detektorët bazë + shpjeguesi HGB
│   │   ├── detectors.py       # PCA, GMM, KNN, HBOS + fabrika
│   │   ├── benchmark.py       # motori i krahasimit (checkpoint/resume)
│   │   ├── comparison.py      # pika kontekstuale (z-score)
│   │   ├── ensemble.py        # kombinimi + dekompozimi ekzakt XAI
│   │   ├── validation.py      # CV, stabilitet, pajtim, kalibrim
│   │   └── explanations.py    # SHAP proxy + kontekst përshkrues i hyrjeve
│   └── pipeline/              # bronze, silver, gold, benchmark, ml, dag
│
├── streamlit_app/             # paneli (shqip)
│   ├── Home.py
│   └── pages/                 # Përmbledhje, Eksploro, Anomalitë,
│                              # Subjektet, Metodologjia, Validimi,
│                              # Krahasimi i Modeleve
│
├── airflow_dags/              # shembull orkestrimi (BashOperator mbi CLI)
├── tests/                     # njësi / kontrata / integrim / faqe UI
├── docs/                      # arkitektura, metodologjia, ADR-të,
│                              # përdorimi i përgjegjshëm, runbook
└── data/
    ├── raw/                   # bronze (OCDS jsonl)
    ├── silver/                # tenders.parquet, awards.parquet
    ├── gold/                  # tender_features, tender_summary + 3 përmbledhje
    ├── dq/                    # skedat e pritshmërive
    ├── models/                # modelet kampione, SHAP, validimi
    │   └── benchmark/         # results.wip.jsonl, release snapshot, leaderboard, champions
    └── _lineage/              # historiku kronologjik i linjës
```

---

## Benchmark-u i modeleve

```bash
python -m thesis pipeline benchmark          # sweep i plotë (1–2 orë)
python -m thesis pipeline benchmark --quick  # provë tymi (sekonda)
```

Protokolli (i dokumentuar edhe në
`data/models/benchmark/leaderboard.md`, në shqip):

| Aspekti | Të pambikëqyrurit (8 familje) | Të mbikëqyrurit (4 familje) |
|---|---|---|
| Rrjeta | 23 konfigurime | 12 konfigurime |
| Saktësia | AUC proxy ndaj etiketave të rregullave (0.4/0.7), Precision@500 | CV e shtresëzuar 5-fold × 2 seeds: ROC-AUC, PR-AUC, Brier |
| Qëndrueshmëria | Jaccard bootstrap (top-5 % flamuj, 4 ri-përshtatje në 80 %); numër i kufizuar, jo interval pasigurie | — |
| Determinizmi | Konsistencë Spearman me 2 seeds shtesë për familjet stokastike (përfshirë PCA me solver `auto`) | seeds të shumtë në CV |
| Besnikëria kohore ndaj proxy-t | — | Ndarje ≤2023/≥2024; etiketa e rregullave dhe inputet mbivendosen fort, prandaj nuk është provë gjeneralizimi |
| Renditja | `0.45×AUC(0.7) + 0.35×stabiliteti + 0.20×konsistenca` | ROC-AUC e besnikërisë ndaj rregullave |

Praktikat DE: checkpoint strikt JSON pas çdo konfigurimi (`results.wip.jsonl`),
resume që anashkalon vetëm konfigurimet me të njëjtin hash të të dhënave,
protokollit **dhe skedarëve relevantë të implementimit**, dhe dështime të
izoluara për konfigurim. `--quick` shkruan `results.quick.jsonl`, ndaj prova
nuk mund të ndryshojë checkpoint-in e plotë. Gjatë sweep-it, publikimi i
mëparshëm mbetet i paprekur; vetëm pas plotësisë dhe kontrollit semantik WIP-i
zëvendëson atomikisht snapshot-in `results.jsonl`. Publikimi lidh me hash atë
snapshot, leaderboard-in dhe kampionët; një kontroll semantik
verifikon plotësinë, formulën dhe ri-zgjedh fituesit para se ML t'i përdorë.

Krahasimi raporton gjithashtu skenarë të deklaruar me pesha alternative,
konfliktin e renditjes `precision@K`, ablacionin me ripërshtatje të modeleve
mbi nënbashkësi veçorish dhe ndjeshmërinë e votës në q=0.90/0.95/0.99. Këto
janë kontrolle të renditjes në snapshot, **jo validim** ndaj rezultateve reale.

**Kufizim i deklaruar:** etiketat proxy vijnë nga shtresa e rregullave —
metrikat masin *pajtimin me rregullat*, jo mashtrimin real. Modelet
renditin rekorde tenderësh për **rishikim njerëzor**. Pikët, percentilet dhe
`high_confidence` janë relative ndaj këtij snapshot-i; shtimi ose heqja e
rekordeve mund t'i ndryshojë edhe pa ndryshuar tenderin në fjalë. Paketa nuk
publikon statistikë reference të ngrirë/versionuar për pikëzim online; çdo
rindërtim i plotë rikalibron renditjet ndaj batch-it të vet.

---

## Rishikimi manual — ende pa etiketa

Pas ekzekutimit final të ML-së, komanda më poshtë krijon një mostër të
ngrirë me deri në 50 tenderë nga secili kuadrant rregull×ansambël; një
kuadrant bosh në pragjet operative raportohet si zero, jo plotësohet artificialisht:

```bash
python -m thesis report audit-sample
```

Dalja është një **radhë e paetiketuar** për auditorët, jo rezultat validimi.
ML-ja mbetet e pavaliduar ndaj rezultateve tender-më-tender derisa njerëzit
të kontrollojnë dokumentet, të plotësojnë fushat e rishikimit dhe të matin
pajtimin ndërmjet rishikuesve. Protokolli dhe rregullat kundër mbishkrimit të
punës njerëzore janë te
[`docs/manual_audit_protocol.md`](docs/manual_audit_protocol.md).

---

## Kontrolli për të dhëna të reja

```bash
python -m thesis pipeline check-updates
```

Komanda bën një kontroll manual të publikimit. Analiza dhe paneli i
dorëzuar mbeten snapshot statik derisa të ekzekutohet e gjithë linja dhe
të rigjenerohen artefaktet; projekti nuk paraqitet si monitorim live.

---

## Konfigurimi

Çdo parametër jetëson në [`src/thesis/config.py`](src/thesis/config.py)
dhe mbivendoset me variabla mjedisi (prefiks `THESIS_`) ose `.env`
(shih [`.env.example`](.env.example)):

```bash
THESIS_LOG_FORMAT=json THESIS_FAIL_FAST_ON_DQ=true \
  python -m thesis pipeline run
```

---

## Licenca

[MIT](LICENSE).

## Burimi i të dhënave

[Open Contracting Partnership — Publikimi 115 (KRPP Kosovë)](https://data.open-contracting.org/en/publication/115)
