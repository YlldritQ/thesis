# Përdorimi i përgjegjshëm

Zbulimi i anomalive në **prokurimin publik është temë e ndjeshme**.
Një tender i sinjalizuar në këtë sistem *nuk* është akuzë. Ky dokument sqaron
çfarë bën projekti, çfarë nuk bën dhe si duhen lexuar rezultatet e tij.
Analiza mbulon vetëm grupin e ruajtur të të dhënave nga Publikimi 115:
75 710 regjistrime dhe 118 muaj me të dhëna nga 121 muaj në intervalin e
publikuar. Nuk është monitorim në kohë reale ose regjistrim i plotë i
prokurimit kombëtar.

## Parimi themelor

> Një pikë e lartë anomalie do të thotë: «ky tender renditet si i pazakontë
> brenda grupit të ruajtur të të dhënave dhe/ose aktivizon rregulla të
> përcaktuara nga autori; një auditor me dokumentet në dorë duhet ta vendosë
> në kontekst».
>
> **Nuk** do të thotë që tenderi është mashtrues, që dikush ka vepruar
> në mënyrë të parregullt apo që ka ndodhur ndonjë shkelje.

Me qëllim përdorim fjalët **sinjal**, **shenjë** dhe **shqyrtim** — **kurrë**
«mashtrim» ose «korrupsion» — kur përshkruajmë rezultatet e modeleve.

Objekti OCDS `award` është vetëm një **vendim i regjistruar për dhënien e
kontratës**. Fusha `awarded_value_eur` nuk dëshmon vlerën e një kontrate të
nënshkruar, të zbatuar ose të paguar dhe nuk është shpenzim real. Për këtë
arsye paneli përdor shprehjen «vlera e vendimeve të dhënies».

## Çfarë bëjmë për t'u mbrojtur nga akuzat e rreme

1. **Pajtim renditjesh, jo provë e pavarur.** Pikët e kombinuara bashkojnë
   renditjet e katër modeleve të përzgjedhura me pikët e rregullave dhe
   pikët e kontekstit. Kolona teknike `high_confidence` (emër i trashëguar),
   së cilës i përgjigjet filtri «Vetëm tenderët ku modelet pajtohen…»,
   do të thotë vetëm se të paktën **3 nga 4** modelet e vendosin tenderin
   mes **5% më të pazakontëve të grupit të analizuar**. Nuk është
   besueshmëri e kalibruar dhe nuk provon se ka më pak pozitive të rreme.

2. **Rregulla transparente.** Çdo rregull ka kod, përshkrim në gjuhë të
   thjeshtë, arsyetim ose prag të deklaruar, kufizime dhe peshë fikse. Nga
   15 rregullat e dukshme, vetëm katër kanë peshë në pikët e rregullave.
   Llogaritjet mund të riprodhohen me makinë llogaritëse. Shihni
   `src/thesis/anomaly/rules.py`.

3. **Vlerësim sipas kontekstit.** Anomalia varet nga konteksti: një tender
   prej 5 mln € mund të jetë i zakonshëm për Ministrinë e Infrastrukturës
   dhe i pazakontë për një komunë të vogël. Pikët e kontekstit («Dallimet nga
   tenderët e ngjashëm», `context_score`) e pasqyrojnë këtë drejtpërdrejt.

4. **Përzgjedhje e modeleve me protokoll të dokumentuar.** Modelet që hyjnë
   në pikët e kombinuara renditen sipas kërkimit në rrjetë të
   hiperparametrave, qëndrueshmërisë bootstrap, qëndrueshmërisë ndaj vlerave
   fillestare të rastësisë (seed) dhe përputhjes me etiketat ndihmëse të
   nxjerra nga rregullat. Ndarja kohore ≤ 2023 / ≥ 2024 nuk simulon përdorim
   real, sepse objektivi i rregullave dhe veçoritë hyrëse të modeleve
   mbivendosen fort. Renditja e plotë publikohet në faqen «Krahasimi i
   modeleve» dhe në `data/models/benchmark/leaderboard.md`.

5. **Kontrolle të brendshme në çdo ekzekutim.** Çdo ekzekutim prodhon
   `data/models/validation_report.json`, me vlerësim të kryqëzuar kundrejt
   etiketave ndihmëse, qëndrueshmëri bootstrap, pajtim ndërmjet modeleve
   dhe një kontroll të kalibrimit kundrejt etiketave të rregullave. Pikët
   nuk janë probabilitete të kalibruara. Këto kontrolle matin sjelljen e
   brendshme të modeleve, jo aftësinë për të zbuluar shkelje.

6. **Paralajmërim i përhershëm.** Çdo faqe e panelit shfaq paralajmërimin
   «Anomalia ≠ mashtrim». Testet e projektit kontrollojnë që ky
   paralajmërim të mbetet; një ndryshim që e heq nuk i kalon kontrollet.

7. **Gjurmimi i prejardhjes.** Skedarët Parquet kanë skedarë shoqërues
   `*.lineage.json` me hash-et e skedarëve hyrës dhe dalës, versionin e
   kodit dhe identifikuesin e ekzekutimit; manifestet e fazave lidhin të
   gjithë skedarët e prodhuar. Kjo mbështet auditimin e grupit të ruajtur të
   të dhënave, por hash-i nuk dëshmon që përmbajtja është e saktë në kuptim.

## Çfarë nuk dimë për pozitivët e rremë

Paketa e dorëzuar nuk përmban etiketa të pavarura, prandaj projekti nuk mund
të llogarisë normën e pozitivëve të rremë. Numri i tenderëve në radhën e
shqyrtimit varet nga pragjet, përbërja e procedurave dhe grupi i ruajtur i të
dhënave. Përqindjet e tenderëve me një ofertues duhen lexuar sipas nënllojit të
procedurës, statusit të dhënies, vitit dhe brezit të vlerës — jo si një
përqindje e vetme kombëtare dhe as si e barasvlershme me një tregues
referues të BE-së.

Pikët e kombinuara, percentilet e modeleve dhe filtri sipas përputhjes së
rezultateve të modeleve varen nga bashkësia e të dhënave që analizohet. Nëse
ndryshon bashkësia e të dhënave, mund të ndryshojë edhe renditja e të njëjtit
tender. Projekti nuk ruan statistika referuese fikse, me version të përcaktuar,
për vlerësimin e vazhdueshëm të tenderëve të rinj. Çdo ekzekutim i plotë i
analizës prodhon një renditje të re brenda bashkësisë përkatëse të të dhënave.

Identiteti i furnizuesve paraqitet në tri mënyra, për të kontrolluar
ndjeshmërinë e rezultateve: ID-ja e biznesit me emrin; ID-ja e biznesit me
ID-në e palës në burim dhe emrin; dhe vetëm ID-ja e biznesit. Vlerat
zëvendësuese që nuk janë ID reale trajtohen si të munguara, por ruhen në
fushën e papërpunuar. ID-ja e palës është çelës brenda publikimit, jo
identifikues juridik i verifikuar; i njëjti emër mund të bashkojë subjekte
të ndryshme, ndërsa ID-ja burimore mund ta ndajë të njëjtin subjekt. Këto
pamje nuk e zgjidhin plotësisht identifikimin e furnizuesve dhe nuk e bëjnë
HHI-në matës të përqendrimit në një treg përkatës.

Kur burimi nuk publikon numrin e ofertuesve, ky numër mbetet i papërcaktuar
dhe përjashtohet nga emëruesi i përqindjeve të tenderëve me një ose zero
ofertues. Mungesa e publikimit nuk interpretohet si mungesë konkurrence.

## Si ta përdorni panelin me përgjegjësi

1. **Filloni nga faqet «Kontrollet e modeleve» dhe «Krahasimi i
   modeleve».** Lexoni kufizimet dhe kontrollet e brendshme para se të
   përdorni renditjen.
2. **Kufizoni analizën në fushën tuaj.** Një auditor komunal ka gjasa të
   dojë vetëm autoritetin e vet; përdorni filtrat në shiritin anësor.
3. **Zgjidhni renditjen te «Rendit sipas».** «Pikët e rregullave»
   (`rule_score`) japin renditjen më transparente, ndërsa «Pikët e
   kombinuara» (`ensemble_score`) japin një renditje eksploruese. Kutia
   «Vetëm tenderët ku modelet pajtohen…» e ngushton listën te tenderët që
   të paktën 3 nga 4 modelet i rendisin mes 5% më të pazakontëve; ajo nuk e
   rrit automatikisht vlefshmërinë e gjetjeve.
4. **Hapni hollësitë e tenderit.** Për «Pikët e kombinuara», përdorni
   zbërthimin e saktë në percentilet e renditjes së modeleve, pikët e
   rregullave dhe pikët e kontekstit; vlera bazë plus ndikimet e përbërësve
   duhet ta rindërtojnë pikën e publikuar. Për «Pikët e rregullave»,
   shpjegimi parësor është lista e rregullave të aktivizuara dhe llogaritja
   e tyre. Grafiku SHAP (ujëvara) është vetëm shpjegim dytësor i modelit
   ndihmës që imiton rregullat (dalje në log-shanse) dhe nuk shpjegon pikët e
   kombinuara.
5. **Merrni dokumentet burimore** para çdo përfundimi. Njoftimi i tenderit,
   kontrata e nënshkruar (nëse ekziston) dhe vendimi i dhënies gjenden te
   autoriteti kontraktues dhe te KRPP-ja; ato janë burimi përfundimtar për
   verifikim.

## Si të mos e përdorni panelin

- **Mos** publikoni lista «kontraktorësh të dyshimtë» bazuar në tenderët e
  sinjalizuar.
- **Mos** e lidhni pikën me emrin e një personi në asnjë publikim.
- **Mos** e trajtoni sinjalin «Vlera e vendimeve tejkalon parashikimin» si
  provë manipulimi të çmimit; ai mund të tregojë thjesht se vlera e
  parashikuar ishte jorealiste ose se lotet nuk janë të krahasueshme.
- **Mos** i trajtoni tenderët me pak ofertues si automatikisht të dyshimtë;
  për punë teknike të specializuara, numri i ofertuesve të kualifikuar është
  natyrshëm i vogël.

## Privatësia

Burimi OCDS është plotësisht publik. Ruajmë vetëm atë që publikohet, nuk e
pasurojmë me të dhëna private dhe nuk lidhim individë me regjistrimet e
prokurimit.

## Raportimi i problemeve

Nëse vëreni një tender që besoni se është klasifikuar gabim, ose një veçori
të modelit që anon sistematikisht kundër një kategorie autoritetesh
kontraktuese apo furnizuesish, raportojeni problemin te autori i projektit.
Raporte të tilla trajtohen si gabime që duhen korrigjuar, jo si mendime.
