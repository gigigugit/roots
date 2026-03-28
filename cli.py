"""
cli.py - Command-line interface for the word etymology and cross-language root finder.

Usage:
    python cli.py <word>
    python cli.py              # prompts for input
    python cli.py --help
"""

import argparse
import sys

from etymology import get_word_info
from cross_language import find_cross_language_roots

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

# Language → terminal color
LANG_COLORS: dict[str, str] = {
    "Latin": RED,
    "Ancient Greek": BLUE,
    "Proto-Germanic": GREEN,
    "Proto-Indo-European": MAGENTA,
    "Sanskrit": YELLOW,
    "Arabic": CYAN,
    "Old French": "\033[38;5;208m",   # orange
    "Middle French": "\033[38;5;214m",
    "Old English": "\033[38;5;34m",   # dark green
    "Middle English": "\033[38;5;40m",
    "Old Norse": "\033[38;5;39m",
    "Persian": "\033[38;5;135m",
    "Hebrew": "\033[38;5;220m",
    "German": "\033[38;5;160m",
    "French": "\033[38;5;21m",
    "Italian": "\033[38;5;118m",
    "Spanish": "\033[38;5;202m",
}


def _lang_color(lang: str) -> str:
    """Return the ANSI color for a given language, defaulting to white."""
    return LANG_COLORS.get(lang, WHITE)


def _print_header(title: str) -> None:
    width = min(80, len(title) + 8)
    print(f"\n{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}")


def _print_section(title: str) -> None:
    print(f"\n{BOLD}{WHITE}── {title} {'─' * (60 - len(title))}{RESET}")


def _print_root(root: dict) -> None:
    lang = root.get("language", "Unknown")
    word = root.get("root", "")
    meaning = root.get("meaning", "")
    color = _lang_color(lang)
    badge = f"{color}[{lang}]{RESET}"
    meaning_str = f'  {DIM}"{meaning}"{RESET}' if meaning else ""
    print(f"  {badge}  {BOLD}{word}{RESET}{meaning_str}")


def _print_cross_language(cross: list[dict]) -> None:
    """Pretty-print the cross-language cognate results."""
    if not cross:
        print(f"  {DIM}No cross-language connections found.{RESET}")
        return

    for item in cross:
        src_root = item.get("source_root", "")
        src_lang = item.get("source_lang", "")
        src_meaning = item.get("source_meaning", "")
        cognates = item.get("cognates", [])

        color = _lang_color(src_lang)
        meaning_str = f'  "{src_meaning}"' if src_meaning else ""
        print(f"\n  {BOLD}{color}*{src_root}{RESET} ({src_lang}){DIM}{meaning_str}{RESET}")

        if cognates:
            for cog in cognates[:8]:  # limit display to 8 per root
                cog_lang = cog.get("language", "")
                cog_word = cog.get("word", "")
                rel = cog.get("relationship", "")
                c_color = _lang_color(cog_lang)
                print(
                    f"    {c_color}• {cog_lang}{RESET}: "
                    f"{BOLD}{cog_word}{RESET}  {DIM}({rel}){RESET}"
                )
            if len(cognates) > 8:
                print(f"    {DIM}… and {len(cognates) - 8} more{RESET}")
        else:
            print(f"    {DIM}No cognates found.{RESET}")


def analyse_word(word: str) -> int:
    """
    Run the full etymology and cross-language analysis for a word and print
    the results to stdout.

    Args:
        word: The word to analyse.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    print(f"\n{DIM}Looking up '{word}' in Wiktionary…{RESET}")

    word_info = get_word_info(word)

    if not word_info["found"]:
        print(f"\n{RED}✗ Error:{RESET} {word_info['error']}", file=sys.stderr)
        return 1

    if not word_info["etymology_texts"] and not word_info["roots"]:
        print(f"\n{YELLOW}⚠ Warning:{RESET} {word_info['error'] or 'No etymology data found.'}")
        return 1

    _print_header(f'Etymology of "{word}"')

    # --- Etymology texts ---
    _print_section("Etymology")
    for i, text in enumerate(word_info["etymology_texts"], 1):
        if len(word_info["etymology_texts"]) > 1:
            print(f"\n  {BOLD}Etymology {i}:{RESET}")
        # Strip wikitext markup for display
        import re  # pylint: disable=import-outside-toplevel
        clean = re.sub(r'\{\{[^}]+\}\}', '', text)
        clean = re.sub(r'\[\[(?:[^|\]]+\|)?([^\]]+)\]\]', r'\1', clean)
        clean = re.sub(r"'{2,3}", '', clean)
        clean = ' '.join(clean.split())
        # Wrap at 70 chars
        words = clean.split()
        line = "  "
        for w in words:
            if len(line) + len(w) + 1 > 72:
                print(line)
                line = "  " + w + " "
            else:
                line += w + " "
        if line.strip():
            print(line)

    # --- Identified roots ---
    _print_section(f"Identified roots ({len(word_info['roots'])} found)")
    if word_info["roots"]:
        for root in word_info["roots"]:
            _print_root(root)
    else:
        print(f"  {DIM}No structured roots extracted.{RESET}")

    # --- Cross-language connections ---
    _print_section("Cross-language connections")
    if word_info["roots"]:
        print(f"  {DIM}Searching for cognates and descendants…{RESET}")
        cross = find_cross_language_roots(word_info["roots"])
        _print_cross_language(cross)
    else:
        print(f"  {DIM}Cannot search for cross-language roots without identified roots.{RESET}")

    print(f"\n{DIM}{'─' * 70}{RESET}\n")
    return 0


def main() -> None:
    """Entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Word etymology and cross-language root finder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cli.py philosophy\n"
            "  python cli.py democracy\n"
            "  python cli.py       # interactive mode\n"
        ),
    )
    parser.add_argument(
        "word",
        nargs="?",
        help="Word to analyse (omit to be prompted)",
    )
    args = parser.parse_args()

    word = args.word
    if not word:
        try:
            word = input("Enter a word to analyse: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.", file=sys.stderr)
            sys.exit(1)

    if not word:
        print("No word provided.", file=sys.stderr)
        sys.exit(1)

    sys.exit(analyse_word(word))


if __name__ == "__main__":
    main()
