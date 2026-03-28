"""
etymology.py - Module for Wiktionary API etymology lookups.

Fetches and parses etymological data for words using the Wiktionary API,
extracting root words and their source languages.

When the Wiktionary API is unreachable (e.g. no network), the module
transparently falls back to a built-in curated etymology database so
the application remains functional offline.
"""

import re
import time
import requests

# Wiktionary API endpoint
WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"

# ---------------------------------------------------------------------------
# Built-in etymology database (offline fallback)
# Maps lowercase word → list of etymology dicts.
# Each dict has:
#   'text'  – human-readable etymology paragraph
#   'roots' – list of {root, language, meaning} dicts
# ---------------------------------------------------------------------------
BUILTIN_ETYMOLOGIES: dict[str, list[dict]] = {
    "philosophy": [
        {
            "text": (
                "From Middle English philosophie, from Old French philosophie, "
                "from Latin philosophia, from Ancient Greek φιλοσοφία (philosophía), "
                "from φίλος (phílos, 'loving, fond of') + σοφία (sophía, 'wisdom'). "
                "Coined by Pythagoras according to tradition."
            ),
            "roots": [
                {"root": "philos", "language": "Ancient Greek", "meaning": "loving, fond of"},
                {"root": "sophia", "language": "Ancient Greek", "meaning": "wisdom"},
                {"root": "philosophia", "language": "Latin", "meaning": "love of wisdom"},
                {"root": "philosophie", "language": "Old French", "meaning": "philosophy"},
            ],
        }
    ],
    "democracy": [
        {
            "text": (
                "From French démocratie, from Medieval Latin democratia, "
                "from Ancient Greek δημοκρατία (dēmokratía), "
                "from δῆμος (dêmos, 'people, populace') + κράτος (krátos, 'rule, power, strength'). "
                "Attested in English from the 16th century."
            ),
            "roots": [
                {"root": "demos", "language": "Ancient Greek", "meaning": "people, populace"},
                {"root": "kratos", "language": "Ancient Greek", "meaning": "rule, power, strength"},
                {"root": "democratia", "language": "Latin", "meaning": "democracy"},
            ],
        }
    ],
    "science": [
        {
            "text": (
                "From Middle English science, from Old French science, "
                "from Latin scientia ('knowledge'), "
                "from sciens (present participle of scire, 'to know'), "
                "from Proto-Indo-European *skey- ('to cut, to separate')."
            ),
            "roots": [
                {"root": "scientia", "language": "Latin", "meaning": "knowledge"},
                {"root": "scire", "language": "Latin", "meaning": "to know"},
                {"root": "*skey-", "language": "Proto-Indo-European", "meaning": "to cut, to separate"},
            ],
        }
    ],
    "biology": [
        {
            "text": (
                "From Ancient Greek βίος (bíos, 'life') + -λογία (-logía, 'study of'), "
                "from λόγος (lógos, 'word, reason, discourse'). "
                "The term was popularised in the early 19th century."
            ),
            "roots": [
                {"root": "bios", "language": "Ancient Greek", "meaning": "life"},
                {"root": "logos", "language": "Ancient Greek", "meaning": "word, reason, study"},
            ],
        }
    ],
    "etymology": [
        {
            "text": (
                "From Middle English ethimologie, from Old French ethimologie, "
                "from Latin etymologia, from Ancient Greek ἐτυμολογία (etumología), "
                "from ἔτυμον (étumon, 'true sense of a word') + -λογία (-logía, 'study of'). "
                "ἔτυμον itself from ἐτυμός (etumós, 'true, real')."
            ),
            "roots": [
                {"root": "etymon", "language": "Ancient Greek", "meaning": "true sense of a word"},
                {"root": "etymos", "language": "Ancient Greek", "meaning": "true, real"},
                {"root": "logos", "language": "Ancient Greek", "meaning": "word, study"},
                {"root": "etymologia", "language": "Latin", "meaning": "etymology"},
            ],
        }
    ],
    "politics": [
        {
            "text": (
                "From Latin politica, from Ancient Greek πολιτικά (politiká), "
                "from πολιτικός (politikós, 'of citizens, of the state'), "
                "from πόλις (pólis, 'city, city-state') + -ικός (-ikós, adjectival suffix)."
            ),
            "roots": [
                {"root": "polis", "language": "Ancient Greek", "meaning": "city, city-state"},
                {"root": "politikos", "language": "Ancient Greek", "meaning": "of citizens"},
                {"root": "politica", "language": "Latin", "meaning": "politics"},
            ],
        }
    ],
    "music": [
        {
            "text": (
                "From Middle English musik, from Old French musique, "
                "from Latin musica, from Ancient Greek μουσική (mousikḗ), "
                "from Μοῦσα (Moûsa, 'Muse'). "
                "The Muses were the goddesses of artistic inspiration in Greek mythology."
            ),
            "roots": [
                {"root": "mousike", "language": "Ancient Greek", "meaning": "art of the Muses"},
                {"root": "Mousa", "language": "Ancient Greek", "meaning": "Muse"},
                {"root": "musica", "language": "Latin", "meaning": "music"},
                {"root": "musique", "language": "Old French", "meaning": "music"},
            ],
        }
    ],
    "geography": [
        {
            "text": (
                "From Latin geographia, from Ancient Greek γεωγραφία (geōgraphía), "
                "from γῆ (gê, 'earth') + γράφω (gráphō, 'to write, to describe'). "
                "Literally 'writing or description of the earth'."
            ),
            "roots": [
                {"root": "ge", "language": "Ancient Greek", "meaning": "earth"},
                {"root": "grapho", "language": "Ancient Greek", "meaning": "to write, to describe"},
                {"root": "geographia", "language": "Latin", "meaning": "geography"},
            ],
        }
    ],
    "technology": [
        {
            "text": (
                "From Ancient Greek τεχνολογία (tekhnología), "
                "from τέχνη (tékhnē, 'art, craft, skill') + -λογία (-logía, 'study of'). "
                "τέχνη is from Proto-Indo-European *teks- ('to weave, to fabricate')."
            ),
            "roots": [
                {"root": "tekhne", "language": "Ancient Greek", "meaning": "art, craft, skill"},
                {"root": "logos", "language": "Ancient Greek", "meaning": "word, study"},
                {"root": "*teks-", "language": "Proto-Indo-European", "meaning": "to weave, to fabricate"},
            ],
        }
    ],
    "mathematics": [
        {
            "text": (
                "From Latin mathematica, from Ancient Greek μαθηματικά (mathēmatiká), "
                "from μαθηματικός (mathēmatikós, 'fond of learning'), "
                "from μάθημα (máthēma, 'lesson, learning'), "
                "from μανθάνω (manthánō, 'to learn'), "
                "from Proto-Indo-European *men- ('to think')."
            ),
            "roots": [
                {"root": "mathema", "language": "Ancient Greek", "meaning": "lesson, learning"},
                {"root": "manthanō", "language": "Ancient Greek", "meaning": "to learn"},
                {"root": "*men-", "language": "Proto-Indo-European", "meaning": "to think"},
                {"root": "mathematica", "language": "Latin", "meaning": "mathematics"},
            ],
        }
    ],
    "psychology": [
        {
            "text": (
                "From New Latin psychologia, from Ancient Greek ψυχή (psukhḗ, 'soul, spirit, mind') "
                "+ -λογία (-logía, 'study of'). "
                "ψυχή derives from ψύχω (psúkhō, 'to breathe, to blow cold')."
            ),
            "roots": [
                {"root": "psyche", "language": "Ancient Greek", "meaning": "soul, spirit, mind"},
                {"root": "logos", "language": "Ancient Greek", "meaning": "word, study"},
            ],
        }
    ],
    "history": [
        {
            "text": (
                "From Latin historia ('narrative, history'), "
                "from Ancient Greek ἱστορία (historía, 'inquiry, knowledge from inquiry'), "
                "from ἵστωρ (hístōr, 'wise man, one who knows'), "
                "from Proto-Indo-European *weid- ('to see, to know')."
            ),
            "roots": [
                {"root": "historia", "language": "Ancient Greek", "meaning": "inquiry, knowledge"},
                {"root": "histor", "language": "Ancient Greek", "meaning": "wise man, one who knows"},
                {"root": "*weid-", "language": "Proto-Indo-European", "meaning": "to see, to know"},
                {"root": "historia", "language": "Latin", "meaning": "narrative, history"},
            ],
        }
    ],
    "astronomy": [
        {
            "text": (
                "From Latin astronomia, from Ancient Greek ἀστρονομία (astronomía), "
                "from ἄστρον (ástron, 'star') + νόμος (nómos, 'law, custom'). "
                "ἄστρον from Proto-Indo-European *h₂ster- ('star')."
            ),
            "roots": [
                {"root": "astron", "language": "Ancient Greek", "meaning": "star"},
                {"root": "nomos", "language": "Ancient Greek", "meaning": "law, custom"},
                {"root": "*h₂ster-", "language": "Proto-Indo-European", "meaning": "star"},
                {"root": "astronomia", "language": "Latin", "meaning": "astronomy"},
            ],
        }
    ],
    "telephone": [
        {
            "text": (
                "From Ancient Greek τῆλε (têle, 'far off, at a distance') "
                "+ φωνή (phōnḗ, 'voice, sound'). "
                "Coined in English in the 19th century. "
                "φωνή from Proto-Indo-European *bʰeh₂- ('to speak')."
            ),
            "roots": [
                {"root": "tele", "language": "Ancient Greek", "meaning": "far off, at a distance"},
                {"root": "phone", "language": "Ancient Greek", "meaning": "voice, sound"},
                {"root": "*bʰeh₂-", "language": "Proto-Indo-European", "meaning": "to speak"},
            ],
        }
    ],
    "catastrophe": [
        {
            "text": (
                "From Latin catastropha, from Ancient Greek καταστροφή (katastrophḗ, 'overturning, sudden turn'), "
                "from κατά (katá, 'down, against') + στρέφω (stréphō, 'to turn'). "
                "Originally a theatrical term for the dénouement of a play."
            ),
            "roots": [
                {"root": "kata", "language": "Ancient Greek", "meaning": "down, against"},
                {"root": "strephō", "language": "Ancient Greek", "meaning": "to turn"},
                {"root": "catastropha", "language": "Latin", "meaning": "overturning"},
            ],
        }
    ],
    "architecture": [
        {
            "text": (
                "From Middle French architecture, from Latin architectura, "
                "from architectus ('architect'), from Ancient Greek ἀρχιτέκτων (arkhitéktōn), "
                "from ἀρχι- (arkhi-, 'chief') + τέκτων (téktōn, 'builder, craftsman'). "
                "τέκτων from Proto-Indo-European *teks- ('to weave, fabricate')."
            ),
            "roots": [
                {"root": "arkhi-", "language": "Ancient Greek", "meaning": "chief, master"},
                {"root": "tekton", "language": "Ancient Greek", "meaning": "builder, craftsman"},
                {"root": "*teks-", "language": "Proto-Indo-European", "meaning": "to weave, to fabricate"},
                {"root": "architectura", "language": "Latin", "meaning": "architecture"},
            ],
        }
    ],
    "language": [
        {
            "text": (
                "From Middle English langage, from Old French langage, language, "
                "from langue ('tongue, language'), from Latin lingua ('tongue, language'), "
                "from Old Latin dingua, from Proto-Indo-European *dn̥ǵʰwéh₂s ('tongue, speech, language')."
            ),
            "roots": [
                {"root": "lingua", "language": "Latin", "meaning": "tongue, language"},
                {"root": "langue", "language": "Old French", "meaning": "tongue, language"},
                {"root": "*dn̥ǵʰwéh₂s", "language": "Proto-Indo-European", "meaning": "tongue, speech"},
            ],
        }
    ],
    "paradise": [
        {
            "text": (
                "From Old French paradis, from Latin paradisus, "
                "from Ancient Greek παράδεισος (parádeisos, 'park, enclosed garden'), "
                "from Old Iranian *pairi-daēza ('enclosed garden'), "
                "from *pairi- ('around') + *daēza ('wall'). "
                "Ultimately from Avestan pairidaēza."
            ),
            "roots": [
                {"root": "parádeisos", "language": "Ancient Greek", "meaning": "park, enclosed garden"},
                {"root": "*pairi-daēza", "language": "Persian", "meaning": "enclosed garden"},
                {"root": "paradisus", "language": "Latin", "meaning": "paradise, garden"},
                {"root": "paradis", "language": "Old French", "meaning": "paradise"},
            ],
        }
    ],
    "algebra": [
        {
            "text": (
                "From Medieval Latin algebra, from Arabic الجبر (al-jabr, 'reunion of broken parts'), "
                "from the title of al-Khwarizmi's 9th-century treatise Kitāb al-mukhtaṣar fī ḥisāb al-jabr waʾl-muqābala. "
                "al-jabr means 'the restoring (of broken bones)'."
            ),
            "roots": [
                {"root": "al-jabr", "language": "Arabic", "meaning": "reunion of broken parts, bone-setting"},
                {"root": "algebra", "language": "Latin", "meaning": "algebra"},
            ],
        }
    ],
    "alcohol": [
        {
            "text": (
                "From Medieval Latin alcoholus, from Arabic الكُحْل (al-kuḥl, 'the kohl'), "
                "referring to a fine metallic powder. The meaning shifted to 'distilled spirit' in the 16th century. "
                "al- is the definite article; kuḥl ('kohl, antimony powder') from כחל (kāḥal, 'to paint the eyes')."
            ),
            "roots": [
                {"root": "al-kuḥl", "language": "Arabic", "meaning": "the kohl, fine metallic powder"},
                {"root": "kāḥal", "language": "Hebrew", "meaning": "to paint the eyes"},
                {"root": "alcoholus", "language": "Latin", "meaning": "alcohol"},
            ],
        }
    ],
    "coffee": [
        {
            "text": (
                "From Dutch koffie or Ottoman Turkish قهوه (kahve), "
                "from Arabic قَهْوَة (qahwa, 'coffee'). "
                "The Arabic word originally referred to a type of wine; "
                "later applied to the coffee drink when wine became prohibited."
            ),
            "roots": [
                {"root": "qahwa", "language": "Arabic", "meaning": "coffee (orig. wine)"},
                {"root": "kahve", "language": "Turkish", "meaning": "coffee"},
                {"root": "koffie", "language": "Dutch", "meaning": "coffee"},
            ],
        }
    ],
    "robot": [
        {
            "text": (
                "From Czech robot, from robota ('drudgery, servitude, forced labour'), "
                "from Proto-Slavic *orbota, from *orb- ('slave'). "
                "Coined by Karel Čapek in his 1920 play R.U.R. (Rossum's Universal Robots)."
            ),
            "roots": [
                {"root": "robota", "language": "Czech", "meaning": "drudgery, forced labour"},
                {"root": "*orbota", "language": "Proto-Slavic", "meaning": "slave labour"},
            ],
        }
    ],
    "disaster": [
        {
            "text": (
                "From Middle French désastre, from Italian disastro, "
                "from dis- (negative prefix) + astro ('star'), from Latin astrum, "
                "from Ancient Greek ἄστρον (ástron, 'star'). "
                "Originally meant 'ill-starred event', reflecting the belief that stars influenced fate."
            ),
            "roots": [
                {"root": "astron", "language": "Ancient Greek", "meaning": "star"},
                {"root": "astrum", "language": "Latin", "meaning": "star"},
                {"root": "disastro", "language": "Italian", "meaning": "disaster (ill-starred)"},
            ],
        }
    ],
    "education": [
        {
            "text": (
                "From Latin educatio ('a rearing, a training'), "
                "from educare ('to bring up, to rear'), "
                "frequentative of educere ('to lead out'), "
                "from e- ('out') + ducere ('to lead, to guide'). "
                "ducere from Proto-Indo-European *dewk- ('to pull, to lead')."
            ),
            "roots": [
                {"root": "educere", "language": "Latin", "meaning": "to lead out"},
                {"root": "ducere", "language": "Latin", "meaning": "to lead, to guide"},
                {"root": "*dewk-", "language": "Proto-Indo-European", "meaning": "to pull, to lead"},
                {"root": "educatio", "language": "Latin", "meaning": "a rearing, training"},
            ],
        }
    ],
    "computer": [
        {
            "text": (
                "From Latin computare ('to count, to reckon'), "
                "from com- ('together') + putare ('to reckon, to prune'). "
                "Originally referred to a person who performs calculations; "
                "the modern mechanical/electronic sense dates from the 20th century."
            ),
            "roots": [
                {"root": "computare", "language": "Latin", "meaning": "to count, to reckon"},
                {"root": "putare", "language": "Latin", "meaning": "to reckon, to prune"},
                {"root": "com-", "language": "Latin", "meaning": "together, with"},
            ],
        }
    ],
    "library": [
        {
            "text": (
                "From Latin librarium ('chest for books'), from liber ('book, bark of a tree'). "
                "liber originally referred to the inner bark of a tree on which people wrote. "
                "From Proto-Indo-European *lubʰro- ('bark'). "
                "Via Old French librairie."
            ),
            "roots": [
                {"root": "liber", "language": "Latin", "meaning": "book, inner bark of a tree"},
                {"root": "librarium", "language": "Latin", "meaning": "chest for books"},
                {"root": "librairie", "language": "Old French", "meaning": "library"},
            ],
        }
    ],
    "school": [
        {
            "text": (
                "From Old English scōl, from Latin schola ('school, leisure'), "
                "from Ancient Greek σχολή (skholḗ, 'leisure, spare time, school'), "
                "originally 'a holding back, a keeping free'. "
                "The sense shift is: 'leisure' → 'use of leisure for learning' → 'place of learning'."
            ),
            "roots": [
                {"root": "skholē", "language": "Ancient Greek", "meaning": "leisure, spare time"},
                {"root": "schola", "language": "Latin", "meaning": "school, leisure"},
                {"root": "scōl", "language": "Old English", "meaning": "school"},
            ],
        }
    ],
}


# Language name normalisation map
LANG_ALIASES = {
    "la": "Latin",
    "latin": "Latin",
    "grc": "Ancient Greek",
    "greek": "Ancient Greek",
    "ancient greek": "Ancient Greek",
    "gem": "Proto-Germanic",
    "proto-germanic": "Proto-Germanic",
    "proto-indo-european": "Proto-Indo-European",
    "pie": "Proto-Indo-European",
    "ar": "Arabic",
    "arabic": "Arabic",
    "fr": "Old French",
    "fro": "Old French",
    "old french": "Old French",
    "frm": "Middle French",
    "middle french": "Middle French",
    "ang": "Old English",
    "old english": "Old English",
    "non": "Old Norse",
    "old norse": "Old Norse",
    "sa": "Sanskrit",
    "sanskrit": "Sanskrit",
    "fa": "Persian",
    "persian": "Persian",
    "he": "Hebrew",
    "hebrew": "Hebrew",
    "de": "German",
    "german": "German",
    "it": "Italian",
    "italian": "Italian",
    "es": "Spanish",
    "spanish": "Spanish",
    "enm": "Middle English",
    "middle english": "Middle English",
    "gem-pro": "Proto-Germanic",
    "ine-pro": "Proto-Indo-European",
}

# Regex patterns for extracting etymology roots from wikitext
ROOT_PATTERNS = [
    # {{inh|en|la|verbum|t=word}} style templates
    re.compile(
        r'\{\{(?:inh|bor|der|cog|m|l)\|[^|]+\|([^|]+)\|([^|}]+)(?:\|t=([^|}]+))?\}\}',
        re.IGNORECASE,
    ),
    # "From Latin X" style prose
    re.compile(
        r'[Ff]rom\s+((?:Proto-Indo-European|Proto-Germanic|Proto-Italic|Proto-Celtic|'
        r'Proto-Slavic|Proto-Balto-Slavic|Proto-Hellenic|'
        r'Ancient\s+Greek|Old\s+French|Middle\s+French|Old\s+English|Middle\s+English|'
        r'Old\s+Norse|Old\s+High\s+German|'
        r'Latin|Greek|Sanskrit|Arabic|Persian|Hebrew|German|French|Spanish|Italian|'
        r'Dutch|Norwegian|Swedish|Danish|Russian|Chinese|Japanese|Turkish|Aramaic))\s+'
        r'[*]?([^\s,;.()\[\]{}]+)',
        re.IGNORECASE,
    ),
    # Wikitext template: {{der|en|la|}} or {{bor|en|grc|λόγος}}
    re.compile(
        r'\{\{(?:der|bor|inh)\|[a-z-]+\|([a-z-]+)\|([^|}]*)',
        re.IGNORECASE,
    ),
]

# Template code → human-readable language name
TEMPLATE_LANG_CODES = {
    "la": "Latin",
    "grc": "Ancient Greek",
    "gem-pro": "Proto-Germanic",
    "ine-pro": "Proto-Indo-European",
    "fro": "Old French",
    "frm": "Middle French",
    "ang": "Old English",
    "enm": "Middle English",
    "non": "Old Norse",
    "ar": "Arabic",
    "sa": "Sanskrit",
    "fa": "Persian",
    "he": "Hebrew",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "es": "Spanish",
    "nl": "Dutch",
    "goh": "Old High German",
    "orv": "Old Russian",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "tr": "Turkish",
    "syc": "Aramaic",
    "osp": "Old Spanish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "pl": "Polish",
    "cs": "Czech",
    "sk": "Slovak",
    "bg": "Bulgarian",
    "sr": "Serbian",
    "hr": "Croatian",
    "uk": "Ukrainian",
    "be": "Belarusian",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "ga": "Irish",
    "cy": "Welsh",
    "br": "Breton",
    "sq": "Albanian",
    "hy": "Armenian",
    "ka": "Georgian",
    "hu": "Hungarian",
    "fi": "Finnish",
    "et": "Estonian",
    "ko": "Korean",
    "vi": "Vietnamese",
    "mn": "Mongolian",
}


def _fetch_wikitext(word: str) -> str | None:
    """
    Fetch the raw wikitext for a Wiktionary page.

    Args:
        word: The word to look up.

    Returns:
        Wikitext string or None if the page is not found / request fails.
    """
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
    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.RequestException:
        return None


def _extract_etymology_section(wikitext: str) -> list[str]:
    """
    Extract all Etymology section(s) from a Wiktionary wikitext block.

    Wiktionary pages may contain multiple Etymology sections (Etymology 1,
    Etymology 2, …) when a word has several distinct origins.

    Args:
        wikitext: Raw wikitext string from the Wiktionary API.

    Returns:
        List of etymology text blocks (one per section found).
    """
    sections: list[str] = []
    # Split on any heading level (== to ====) that contains "Etymology"
    parts = re.split(r'={2,4}\s*Etymology(?:\s+\d+)?\s*={2,4}', wikitext, flags=re.IGNORECASE)
    if len(parts) <= 1:
        return sections

    for part in parts[1:]:
        # Take text up to the next heading
        section = re.split(r'\n={2,}', part)[0].strip()
        if section:
            sections.append(section)
    return sections


def _builtin_lookup(word: str) -> dict | None:
    """
    Look up a word in the built-in etymology database.

    Performs case-insensitive exact and substring matching.

    Args:
        word: The word to look up.

    Returns:
        A result dict compatible with ``get_etymology`` output, or None if
        the word is not in the built-in database.
    """
    key = word.strip().lower()
    entries = BUILTIN_ETYMOLOGIES.get(key)
    if not entries:
        # Try partial match (e.g. plural/inflected forms)
        for db_key, db_entries in BUILTIN_ETYMOLOGIES.items():
            if db_key in key or key in db_key:
                entries = db_entries
                break
    if not entries:
        return None

    sections = [e["text"] for e in entries]
    return {"word": word, "found": True, "sections": sections, "error": "", "_builtin": True}


def get_etymology(word: str, lang: str = "en") -> dict:
    """
    Fetch etymology text for a word.

    First attempts the live Wiktionary API; if the API is unreachable or
    returns no data, falls back to the built-in etymology database.

    Args:
        word: The word whose etymology to retrieve.
        lang: Language code of the word's language (default 'en' for English).

    Returns:
        A dict with keys:
            'word'      – the queried word
            'found'     – bool, True if the page and etymology were found
            'sections'  – list of raw etymology text strings
            'error'     – error message string (empty string on success)
            '_builtin'  – bool, True when data came from the built-in database
    """
    wikitext = _fetch_wikitext(word)

    if wikitext is not None:
        sections = _extract_etymology_section(wikitext)
        if sections:
            return {"word": word, "found": True, "sections": sections, "error": "", "_builtin": False}
        # Page exists but has no etymology — still try builtin
        builtin = _builtin_lookup(word)
        if builtin:
            return builtin
        return {
            "word": word,
            "found": True,
            "sections": [],
            "error": f"No etymology section found for '{word}'.",
            "_builtin": False,
        }

    # API failed (network error, page not found, etc.) — try built-in fallback
    builtin = _builtin_lookup(word)
    if builtin:
        return builtin

    return {
        "word": word,
        "found": False,
        "sections": [],
        "error": (
            f"Word '{word}' was not found in Wiktionary and is not in the built-in database. "
            "Please check spelling or try a related word."
        ),
        "_builtin": False,
    }


def _normalise_language(raw: str) -> str:
    """
    Convert a raw language string (code or name) to a normalised display name.

    Args:
        raw: Raw language identifier (e.g. 'la', 'Latin', 'grc').

    Returns:
        Human-readable language name.
    """
    key = raw.strip().lower()
    if key in LANG_ALIASES:
        return LANG_ALIASES[key]
    if key in TEMPLATE_LANG_CODES:
        return TEMPLATE_LANG_CODES[key]
    # Return title-cased original if unknown
    return raw.strip().title()


def extract_roots(etymology_text: str) -> list[dict]:
    """
    Parse roots from a raw etymology text string.

    Tries multiple regex strategies to identify root words and their
    source languages.  Deduplicates results before returning.

    Args:
        etymology_text: Raw etymology section text (wikitext or plain text).

    Returns:
        List of dicts, each containing:
            'root'     – the root word or morpheme
            'language' – human-readable source language name
            'meaning'  – meaning/gloss if available, else empty string
    """
    roots: list[dict] = []
    seen: set[tuple] = set()

    # --- Strategy 1: Wikitext templates like {{inh|en|la|verbum|t=word}} ---
    template_re = re.compile(
        r'\{\{(?:inh|bor|der|cog|m|l)\|([a-z-]+)\|([a-z-]+)\|([^|}]*?)(?:\|t=([^|}]*))?[^}]*\}\}',
        re.IGNORECASE,
    )
    for m in template_re.finditer(etymology_text):
        lang_code = m.group(2).strip()
        root_word = m.group(3).strip().lstrip("*")
        meaning = (m.group(4) or "").strip()
        if not root_word or root_word == lang_code:
            continue
        lang_name = _normalise_language(lang_code)
        key = (root_word.lower(), lang_name)
        if key not in seen:
            seen.add(key)
            roots.append({"root": root_word, "language": lang_name, "meaning": meaning})

    # --- Strategy 2: "From <Language> <root>" prose patterns ---
    prose_re = re.compile(
        r'[Ff]rom\s+(Proto-Indo-European|Proto-Germanic|Proto-Italic|Proto-Celtic|'
        r'Proto-Slavic|Proto-Balto-Slavic|Proto-Hellenic|'
        r'Ancient\s+Greek|Old\s+French|Middle\s+French|Old\s+English|Middle\s+English|'
        r'Old\s+Norse|Old\s+High\s+German|'
        r'Latin|Greek|Sanskrit|Arabic|Persian|Hebrew|German|French|Spanish|Italian|'
        r'Dutch|Norwegian|Swedish|Danish|Russian|Chinese|Japanese|Turkish|Aramaic)\s+'
        r'[*]?([^\s,;.()\[\]{}|\'\"]+)',
        re.IGNORECASE,
    )
    for m in prose_re.finditer(etymology_text):
        lang_raw = m.group(1).strip()
        root_word = m.group(2).strip().lstrip("*")
        if not root_word:
            continue
        lang_name = _normalise_language(lang_raw)
        key = (root_word.lower(), lang_name)
        if key not in seen:
            seen.add(key)
            roots.append({"root": root_word, "language": lang_name, "meaning": ""})

    # --- Strategy 3: {{der|en|la|}} or {{bor|en|grc|λόγος}} templates ---
    deriv_re = re.compile(
        r'\{\{(?:der|bor|inh)\|[a-z-]+\|([a-z-]+)\|([^|}]*)',
        re.IGNORECASE,
    )
    for m in deriv_re.finditer(etymology_text):
        lang_code = m.group(1).strip()
        root_word = m.group(2).strip().lstrip("*")
        if not root_word:
            continue
        lang_name = _normalise_language(lang_code)
        key = (root_word.lower(), lang_name)
        if key not in seen:
            seen.add(key)
            roots.append({"root": root_word, "language": lang_name, "meaning": ""})

    return roots


def get_word_info(word: str) -> dict:
    """
    Retrieve full etymological information for a word, combining API fetch
    and root extraction.

    When the built-in database is used as a fallback, pre-parsed root data
    is used directly rather than re-parsing prose text.

    Args:
        word: The word to analyse.

    Returns:
        A dict with keys:
            'word'             – the queried word
            'found'            – bool
            'error'            – error message or empty string
            'etymology_texts'  – list of raw etymology section strings
            'roots'            – deduplicated list of root dicts
                                 (each has 'root', 'language', 'meaning')
            'etymology_count'  – number of distinct etymologies found
    """
    ety_data = get_etymology(word)

    if not ety_data["found"] or not ety_data["sections"]:
        return {
            "word": word,
            "found": ety_data["found"],
            "error": ety_data["error"],
            "etymology_texts": [],
            "roots": [],
            "etymology_count": 0,
        }

    # If the data came from the built-in DB, use its pre-parsed roots directly.
    if ety_data.get("_builtin"):
        db_entries = BUILTIN_ETYMOLOGIES.get(word.strip().lower(), [])
        if not db_entries:
            for db_key, entries in BUILTIN_ETYMOLOGIES.items():
                if db_key in word.lower() or word.lower() in db_key:
                    db_entries = entries
                    break
        all_roots: list[dict] = []
        seen_keys: set[tuple] = set()
        for entry in db_entries:
            for r in entry.get("roots", []):
                key = (r["root"].lower(), r["language"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_roots.append(r)
        return {
            "word": word,
            "found": True,
            "error": "",
            "etymology_texts": ety_data["sections"],
            "roots": all_roots,
            "etymology_count": len(ety_data["sections"]),
        }

    # Live API data: parse roots from wikitext sections.
    all_roots = []
    seen_keys = set()
    for section in ety_data["sections"]:
        section_roots = extract_roots(section)
        for r in section_roots:
            key = (r["root"].lower(), r["language"])
            if key not in seen_keys:
                seen_keys.add(key)
                all_roots.append(r)

    return {
        "word": word,
        "found": True,
        "error": "",
        "etymology_texts": ety_data["sections"],
        "roots": all_roots,
        "etymology_count": len(ety_data["sections"]),
    }
