# Përdorimi i Përgjegjshëm

Zbulimi i anomalive në **prokurime publike është temë e ndjeshme**.
Një shenjë (flag) në këtë sistem *nuk* është akuzë. Ky dokument sqaron
çfarë bën projekti, çfarë nuk bën, dhe si duhen lexuar rezultatet e tij.
Analiza mbulon vetëm snapshot-in e Publikimit 115: 75,710 rekorde dhe
118 muaj me të dhëna nga 121 muaj në intervalin e publikuar. Nuk është
monitorim live ose cens i plotë i prokurimit kombëtar.

## Parimi themelor

> Një pikë e lartë anomalie do të thotë *"ky rekord tenderi renditet si i
> pazakontë brenda snapshot-it dhe/ose aktivizon tregues të përcaktuar nga
> autori; një auditor me dokumente në dorë duhet ta vendosë në kontekst"*.
>
> **Nuk** do të thotë që tenderi është mashtrues, që dikush ka vepruar
> në mënyrë të parregullt, apo që ka ndodhur ndonjë shkelje.

Përdorim me qëllim fjalët **shenjë**, **sinjal**, **rishikim** —
**kurrë** "mashtrim" ose "korrupsion" — kur përshkruajmë daljet e modelit.

Objekti OCDS `award` është vetëm një **vendim dhënieje i regjistruar**.
`awarded_value_eur` nuk është provë e vlerës së një kontrate të nënshkruar,
të ekzekutuar ose të paguar dhe nuk është shpenzim real. Për këtë arsye
paneli përdor shprehjen “vlera e dhënieve të regjistruara”.

## Çfarë bëjmë për t'u mbrojtur nga akuzat e rreme

1. **Pajtim renditjesh, jo provë e pavarur.** Ansambli kombinon renditjet e
   katër detektorëve kampionë me shtresën e rregullave dhe pikën
   kontekstuale. Kolona historikisht e quajtur `high_confidence` do të
   thotë vetëm se të paktën **3 nga 4** detektorët e vendosin rekordin në
   **5% më të lartë të batch-it aktual**. Nuk është besueshmëri e
   kalibruar dhe nuk provon më pak falsë pozitive.

2. **Rregulla transparente.** Çdo rregull ka kod, përshkrim në gjuhë të
   thjeshtë, arsyetim/prag të deklaruar, kufizime dhe peshë fikse.
   Riprodhohen me makinë llogaritëse. Shih `src/thesis/anomaly/rules.py`.

3. **Vlerësim kontekstual.** Anomalia është kontekstuale: një tender
   5 mln € është normal për Ministrinë e Infrastrukturës dhe i pazakontë
   për një komunë të vogël. `context_score` e pasqyron këtë shprehimisht.

4. **Zgjedhje modeli me protokoll të dokumentuar.** Modelet në ansambël
   renditen me rrjeta hiperparametrash, stabilitet bootstrap, konsistencë
   seed-esh dhe besnikëri ndaj etiketave proxy të rregullave. Ndarja
   ≤2023/≥2024 nuk simulon përdorim real: objektivi i rregullave dhe
   inputet e modelit mbivendosen fort. E gjithë renditja publikohet në
   faqen "Krahasimi i Modeleve" dhe në
   `data/models/benchmark/leaderboard.md`.

5. **Kontrolle të brendshme çdo herë.** Ekzekutimi prodhon
   `data/models/validation_report.json` me CV kundër proxy-t,
   stabilitet bootstrap, pajtim ndër-modelesh dhe kalibrim ndaj etiketave
   të rregullave. Këto matin sjelljen e brendshme, jo aftësi zbulimi.

6. **Banner i përhershëm.** Çdo faqe e panelit mban paralajmërimin
   "Anomalia ≠ mashtrim". Është kërkesë e fortë (bllokohet në PR) që ky
   banner të mbetet.

7. **Gjurmim linje.** Artefaktet Parquet mbajnë sidecar `*.lineage.json`
   me hash-e inputesh/daljesh, version kodi dhe run-id; manifestet e fazave
   lidhin grupin e plotë të daljes. Kjo mbështet auditimin e snapshot-it, por
   nuk e kthen hash-in në provë të vlefshmërisë semantike.

## Çfarë nuk dimë për falsë pozitivët

Nuk ka etiketa të pavarura në paketën e dorëzuar, prandaj projekti nuk
mund të llogarisë normën e falsë-pozitivëve. Numri i rekordeve në radhën
e rishikimit varet nga pragjet, përzierja e procedurave dhe snapshot-i.
Normat e ofertuesit të vetëm duhen lexuar sipas nënllojit të procedurës,
statusit të dhënies, vitit dhe brezit të vlerës — jo si një përqindje e
përbashkët kombëtare ose si ekuivalent i një benchmark-u të BE-së.

`ensemble_score`, percentilet e detektorëve dhe `high_confidence` janë
relative ndaj snapshot-it aktual. Ndryshimi i popullatës krahasuese mund
të ndryshojë renditjen e të njëjtit rekord. Nuk ka statistikë reference të
ngrirë/versionuar për pikëzim online; çdo ekzekutim i plotë krijon renditje të
reja ndaj batch-it të vet.

Identiteti i furnizuesit raportohet me pamje ndjeshmërie: ID biznesi/emër,
ID biznesi/ID pale burimore/emër dhe vetëm ID biznesi. ID-të sentinel
normalizohen si të munguara, por ruhen në fushën e papërpunuar. ID-ja e palës
është çelës i publikimit, jo identifikues juridik i verifikuar; emri mund të
bashkojë subjekte të ndryshme dhe ID-ja burimore mund ta ndajë të njëjtin
subjekt. Këto pamje nuk janë zgjidhje e plotë identiteti dhe nuk e bëjnë HHI-në
një përkufizim tregu relevant.

Kur burimi nuk publikon ofertuesit, numri mbetet i papërcaktuar dhe përjashtohet
nga emëruesi i normës së ofertuesit të vetëm/zero. Mungesa e publikimit nuk
interpretohet si zero konkurrencë.

## Si të përdoret paneli me përgjegjësi

1. **Fillo nga faqja "Validimi"** dhe "Krahasimi i Modeleve" — lexo
   kufizimet dhe kontrollet e brendshme para se të përdorësh renditjen.
2. **Filtro në fushën tënde.** Një auditor komunal ka gjasa të dojë
   vetëm autoritetin e vet — përdor shiritin anësor.
3. **Rendit sipas `ensemble_score`** për një renditje eksploruese, ose
   sipas `rule_score` për shtresën transparente. Filtri
   `high_confidence` ngushton te pajtimi i renditjeve top-5%; nuk rrit
   automatikisht vlefshmërinë e gjetjeve.
4. **Hap pamjen për-tender.** Për `ensemble_score`, përdor zbërthimin ekzakt
   të rank-percentileve të detektorëve, `rule_score` dhe `context_score`;
   baza plus efektet e komponentëve duhet ta rindërtojnë pikën e publikuar.
   Për radhën heuristike, lista dhe aritmetika e rregullave janë shpjegimi
   parësor. Ujëvara SHAP është vetëm shpjegim dytësor i daljes log-odds të
   proxy-t të rregullave dhe nuk shpjegon ansamblin.
5. **Tërhiq dokumentet burimore** para çdo përfundimi. Njoftimi i
   tenderit, kontrata e nënshkruar (nëse ekziston) dhe vendimi i dhënies
   qëndrojnë tek autoriteti kontraktues dhe KRPP — ato janë e vërteta bazë.

## Si të MOS përdoret paneli

- **Mos** publiko një listë "kontraktorësh të dyshimtë" bazuar në
  bashkësinë e shenjuar.
- **Mos** kombino pikën me emrin e një personi në asnjë dalje publike.
- **Mos** e trajto rregullën `awarded > estimated` si provë manipulimi
  çmimi; mund të thotë thjesht që vlerësimi ishte jorealist.
- **Mos** i trajto tenderët me pak ofertues si automatikisht të dyshimtë —
  në punë teknike bazeni i ofertuesve të kualifikuar është i vogël nga
  natyra.

## Privatësia

Feed-i OCDS është plotësisht publik. Ruajmë vetëm çfarë publikohet. Nuk
pasurojmë me të dhëna private. Nuk lidhim individë me rekorde prokurimi.

## Raportimi i problemeve

Nëse vëren një rekord tenderi që beson se është klasifikuar gabim, ose një
veçori të modelit që anon sistematikisht kundër një kategorie blerësi
apo furnizuesi, hap një issue. Raporte të tilla i trajtojmë si gabime
(bugs), jo si opinione.
