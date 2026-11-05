"""Albanian descriptions of the published rules, for dashboard presentation only."""

RULE_TEXT_SQ: dict[str, dict[str, str]] = {
    "SINGLE_BIDDER": {
        "description": (
            "Vetëm një ofertues në një procedurë që nuk klasifikohet si procedurë e hapur standarde "
            "(sinjal që kërkon shqyrtim në kontekst)."
        ),
        "threshold_rationale": (
            "Numri i publikuar i ofertuesve është një. Ky është tregues përshkrues, "
            "jo konstatim i një shkeljeje ligjore."
        ),
        "limitations": (
            "Një ofertues i vetëm mund të shpjegohet nga mënyra e organizimit të procedurës, "
            "madhësia e tregut ose plotësia e të dhënave për ofertuesit."
        ),
    },
    "SINGLE_BIDDER_OPEN": {
        "description": (
            "Vetëm një ofertues në një procedurë që burimi e klasifikon si procedurë e hapur standarde."
        ),
        "threshold_rationale": (
            "Numri i publikuar i ofertuesve është një dhe nënlloji i procedurës në burim është "
            "procedurë e hapur standarde. Pesha 0,75 është zgjedhje e shprehur e autorit. "
            "Pas shkallëzimit për paraqitje, ky kusht i vetëm mbetet nën pragun 0,5 për shqyrtim."
        ),
        "limitations": (
            "Nuk vërteton marrëveshje të fshehtë mes ofertuesve. Burimi nuk jep numrin e "
            "operatorëve të kualifikuar në treg ose ofertat e përjashtuara para publikimit."
        ),
    },
    "ZERO_BIDDER": {
        "description": (
            "Numri i publikuar i ofertuesve është zero dhe nuk ka vendim të regjistruar për "
            "dhënien e kontratës (kontroll i ecurisë së procedurës)."
        ),
        "threshold_rationale": "Numri i publikuar i ofertuesve është zero.",
        "limitations": (
            "Rregulli kërkon gjithashtu që të mos ketë vendime të regjistruara për dhënien e "
            "kontratës. Nuk është sinjal për dhënie të drejtpërdrejtë të kontratës. Mungesa "
            "e të dhënave për ofertuesit nuk e aktivizon këtë rregull."
        ),
    },
    "RATIO_BELOW_50": {
        "description": (
            "Vlera sipas vendimeve është të paktën 1%, por më pak se 50% e vlerës së parashikuar."
        ),
        "threshold_rationale": (
            "Brezi diagnostik i ruajtur nga versionet e mëparshme është 0,01 ≤ raporti < 0,50. "
            "Nuk është përcaktuar sipas pragjeve ligjore."
        ),
        "limitations": (
            "Shuma e vlerave sipas vendimeve për të gjithë tenderin mund të mos jetë e "
            "krahasueshme me vlerat e parashikuara për lote të veçanta."
        ),
    },
    "RATIO_ABOVE_ESTIMATE": {
        "description": (
            "Vlera totale sipas vendimeve është të paktën 105% dhe jo më shumë se 400% e "
            "vlerës së parashikuar (interval krahasimi)."
        ),
        "threshold_rationale": (
            "Brezi diagnostik 1,05–4,00 është ruajtur nga versionet e mëparshme. "
            "Nuk është përcaktuar sipas pragjeve ligjore."
        ),
        "limitations": (
            "Nuk shton pikë derisa të sigurohet se vlerat e parashikuara dhe vlerat sipas "
            "vendimeve janë të krahasueshme për secilin lot ose kontratë."
        ),
    },
    "IMPLAUSIBLE_ESTIMATE": {
        "description": (
            "Vlera sipas vendimeve është mbi katërfishin e vlerës së parashikuar; fushat "
            "mund të mos jenë të krahasueshme ose mund të ketë gabim në të dhëna."
        ),
        "threshold_rationale": (
            "Raporti mbi 4,0 është ruajtur nga versionet e mëparshme dhe përdoret për "
            "kontrollin e cilësisë së të dhënave."
        ),
        "limitations": (
            "Dallimi mund të shpjegohet nga një gabim në burim. Nuk nxirret përfundim për "
            "integritetin e procedurës së prokurimit."
        ),
    },
    "NEGATIVE_DAYS_TO_AWARD": {
        "description": (
            "Data e vendimit për dhënien e kontratës është para datës së regjistruar të "
            "përfundimit të tenderit (kontroll i cilësisë së datave)."
        ),
        "threshold_rationale": (
            "Data dhe ora e vendimit të parë të regjistruar janë më të hershme se data "
            "dhe ora e regjistruar e përfundimit të tenderit."
        ),
        "limitations": (
            "Kuptimi i fushave të datave në burim ose korrigjimet e tyre mund ta shpjegojnë këtë renditje."
        ),
    },
    "ULTRA_SHORT_OPEN": {
        "description": (
            "Afati për ofertim është më i shkurtër se 7 ditë në një procedurë që burimi e "
            "klasifikon si procedurë e hapur standarde (vetëm për kontroll)."
        ),
        "threshold_rationale": (
            "Prag konservativ i përzgjedhur nga autori për shqyrtimin e rasteve, jo test i "
            "respektimit të afateve ligjore."
        ),
        "limitations": (
            "Të dhënat e nxjerra nuk përfshijnë rrethanat e urgjencës, korrigjimet e "
            "njoftimeve ose të gjitha përjashtimet që vlejnë në periudha të ndryshme. Për "
            "këtë arsye, ky tregues nuk jep kontribut të drejtpërdrejtë në pikët e kombinuara."
        ),
    },
    "PRICE_QUOTATION_VALUE_BAND_CONFLICT": {
        "description": (
            "Burimi e kodon procedurën si kuotim të çmimeve, ndërsa vlera e parashikuar "
            "është të paktën 10 000 € (kontroll i cilësisë së të dhënave)."
        ),
        "threshold_rationale": (
            "Nënlloji i publikuar i procedurës është kuotim i çmimeve dhe vlera e "
            "parashikuar është të paktën 10 000 €."
        ),
        "limitations": (
            "Mund të shpjegohet nga gabime në burim, ndryshime të dokumenteve, mënyra e "
            "paraqitjes së loteve ose marrëveshjeve kornizë, apo rrethana të tjera të "
            "dokumentuara. Nuk është konstatim i paligjshmërisë."
        ),
    },
    "BUYER_NAME_ID_COLLISION": {
        "description": (
            "I njëjti emër i normalizuar i autoritetit kontraktues shfaqet me disa "
            "identifikues në burim (kontroll i cilësisë së të dhënave)."
        ),
        "threshold_rationale": (
            "I njëjti emër i normalizuar lidhet me më shumë se një identifikues të "
            "plotësuar në burim."
        ),
        "limitations": (
            "Mund të pasqyrojë ndryshim të sistemit të identifikimit ose subjekte "
            "juridike të ndryshme me emra të ngjashëm. Procesi i përpunimit i mban veçmas."
        ),
    },
    "HIGH_VALUE_SINGLE": {
        "description": (
            "Tender me vlerë në grupin e 1% të tenderëve me vlerat më të larta dhe me "
            "vetëm një ofertues."
        ),
        "threshold_rationale": (
            "Vlera arrin percentilin e 99-të brenda kategorisë dhe është regjistruar "
            "vetëm një ofertues. Kushtet janë përzgjedhur nga autori."
        ),
        "limitations": (
            "Percentili varet nga bashkësia e të dhënave të analizuara. Sinjali shpreh "
            "ndërthurjen e dy kushteve dhe nuk përbën dëshmi të pavarur."
        ),
    },
    "END_BEFORE_START_OPEN": {
        "description": (
            "Në një procedurë të hapur standarde, data e përfundimit është para datës së "
            "fillimit (kontroll i cilësisë së datave)."
        ),
        "threshold_rationale": (
            "Data dhe ora e regjistruar e përfundimit janë më të hershme se data dhe "
            "ora e regjistruar e fillimit."
        ),
        "limitations": (
            "Përdoret vetëm për kontrollin e cilësisë së të dhënave burimore, jo si "
            "përcaktim i integritetit të procedurës."
        ),
    },
    "LOT_VALUE_MISMATCH": {
        "description": (
            "Shuma e vlerave të loteve ndryshon nga vlera e tenderit njëkohësisht për "
            "më shumë se 100 € dhe më shumë se 0,1%."
        ),
        "threshold_rationale": (
            "Tolerancë e kombinuar e mospërputhjes: 100 € në vlerë absolute dhe 0,1% "
            "në vlerë relative."
        ),
        "limitations": (
            "Vlerat e loteve dhe vlera e tenderit mund të jenë përmbledhur në mënyra të ndryshme."
        ),
    },
    "WINNER_TAKES_ALL_LARGE": {
        "description": (
            "Në një tender me disa lote dhe vlerë të parashikuar të paktën 100 000 €, "
            "të paktën 95% e vlerës sipas vendimeve lidhet me një furnizues."
        ),
        "threshold_rationale": (
            "Pjesa prej 95% dhe vlera minimale prej 100 000 € janë përzgjedhur nga autori."
        ),
        "limitations": (
            "Përdor shumën e vlerave sipas vendimeve për të gjithë tenderin, sepse "
            "vendimet lidhen me lotet vetëm sipas titujve. Kërkon shqyrtimin e "
            "strukturës së loteve. Pragjet nuk janë përcaktuar mbi bazën e rezultateve të verifikuara."
        ),
    },
    "UNAWARDED_HIGH_VALUE": {
        "description": (
            "Tender me vlerë në grupin e 5% të tenderëve me vlerat më të larta, pa "
            "vendim të regjistruar për dhënien e kontratës (kontroll i ecurisë së procedurës)."
        ),
        "threshold_rationale": (
            "Vlera arrin percentilin e 95-të brenda kategorisë dhe nuk ka vendim të "
            "regjistruar për dhënien e kontratës."
        ),
        "limitations": (
            "Tenderi mund të jetë anuluar, i papërfunduar ose të mos ketë përfunduar "
            "me dhënie kontrate për arsye të ligjshme. Nuk është sinjal korrupsioni."
        ),
    },
}
