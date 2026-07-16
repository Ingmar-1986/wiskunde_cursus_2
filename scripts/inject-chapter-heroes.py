#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import sys
from pathlib import Path


# ============================================================
# CONFIGURATIE VAN DE THEMA'S
# ============================================================

THEMES: dict[str, dict[str, str]] = {
    "basiswiskunde": {
        "number": "1",
        "title": "Basiswiskunde",
    },
    "algebra": {
        "number": "2",
        "title": "Algebra",
    },
    "vergelijkingen": {
        "number": "3",
        "title": "Vergelijkingen",
    },
    "functies": {
        "number": "4",
        "title": "Functies",
    },
    "vectoren": {
        "number": "5",
        "title": "Vectoren",
    },
    "coordinaten": {
        "number": "6",
        "title": "Coördinaten",
    },
    "3d-meetkunde": {
        "number": "7",
        "title": "3D-meetkunde",
    },
    "goniometrie": {
        "number": "8",
        "title": "Goniometrie",
    },
    "logaritmen": {
        "number": "9",
        "title": "Logaritmen",
    },
    "transformaties": {
        "number": "10",
        "title": "Transformaties",
    },
}


# ============================================================
# REGULIERE EXPRESSIES
# ============================================================

ACTIVITY_PATTERN = re.compile(
    r"""
    \\(?:activity|include|input)
    (?:\[[^\]]*\])?
    \{
        (?P<path>[^}]+)
    \}
    """,
    re.VERBOSE,
)

TITLE_PATTERNS = [
    re.compile(
        r'<h1\b[^>]*>(?P<title>.*?)</h1>',
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r'<div\b[^>]*class=["\'][^"\']*\btitle\b[^"\']*["\'][^>]*>'
        r'(?P<title>.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r'<title\b[^>]*>(?P<title>.*?)</title>',
        re.IGNORECASE | re.DOTALL,
    ),
]

ABSTRACT_PATTERNS = [
    re.compile(
        r'''
        <(?P<tag>div|section|p)\b
        (?=[^>]*\bclass=["'][^"']*\babstract\b[^"']*["'])
        [^>]*>
        (?P<abstract>.*?)
        </(?P=tag)>
        ''',
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    ),
    re.compile(
        r'''
        <p\b[^>]*>
        \s*
        (?:<strong\b[^>]*>)?
        \s*Abstract\.?
        \s*
        (?:</strong>)?
        (?P<abstract>.*?)
        </p>
        ''',
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    ),
]

EXISTING_HERO_PATTERN = re.compile(
    r'<!--\s*CHAPTER_HERO_START\s*-->.*?'
    r'<!--\s*CHAPTER_HERO_END\s*-->',
    re.IGNORECASE | re.DOTALL,
)

FIRST_H1_PATTERN = re.compile(
    r'<h1\b[^>]*>.*?</h1>',
    re.IGNORECASE | re.DOTALL,
)

MAIN_OPEN_PATTERN = re.compile(
    r'<main\b[^>]*>',
    re.IGNORECASE,
)

ARTICLE_OPEN_PATTERN = re.compile(
    r'<article\b[^>]*>',
    re.IGNORECASE,
)

BODY_OPEN_PATTERN = re.compile(
    r'<body\b[^>]*>',
    re.IGNORECASE,
)

TAG_PATTERN = re.compile(r'<[^>]+>', re.DOTALL)

WHITESPACE_PATTERN = re.compile(r'\s+')


# ============================================================
# HULPFUNCTIES
# ============================================================

def clean_text(value: str) -> str:
    """Verwijder HTML-tags en normaliseer witruimte."""

    value = re.sub(
        r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>',
        '',
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )

    value = TAG_PATTERN.sub(' ', value)
    value = html.unescape(value)
    value = WHITESPACE_PATTERN.sub(' ', value)

    return value.strip()


def humanize_slug(slug: str) -> str:
    """Zet een map- of bestandsnaam om naar een leesbare titel."""

    value = slug.replace('_', ' ').replace('-', ' ')
    value = WHITESPACE_PATTERN.sub(' ', value).strip()

    if not value:
        return "Wiskunde"

    return value[0].upper() + value[1:]


def normalize_chapter_title(title: str) -> str:
    """Verwijder een eventueel bestaand hoofdstuknummer uit de titel."""

    title = clean_text(title)

    title = re.sub(
        r'^\s*hoofdstuk\s+\d+\s*[:.\-–—]?\s*',
        '',
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r'^\s*\d+\s*[:.\-–—]\s*',
        '',
        title,
    )

    return title.strip()


def remove_abstract_label(text: str) -> str:
    """Verwijder het woord Abstract aan het begin."""

    return re.sub(
        r'^\s*Abstract\.?\s*',
        '',
        text,
        flags=re.IGNORECASE,
    ).strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


# ============================================================
# THEMA BEPALEN
# ============================================================

def get_theme(module_dir: Path) -> tuple[str, str]:
    """Bepaal themanummer en thematitel uit de modulemap."""

    module_name = module_dir.name.lower()

    if module_name in THEMES:
        theme = THEMES[module_name]
        return theme["number"], theme["title"]

    return "", humanize_slug(module_dir.name)


# ============================================================
# HOOFDSTUKVOLGORDE UIT INDEX.TEX
# ============================================================

def normalize_activity_path(raw_path: str) -> str:
    """Maak van een LaTeX-pad een bestandsstam."""

    value = raw_path.strip()
    value = value.replace("\\", "/")

    if value.endswith(".tex"):
        value = value[:-4]

    return Path(value).name


def read_chapter_order(course_file: Path) -> list[str]:
    """Lees de hoofdstukvolgorde uit activity/include/input in index.tex."""

    document = read_text(course_file)

    chapters: list[str] = []

    for match in ACTIVITY_PATTERN.finditer(document):
        stem = normalize_activity_path(match.group("path"))

        if not stem:
            continue

        if stem.lower() == "index":
            continue

        if stem not in chapters:
            chapters.append(stem)

    return chapters


# ============================================================
# TITEL EN ABSTRACT UIT HTML HALEN
# ============================================================

def extract_title(document: str, fallback: str) -> str:
    """Zoek de hoofdstuktitel in de gegenereerde HTML."""

    for pattern in TITLE_PATTERNS:
        match = pattern.search(document)

        if not match:
            continue

        title = normalize_chapter_title(match.group("title"))

        if title:
            return title

    return humanize_slug(fallback)


def extract_abstract(document: str, title: str) -> tuple[str, tuple[int, int] | None]:
    """
    Zoek het bestaande abstract.

    Geeft zowel de tekst als de positie van het gevonden HTML-element terug,
    zodat de oude abstractweergave kan worden verwijderd.
    """

    for pattern in ABSTRACT_PATTERNS:
        match = pattern.search(document)

        if not match:
            continue

        abstract = clean_text(match.group("abstract"))
        abstract = remove_abstract_label(abstract)

        if abstract:
            return abstract, match.span()

    fallback = (
        f"In dit hoofdstuk leer je de belangrijkste begrippen, "
        f"methodes en toepassingen van {title.lower()}."
    )

    return fallback, None


# ============================================================
# HERO MAKEN
# ============================================================

def create_hero(
    template: str,
    theme_number: str,
    theme_title: str,
    chapter_number: int,
    chapter_title: str,
    chapter_abstract: str,
) -> str:
    """Vul de placeholders van chapter-hero.html."""

    theme_number_text = str(theme_number).strip()

    if theme_number_text:
        theme_label = f"Thema {theme_number_text}"
    else:
        theme_label = "Thema"

    replacements = {
        "THEME_NUMBER": html.escape(
            theme_number_text,
            quote=False,
        ),
        "THEME_LABEL": html.escape(
            theme_label,
            quote=False,
        ),
        "THEME_TITLE": html.escape(
            theme_title,
            quote=False,
        ),
        "CHAPTER_NUMBER": html.escape(
            str(chapter_number),
            quote=False,
        ),
        "CHAPTER_TITLE": html.escape(
            chapter_title,
            quote=False,
        ),
        "CHAPTER_ABSTRACT": html.escape(
            chapter_abstract,
            quote=False,
        ),
    }

    result = template

    for placeholder, value in replacements.items():
        result = result.replace(
            "{{" + placeholder + "}}",
            value,
        )

    return result.strip()


# ============================================================
# OUDE TITEL EN ABSTRACT VERWIJDEREN
# ============================================================

def remove_old_abstract(
    document: str,
    abstract_span: tuple[int, int] | None,
) -> str:
    """Verwijder het oude abstractelement als het werd teruggevonden."""

    if abstract_span is None:
        return document

    start, end = abstract_span
    return document[:start] + document[end:]


def remove_first_h1(document: str, expected_title: str) -> str:
    """
    Verwijder de eerste h1 wanneer die overeenkomt met de hoofdstuktitel.

    Zo verschijnt de titel niet dubbel onder de hero.
    """

    match = FIRST_H1_PATTERN.search(document)

    if not match:
        return document

    old_title = normalize_chapter_title(match.group(0))

    normalized_old = old_title.casefold()
    normalized_expected = expected_title.casefold()

    titles_match = (
        normalized_old == normalized_expected
        or normalized_expected in normalized_old
        or normalized_old in normalized_expected
    )

    if not titles_match:
        return document

    return document[:match.start()] + document[match.end():]


# ============================================================
# HERO INVOEGEN
# ============================================================

def wrap_hero(hero: str) -> str:
    return (
        "<!-- CHAPTER_HERO_START -->\n"
        f"{hero}\n"
        "<!-- CHAPTER_HERO_END -->"
    )


def insert_after_match(
    document: str,
    match: re.Match[str],
    block: str,
) -> str:
    position = match.end()

    return (
        document[:position]
        + "\n"
        + block
        + "\n"
        + document[position:]
    )


def inject_hero(document: str, hero: str) -> str:
    """Vervang een bestaande hero of voeg hem bovenaan de inhoud in."""

    generated_block = wrap_hero(hero)

    if EXISTING_HERO_PATTERN.search(document):
        return EXISTING_HERO_PATTERN.sub(
            generated_block,
            document,
            count=1,
        )

    main_match = MAIN_OPEN_PATTERN.search(document)

    if main_match:
        return insert_after_match(
            document,
            main_match,
            generated_block,
        )

    article_match = ARTICLE_OPEN_PATTERN.search(document)

    if article_match:
        return insert_after_match(
            document,
            article_match,
            generated_block,
        )

    body_match = BODY_OPEN_PATTERN.search(document)

    if body_match:
        return insert_after_match(
            document,
            body_match,
            generated_block,
        )

    return generated_block + "\n" + document


# ============================================================
# HTML-BESTANDEN ZOEKEN
# ============================================================

def html_candidates(module_dir: Path, stem: str) -> list[Path]:
    """
    Zoek gewone en online HTML-versies van een hoofdstuk.

    Bijvoorbeeld:
      rekenen.html
      rekenen.online.html
    """

    candidates = [
        module_dir / f"{stem}.html",
        module_dir / f"{stem}.online.html",
    ]

    return [
        path
        for path in candidates
        if path.is_file()
    ]


def fallback_html_files(module_dir: Path) -> list[Path]:
    """Fallback wanneer index.tex geen activities oplevert."""

    files = sorted(module_dir.glob("*.html"))

    return [
        path
        for path in files
        if path.name != "index.html"
        and not path.name.endswith(".online.html")
    ]


# ============================================================
# ÉÉN HOOFDSTUK VERWERKEN
# ============================================================

def process_html_file(
    html_path: Path,
    template: str,
    theme_number: str,
    theme_title: str,
    chapter_number: int,
    fallback_title: str,
) -> None:
    document = read_text(html_path)

    title = extract_title(
        document,
        fallback=fallback_title,
    )

    abstract, abstract_span = extract_abstract(
        document,
        title,
    )

    hero = create_hero(
        template=template,
        theme_number=theme_number,
        theme_title=theme_title,
        chapter_number=chapter_number,
        chapter_title=title,
        chapter_abstract=abstract,
    )

    # Eerst oude hero vervangen wanneer die al aanwezig is.
    if EXISTING_HERO_PATTERN.search(document):
        result = inject_hero(document, hero)
    else:
        # Anders eerst oude titel en abstract verwijderen.
        result = remove_old_abstract(
            document,
            abstract_span,
        )

        result = remove_first_h1(
            result,
            title,
        )

        result = inject_hero(
            result,
            hero,
        )

    write_text(html_path, result)

    print(
        f"Hero ingevoegd: {html_path} "
        f"(hoofdstuk {chapter_number}: {title})"
    )


# ============================================================
# VOLLEDIGE MODULE VERWERKEN
# ============================================================

def process_module(
    module_dir: Path,
    course_file: Path,
    template_path: Path,
) -> int:
    if not module_dir.is_dir():
        raise ValueError(
            f"Modulemap bestaat niet: {module_dir}"
        )

    if not course_file.is_file():
        raise ValueError(
            f"index.tex bestaat niet: {course_file}"
        )

    if not template_path.is_file():
        raise ValueError(
            f"Hero-template bestaat niet: {template_path}"
        )

    template = read_text(template_path)

    theme_number, theme_title = get_theme(module_dir)
    chapter_order = read_chapter_order(course_file)

    processed_count = 0

    if chapter_order:
        for chapter_number, stem in enumerate(
            chapter_order,
            start=1,
        ):
            candidates = html_candidates(
                module_dir,
                stem,
            )

            if not candidates:
                print(
                    f"Waarschuwing: geen HTML gevonden voor "
                    f"hoofdstuk {chapter_number}: {stem}",
                    file=sys.stderr,
                )
                continue

            for html_path in candidates:
                process_html_file(
                    html_path=html_path,
                    template=template,
                    theme_number=theme_number,
                    theme_title=theme_title,
                    chapter_number=chapter_number,
                    fallback_title=stem,
                )

                processed_count += 1

    else:
        print(
            "Waarschuwing: geen activities gevonden in index.tex. "
            "HTML-bestanden worden alfabetisch verwerkt.",
            file=sys.stderr,
        )

        files = fallback_html_files(module_dir)

        for chapter_number, html_path in enumerate(
            files,
            start=1,
        ):
            process_html_file(
                html_path=html_path,
                template=template,
                theme_number=theme_number,
                theme_title=theme_title,
                chapter_number=chapter_number,
                fallback_title=html_path.stem,
            )

            processed_count += 1

    if processed_count == 0:
        raise ValueError(
            f"Geen hoofdstuk-HTML-bestanden verwerkt in {module_dir}"
        )

    return processed_count


# ============================================================
# COMMANDOLIJN
# ============================================================

def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Gebruik:\n"
            "  python3 scripts/inject-chapter-heroes.py "
            "<modulemap> <index.tex> <chapter-hero.html>\n\n"
            "Voorbeeld:\n"
            "  python3 scripts/inject-chapter-heroes.py "
            "modules/basiswiskunde "
            "modules/basiswiskunde/index.tex "
            "assets/html/chapter-hero.html",
            file=sys.stderr,
        )

        return 1

    module_dir = Path(sys.argv[1])
    course_file = Path(sys.argv[2])
    template_path = Path(sys.argv[3])

    try:
        count = process_module(
            module_dir=module_dir,
            course_file=course_file,
            template_path=template_path,
        )
    except (OSError, ValueError) as error:
        print(
            f"Fout: {error}",
            file=sys.stderr,
        )

        return 1

    print()
    print(
        f"Klaar: {count} hoofdstukbestand(en) verwerkt "
        f"in {module_dir}."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())