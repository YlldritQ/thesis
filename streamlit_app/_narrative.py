"""Clear Albanian presentation text; analytical definitions remain unchanged."""

from __future__ import annotations

from typing import Any

import pandas as pd
from _charts import fmt_eur

from thesis.narrative import FLAG_NARRATIVE as _SOURCE_FLAGS
from thesis.narrative import METRIC_HELP as _SOURCE_HELP
from thesis.narrative import contract_severity as _source_severity
from thesis.narrative import explain_flags as _source_flags

METRIC_HELP = {
    **_SOURCE_HELP,
    "estimated_value_eur": "Vlera që autoriteti kontraktues ka parashikuar për tenderin. "
    "Nuk është shpenzim i kryer.",
    "total_awarded_eur": "Shuma e vlerave në vendimet e regjistruara për dhënie të kontratës. "
    "Një vendim dhënieje nuk dëshmon se kontrata është nënshkruar, ekzekutuar ose paguar. "
    "Kur nuk ka vendim të regjistruar, shfaqet —.",
    "awarded_value_ratio": "Vlera e vendimeve të dhënies pjesëtuar me vlerën e parashikuar. "
    "100% do të thotë se dy vlerat janë të barabarta. Lote ose vendime të pjesshme "
    "mund ta bëjnë krahasimin të paplotë; raporti nuk mat kursim ose tejkalim shpenzimesh.",
    "num_bidders": "Numri i ofertuesve të regjistruar në burim. Një ofertues mund të jetë "
    "operator ekonomik ose grup operatorësh. Shenja — tregon se numri mungon, jo se është zero.",
    "n_awards": "Numri i vendimeve ose rreshtave të dhënies të regjistruar për tenderin. "
    "Nuk është numri i kontratave të nënshkruara ose i pagesave.",
    "winner_top_share": "Pjesa e vlerës së vendimeve të dhënies që lidhet me furnizuesin "
    "kryesor. 100% do të thotë se e gjithë vlera e regjistruar lidhet me të njëjtin identitet.",
    "days_tender_open": "Ditët ndërmjet fillimit dhe afatit për dorëzimin e ofertave, "
    "sipas datave të publikuara. Kuptimi varet nga lloji i procedurës dhe korrigjimet e mundshme.",
    "days_to_first_award": "Ditët nga afati për dorëzimin e ofertave deri te vendimi i parë "
    "i dhënies. Vlerat negative kërkojnë verifikim të datave në dokumentet burimore.",
    "ensemble_score": "Pikë nga 0 në 1 që kombinon rregullat dhe modelet statistikore. "
    "Sa më e lartë, aq më lart renditet tenderi për shqyrtim në këtë grup të dhënash. "
    "Nuk është probabilitet shkeljeje dhe nuk ndryshon kur përdorni filtrat e faqes.",
    "rule_score": "Pikë nga 0 në 1, sipas sinjaleve për shqyrtim dhe peshave të zgjedhura "
    "nga autori. Kontrollet e cilësisë së të dhënave nuk shtojnë pikë. Nuk mat probabilitet shkeljeje.",
    "context_score": "Sa ndryshon tenderi nga tenderë të ngjashëm të të njëjtit autoritet, "
    "në të njëjtën kategori dhe procedurë. Ndryshimi statistikor kërkon shpjegim në kontekst.",
    "supplier_hhi": "Tregues i përqendrimit të vlerës së vendimeve te furnizuesit, nga "
    "afër 0 deri në 10 000. Vlera më të larta tregojnë përqendrim te më pak furnizues. "
    "Varet nga identifikimi i furnizuesve dhe nuk është matje e konkurrencës së një tregu.",
    "single_bidder_pct": "Përqindja e tenderëve me vetëm një ofertues, ndër tenderët ku "
    "numri i ofertuesve është publikuar. Tenderët me numër të panjohur nuk përfshihen në llogaritje.",
}

# Keep codes and severity levels aligned with the published analytical rules.
FLAG_NARRATIVE = {
    **_SOURCE_FLAGS,
    "SINGLE_BIDDER_OPEN": (
        "Një ofertues në procedurë të hapur",
        "Në një procedurë të hapur standarde është regjistruar vetëm një ofertues. "
        "Kontrolloni kushtet e tenderit dhe rrethanat e tregut për të kuptuar pjesëmarrjen e ulët.",
        2,
    ),
    "SINGLE_BIDDER": (
        "Vetëm një ofertues",
        "Është regjistruar vetëm një ofertues. Kuptimi varet nga procedura, vlera dhe tregu; "
        "ky sinjal merr peshë më të ulët se një ofertues i vetëm në procedurë të hapur.",
        1,
    ),
    "ZERO_BIDDER": (
        "Asnjë ofertues i regjistruar",
        "Burimi shënon zero ofertues dhe nuk përmban vendim dhënieje. Kontrolloni nëse "
        "procedura është anuluar, është ende në zhvillim ose të dhënat janë të paplota.",
        1,
    ),
    "RATIO_ABOVE_ESTIMATE": (
        "Vlera e vendimeve tejkalon parashikimin",
        "Shuma e regjistruar është nga 105% deri në 400% e vlerës së parashikuar. "
        "Verifikoni nëse lotet dhe vendimet janë të krahasueshme para se ta interpretoni ndryshimin.",
        1,
    ),
    "IMPLAUSIBLE_ESTIMATE": (
        "Dallim shumë i madh ndërmjet vlerave",
        "Vlera në vendimet e dhënies është mbi katërfishin e vlerës së parashikuar. "
        "Mund të ketë gabim në njësinë, shumën ose fushën e publikuar. Krahasimi i këtyre "
        "vlerave kërkon verifikim në dokumentet burimore.",
        1,
    ),
    "RATIO_BELOW_50": (
        "Vlera e vendimeve është nën gjysmën e parashikimit",
        "Vlera e regjistruar është të paktën 1%, por më pak se 50% e parashikimit. "
        "Mund të mbulojë vetëm disa lote ose vendime të pjesshme. Nuk mjafton për të matur kursimin.",
        1,
    ),
    "NEGATIVE_DAYS_TO_AWARD": (
        "Vendimi daton para afatit për oferta",
        "Data e vendimit të dhënies është para afatit për dorëzimin e ofertave. "
        "Verifikoni kuptimin dhe saktësinë e të dy datave në dokumentet burimore.",
        1,
    ),
    "ULTRA_SHORT_OPEN": (
        "Afat nën shtatë ditë në procedurë të hapur",
        "Periudha e regjistruar për dorëzimin e ofertave është nën shtatë ditë në një "
        "procedurë të hapur standarde. Kuotimet e çmimeve përjashtohen nga ky kontroll. "
        "Verifikoni urgjencën, korrigjimet dhe dokumentet përkatëse; sinjali nuk konstaton shkelje.",
        1,
    ),
    "PRICE_QUOTATION_VALUE_BAND_CONFLICT": (
        "Vlerë e pazakontë për kuotim të çmimeve",
        "Procedura është koduar si kuotim i çmimeve, por vlera e parashikuar është së paku "
        "10 000 €. Kontrolloni kodimin, lotet dhe ndryshimet në dokumentet burimore.",
        1,
    ),
    "BUYER_NAME_ID_COLLISION": (
        "I njëjti emër autoriteti me disa identifikues",
        "Emri i autoritetit shfaqet me më shumë se një identifikues. Mund të jetë ndryshim "
        "identifikuesi ose institucione me emra të njëjtë. Ato mbahen të ndara derisa të verifikohen.",
        1,
    ),
    "HIGH_VALUE_SINGLE": (
        "Vlerë e lartë dhe vetëm një ofertues",
        "Tenderi është ndër 1% me vlerën më të lartë në kategorinë e vet dhe ka vetëm "
        "një ofertues. Ky kombinim merr përparësi për shqyrtim; nuk provon shkelje.",
        2,
    ),
    "END_BEFORE_START_OPEN": (
        "Afati për oferta është para datës së fillimit",
        "Në procedurën e hapur, data e përfundimit del para datës së fillimit. "
        "Kjo mospërputhje kërkon kontroll të datave në burim.",
        1,
    ),
    "LOT_VALUE_MISMATCH": (
        "Shuma e loteve ndryshon nga vlera e tenderit",
        "Vlerat e loteve ndryshojnë nga totali i tenderit për më shumë se 100 € dhe 0,1%. "
        "Ky është kontroll i të dhënave; kontrolloni nëse të gjitha pjesët janë publikuar njësoj.",
        1,
    ),
    "WINNER_TAKES_ALL_LARGE": (
        "Së paku 95% e vlerës lidhet me një furnizues",
        "Tenderi ka vlerë të parashikuar së paku 100 000 €, disa lote dhe vendime dhënieje; së paku 95% e vlerës "
        "lidhet me një identitet furnizuesi. Lidhja ndërmjet loteve dhe vendimeve mbështetet "
        "vetëm në tituj; verifikoni dokumentet para interpretimit.",
        2,
    ),
    "UNAWARDED_HIGH_VALUE": (
        "Tender me vlerë të lartë, pa vendim të regjistruar",
        "Tenderi është ndër 5% me vlerën më të lartë në kategorinë e vet dhe nuk ka vendim dhënieje në të dhënat "
        "e analizuara. Mund të jetë anuluar, në zhvillim ose me vendim të papublikuar.",
        1,
    ),
}


def explain_flags(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Use published ordering and suppression while displaying accessible wording."""
    clean = {key: False if pd.isna(row.get(key)) else row[key] for key in FLAG_NARRATIVE}
    return [
        {
            **flag,
            "title": FLAG_NARRATIVE[flag["code"]][0],
            "detail": FLAG_NARRATIVE[flag["code"]][1],
        }
        for flag in _source_flags(clean)
    ]


def contract_severity(row_or_score: Any) -> dict[str, Any]:
    if isinstance(row_or_score, dict):
        row_or_score = {
            key: False if key in FLAG_NARRATIVE and pd.isna(value) else value
            for key, value in row_or_score.items()
        }
    result = _source_severity(row_or_score)
    labels = {
        "Vëmendje — sinjal i lehtë": "Sinjal për verifikim",
        "I pazakontë statistikisht — pa arsye të qartë (kërkon ekspert)": "I pazakontë sipas modeleve — pa sinjal nga rregullat",
        "Pak i pazakontë — vëmendje": "Dallime statistikore për shqyrtim",
    }
    result["label"] = (
        labels.get(result["label"], result["label"])
        .replace("rishikim", "shqyrtim")
        .replace("në snapshot", "në grupin e të dhënave")
    )
    return result


def plain_summary(row: dict[str, Any]) -> str:
    """Describe only what is actually recorded, without inferring contract status."""
    entity = row.get("procuring_entity_name")
    entity = str(entity) if pd.notna(entity) and str(entity).strip() else "Autoritet i panjohur"
    parts = [f"Autoriteti kontraktues: **{entity}**."]
    estimated = row.get("estimated_value_eur")
    if pd.notna(estimated):
        parts.append(f"Vlera e parashikuar është **{fmt_eur(estimated)}**.")
    awarded = row.get("was_awarded")
    if pd.isna(awarded):
        count = row.get("n_awards")
        awarded = pd.notna(count) and float(count) >= 1
    award_value = row.get("total_awarded_eur")
    if awarded and pd.notna(award_value):
        parts.append(f"Vlera në vendimet e dhënies është **{fmt_eur(award_value)}**.")
    elif not awarded:
        parts.append("Nuk ka vendim dhënieje të regjistruar në të dhënat e analizuara.")
    bidders = row.get("num_bidders")
    if pd.isna(bidders):
        parts.append("Numri i ofertuesve nuk është publikuar.")
    elif int(bidders) == 0:
        parts.append("Burimi shënon **zero ofertues**.")
    elif int(bidders) == 1:
        parts.append("Është regjistruar **1 ofertues**.")
    else:
        parts.append(f"Janë regjistruar **{int(bidders)} ofertues**.")
    return " ".join(parts)


DATA_LIMITATION_BIDS = (
    "Burimi nuk jep çmimin e secilës ofertë. Prandaj nuk mund të krahasojmë çmimin e "
    "fituesit me ofertat e tjera. Krahasimi me vlerën e parashikuar mund të përfshijë lote "
    "ose vendime të pjesshme dhe nuk mat mbiçmim, kursim ose pagesë. Vendimi i dhënies "
    "nuk dëshmon se kontrata është nënshkruar, ekzekutuar ose paguar."
)
