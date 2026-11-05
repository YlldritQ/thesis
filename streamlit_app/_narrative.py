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
    "Nuk përfaqëson shpenzim të realizuar.",
    "total_awarded_eur": "Shuma e vlerave në vendimet e regjistruara për dhënie të kontratës. "
    "Vendimi nuk dëshmon se kontrata është nënshkruar apo zbatuar, ose se janë kryer pagesa. "
    "Nëse nuk ka vendim të regjistruar, shfaqet shenja —.",
    "awarded_value_ratio": "Vlera sipas vendimeve, e pjesëtuar me vlerën e parashikuar. "
    "Një raport prej 100% tregon se të dyja vlerat janë të barabarta. "
    "Lotet ose vendimet e pjesshme mund ta bëjnë krahasimin të paplotë. "
    "Ky raport nuk mat kursimin apo tejkalimin e shpenzimeve.",
    "num_bidders": "Numri i ofertuesve të regjistruar në burim. Një ofertues mund të jetë "
    "operator ekonomik ose grup operatorësh. Shenja — tregon se numri mungon, jo se është zero.",
    "n_awards": "Numri i vendimeve për dhënien e kontratës ose i rreshtave përkatës të regjistruar për tenderin. "
    "Nuk është numri i kontratave të nënshkruara ose i pagesave.",
    "winner_top_share": "Pjesa e vlerës sipas vendimeve që i takon furnizuesit "
    "kryesor. Një vlerë prej 100% tregon se e gjithë shuma lidhet me të njëjtin furnizues, "
    "sipas identifikimit në burim.",
    "days_tender_open": "Numri i ditëve nga fillimi deri në përfundimin e afatit për dorëzimin e ofertave, "
    "sipas datave të publikuara. Interpretimi varet nga procedura dhe korrigjimet e mundshme.",
    "days_to_first_award": "Ditët nga afati për dorëzimin e ofertave deri te vendimi i parë "
    "për dhënien e kontratës. Nëse vlera është negative, datat duhen verifikuar në dokumentet burimore.",
    "ensemble_score": "Vlerë nga 0 në 1, e llogaritur nga renditjet e modeleve, rregullat "
    "dhe krahasimi me tenderë të ngjashëm. Sa më e lartë të jetë, aq më lart renditet tenderi "
    "për shqyrtim brenda kësaj bashkësie të dhënash. "
    "Nuk tregon probabilitetin e shkeljes dhe nuk ndryshon kur përdorni filtrat e faqes.",
    "rule_score": "Vlerë nga 0 në 1, e llogaritur nga sinjalet për shqyrtim "
    "dhe peshat e caktuara nga autori. Kontrollet e cilësisë së të dhënave nuk shtojnë pikë. "
    "Kjo vlerë nuk tregon probabilitetin e shkeljes.",
    "context_score": "Sa ndryshon tenderi nga tenderë të ngjashëm të të njëjtit autoritet, "
    "në të njëjtën kategori dhe me të njëjtën procedurë. Dallimi statistikor duhet interpretuar "
    "duke marrë parasysh rrethanat e tenderit.",
    "supplier_hhi": "Tregues i përqendrimit të vlerës sipas vendimeve ndërmjet furnizuesve, nga "
    "afër 0 deri në 10 000. Vlera më të larta tregojnë përqendrim te më pak furnizues. "
    "Varet nga identifikimi i furnizuesve dhe nuk mat drejtpërdrejt konkurrencën në treg.",
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
        "në llogaritjen e pikëve, ky sinjal ka peshë më të vogël se sinjali për një ofertues të vetëm në procedurë të hapur.",
        1,
    ),
    "ZERO_BIDDER": (
        "Asnjë ofertues i regjistruar",
        "Burimi shënon zero ofertues dhe nuk përmban vendim për dhënien e kontratës. Kontrolloni nëse "
        "procedura është anuluar, është ende në zhvillim ose të dhënat janë të paplota.",
        1,
    ),
    "RATIO_ABOVE_ESTIMATE": (
        "Vlera sipas vendimeve tejkalon parashikimin",
        "Shuma e regjistruar është nga 105% deri në 400% e vlerës së parashikuar. "
        "Verifikoni nëse lotet dhe vendimet janë të krahasueshme para se ta interpretoni ndryshimin.",
        1,
    ),
    "IMPLAUSIBLE_ESTIMATE": (
        "Dallim shumë i madh ndërmjet vlerave",
        "Vlera sipas vendimeve është më shumë se katërfishi i vlerës së parashikuar. "
        "Mund të ketë gabim në njësinë, shumën ose fushën e publikuar. Krahasimi i këtyre "
        "vlerave kërkon verifikim në dokumentet burimore.",
        1,
    ),
    "RATIO_BELOW_50": (
        "Vlera sipas vendimeve është nën gjysmën e parashikimit",
        "Vlera e regjistruar është të paktën 1%, por më pak se 50% e vlerës së parashikuar. "
        "Mund të mbulojë vetëm disa lote ose vendime të pjesshme. Nuk mjafton për të matur kursimin.",
        1,
    ),
    "NEGATIVE_DAYS_TO_AWARD": (
        "Vendimi daton para afatit për oferta",
        "Data e vendimit për dhënien e kontratës është para afatit për dorëzimin e ofertave. "
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
        "Tenderi bën pjesë në 1% të tenderëve me vlerën më të lartë në kategorinë e vet dhe ka vetëm "
        "një ofertues. Ky kombinim merr përparësi për shqyrtim; nuk provon shkelje.",
        2,
    ),
    "END_BEFORE_START_OPEN": (
        "Afati për oferta është para datës së fillimit",
        "Në procedurën e hapur, data e regjistruar e përfundimit është më e hershme se data e fillimit. "
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
        "Tenderi ka vlerë të parashikuar të paktën 100 000 €, disa lote dhe vendime për dhënien e kontratës. "
        "Të paktën 95% e vlerës lidhet me të njëjtin furnizues, sipas identifikimit në burim. "
        "Lidhja ndërmjet loteve dhe vendimeve mbështetet "
        "vetëm në tituj; verifikoni dokumentet para interpretimit.",
        2,
    ),
    "UNAWARDED_HIGH_VALUE": (
        "Tender me vlerë të lartë, pa vendim të regjistruar",
        "Tenderi bën pjesë në 5% të tenderëve me vlerën më të lartë në kategorinë e vet dhe nuk ka vendim për dhënien e kontratës në të dhënat "
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
        .replace("në snapshot", "në bashkësinë e të dhënave")
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
        parts.append(f"Vlera sipas vendimeve është **{fmt_eur(award_value)}**.")
    elif not awarded:
        parts.append("Nuk ka vendim për dhënien e kontratës në të dhënat e analizuara.")
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
    "ose vendime të pjesshme dhe nuk mat mbiçmimin, kursimin apo pagesat. "
    "Vendimi për dhënien e kontratës nuk dëshmon se ajo është nënshkruar apo zbatuar, "
    "ose se janë kryer pagesa."
)
