#!/usr/bin/env python3
"""Upgrade Fear Itself to the complete audited Italian physical route.

The chronology contains narrative US chapters only.  The checklist contains
one node per distinct first Italian physical publication, including the cases
where one American anthology was split over several Italian issues.  Missing
Italian chapters and missing backup stories are declared explicitly instead of
being represented by invented physical editions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PATH_ID = "fear-itself"
MANIFEST_VERSION = 21


READING_ORDER = [
    "Fear Itself: Book of the Skull (2011) #1",
    "Fear Itself: Sin's Past (2011) #1 — Born in Sin",
    "The Invincible Iron Man (2008) #503",
    "Fear Itself (2011) #1",
    "Journey into Mystery (1952) #622",
    "Fear Itself: The Home Front (2011) #1",
    "Fear Itself (2011) #2",
    "Fear Itself: The Worthy (2011) #1",
    "Avengers (2010) #13",
    "Thunderbolts (1997) #158",
    "Thunderbolts (1997) #159",
    "Journey into Mystery (1952) #623",
    "Herc (2011) #3",
    "Fear Itself: Spider-Man (2011) #1",
    "Fear Itself: The Home Front (2011) #2",
    "The Invincible Iron Man (2008) #504",
    "The Invincible Iron Man (2008) #505",
    "Fear Itself: Deadpool (2011) #1",
    "Fear Itself: Deadpool (2011) #2",
    "Fear Itself: Deadpool (2011) #3",
    "Fear Itself: Youth in Revolt (2011) #1",
    "Fear Itself: Wolverine (2011) #1",
    "Secret Avengers (2010) #13",
    "Iron Man 2.0 (2011) #5",
    "Iron Man 2.0 (2011) #6",
    "Iron Man 2.0 (2011) #7",
    "Fear Itself (2011) #3",
    "Fear Itself: Wolverine (2011) #2",
    "Journey into Mystery (1952) #624",
    "Herc (2011) #4",
    "Fear Itself: Spider-Man (2011) #2",
    "Fear Itself: FF (2011) #1",
    "Heroes for Hire (2010) #9",
    "Heroes for Hire (2010) #10",
    "Heroes for Hire (2010) #11",
    "Fear Itself: Youth in Revolt (2011) #2",
    "Alpha Flight (2011) #1",
    "Alpha Flight (2011) #2",
    "Alpha Flight (2011) #3",
    "Avengers Academy (2010) #15",
    "Avengers Academy (2010) #16",
    "Fear Itself: The Home Front (2011) #3",
    "Fear Itself: The Home Front (2011) #4",
    "Ghost Rider (2011) #0.1",
    "Ghost Rider (2011) #1",
    "Secret Avengers (2010) #14",
    "Hulk (2008) #37",
    "Avengers (2010) #14",
    "New Avengers (2010) #14",
    "Hulk (2008) #38",
    "Fear Itself: Wolverine (2011) #3",
    "Fear Itself: Spider-Man (2011) #3",
    "New Avengers (2010) #15",
    "Avengers (2010) #15",
    "Ghost Rider (2011) #2",
    "Ghost Rider (2011) #3",
    "Ghost Rider (2011) #4",
    "Thunderbolts (1997) #160",
    "Fear Itself: Fearsome Four (2011) #1",
    "Fear Itself: Fearsome Four (2011) #2",
    "Fear Itself: Fearsome Four (2011) #3",
    "Fear Itself: Fearsome Four (2011) #4",
    "Thunderbolts (1997) #161",
    "Thunderbolts (1997) #162",
    "Black Panther: The Man Without Fear (2011) #521",
    "Black Panther: The Man Without Fear (2011) #522",
    "Black Panther: The Man Without Fear (2011) #523",
    "Fear Itself: Uncanny X-Force (2011) #1",
    "Fear Itself: Uncanny X-Force (2011) #2",
    "Fear Itself: Uncanny X-Force (2011) #3",
    "Fear Itself: Youth in Revolt (2011) #3",
    "Fear Itself: Youth in Revolt (2011) #4",
    "Fear Itself: Youth in Revolt (2011) #5",
    "Uncanny X-Men (1963) #540",
    "Journey into Mystery (1952) #625",
    "Avengers (2010) #16",
    "Fear Itself (2011) #4",
    "Avengers Academy (2010) #17",
    "Avengers Academy (2010) #18",
    "Alpha Flight (2011) #4",
    "Herc (2011) #5",
    "Journey into Mystery (1952) #626",
    "New Mutants (2009) #29",
    "New Mutants (2009) #30",
    "New Mutants (2009) #31",
    "Uncanny X-Men (1963) #541",
    "Uncanny X-Men (1963) #542",
    "Uncanny X-Men (1963) #543",
    "New Mutants (2009) #32",
    "Avengers (2010) #17",
    "Fear Itself (2011) #5",
    "Fear Itself: The Home Front (2011) #5",
    "Fear Itself: The Home Front (2011) #6",
    "Herc (2011) #6",
    "Secret Avengers (2010) #15",
    "Fear Itself: Black Widow (2011) #1",
    "Tomb of Dracula Presents: Throne of Blood (2011) #1",
    "Fear Itself: Hulk vs. Dracula (2011) #1",
    "Fear Itself: Hulk vs. Dracula (2011) #2",
    "Fear Itself: Hulk vs. Dracula (2011) #3",
    "Fear Itself: The Deep (2011) #1",
    "Fear Itself: The Deep (2011) #2",
    "Fear Itself: The Deep (2011) #3",
    "Fear Itself: The Deep (2011) #4",
    "Fear Itself: The Monkey King (2011) #1",
    "Journey into Mystery (1952) #627",
    "Avengers Academy (2010) #19",
    "The Invincible Iron Man (2008) #506",
    "The Invincible Iron Man (2008) #507",
    "The Invincible Iron Man (2008) #508",
    "Fear Itself (2011) #6",
    "Journey into Mystery (1952) #628",
    "The Invincible Iron Man (2008) #509",
    "Fear Itself (2011) #7",
    "Fear Itself: Youth in Revolt (2011) #6",
    "New Avengers (2010) #16",
    "Journey into Mystery (1952) #629",
    "Fear Itself: The Home Front (2011) #7",
    "Avengers Academy (2010) #20",
    "Journey into Mystery (1952) #630",
    "The Mighty Thor (2011) #7",
    "Fear Itself (2011) #7.1 — Captain America",
    "Fear Itself (2011) #7.2 — Thor",
    "Fear Itself (2011) #7.3 — Iron Man",
    "Fear Itself: The Fearless (2011) #1",
    "Fear Itself: The Fearless (2011) #2",
    "Fear Itself: The Fearless (2011) #3",
    "Fear Itself: The Fearless (2011) #4",
    "Fear Itself: The Fearless (2011) #5",
    "Fear Itself: The Fearless (2011) #6",
    "Fear Itself: The Fearless (2011) #7",
    "Fear Itself: The Fearless (2011) #8",
    "Fear Itself: The Fearless (2011) #9",
    "Fear Itself: The Fearless (2011) #10",
    "Fear Itself: The Fearless (2011) #11",
    "Fear Itself: The Fearless (2011) #12",
]


CHAPTER_TO_ITALIAN: dict[str, str | list[str]] = {
    "Fear Itself: Book of the Skull (2011) #1": "MMMI:118",
    "Fear Itself: Sin's Past (2011) #1 — Born in Sin": "MMMI:118",
    "The Invincible Iron Man (2008) #503": ["IM_VEN2:44", "IM_VEN2:45"],
    "Fear Itself (2011) #1": "MMMI:119",
    "Journey into Mystery (1952) #622": "THORVE_M:152",
    "Fear Itself: The Home Front (2011) #1": ["MARMONED:18", "MMMI:120", "SPIDER_MAIN:570"],
    "Fear Itself (2011) #2": "MMMI:120",
    "Fear Itself: The Worthy (2011) #1": ["MMMI:122", "MMMI:123"],
    "Avengers (2010) #13": "IM_VEN2:45",
    "Thunderbolts (1997) #158": "MAR_MIX:99",
    "Thunderbolts (1997) #159": "MAR_MIX:99",
    "Journey into Mystery (1952) #623": "THORVE_M:153",
    "Fear Itself: Spider-Man (2011) #1": "SPIDER_MAIN:573",
    "Fear Itself: The Home Front (2011) #2": ["MARMONED:18", "MMMI:120", "SPIDER_MAIN:570"],
    "The Invincible Iron Man (2008) #504": "IM_VEN2:45",
    "The Invincible Iron Man (2008) #505": "IM_VEN2:46",
    "Fear Itself: Deadpool (2011) #1": "DEDPL_M:7",
    "Fear Itself: Deadpool (2011) #2": "DEDPL_M:8",
    "Fear Itself: Deadpool (2011) #3": "DEDPL_M:9",
    "Fear Itself: Youth in Revolt (2011) #1": "MARMONED:18",
    "Fear Itself: Wolverine (2011) #1": "MA_MEG:76",
    "Secret Avengers (2010) #13": "CAP_M:19",
    "Iron Man 2.0 (2011) #5": "IM_VEN2:45",
    "Iron Man 2.0 (2011) #6": "IM_VEN2:46",
    "Iron Man 2.0 (2011) #7": "IM_VEN2:47",
    "Fear Itself (2011) #3": "MMMI:121",
    "Fear Itself: Wolverine (2011) #2": "MA_MEG:76",
    "Journey into Mystery (1952) #624": "THORVE_M:154",
    "Fear Itself: Spider-Man (2011) #2": "SPIDER_MAIN:573",
    "Fear Itself: FF (2011) #1": "F4_SM:328",
    "Heroes for Hire (2010) #9": "MARMONED:17",
    "Heroes for Hire (2010) #10": "MARMONED:17",
    "Heroes for Hire (2010) #11": "MARMONED:17",
    "Fear Itself: Youth in Revolt (2011) #2": "MARMONED:18",
    "Alpha Flight (2011) #1": "F4_SM:329",
    "Alpha Flight (2011) #2": "F4_SM:330",
    "Alpha Flight (2011) #3": "F4_SM:331",
    "Avengers Academy (2010) #15": "MA_ICON:7",
    "Avengers Academy (2010) #16": "MA_ICON:7",
    "Fear Itself: The Home Front (2011) #3": ["MARMONED:18", "MMMI:121", "MARMONED:17"],
    "Fear Itself: The Home Front (2011) #4": ["MARMONED:18", "MMMI:121", "MMMI:124"],
    "Ghost Rider (2011) #0.1": "DEVIL_M:1",
    "Ghost Rider (2011) #1": ["DEVIL_M:2", "DEVIL_M:3"],
    "Secret Avengers (2010) #14": "CAP_M:20",
    "Hulk (2008) #37": "HULK_M:183",
    "Avengers (2010) #14": "IM_VEN2:46",
    "New Avengers (2010) #14": "THORVE_M:155",
    "Hulk (2008) #38": "HULK_M:184",
    "Fear Itself: Wolverine (2011) #3": "MA_MEG:76",
    "Fear Itself: Spider-Man (2011) #3": "SPIDER_MAIN:573",
    "New Avengers (2010) #15": "THORVE_M:156",
    "Avengers (2010) #15": "IM_VEN2:47",
    "Ghost Rider (2011) #2": "DEVIL_M:3",
    "Ghost Rider (2011) #3": "DEVIL_M:4",
    "Ghost Rider (2011) #4": "DEVIL_M:5",
    "Thunderbolts (1997) #160": "MAR_MIX:99",
    "Fear Itself: Fearsome Four (2011) #1": "MARMONED:17",
    "Fear Itself: Fearsome Four (2011) #2": "MARMONED:17",
    "Fear Itself: Fearsome Four (2011) #3": "MARMONED:17",
    "Fear Itself: Fearsome Four (2011) #4": "MARMONED:17",
    "Thunderbolts (1997) #161": "MAR_MIX:99",
    "Thunderbolts (1997) #162": "MAR_MIX:99",
    "Black Panther: The Man Without Fear (2011) #521": "100M:148",
    "Black Panther: The Man Without Fear (2011) #522": "100M:148",
    "Black Panther: The Man Without Fear (2011) #523": "100M:148",
    "Fear Itself: Uncanny X-Force (2011) #1": "MA_MEG:76",
    "Fear Itself: Uncanny X-Force (2011) #2": "MA_MEG:76",
    "Fear Itself: Uncanny X-Force (2011) #3": "MA_MEG:76",
    "Fear Itself: Youth in Revolt (2011) #3": "MARMONED:18",
    "Fear Itself: Youth in Revolt (2011) #4": "MARMONED:18",
    "Fear Itself: Youth in Revolt (2011) #5": "MARMONED:18",
    "Uncanny X-Men (1963) #540": "XM_SM:261",
    "Journey into Mystery (1952) #625": "THORVE_M:155",
    "Avengers (2010) #16": "IM_VEN2:48",
    "Fear Itself (2011) #4": "MMMI:122",
    "Avengers Academy (2010) #17": "MA_ICON:7",
    "Avengers Academy (2010) #18": "MA_ICON:7",
    "Alpha Flight (2011) #4": "F4_SM:332",
    "Journey into Mystery (1952) #626": "THORVE_M:156",
    "New Mutants (2009) #29": "XM_DX:205",
    "New Mutants (2009) #30": "XM_DX:205",
    "New Mutants (2009) #31": "XM_DX:206",
    "Uncanny X-Men (1963) #541": "XM_SM:261",
    "Uncanny X-Men (1963) #542": "XM_SM:262",
    "Uncanny X-Men (1963) #543": "XM_SM:262",
    "New Mutants (2009) #32": "XM_DX:206",
    "Avengers (2010) #17": "IM_VEN2:49",
    "Fear Itself (2011) #5": "MMMI:123",
    "Fear Itself: The Home Front (2011) #5": ["MARMONED:18", "MMMI:124"],
    "Fear Itself: The Home Front (2011) #6": ["MARMONED:18", "MMMI:124"],
    "Secret Avengers (2010) #15": "CAP_M:21",
    "Tomb of Dracula Presents: Throne of Blood (2011) #1": "MARMONED:17",
    "Fear Itself: Hulk vs. Dracula (2011) #1": "MARMONED:18",
    "Fear Itself: Hulk vs. Dracula (2011) #2": "MARMONED:18",
    "Fear Itself: Hulk vs. Dracula (2011) #3": "MARMONED:18",
    "Fear Itself: The Deep (2011) #1": "MARMONED:17",
    "Fear Itself: The Deep (2011) #2": "MARMONED:17",
    "Fear Itself: The Deep (2011) #3": "MARMONED:17",
    "Fear Itself: The Deep (2011) #4": "MARMONED:17",
    "Journey into Mystery (1952) #627": "THORVE_M:157",
    "Avengers Academy (2010) #19": "MA_ICON:7",
    "The Invincible Iron Man (2008) #506": "IM_VEN2:47",
    "The Invincible Iron Man (2008) #507": "IM_VEN2:48",
    "The Invincible Iron Man (2008) #508": "IM_VEN2:49",
    "Fear Itself (2011) #6": "MMMI:124",
    "Journey into Mystery (1952) #628": "THORVE_M:158",
    "The Invincible Iron Man (2008) #509": "IM_VEN2:50",
    "Fear Itself (2011) #7": "MMMI:125",
    "Fear Itself: Youth in Revolt (2011) #6": "MARMONED:18",
    "New Avengers (2010) #16": "THORVE_M:157",
    "Journey into Mystery (1952) #629": "THORVE_M:159",
    "Fear Itself: The Home Front (2011) #7": ["MARMONED:18", "MMMI:125"],
    "Avengers Academy (2010) #20": "MA_ICON:7",
    "Journey into Mystery (1952) #630": "THORVE_M:160",
    "The Mighty Thor (2011) #7": "THORVE_M:158",
    "Fear Itself (2011) #7.1 — Captain America": "CAP_M:25",
    "Fear Itself (2011) #7.2 — Thor": "THORVE_M:159",
    "Fear Itself (2011) #7.3 — Iron Man": "IM_VEN2:51",
    "Fear Itself: The Fearless (2011) #1": "MWORLD_M:9",
    "Fear Itself: The Fearless (2011) #2": "MWORLD_M:9",
    "Fear Itself: The Fearless (2011) #3": "MWORLD_M:10",
    "Fear Itself: The Fearless (2011) #4": "MWORLD_M:10",
    "Fear Itself: The Fearless (2011) #5": "MWORLD_M:11",
    "Fear Itself: The Fearless (2011) #6": "MWORLD_M:11",
    "Fear Itself: The Fearless (2011) #7": "MWORLD_M:12",
    "Fear Itself: The Fearless (2011) #8": "MWORLD_M:12",
    "Fear Itself: The Fearless (2011) #9": "MWORLD_M:13",
    "Fear Itself: The Fearless (2011) #10": "MWORLD_M:13",
    "Fear Itself: The Fearless (2011) #11": "MWORLD_M:14",
    "Fear Itself: The Fearless (2011) #12": "MWORLD_M:14",
}


ITALIAN_GAPS = {
    "Herc (2011) #3": "Nessuna pubblicazione italiana censita nell'audit ComicsBox",
    "Herc (2011) #4": "Nessuna pubblicazione italiana censita nell'audit ComicsBox",
    "Herc (2011) #5": "Nessuna pubblicazione italiana censita nell'audit ComicsBox",
    "Herc (2011) #6": "Nessuna pubblicazione italiana censita nell'audit ComicsBox",
    "Fear Itself: Black Widow (2011) #1": "Nessuna pubblicazione italiana censita nell'audit ComicsBox",
    "Fear Itself: The Monkey King (2011) #1": "Nessuna pubblicazione italiana censita nell'audit ComicsBox",
}


ITALIAN_PARTIAL_GAPS = [
    {
        "chapter": "Fear Itself: The Home Front (2011) #5",
        "story": "The Chosen, part 1",
        "reason": "Storia breve di backup senza pubblicazione italiana censita",
    },
    {
        "chapter": "Fear Itself: The Home Front (2011) #6",
        "story": "The Chosen, part 2",
        "reason": "Storia breve di backup senza pubblicazione italiana censita",
    },
    {
        "chapter": "Fear Itself: The Home Front (2011) #7",
        "story": "Pearl Harbor / The Chosen, part 3",
        "reason": "Storia breve di backup senza pubblicazione italiana censita",
    },
]


MAPPING_NOTES: dict[tuple[str, str], str] = {
    ("The Invincible Iron Man (2008) #503", "IM_VEN2:44"): "Fix Me, part 3",
    ("The Invincible Iron Man (2008) #503", "IM_VEN2:45"): "How I Met Your Mother",
    ("Fear Itself: The Worthy (2011) #1", "MMMI:122"): "origini di Skadi, Kuurth, Skirn e Mokk",
    ("Fear Itself: The Worthy (2011) #1", "MMMI:123"): "origini di Nul, Nerkkod, Greithoth e Angrir",
    ("Fear Itself: The Home Front (2011) #1", "MARMONED:18"): "Lurker",
    ("Fear Itself: The Home Front (2011) #1", "MMMI:120"): "Age of Anxiety 1 + J. Jonah Jameson",
    ("Fear Itself: The Home Front (2011) #1", "SPIDER_MAIN:570"): "Homeless",
    ("Fear Itself: The Home Front (2011) #2", "MARMONED:18"): "Scapegoat",
    ("Fear Itself: The Home Front (2011) #2", "MMMI:120"): "Age of Anxiety 2 + Purple Man",
    ("Fear Itself: The Home Front (2011) #2", "SPIDER_MAIN:570"): "Between Stations",
    ("Fear Itself: The Home Front (2011) #3", "MARMONED:18"): "Going Viral",
    ("Fear Itself: The Home Front (2011) #3", "MMMI:121"): "Age of Anxiety 3 + The People of Paris",
    ("Fear Itself: The Home Front (2011) #3", "MARMONED:17"): "Breakdown",
    ("Fear Itself: The Home Front (2011) #4", "MARMONED:18"): "Fatal Errors",
    ("Fear Itself: The Home Front (2011) #4", "MMMI:121"): "Age of Anxiety 4 + Kida of Atlantis",
    ("Fear Itself: The Home Front (2011) #4", "MMMI:124"): "Legacy",
    ("Fear Itself: The Home Front (2011) #5", "MARMONED:18"): "Hope Itself",
    ("Fear Itself: The Home Front (2011) #5", "MMMI:124"): "Mr. Fear + Red, White and Blues",
    ("Fear Itself: The Home Front (2011) #6", "MARMONED:18"): "Sisters of Sin",
    ("Fear Itself: The Home Front (2011) #6", "MMMI:124"): "A Moment With... Dust + Great Lakes Avengers",
    ("Fear Itself: The Home Front (2011) #7", "MARMONED:18"): "Hope Like Fire",
    ("Fear Itself: The Home Front (2011) #7", "MMMI:125"): "J. Jonah Jameson + Home Front Lines",
    ("Ghost Rider (2011) #1", "DEVIL_M:2"): "Give Up the Ghost, part 1",
    ("Ghost Rider (2011) #1", "DEVIL_M:3"): "Sacrifice",
}


SERIES_META = {
    "MMMI": ("Marvel Miniserie", "Marvel Italia / Panini Comics", "MMMI"),
    "IM_VEN2": ("Iron Man e i potenti Vendicatori", "Marvel Italia / Panini Comics", "IM_VEN2"),
    "THORVE_M": ("Thor", "Marvel Italia / Panini Comics", "THORVE_M"),
    "MARMONED": ("Marvel Monster Edition", "Marvel Italia", "MARMONED"),
    "MAR_MIX": ("Marvel Mix", "Marvel Italia", "MAR_MIX"),
    "DEDPL_M": ("Deadpool", "Panini Comics", "DEDPL_M"),
    "CAP_M": ("Capitan America", "Panini Comics", "CAP_M"),
    "F4_SM": ("Fantastici Quattro", "Panini Comics", "F4_SM"),
    "DEVIL_M": ("Devil e i Cavalieri Marvel", "Panini Comics", "DEVIL_M"),
    "100M": ("100% Marvel", "Marvel Italia", "100M"),
    "HULK_M": ("L'Incredibile Hulk", "Panini Comics", "HULK_M"),
    "MA_ICON": ("Marvel Icon", "Panini Comics", "MA_ICON"),
    "XM_DX": ("X-Men Deluxe", "Marvel Italia", "XM_DX"),
    "MA_MEG": ("Marvel Mega", "Marvel Italia", "MA_MEG"),
    "XM_SM": ("Gli Incredibili X-Men", "Panini Comics", "XM_SM"),
    "MWORLD_M": ("Marvel World", "Panini Comics", "MWORLD_M"),
}


FALLBACK_META = {
    "MARMONED:17": ("Marvel Monster Edition #17", "Fear Itself, pt 1", "Febbraio 2012"),
    "MARMONED:18": ("Marvel Monster Edition #18", "Fear Itself, pt 2", "Maggio 2012"),
    "MAR_MIX:99": ("Marvel Mix #99", "Thunderbolts 8: Fear Itself", "Marzo 2012"),
    "DEDPL_M:7": ("Deadpool #7", "Fear Itself", "Dicembre 2011"),
    "DEDPL_M:8": ("Deadpool #8", "Fear Itself", "Gennaio 2012"),
    "DEDPL_M:9": ("Deadpool #9", "Fear Itself", "Febbraio 2012"),
    "CAP_M:19": ("Capitan America #19", "Fear Itself", "Dicembre 2011"),
    "CAP_M:20": ("Capitan America #20", "Fear Itself", "Gennaio 2012"),
    "CAP_M:21": ("Capitan America #21", "Secret Avengers — Fear Itself", "Febbraio 2012"),
    "CAP_M:25": ("Capitan America #25", "Fear Itself 7.1", "Giugno 2012"),
    "DEVIL_M:1": ("Devil e i Cavalieri Marvel #1", "Ghost Rider 0.1", "Febbraio 2012"),
    "DEVIL_M:2": ("Devil e i Cavalieri Marvel #2", "Ghost Rider — Fear Itself", "Marzo 2012"),
    "DEVIL_M:3": ("Devil e i Cavalieri Marvel #3", "Ghost Rider — Fear Itself", "Aprile 2012"),
    "DEVIL_M:4": ("Devil e i Cavalieri Marvel #4", "Ghost Rider — Fear Itself", "Maggio 2012"),
    "DEVIL_M:5": ("Devil e i Cavalieri Marvel #5", "Ghost Rider — Fear Itself", "Giugno 2012"),
    "100M:148": ("100% Marvel #148", "Pantera Nera: Paura e delirio a Hell's Kitchen", "Ottobre 2012"),
    "MA_ICON:7": ("Marvel Icon #7", "Vendicatori Accademia, pt 3", "Aprile 2012"),
    "XM_DX:205": ("X-Men Deluxe #205", "Nuovi Mutanti: Fear Itself 1", "Aprile 2012"),
    "XM_DX:206": ("X-Men Deluxe #206", "Nuovi Mutanti: Fear Itself 2", "Maggio 2012"),
    "MA_MEG:76": ("Marvel Mega #76", "Wolverine e X-Force: Fear Itself", "Marzo 2012"),
    "MWORLD_M:9": ("Marvel World #9", "Fear Itself: I Temerari, pt 1", "Giugno 2012"),
    "MWORLD_M:10": ("Marvel World #10", "Fear Itself: I Temerari, pt 2", "Luglio 2012"),
    "MWORLD_M:11": ("Marvel World #11", "Fear Itself: I Temerari, pt 3", "Agosto 2012"),
    "MWORLD_M:12": ("Marvel World #12", "Fear Itself: I Temerari, pt 4", "Agosto 2012"),
    "MWORLD_M:13": ("Marvel World #13", "Fear Itself: I Temerari, pt 5", "Settembre 2012"),
    "MWORLD_M:14": ("Marvel World #14", "Fear Itself: I Temerari, pt 6", "Novembre 2012"),
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def prefix_and_number(issue_id: str) -> tuple[str, int]:
    prefix, raw = issue_id.split(":", 1)
    match = re.match(r"\d+", raw)
    if not match:
        raise RuntimeError(f"Numero non ricavabile da {issue_id}")
    return prefix, int(match.group())


def clean_catalog_issue(row: dict) -> dict:
    issue = {key: value for key, value in row.items() if key not in {"paths", "pathNames", "hubs"}}
    issue["required"] = True
    issue["skip"] = False
    issue["future"] = False
    issue["coverSource"] = issue.get("coverSource") or "ComicsBox"
    return issue


def fallback_issue(issue_id: str) -> dict:
    prefix, number = prefix_and_number(issue_id)
    try:
        series, publisher, cover_prefix = SERIES_META[prefix]
        name, title, date = FALLBACK_META[issue_id]
    except KeyError as exc:
        raise RuntimeError(f"Metadati italiani mancanti per {issue_id}") from exc
    return {
        "id": issue_id,
        "n": number,
        "name": name,
        "title": title,
        "date": date,
        "seriesId": prefix,
        "series": series,
        "publisher": publisher,
        "cover": f"https://www.comicsbox.it/cover/{cover_prefix}_{number:03d}.jpg",
        "url": f"https://www.comicsbox.it/albo/{cover_prefix}_{number:03d}",
        "required": True,
        "skip": False,
        "future": False,
        "coverSource": "ComicsBox",
    }


def mapping_ids(value: str | list[str]) -> list[str]:
    return [value] if isinstance(value, str) else value


def mapping_label(chapter: str, issue_id: str) -> str:
    note = MAPPING_NOTES.get((chapter, issue_id))
    return f"{chapter} [{note}]" if note else chapter


def set_edition_coverage(payload: dict, edition_id: str, issue_ids: list[str], label: str) -> None:
    edition = next((row for row in payload.get("editions", []) if row.get("id") == edition_id), None)
    if edition is None:
        raise RuntimeError(f"Edizione alternativa {edition_id} non trovata")
    coverage = [row for row in edition.get("coverage", []) if row.get("path") != PATH_ID]
    coverage.append({"path": PATH_ID, "issueIds": issue_ids, "label": label})
    edition["coverage"] = coverage
    edition["coverageSource"] = "curated:fear-itself-complete"


def ensure_curated_edition(curated: dict, generated: dict, edition_id: str) -> None:
    if any(row.get("id") == edition_id for row in curated.get("editions", [])):
        return
    source = next((row for row in generated.get("editions", []) if row.get("id") == edition_id), None)
    if source is None:
        raise RuntimeError(f"Metadati edizione {edition_id} non trovati")
    clone = dict(source)
    clone["coverage"] = []
    clone.pop("coverageSource", None)
    curated.setdefault("editions", []).append(clone)
    curated["editions"].sort(key=lambda row: row.get("id", ""))


def main() -> None:
    if len(READING_ORDER) != 136 or len(set(READING_ORDER)) != 136:
        raise RuntimeError(f"Reading order Fear Itself inatteso: {len(READING_ORDER)}")
    if set(READING_ORDER) != set(CHAPTER_TO_ITALIAN) | set(ITALIAN_GAPS):
        missing = set(READING_ORDER) - set(CHAPTER_TO_ITALIAN) - set(ITALIAN_GAPS)
        extra = (set(CHAPTER_TO_ITALIAN) | set(ITALIAN_GAPS)) - set(READING_ORDER)
        raise RuntimeError(f"Audit incompleto. Missing={missing}; extra={extra}")
    if set(CHAPTER_TO_ITALIAN) & set(ITALIAN_GAPS):
        raise RuntimeError("Un capitolo non può essere insieme mappato e gap")
    if len(CHAPTER_TO_ITALIAN) != 130 or len(ITALIAN_GAPS) != 6:
        raise RuntimeError("Conteggio copertura italiana Fear Itself inatteso")

    current = read_json(DATA / "characters" / "fear-itself.json")
    old_core = {row["id"]: row for row in current.get("issues", [])}
    if not all(f"MMMI:{number}" in old_core for number in range(118, 126)):
        raise RuntimeError("Core Fear Itself #118–125 non trovato")

    catalog = read_json(DATA / "catalog.json")
    catalog_by_id = {row["id"]: row for row in catalog.get("issues", [])}

    physical_to_chapters: dict[str, list[str]] = {}
    physical_to_labels: dict[str, list[str]] = {}
    physical_positions: dict[str, list[int]] = {}
    first_use: list[str] = []
    for position, chapter in enumerate(READING_ORDER, start=1):
        mapped = CHAPTER_TO_ITALIAN.get(chapter)
        if mapped is None:
            continue
        for issue_id in mapping_ids(mapped):
            if issue_id not in physical_to_chapters:
                physical_to_chapters[issue_id] = []
                physical_to_labels[issue_id] = []
                physical_positions[issue_id] = []
                first_use.append(issue_id)
            physical_to_chapters[issue_id].append(chapter)
            physical_to_labels[issue_id].append(mapping_label(chapter, issue_id))
            physical_positions[issue_id].append(position)

    if len(first_use) != 62:
        raise RuntimeError(f"Pubblicazioni italiane Fear Itself inattese: {len(first_use)}")

    issues = []
    for issue_id in first_use:
        if issue_id in old_core:
            issue = dict(old_core[issue_id])
            issue.update({"required": True, "skip": False, "future": False})
        elif issue_id in catalog_by_id:
            issue = clean_catalog_issue(catalog_by_id[issue_id])
        else:
            issue = fallback_issue(issue_id)

        positions = physical_positions[issue_id]
        labels = physical_to_labels[issue_id]
        issue["era"] = (
            "Epilogo — I Temerari" if any(position >= 125 for position in positions)
            else "Prologo — Il Serpente" if min(positions) <= 4
            else "Evento completo e tie-in"
        )
        issue["readingOrderPositions"] = positions
        issue["instruction"] = (
            f"Nel reading order completo usa questa pubblicazione ai passaggi {', '.join(map(str, positions))}: "
            f"{'; '.join(labels)}. Se contiene altre storie, leggile soltanto quando richiesto dall'ordine."
        )
        issues.append(issue)

    payload = {
        "id": PATH_ID,
        "name": "Fear Itself",
        "subtitle": "Avengers · Thor · The Fearless — evento completo 2011–2012",
        "accent": "#8d684c",
        "start": "Marvel Miniserie #118 — Sin's Past / Il libro del Teschio",
        "end": "Marvel World #14 — The Fearless #11–12",
        "description": (
            "Percorso narrativo completo di Fear Itself: 136 capitoli USA, dal preludio di Sin e del "
            "Serpente fino a Fearless #12. Dei 130 capitoli con almeno una prima pubblicazione italiana, "
            "127 sono integralmente mappati e tre Home Front sono parziali; il tracker li riconduce a 62 "
            "albi fisici distinti. Herc #3–6, Black Widow e The Monkey King restano sei gap dichiarati. "
            "La guida Marvel è corretta reinserendo Fear Itself #1, omesso dalla pagina, e integrata con "
            "quattro one-shot narrativi; Fellowship of Fear e Spotlight sono esclusi perché non narrativi."
        ),
        "timelineMode": True,
        "eventScope": "complete",
        "readingOrderSource": (
            "Marvel official Fear Itself guide, integrata con Marvel Guides e Comic Book Herald; "
            "prime pubblicazioni italiane verificate su ComicsBox"
        ),
        "readingOrderSources": [
            {"name": "Marvel — Fear Itself guide", "url": "https://www.marvel.com/comics/guides/430/fear-itself"},
            {"name": "Marvel Guides — Fear Itself reading order", "url": "https://marvelguides.com/fear-itself-reading-order"},
            {"name": "Comic Book Herald — Fear Itself", "url": "https://www.comicbookherald.com/the-complete-marvel-reading-order-guide/guide-part-15-fear-itself/"},
            {"name": "ComicsBox — Fear Itself", "url": "https://www.comicsbox.it/serie/FEARIT"},
        ],
        "scopeNotes": [
            "Fear Itself #1 è incluso: la pagina della guida Marvel lo omette per un errore del catalogo.",
            "Sin's Past (Born in Sin), The Worthy, The Monkey King e Throne of Blood sono one-shot narrativi integrati.",
            "Fear Itself: Fellowship of Fear è un handbook; Fear Itself: Spotlight contiene interviste e anticipazioni: entrambi sono esclusi.",
            "Fearless #1–12 è l'epilogo diretto; Fearless #0 e Battle Scars restano fuori da questo perimetro.",
        ],
        "readingOrder": READING_ORDER,
        "italianCoverage": {
            "officialChapters": len(READING_ORDER),
            "mappedChapters": len(CHAPTER_TO_ITALIAN),
            "fullyMappedChapters": len(CHAPTER_TO_ITALIAN) - len(ITALIAN_PARTIAL_GAPS),
            "partiallyMappedChapters": len(ITALIAN_PARTIAL_GAPS),
            "unmappedChapters": len(ITALIAN_GAPS),
            "unmappedStories": len(ITALIAN_PARTIAL_GAPS),
            "physicalPublications": len(issues),
        },
        "italianGaps": [
            {"chapter": chapter, "reason": reason}
            for chapter, reason in ITALIAN_GAPS.items()
        ],
        "italianPartialGaps": ITALIAN_PARTIAL_GAPS,
        "series": [
            {"id": "FEAR-PRELUDE", "name": "Fear Itself — preludio", "publisher": "Panini Comics", "range": "Sin's Past, Book of the Skull, Invincible Iron Man", "years": "2011"},
            {"id": "FEAR-CORE", "name": "Fear Itself — evento principale", "publisher": "Marvel Italia / Panini Comics", "range": "Fear Itself #1–7 + The Worthy", "years": "2011–2012"},
            {"id": "FEAR-TIEINS", "name": "Fear Itself — tie-in completi", "publisher": "Marvel Italia / Panini Comics", "range": "Avengers, Thor, X-Men, Spider-Man, Home Front e speciali", "years": "2011–2012"},
            {"id": "FEAR-EPILOGUE", "name": "Fear Itself — epiloghi", "publisher": "Panini Comics", "range": "#7.1–7.3 + The Fearless #1–12", "years": "2012"},
        ],
        "archives": [],
        "totalRequired": len(issues),
        "availableTotal": len(issues),
        "issues": issues,
    }
    write_json(DATA / "characters" / "fear-itself.json", payload)

    manifest = read_json(DATA / "characters.json")
    manifest["version"] = MANIFEST_VERSION
    meta = next(row for row in manifest["characters"] if row["id"] == PATH_ID)
    meta.update({
        "subtitle": payload["subtitle"],
        "start": payload["start"],
        "end": payload["end"],
        "totalRequired": len(issues),
        "eventScope": "complete",
    })
    write_json(DATA / "characters.json", manifest)

    hubs = read_json(DATA / "hubs.json")
    event_hub = next(row for row in hubs["hubs"] if row["id"] == "events")
    groups = {row["id"]: row for row in event_hub["groups"]}
    for group_id, group in groups.items():
        if group_id != "complete":
            group["paths"] = [path for path in group.get("paths", []) if path != PATH_ID]
    complete = [path for path in groups["complete"]["paths"] if path != PATH_ID]
    insert_at = complete.index("siege") + 1 if "siege" in complete else len(complete)
    complete.insert(insert_at, PATH_ID)
    groups["complete"]["paths"] = complete
    write_json(DATA / "hubs.json", hubs)

    editions = read_json(DATA / "editions.json")
    curated = read_json(DATA / "curated-editions.json")
    for edition_id in ("MAROMNIB:27", "MAROMNIB:28", "MARVELMUST:48"):
        ensure_curated_edition(curated, editions, edition_id)

    for payload_editions in (editions, curated):
        set_edition_coverage(
            payload_editions,
            "MAROMNIB:27",
            ["MMMI:118", "MMMI:119", "MMMI:122", "MMMI:123", "CAP_M:25", "IM_VEN2:51"],
            "Sin's Past, Book of the Skull, core #1–7, #7.1–7.3 e The Worthy; gli albi misti con Home Front o Journey into Mystery restano esclusi",
        )
        set_edition_coverage(
            payload_editions,
            "MAROMNIB:28",
            ["SPIDER_MAIN:570", "SPIDER_MAIN:573", "MA_MEG:76"],
            "Home Front #1–7, Spider-Man #1–3, Wolverine #1–3 e Uncanny X-Force #1–3; sostituisce soltanto i tre nodi interamente coperti",
        )
        set_edition_coverage(
            payload_editions,
            "MARVELMUST:48",
            ["MMMI:119"],
            "Book of the Skull + core #1–7; sostituisce soltanto #119 perché gli altri albi italiani contengono ulteriori capitoli obbligatori",
        )
    write_json(DATA / "editions.json", editions)
    write_json(DATA / "curated-editions.json", curated)

    verify_path = ROOT / "scripts" / "verify-data.mjs"
    verify = verify_path.read_text(encoding="utf-8")
    old = 'assert.equal(manifest.version, 20, "Il manifest deve usare la versione cache v20");'
    new = 'assert.equal(manifest.version, 21, "Il manifest deve usare la versione cache v21");'
    if old not in verify and new not in verify:
        raise RuntimeError("Versione manifest attesa non trovata nel verifier")
    verify_path.write_text(verify.replace(old, new), encoding="utf-8")

    print(
        "Fear Itself completo: "
        f"{len(READING_ORDER)} capitoli USA / {len(CHAPTER_TO_ITALIAN)} mappati / "
        f"{len(ITALIAN_GAPS)} gap / {len(ITALIAN_PARTIAL_GAPS)} gap parziali / "
        f"{len(issues)} pubblicazioni italiane"
    )


if __name__ == "__main__":
    main()
