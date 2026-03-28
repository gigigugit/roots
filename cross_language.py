"""
cross_language.py - Module for cross-language root finding.

Given a list of roots extracted from an etymology, this module searches
Wiktionary for related words in other languages that share the same root
(cognates and descendants), and provides a curated fallback database for
common roots when the API does not return results.
"""

import re
import time
import requests

WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"

# ---------------------------------------------------------------------------
# Fallback cognate database
# Maps a normalised root key to a list of related words in other languages.
# Used when the live API does not return results.
# ---------------------------------------------------------------------------
FALLBACK_COGNATES: dict[str, list[dict]] = {
    # Proto-Indo-European *pṓds / *ped- "foot"
    "ped": [
        {"language": "Latin", "word": "pes/pedis", "relationship": "cognate"},
        {"language": "Ancient Greek", "word": "πούς (poús)", "relationship": "cognate"},
        {"language": "Sanskrit", "word": "pāda", "relationship": "cognate"},
        {"language": "Old English", "word": "fōt", "relationship": "cognate"},
        {"language": "German", "word": "Fuß", "relationship": "cognate"},
        {"language": "French", "word": "pied", "relationship": "descendant"},
        {"language": "Italian", "word": "piede", "relationship": "descendant"},
        {"language": "Spanish", "word": "pie", "relationship": "descendant"},
    ],
    # PIE *gʷen- "woman, wife"
    "gyne": [
        {"language": "Latin", "word": "mulier", "relationship": "semantic equivalent"},
        {"language": "Ancient Greek", "word": "γυνή (gynḗ)", "relationship": "cognate"},
        {"language": "Sanskrit", "word": "jáni", "relationship": "cognate"},
        {"language": "Old English", "word": "cwēn", "relationship": "cognate"},
        {"language": "Persian", "word": "zan", "relationship": "cognate"},
    ],
    # PIE *bʰer- "to carry"
    "ferre": [
        {"language": "Ancient Greek", "word": "φέρω (phérō)", "relationship": "cognate"},
        {"language": "Sanskrit", "word": "bharati", "relationship": "cognate"},
        {"language": "Old English", "word": "beran", "relationship": "cognate"},
        {"language": "German", "word": "gebären", "relationship": "cognate"},
        {"language": "French", "word": "porter", "relationship": "semantic equivalent"},
    ],
    # PIE *wódr̥ "water"
    "water": [
        {"language": "Latin", "word": "aqua", "relationship": "semantic equivalent"},
        {"language": "Ancient Greek", "word": "ὕδωρ (hýdōr)", "relationship": "cognate"},
        {"language": "Sanskrit", "word": "udán", "relationship": "cognate"},
        {"language": "Russian", "word": "вода (voda)", "relationship": "cognate"},
        {"language": "German", "word": "Wasser", "relationship": "cognate"},
        {"language": "Dutch", "word": "water", "relationship": "cognate"},
    ],
    # PIE *h₁ed- "to eat"
    "edere": [
        {"language": "Ancient Greek", "word": "ἔδω (édō)", "relationship": "cognate"},
        {"language": "Sanskrit", "word": "admi", "relationship": "cognate"},
        {"language": "Old English", "word": "etan", "relationship": "cognate"},
        {"language": "German", "word": "essen", "relationship": "cognate"},
        {"language": "Russian", "word": "есть (yest')", "relationship": "cognate"},
    ],
    # PIE *weid- "to see / to know"
    "videre": [
        {"language": "Ancient Greek", "word": "εἶδον (eîdon)", "relationship": "cognate"},
        {"language": "Sanskrit", "word": "veda", "relationship": "cognate"},
        {"language": "Old English", "word": "witan", "relationship": "cognate"},
        {"language": "German", "word": "wissen", "relationship": "cognate"},
        {"language": "Russian", "word": "видеть (videt')", "relationship": "cognate"},
    ],
    # logos / logy
    "logos": [
        {"language": "Latin", "word": "verbum / ratio", "relationship": "semantic equivalent"},
        {"language": "Sanskrit", "word": "vāc", "relationship": "semantic equivalent"},
        {"language": "French", "word": "-logie", "relationship": "descendant"},
        {"language": "German", "word": "-logie", "relationship": "descendant"},
        {"language": "Spanish", "word": "-logía", "relationship": "descendant"},
        {"language": "Italian", "word": "-logia", "relationship": "descendant"},
    ],
    # PIE *bʰiloH- "friendly, loving" → philo-
    "philos": [
        {"language": "Latin", "word": "amicus", "relationship": "semantic equivalent"},
        {"language": "Sanskrit", "word": "priya", "relationship": "semantic equivalent"},
        {"language": "French", "word": "ami", "relationship": "semantic equivalent"},
        {"language": "Spanish", "word": "amigo", "relationship": "semantic equivalent"},
    ],
    # PIE *dʰeH₁- "to place / do"
    "facere": [
        {"language": "Ancient Greek", "word": "τίθημι (títhēmi)", "relationship": "cognate"},
        {"language": "Sanskrit", "word": "dadhāmi", "relationship": "cognate"},
        {"language": "Old English", "word": "dōn", "relationship": "cognate"},
        {"language": "German", "word": "tun", "relationship": "cognate"},
        {"language": "French", "word": "faire", "relationship": "descendant"},
        {"language": "Italian", "word": "fare", "relationship": "descendant"},
        {"language": "Spanish", "word": "hacer", "relationship": "descendant"},
    ],
    # PIE *h₂er- "to fit together"
    "arma": [
        {"language": "Ancient Greek", "word": "ἀραρίσκω (ararísko)", "relationship": "cognate"},
        {"language": "Sanskrit", "word": "ara", "relationship": "cognate"},
        {"language": "French", "word": "armes", "relationship": "descendant"},
        {"language": "Spanish", "word": "armas", "relationship": "descendant"},
        {"language": "Italian", "word": "armi", "relationship": "descendant"},
    ],
    # terra / earth
    "terra": [
        {"language": "Ancient Greek", "word": "γῆ (gê)", "relationship": "semantic equivalent"},
        {"language": "Sanskrit", "word": "dharā", "relationship": "semantic equivalent"},
        {"language": "Old English", "word": "eorþe", "relationship": "semantic equivalent"},
        {"language": "French", "word": "terre", "relationship": "descendant"},
        {"language": "Spanish", "word": "tierra", "relationship": "descendant"},
        {"language": "Italian", "word": "terra", "relationship": "descendant"},
        {"language": "Portuguese", "word": "terra", "relationship": "descendant"},
    ],
    # vita / life
    "vita": [
        {"language": "Ancient Greek", "word": "βίος (bíos) / ζωή (zōḗ)", "relationship": "semantic equivalent"},
        {"language": "Sanskrit", "word": "jīva", "relationship": "cognate"},
        {"language": "Old English", "word": "līf", "relationship": "semantic equivalent"},
        {"language": "French", "word": "vie", "relationship": "descendant"},
        {"language": "Spanish", "word": "vida", "relationship": "descendant"},
        {"language": "Italian", "word": "vita", "relationship": "descendant"},
        {"language": "Portuguese", "word": "vida", "relationship": "descendant"},
    ],
}

# Language → typical descendant relationships for common proto-languages
PROTO_LANGUAGE_FAMILIES: dict[str, list[str]] = {
    "Proto-Indo-European": [
        "Latin", "Ancient Greek", "Sanskrit", "Proto-Germanic",
        "Old Iranian", "Lithuanian", "Old Church Slavonic",
    ],
    "Proto-Germanic": [
        "Old English", "Old Norse", "Old High German",
        "Gothic", "Old Saxon", "Old Dutch",
    ],
    "Latin": [
        "French", "Spanish", "Italian", "Portuguese",
        "Romanian", "Catalan", "Occitan",
    ],
    "Ancient Greek": [
        "Modern Greek", "Byzantine Greek",
    ],
    "Old English": ["Middle English", "English"],
    "Old Norse": ["Icelandic", "Norwegian", "Swedish", "Danish"],
    "Old High German": ["Middle High German", "German", "Yiddish"],
}


def _fetch_wikitext(word: str) -> str | None:
    """
    Fetch raw wikitext for a Wiktionary page, with a small rate-limit delay.

    Args:
        word: The page title to retrieve.

    Returns:
        Wikitext string or None on failure / not found.
    """
    time.sleep(0.3)  # polite rate limiting
    params = {
        "action": "parse",
        "page": word,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }
    try:
        resp = requests.get(WIKTIONARY_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            return None
        return data.get("parse", {}).get("wikitext", None)
    except requests.exceptions.RequestException:
        return None


def _parse_descendants(wikitext: str) -> list[dict]:
    """
    Extract descendant words from a Wiktionary page's Descendants section.

    Args:
        wikitext: Raw wikitext for a root word's page.

    Returns:
        List of dicts with 'language', 'word', 'relationship' keys.
    """
    descendants: list[dict] = []

    # Locate the Descendants section
    desc_match = re.search(
        r'={2,4}\s*Descendants\s*={2,4}(.*?)(?:\n={2,}|\Z)',
        wikitext,
        re.DOTALL | re.IGNORECASE,
    )
    if not desc_match:
        return descendants

    section = desc_match.group(1)

    # Match "* {{desc|fr|mot}}" or "** {{l|fr|mot}}" style entries
    entry_re = re.compile(
        r'\{\{(?:desc|l|cog)\|([a-z-]+)\|([^|}]+)',
        re.IGNORECASE,
    )
    # Language code → display name mapping (reuse from etymology module)
    from etymology import TEMPLATE_LANG_CODES  # pylint: disable=import-outside-toplevel

    for m in entry_re.finditer(section):
        lang_code = m.group(1).strip()
        word = m.group(2).strip().lstrip("*")
        if not word:
            continue
        lang_name = TEMPLATE_LANG_CODES.get(lang_code, lang_code.title())
        descendants.append({
            "language": lang_name,
            "word": word,
            "relationship": "descendant",
        })

    return descendants


def _lookup_fallback(root: str) -> list[dict]:
    """
    Look up a root in the local fallback cognate database.

    Performs a case-insensitive substring search over the database keys
    so that partial root matches (e.g. 'logos' in 'philologos') still work.

    Args:
        root: The root word to look up.

    Returns:
        List of cognate dicts from the fallback database, or empty list.
    """
    root_lower = root.lower().lstrip("*")
    # Exact key match first
    if root_lower in FALLBACK_COGNATES:
        return FALLBACK_COGNATES[root_lower]
    # Substring match
    for key, cognates in FALLBACK_COGNATES.items():
        if key in root_lower or root_lower in key:
            return cognates
    return []


def find_cognates(root: str, source_lang: str) -> list[dict]:
    """
    Find words in other languages that share the same etymological root.

    Tries the following strategies in order:
    1. Fetch the Wiktionary page for the root word and parse its Descendants section.
    2. If source_lang is a proto-language, generate expected descendant language list.
    3. Fall back to the local curated cognate database.

    Args:
        root:        The root word or morpheme to look up.
        source_lang: Human-readable source language of the root (e.g. 'Latin').

    Returns:
        List of dicts, each with:
            'language'     – language of the cognate
            'word'         – the cognate word
            'relationship' – 'descendant', 'cognate', or 'semantic equivalent'
    """
    cognates: list[dict] = []

    # --- Strategy 1: Live Wiktionary descendants lookup ---
    clean_root = root.lstrip("*").strip()
    if clean_root:
        try:
            wikitext = _fetch_wikitext(clean_root)
            if wikitext:
                cognates = _parse_descendants(wikitext)
        except Exception:  # pylint: disable=broad-except
            pass  # network unavailable — fall through to other strategies

    # --- Strategy 2: Proto-language family expansion ---
    if not cognates and source_lang in PROTO_LANGUAGE_FAMILIES:
        for descendant_lang in PROTO_LANGUAGE_FAMILIES[source_lang]:
            cognates.append({
                "language": descendant_lang,
                "word": f"(descendant of *{clean_root})",
                "relationship": "expected descendant",
            })

    # --- Strategy 3: Fallback database ---
    if not cognates:
        cognates = _lookup_fallback(clean_root)

    return cognates


def find_cross_language_roots(roots_list: list[dict]) -> list[dict]:
    """
    For each root in the provided list, find related roots in other languages.

    Args:
        roots_list: List of root dicts as returned by ``extract_roots()``.
                    Each dict should have 'root', 'language', and 'meaning' keys.

    Returns:
        List of result dicts, each containing:
            'source_root'    – the original root word
            'source_lang'    – the source language of that root
            'source_meaning' – gloss/meaning if available
            'cognates'       – list of cognate dicts for this root
    """
    results: list[dict] = []

    for root_info in roots_list:
        root_word = root_info.get("root", "")
        source_lang = root_info.get("language", "Unknown")
        meaning = root_info.get("meaning", "")

        if not root_word:
            continue

        cognates = find_cognates(root_word, source_lang)

        results.append({
            "source_root": root_word,
            "source_lang": source_lang,
            "source_meaning": meaning,
            "cognates": cognates,
        })

    return results
