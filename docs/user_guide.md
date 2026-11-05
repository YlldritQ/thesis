# Udhëzuesi i përdorimit

Paneli ndihmon në shqyrtimin e të dhënave të publikuara të prokurimit në Kosovë:
çfarë parashihet të blihet, kush merr pjesë dhe cilët tenderë kërkojnë verifikim.
Është pjesë e një projekti diplome, jo shërbim zyrtar i institucioneve. Analiza
përdor një version të ruajtur të të dhënave, pa përditësim automatik.

**Anomalia ≠ mashtrim.** Një sinjal është arsye për të shqyrtuar dokumentet,
jo përfundim se ka ndodhur shkelje. Lexoni edhe
[përdorimin e përgjegjshëm](responsible_use.md).

Për instalimin dhe nisjen e panelit, shihni [README-n kryesor](../README.md).

## Nëntë faqet e panelit

Tabela më poshtë përdor emërtimet e menysë anësore.

| Faqja | Për çfarë shërben |
|---|---|
| **Ballina** | Paraqet numrin e tenderëve dhe autoriteteve, vlerën e parashikuar, rastet mbi pragun e rregullave dhe ecurinë mujore. Përfshin të gjithë bashkësinë e të dhënave. |
| **Përmbledhja** | Krahason ecurinë, kategoritë, procedurat, konkurrencën dhe shpërndarjen e vlerave sipas filtrave. Lejon shkarkimin e tenderëve të përzgjedhur në CSV. |
| **Kërko tenderë** | Kërkon sipas titullit, autoritetit, furnizuesit ose identifikuesit. Paraqet të dhënat e një tenderi, sinjalet dhe furnizuesit sipas vendimeve për dhënien e kontratës. |
| **Sinjalet për shqyrtim** | Shpjegon arsyet e veçimit të një tenderi. Ofron renditje sipas pikëve, filtra sipas sinjalit dhe llogaritjet që qëndrojnë pas rezultatit. |
| **Autoritetet dhe furnizuesit** | Krahason aktivitetin dhe paraqet profile të veçanta, për të gjithë periudhën. Shpjegon edhe përqendrimin e vlerës te furnizuesit dhe kufizimet e identifikimit të tyre. |
| **Si funksionon analiza** | Shpjegon hapat, rregullat dhe cilësinë e të dhënave. Dokumentacioni teknik hapet sipas nevojës. |
| **Vlerësimi i modeleve** | Krahason përzgjedhjen sipas rregullave me pikët e kombinuara dhe tregon sa të qëndrueshme janë rezultatet kur analiza përsëritet. |
| **Krahasimi i modeleve** | Tregon konfigurimet e krahasuara, modelet e përzgjedhura dhe mënyrën e përzgjedhjes. Rezultatet janë matje të brendshme, jo saktësi zbulimi të mashtrimit. |
| **Fjalori i termave** | Shpjegon termat e prokurimit dhe mësimit makinerik, treguesit, ngjyrat dhe sinjalet. Ofron kërkim sipas termit, shembuj interpretimi dhe referenca për terminologjinë shqipe. |

## Një mënyrë e thjeshtë për të filluar

1. **Shihni Ballinën.** Kontrolloni periudhën dhe burimin. Hapni shpjegimin
   për mbulimin e të dhënave përpara se të interpretoni ecurinë mujore.
2. **Filtroni të dhënat në Përmbledhje.** Te **Filtro të dhënat**, zgjidhni,
   për shembull, një autoritet dhe një vit. Krahasoni numrin dhe vlerat e tenderëve.
   Te **Konkurrenca**, shqyrtoni së bashku përqindjen e tenderëve me një ofertues
   dhe mbulimin e të dhënave për ofertuesit.
3. **Gjeni një rast te Kërko tenderë.** Shkruani një titull, emër ose numër
   tenderi; pastaj përdorni **Zgjidh nga rezultatet**. Lexoni vlerat, afatin
   dhe pjesën **Çfarë kërkon verifikim?** Tabela dhe përzgjedhësi paraqesin
   deri në 500 rezultate; ngushtoni kërkimin nëse lista është më e gjatë.
   Te hollësitë e pikëve, **Shpjego pikët e këtij tenderi →** hap shpjegimet
   për të njëjtin tender te **Sinjalet për shqyrtim**.
4. **Kuptoni sinjalin.** Te **Sinjalet për shqyrtim**, zgjidhni një nga
   tenderët e renditur ose vendosni OCID-in e rastit. Lexoni shpjegimin
   përpara se të interpretoni pikët. Llogaritjet teknike gjenden në seksionet
   që zgjerohen me klikim.
5. **Kontrolloni dokumentet burimore.** Mbani shënim OCID-in, filtrat dhe
   arsyen e shqyrtimit. Verifikoni njoftimet, lotet dhe vendimet në burimin
   përkatës. Nëse dëshironi vlerësim të strukturuar për punimin, ndiqni
   [protokollin e shqyrtimit manual](manual_audit_protocol.md).

Në faqen e sinjaleve, zgjedhjet te **Krahaso tenderët sipas pikëve** ndryshojnë
listën poshtë tyre. Ato nuk ndryshojnë automatikisht tenderin e hapur më sipër.

## Filtrat dhe shkarkimi

Filtrat e përbashkët gjenden te **Filtro të dhënat**, në faqet **Përmbledhja**,
**Kërko tenderë** dhe **Sinjalet për shqyrtim**. Mund të zgjidhni vitin e publikimit, kategorinë,
metodën sipas burimit, autoritetin dhe kufijtë e vlerës së parashikuar në euro.

- Një fushë pa përzgjedhje përfshin të gjitha vlerat; **Hiq filtrat**
  heq filtrat e përbashkët. Teksti i kërkimit dhe zgjedhjet e veçanta të
  secilës faqe menaxhohen më vete.
- **E papërcaktuar** përfshin të dhënat pa klasifikim ose pa vit të njohur.
  Kur vendosni kufij në euro, tenderët pa vlerë të parashikuar përjashtohen.
- **Ballina** dhe **Autoritetet dhe furnizuesit** paraqesin të gjithë bashkësinë;
  filtrat e faqeve të tjera nuk i kufizojnë këto përmbledhje.
- Kërkimi i drejtpërdrejtë me OCID e gjen tenderin në të gjithë bashkësinë,
  edhe kur ai nuk i plotëson filtrat e listës.

Te **Përmbledhja**, hapni **Shkarko të dhënat e filtruara**.
CSV-ja përfshin të gjithë tenderët që përputhen me filtrat, jo vetëm rreshtat
që duken në ekran. Emrat teknikë të kolonave ruhen për ripërdorim në analizë.

## Si të lexoni shifrat

| Treguesi | Kuptimi |
|---|---|
| **Vlera e parashikuar** | Vlera që autoriteti kontraktues ka parashikuar për tenderin. Nuk është shpenzim i kryer. |
| **Vlera sipas vendimeve** | Shuma e vlerave të shënuara në vendimet për dhënien e kontratës. Këto vendime nuk dëshmojnë se kontrata është nënshkruar apo zbatuar, ose se janë kryer pagesa. |
| **Me vetëm një ofertues** | Te **Përmbledhja**, përqindja llogaritet vetëm ndër tenderët me numër të publikuar ofertuesish. Mungesat përjashtohen nga baza e përqindjes. |
| **Mediana** | Vlera në mes të listës së renditur; ndikohet më pak nga disa tenderë me vlera shumë të mëdha. |
| **Pikët sipas rregullave** | Përmbledhje nga 0 në 1 e sinjaleve që shtojnë pikë, me pesha të përcaktuara nga autori. Kontrollet e cilësisë nuk shtojnë pikë. |
| **Pikët e kombinuara** | Përmbledhin renditjet e modeleve, rregullat dhe krahasimin me tenderë të ngjashëm. Shërbejnë për renditje brenda bashkësisë së analizuar. |
| **Vetëm tenderët e sinjalizuar nga disa modele: …** | Kuti zgjedhjeje te **Sinjalet për shqyrtim**. Në versionin e përfshirë, mban tenderët që së paku 3 nga 4 modelet i rendisin ndër 5% më të pazakontët. Numri i modeleve dhe pragu shfaqen në etiketë sipas konfigurimit. Veçoritë e modeleve përkojnë pjesërisht, prandaj përputhja e rezultateve nuk është garanci se ka shkelje. |
| **HHI** | Përqendrimi i vlerës së vendimeve te furnizuesit. Vlera më të larta tregojnë përqendrim te më pak furnizues, sipas mënyrës së identifikimit të përdorur. Nuk mat vetvetiu konkurrencën e një tregu. |

Shenja **—** tregon vlerë të munguar ose të papërcaktueshme; nuk është zero.
Në grafikët kohorë, një muaj bosh nuk provon mungesë prokurimi. Tenderët pa
datë publikimi mund të jenë në treguesit kryesorë, por mungojnë në grafikët kohorë.

Te profilet e furnizuesve, **Vendime për tenderë me një ofertues (%)** përdor rreshtat
e vendimeve me të dhëna të njohura. Një tender me disa vendime mund të
numërohet disa herë në këtë tregues; mos e barazoni drejtpërdrejt me
përqindjen e tenderëve në Përmbledhje.

## Çfarë mund të përfundoni nga analiza?

Pikët dhe ngjyrat ndihmojnë në përzgjedhjen e rasteve për shqyrtim.
Një vlerë prej 0,8 pikësh nuk do të thotë probabilitet 80% që të ketë mashtrim. Filtrat ndryshojnë
rastet e shfaqura, jo pikët e ruajtura; pikët mund të ndryshojnë kur
analiza rindërtohet me një bashkësi tjetër të dhënash.

Dallimi ndërmjet vlerës së parashikuar dhe vlerës sipas vendimeve nuk mat automatikisht
kursimet apo tejkalimin e shpenzimeve: lotet dhe vendimet e pjesshme mund t'i bëjnë
vlerat të pakrahasueshme. Gjithashtu, pa çmimet e secilës ofertë nuk mund të
përcaktohet nëse u zgjodh oferta më e lirë.

Matjet ROC-AUC dhe PR-AUC në faqet e modeleve përdorin etiketa të nxjerra nga
rregullat. Ato matin përputhjen me këto rregulla. Qëndrueshmëria mat sa
përsëritet përzgjedhja. Asnjëra nuk zëvendëson verifikimin e pavarur të rasteve.

Emrat ose identifikuesit e furnizuesve mund të jenë të paplotë. Një renditje
institucionesh ose furnizuesish përshkruan të dhënat e analizuara; nuk është
renditje e ligjshmërisë apo performancës së tyre. Mungesa e sinjaleve nuk
vërteton mungesën e problemeve.

Për përkufizimet dhe kufizimet e plota, shihni [metodologjinë](methodology.md).
Për dokumentet e tjera, kthehuni te [indeksi i dokumentacionit](README.md).
