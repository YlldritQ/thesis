"""Shtresa narrative — kthen flamujt teknikë dhe vlerat numerike në fjali
të thjeshta shqip që një qytetar pa njohuri teknike i kupton.

Ndarja e përgjegjësisë:
* :data:`METRIC_HELP` — shpjegim një-fjalësh për çdo vlerë (ç'tregon).
* :func:`explain_flags` — për çdo rregull të aktivizuar, një fjali "pse
  kjo është shqetësuese".
* :func:`contract_severity` — semafor (jeshile/verdhë/portokalli/kuqe).
* :func:`plain_summary` — një paragraf përmbledhës për tenderin/rekordin.

Kufizim i rëndësishëm (i deklaruar në UI): të dhënat OCDS përmbajnë vetëm
emrin e secilit ofertues, JO çmimin që ofroi secili. Prandaj "iu dha
kompanisë më të shtrenjtë" nuk matet dot. Raporti tender-nivel
dhënie/parashikuar shfaqet vetëm si kontroll krahasues i cilësisë; pa
lidhje lot–vendim dhënieje nuk interpretohet si mbiçmim ose kursim. Objekti
OCDS ``award`` është vendim dhënieje i regjistruar; nuk dëshmon kontratë të
nënshkruar, të ekzekutuar ose të paguar.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

# =====================================================================
#  Shpjegimi i çdo vlere — "ç'tregon kjo shifër"
# =====================================================================
METRIC_HELP: dict[str, str] = {
    "estimated_value_eur": "Sa parashikoi institucioni të shpenzonte për këtë tender, para se "
    "të hapte konkurrimin.",
    "total_awarded_eur": "Vlera totale e dhënieve të regjistruara, vetëm kur ekziston të paktën "
    "një vendim dhënieje. Objekti award nuk dëshmon kontratë të nënshkruar, "
    "të ekzekutuar ose të paguar; pa vendim vlera paraqitet si e papërcaktuar, jo €0.",
    "awarded_value_ratio": "Raporti: vlera e dhënieve të regjistruara ÷ vlera e parashikuar. "
    "Është diagnostik për kontroll të të dhënave; pa lidhje të saktë "
    "lot–vendim dhënieje nuk interpretohet si mbiçmim ose kursim.",
    "num_bidders": "Sa kompani u regjistruan si ofertues për këtë tender. Kur burimi "
    "nuk publikon listën/rolet, shfaqet — dhe mungesa nuk trajtohet si zero. "
    "Numri jep kontekst për konkurrencën, por nuk mat vetë drejtësinë e çmimit.",
    "n_awards": "Sa rreshta/vendime dhënieje të regjistruara ka ky tender. Ky numër "
    "nuk provon sa kontrata janë nënshkruar, ekzekutuar ose paguar.",
    "winner_top_share": "Sa përqind e vlerës totale e mori kompania kryesore. 100% = një "
    "e vetme mori gjithçka.",
    "days_tender_open": "Sa ditë rezulton i hapur tenderi për oferta. Afati interpretohet "
    "vetëm me nënllojin e procedurës dhe përjashtimet përkatëse.",
    "days_to_first_award": "Sa ditë kaluan nga mbyllja e tenderit deri te vendimi i parë i dhënies. "
    "Vlera negative tregon renditje të papritur të datave dhe kërkon "
    "kontroll të semantikës ose të dokumentit burimor.",
    "ensemble_score": "Renditje eksploruese brenda këtij snapshot-i. Vlera varet nga "
    "popullata e plotë e rindërtimit dhe nuk është probabilitet rreziku.",
    "rule_score": "Pikë prioritizimi nga indikatorët e aktivizuar për rishikim. Peshat "
    "janë zgjedhje të autorit, jo probabilitete të kalibruara.",
    "context_score": "Sa i pazakontë është ky rekord krahasuar me tenderë të ngjashëm "
    "(i njëjti institucion, e njëjta kategori/metodë).",
    "supplier_hhi": "Përqendrim përshkrues i blerjeve të institucionit sipas çelësit të "
    "furnizuesit. Nuk përkufizon një treg konkurrues dhe varet nga mbulimi "
    "i identitetit.",
    "single_bidder_pct": "Përqindja e tenderëve me të dhëna të publikuara të ofertuesve "
    "ku konkurroi vetëm një kompani; rekordet pa këtë fushë përjashtohen nga emëruesi.",
}


# =====================================================================
#  Shpjegimi qytetar i secilit flamur (rregull)
# =====================================================================
# code -> (titull i shkurtër, fjalia "pse është shqetësuese", ashpërsia 1-3)
FLAG_NARRATIVE: dict[str, tuple[str, str, int]] = {
    "SINGLE_BIDDER_OPEN": (
        "Vetëm një ofertues në garë të hapur",
        "Vetëm 1 kompani konkurroi në një procedurë që burimi e identifikon "
        "si të hapur standarde. Kjo mat konkurrencë të ulët dhe meriton "
        "kontekst tregu e dokumente; nuk provon favorizim ose korrupsion.",
        2,
    ),
    "SINGLE_BIDDER": (
        "Vetëm një ofertues",
        "Vetëm 1 kompani konkurroi. Kuptimi ndryshon sipas nënllojit të "
        "procedurës, vlerës dhe tregut; prandaj ky është vetëm kontekst për "
        "rishikim.",
        1,
    ),
    "ZERO_BIDDER": (
        "Asnjë ofertues i regjistruar",
        "Nuk u regjistrua asnjë ofertues dhe në snapshot nuk ka vendim dhënieje të "
        "regjistruar. Mund të jetë procedurë e anuluar, e papërfunduar ose mangësi "
        "e të dhënave; përdoret vetëm për ndjekje operative.",
        1,
    ),
    "RATIO_ABOVE_ESTIMATE": (
        "Totali i regjistruar mbi parashikim",
        "Vlera e dhënieve të regjistruara është mbi vlerën e parashikuar. "
        "Pa lidhje lot–vendim dhënieje ky është kontroll krahasues i të dhënave, jo "
        "përfundim për mbiçmim; nuk hyn në pikën e prioritizimit.",
        1,
    ),
    "IMPLAUSIBLE_ESTIMATE": (
        "Parashikimi duket i pasaktë",
        "Vlera e parashikuar nga institucioni është shumë më e vogël se vlera "
        "e dhënieve të regjistruara (p.sh. €180 parashikim për një vendim dhënieje "
        "me vlerë €178 mijë). "
        "Kjo zakonisht tregon papajtueshmëri ose gabim të fushave. Krahasimi "
        "dhënie të regjistruara ÷ parashikuar këtu NUK është i besueshëm dhe nuk hyn në "
        "pikën e prioritizimit.",
        1,
    ),
    "RATIO_BELOW_50": (
        "Dhënie të regjistruara 1–50% e parashikimit",
        "Vlera e dhënieve të regjistruara është të paktën 1% por nën 50% "
        "të parashikimit. Raportet nën 1% përjashtohen nga ky flamur sepse "
        "ka gjasa të jenë vlera të paplota ose fusha të pakrahasueshme. "
        "Mund të pasqyrojë lote, dhënie të pjesshme ose fusha të papajtueshme; "
        "është diagnostik dhe nuk hyn në pikën e prioritizimit.",
        1,
    ),
    "NEGATIVE_DAYS_TO_AWARD": (
        "Vendimi i dhënies daton para mbylljes së tenderit",
        "Data e vendimit të dhënies është PARA datës së mbylljes së tenderit "
        "— mospërputhje që kërkon verifikim të kuptimit të datave dhe "
        "dokumenteve burimore. Trajtohet si kontroll i cilësisë së të dhënave.",
        1,
    ),
    "ULTRA_SHORT_OPEN": (
        "Afat i shkurtër në procedurë të hapur standarde",
        "Burimi e identifikon procedurën si të hapur standarde dhe periudha "
        "e regjistruar është nën 7 ditë. Procedurat e kuotimit me minimum "
        "ligjor pesëditor përjashtohen. Pa të dhëna për urgjencë/korrigjime, "
        "ky mbetet diagnostik dhe nuk hyn në pikën e prioritizimit.",
        1,
    ),
    "PRICE_QUOTATION_VALUE_BAND_CONFLICT": (
        "Kuotim çmimi me vlerë jashtë brezit të pritshëm",
        "Burimi e kodon procedurën si kuotim çmimi, por vlera e parashikuar "
        "është të paktën €10,000. Mund të jetë gabim burimi, ndryshim, strukturë "
        "loti/kornize ose rrethanë tjetër e dokumentuar; është kontroll i cilësisë, "
        "jo konstatim paligjshmërie.",
        1,
    ),
    "BUYER_NAME_ID_COLLISION": (
        "I njëjti emër blerësi me disa ID burimore",
        "Emri i normalizuar i autoritetit është publikuar me më shumë se një ID. "
        "Kjo mund të pasqyrojë migrim identifikuesi ose entitete të ndryshme me "
        "emër të njëjtë; kërkon verifikim dhe nuk bashkon automatikisht blerësit.",
        1,
    ),
    "HIGH_VALUE_SINGLE": (
        "Vlerë e madhe + një ofertues",
        "Tender me vlerë ndër 1% më të lartat POR me vetëm një ofertues. "
        "Kombinim që rrit prioritetin e rishikimit: vlerë e lartë relative "
        "brenda kategorisë dhe konkurrencë e ulët. Nuk është provë shkeljeje.",
        2,
    ),
    "END_BEFORE_START_OPEN": (
        "Datat e tenderit të përmbysura",
        "Te procedura e hapur, data e mbylljes del para asaj të fillimit — "
        "mospërputhje e datave që duhet kontrolluar në dokumentin burimor.",
        1,
    ),
    "LOT_VALUE_MISMATCH": (
        "Shumat e loteve nuk përputhen",
        "Shuma e vlerave të pjesëve (loteve) nuk përputhet me vlerën totale "
        "të tenderit për më shumë se €100 dhe 0.1% — kontroll i cilësisë, jo "
        "sinjal i sjelljes së paligjshme.",
        1,
    ),
    "WINNER_TAKES_ALL_LARGE": (
        "Një kompani mori pothuajse gjithçka",
        "Edhe pse tenderi kishte disa pjesë (lote) dhe disa dhënie të regjistruara, një "
        "identitet furnizuesi mori mbi 95% të vlerës së dhënieve në nivel tenderi. "
        "Lidhja vendim–lot është vetëm me titull, ndaj struktura e loteve dhe "
        "dokumentet burimore duhen kontrolluar para çdo interpretimi.",
        2,
    ),
    "UNAWARDED_HIGH_VALUE": (
        "Tender i madh i pafinalizuar",
        "Tender me vlerë ndër 5% më të lartat pa vendim dhënieje të regjistruar. "
        "Mund të jetë i anuluar, i papërfunduar ose me dhënie të papublikuar; është "
        "vetëm sinjal për ndjekje operative.",
        1,
    ),
}


# Bandat e semaforit të bazuara vetëm në ensemble_score (për shpjegim në Fjalor)
SEVERITY_BANDS = [
    # (prag i poshtëm i ensemble_score, emoji, etiketë, ngjyrë)
    (0.70, "🔴", "Renditje shumë e lartë në snapshot — rishikim", "#c0392b"),
    (0.50, "🟠", "Renditje e lartë në snapshot", "#e67e22"),
    (0.30, "🟡", "Renditje e ngritur në snapshot", "#f1c40f"),
    (0.00, "🟢", "Renditje e ulët në snapshot", "#2ca25f"),
]

_GREEN = "#2ca25f"
_YELLOW = "#f1c40f"
_ORANGE = "#e67e22"
_RED = "#c0392b"
_BLUE = "#2c7fb8"


def _num(x: Any) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def contract_severity(row_or_score: Any) -> dict[str, Any]:
    """Kthen semaforin (emoji, etiketë, ngjyrë).

    **I shpjegueshëm i pari.** Nëse dihen flamujt (kalohet një rresht dict),
    kuqja rezervohet për tenderë me flamuj të vërtetë të kuq. Një tender që
    modelet statistikore e shohin të pazakontë POR që s'aktivizon asnjë
    flamur shënohet blu — "i pazakontë, pa arsye të qartë; kërkon ekspert" —
    jo i kuq, sepse nuk mund t'i shpjegojmë qytetarit pse.

    Prapambetje: nëse kalohet vetëm një numër (ensemble_score), përdoren
    bandat klasike.
    """
    if isinstance(row_or_score, dict):
        ens = _num(row_or_score.get("ensemble_score"))
        flags = explain_flags(row_or_score)
        n_sev3 = sum(1 for f in flags if f["severity"] >= 3)  # të rëndë
        n_sev2 = sum(1 for f in flags if f["severity"] >= 2)  # të rëndë+mesëm
        max_sev = max((f["severity"] for f in flags), default=0)

        if n_sev3 >= 2 or n_sev2 >= 2:
            return {
                "emoji": "🔴",
                "label": "Prioritet i lartë — kombinim sinjalesh",
                "color": _RED,
                "score": ens,
            }
        if n_sev3 == 1 or n_sev2 == 1:
            return {
                "emoji": "🟠",
                "label": "Prioritet i mesëm — sinjal për rishikim",
                "color": _ORANGE,
                "score": ens,
            }
        if max_sev == 1:  # vetëm flamuj minorë
            return {
                "emoji": "🟡",
                "label": "Vëmendje — sinjal i lehtë",
                "color": _YELLOW,
                "score": ens,
            }
        if ens >= 0.7:
            return {
                "emoji": "🔵",
                "label": "I pazakontë statistikisht — pa arsye të qartë (kërkon ekspert)",
                "color": _BLUE,
                "score": ens,
            }
        if ens >= 0.4:
            return {
                "emoji": "🟡",
                "label": "Pak i pazakontë — vëmendje",
                "color": _YELLOW,
                "score": ens,
            }
        return {"emoji": "🟢", "label": "Pa sinjale të dukshme", "color": _GREEN, "score": ens}

    # prapambetje: vetëm një pikë numerike
    s = _num(row_or_score)
    for lo, emoji, label, color in SEVERITY_BANDS:
        if s >= lo:
            return {"emoji": emoji, "label": label, "color": color, "score": s}
    return {"emoji": "🟢", "label": "Pa sinjale", "color": _GREEN, "score": s}


# Flamuj që zëvendësohen nga një variant më specifik (mos i shfaq të dytë)
_SUPERSEDED_BY = {"SINGLE_BIDDER_OPEN": "SINGLE_BIDDER"}


def explain_flags(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Kthen listën e flamujve të aktivizuar si fjali qytetare, të renditur
    sipas ashpërsisë (më të rëndët në krye).

    Kur një flamur më specifik është aktiv (p.sh. SINGLE_BIDDER_OPEN), varianti
    i tij i përgjithshëm (SINGLE_BIDDER) hiqet për të mos u përsëritur.
    """
    active = {code for code in FLAG_NARRATIVE if bool(row.get(code, False))}
    suppressed = {generic for specific, generic in _SUPERSEDED_BY.items() if specific in active}
    out = [
        {"code": code, "title": t, "detail": d, "severity": s}
        for code, (t, d, s) in FLAG_NARRATIVE.items()
        if code in active and code not in suppressed
    ]

    def _severity(item: dict[str, Any]) -> int:
        value = item.get("severity")
        return value if isinstance(value, int) else 0

    out.sort(key=_severity, reverse=True)
    return out


def _fmt_eur(x: Any) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    x = float(x)
    if abs(x) >= 1e6:
        return f"{x / 1e6:.2f} milionë €"
    if abs(x) >= 1e3:
        return f"{x / 1e3:.0f} mijë €"
    return f"{x:.0f} €"


def plain_summary(row: dict[str, Any]) -> str:
    """Një paragraf përmbledhës në shqip për tenderin/rekordin."""
    entity = row.get("procuring_entity_name") or "Një institucion"
    title = row.get("title") or "një tender"
    est = row.get("estimated_value_eur")
    awd = row.get("total_awarded_eur")
    nb = row.get("num_bidders")
    flags = explain_flags(row)

    parts = [f"**{entity}** shpalli tenderin «{title}»."]
    if est is not None and not (isinstance(est, float) and math.isnan(est)):
        parts.append(f"Institucioni parashikoi të shpenzonte rreth {_fmt_eur(est)}.")
    was_awarded = bool(row.get("was_awarded", _num(row.get("n_awards")) >= 1))
    if was_awarded and awd is not None and not (isinstance(awd, float) and math.isnan(awd)):
        parts.append(f"Vlera e dhënieve të regjistruara është {_fmt_eur(awd)}.")
    elif not was_awarded:
        parts.append("Në snapshot nuk ka vendim dhënieje të regjistruar për këtë tender.")
    if nb is not None and not bool(pd.isna(nb)):
        nb = int(nb)
        if nb == 0:
            parts.append("Nuk u regjistrua asnjë ofertues konkurrues.")
        elif nb == 1:
            parts.append("Konkurroi vetëm **1 kompani**.")
        else:
            parts.append(f"Konkurruan {nb} kompani.")
    else:
        parts.append("Burimi nuk publikon numrin e ofertuesve për këtë rekord.")

    if flags:
        n = len(flags)
        parts.append(
            f"Ky tender aktivizoi **{n} tregues rishikimi/diagnostik**"
            f"{': ' + flags[0]['title'].lower() if flags else ''}"
            + (f", {flags[1]['title'].lower()}" if n > 1 else "")
            + (" e të tjera" if n > 2 else "")
            + "."
        )
    else:
        parts.append("Nuk aktivizoi asnjë tregues nga regjistri i rregullave.")

    return " ".join(parts)


def why_flagged_headline(row: dict[str, Any]) -> str:
    """Një fjali e vetme që përmbledh arsyen kryesore të shenjimit."""
    flags = explain_flags(row)
    if not flags:
        sev = contract_severity(row.get("ensemble_score"))
        if sev["score"] >= 0.5:
            return (
                "Modelet eksploruese e rendisin si statistikisht të pazakontë, "
                "megjithëse nuk aktivizoi asnjë rregull të qartë."
            )
        return "Nuk u shenjua nga rregullat."
    return str(flags[0]["detail"])


# Kufizim i të dhënave për transparencë në UI
DATA_LIMITATION_BIDS = (
    "Të dhënat publike OCDS përmbajnë vetëm emrin e secilit ofertues, jo "
    "çmimin që ofroi secili. Prandaj nuk mund të vërtetojmë drejtpërdrejt "
    "nëse tenderi iu dha kompanisë më të shtrenjtë ndër ofertuesit. "
    "Raporti tender-nivel «vlerë e dhënieve të regjistruara ÷ vlerë e parashikuar» "
    "shfaqet vetëm si diagnostik krahasues: mund të përziejë vendime dhënieje, "
    "lote ose dhënie të pjesshme dhe nuk provon mbiçmim apo pagesë mbi plan. "
    "Fusha OCDS award nuk është dëshmi se një kontratë është nënshkruar, "
    "ekzekutuar ose paguar."
)
