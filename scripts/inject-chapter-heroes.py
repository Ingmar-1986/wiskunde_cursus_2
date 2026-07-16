#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import sys
from pathlib import Path


# ============================================================
# THEMA-INSTELLINGEN
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
    "coördinaten": {
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

EXISTING_HERO_PATTERN = re.compile(
    r"<!--\s*CHAPTER_HERO_START\s*-->.*?"
    r"<!--\s*CHAPTER_HERO_END\s*-->",
    re.IGNORECASE | re.DOTALL,
)

HEAD_CLOSE_PATTERN = re.compile(
    r"</head>",
    re.IGNORECASE,
)

MAIN_OPEN_PATTERN = re.compile(
    r"<main\b[^>]*>",
    re.IGNORECASE,
)

ARTICLE_OPEN_PATTERN = re.compile(
    r"<article\b[^>]*>",
    re.IGNORECASE,
)

BODY_OPEN_PATTERN = re.compile(
    r"<body\b[^>]*>",
    re.IGNORECASE,
)

HEADING_PATTERN = re.compile(
    r"<h(?P<level>[1-3])\b(?P<attributes>[^>]*)>"
    r"(?P<title>.*?)"
    r"</h(?P=level)>",
    re.IGNORECASE | re.DOTALL,
)

TITLE_ELEMENT_PATTERN = re.compile(
    r"""
    <(?:div|span|p)\b
    (?=[^>]*class=["'][^"']*
        (?:activity-title|chapter-title|document-title|ximera-title)
        [^"']*["'])
    [^>]*>
    (?P<title>.*?)
    </(?:div|span|p)>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

ABSTRACT_CLASS_PATTERN = re.compile(
    r"""
    <(?P<tag>div|section|p)\b
    (?=[^>]*class=["'][^"']*\babstract\b[^"']*["'])
    [^>]*>
    (?P<abstract>.*?)
    </(?P=tag)>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

ABSTRACT_PARAGRAPH_PATTERN = re.compile(
    r"""
    <p\b[^>]*>
    \s*
    (?:<strong\b[^>]*>)?
    \s*Abstract\.?
    \s*
    (?:</strong>)?
    (?P<abstract>.*?)
    </p>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

SCRIPT_STYLE_PATTERN = re.compile(
    r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>",
    re.IGNORECASE | re.DOTALL,
)

TAG_PATTERN = re.compile(
    r"<[^>]+>",
    re.DOTALL,
)

WHITESPACE_PATTERN = re.compile(
    r"\s+",
)


# ============================================================
# BASISFUNCTIES
# ============================================================

def read_text(path: Path) -> str:
    """Lees een UTF-8-bestand."""

    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    """Schrijf een UTF-8-bestand."""

    path.write_text(content, encoding="utf-8")


def clean_text(value: str) -> str:
    """Verwijder HTML-tags en normaliseer witruimte."""

    value = SCRIPT_STYLE_PATTERN.sub("", value)
    value = TAG_PATTERN.sub(" ", value)
    value = html.unescape(value)
    value = WHITESPACE_PATTERN.sub(" ", value)

    return value.strip()


def humanize_slug(slug: str) -> str:
    """Zet een bestandsnaam om naar een leesbare titel."""

    value = slug.replace("_", " ").replace("-", " ")
    value = WHITESPACE_PATTERN.sub(" ", value).strip()

    if not value:
        return "Wiskunde"

    return value[0].upper() + value[1:]


def normalize_title(title: str) -> str:
    """Verwijder nummering en het woord hoofdstuk uit een titel."""

    title = clean_text(title)

    title = re.sub(
        r"^\s*hoofdstuk\s+\d+\s*[:.\-–—]?\s*",
        "",
        title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"^\s*\d+(?:\.\d+)*\s*[:.\-–—]?\s*",
        "",
        title,
    )

    return title.strip()


def remove_abstract_label(value: str) -> str:
    """Verwijder het woord Abstract aan het begin."""

    return re.sub(
        r"^\s*Abstract\.?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()


# ============================================================
# THEMA BEPALEN
# ============================================================

def get_theme(module_dir: Path) -> tuple[str, str]:
    """Bepaal themanummer en thematitel uit de modulemap."""

    module_name = module_dir.name.casefold()

    if module_name in THEMES:
        theme = THEMES[module_name]

        return (
            theme["number"],
            theme["title"],
        )

    return (
        "",
        humanize_slug(module_dir.name),
    )


# ============================================================
# INDEX.TEX LEZEN
# ============================================================

def normalize_activity_path(raw_path: str) -> str:
    """Zet een LaTeX-pad om naar een bestandsstam."""

    value = raw_path.strip()
    value = value.replace("\\", "/")

    if value.endswith(".tex"):
        value = value[:-4]

    return Path(value).name


def read_chapter_order(course_file: Path) -> list[str]:
    """Lees de hoofdstukvolgorde uit index.tex."""

    document = read_text(course_file)
    chapters: list[str] = []

    ignored_stems = {
        "index",
        "preamble",
        "header",
        "footer",
        "macros",
        "commands",
    }

    for match in ACTIVITY_PATTERN.finditer(document):
        stem = normalize_activity_path(
            match.group("path")
        )

        if not stem:
            continue

        if stem.casefold() in ignored_stems:
            continue

        if stem not in chapters:
            chapters.append(stem)

    return chapters


# ============================================================
# TITEL VINDEN
# ============================================================

def is_bad_title(
    title: str,
    theme_title: str,
) -> bool:
    """Controleer of een titel geen hoofdstuktitel is."""

    normalized = title.casefold().strip()

    rejected_exact = {
        "",
        "wiskunde",
        "wiskunde 7 fvd",
        "7 fvd",
        "cursusinhoud",
        "inhoud",
        "voorkennis",
        "leerdoelen",
        "begrippen",
        "abstract",
        "hoofdstuk",
        theme_title.casefold(),
    }

    if normalized in rejected_exact:
        return True

    rejected_fragments = (
        "fundamentele vorming digitale creatie",
        "digital arts & entertainment",
        "digital arts and entertainment",
        "athena",
        "howest",
    )

    return any(
        fragment in normalized
        for fragment in rejected_fragments
    )


def extract_title(
    document: str,
    fallback: str,
    theme_title: str,
) -> str:
    """Zoek de meest waarschijnlijke hoofdstuktitel."""

    for match in TITLE_ELEMENT_PATTERN.finditer(document):
        title = normalize_title(
            match.group("title")
        )

        if title and not is_bad_title(
            title,
            theme_title,
        ):
            return title

    candidates: list[tuple[int, int, str]] = []

    for order, match in enumerate(
        HEADING_PATTERN.finditer(document)
    ):
        title = normalize_title(
            match.group("title")
        )

        if not title:
            continue

        if is_bad_title(
            title,
            theme_title,
        ):
            continue

        level = int(
            match.group("level")
        )

        attributes = match.group(
            "attributes"
        ).casefold()

        score = 0

        if level == 1:
            score += 30
        elif level == 2:
            score += 20
        else:
            score += 10

        if any(
            name in attributes
            for name in (
                "chapter-title",
                "activity-title",
                "document-title",
                "ximera-title",
                "title",
            )
        ):
            score += 50

        if title.casefold() in {
            "voorkennis",
            "leerdoelen",
            "begrippen",
            "wat leer je",
            "veelgemaakte fouten",
        }:
            score -= 100

        candidates.append(
            (
                score,
                -order,
                title,
            )
        )

    if candidates:
        candidates.sort(
            reverse=True
        )

        return candidates[0][2]

    return humanize_slug(fallback)


# ============================================================
# ABSTRACT VINDEN
# ============================================================

def extract_abstract(
    document: str,
    title: str,
) -> tuple[str, tuple[int, int] | None]:
    """
    Zoek de bestaande abstracttekst.

    Geeft ook de positie terug, zodat de oude abstracttekst
    eventueel uit de gewone pagina-inhoud kan worden verwijderd.
    """

    for pattern in (
        ABSTRACT_CLASS_PATTERN,
        ABSTRACT_PARAGRAPH_PATTERN,
    ):
        match = pattern.search(document)

        if not match:
            continue

        abstract = clean_text(
            match.group("abstract")
        )

        abstract = remove_abstract_label(
            abstract
        )

        if abstract:
            return (
                abstract,
                match.span(),
            )

    fallback = (
        f"In dit hoofdstuk leer je de belangrijkste begrippen, "
        f"methodes en toepassingen van {title.lower()}."
    )

    return (
        fallback,
        None,
    )


# ============================================================
# HERO OPBOUWEN
# ============================================================

def create_hero(
    template: str,
    theme_number: str,
    theme_title: str,
    chapter_number: int,
    chapter_title: str,
    chapter_abstract: str,
) -> str:
    """Vul de placeholders in chapter-hero.html."""

    replacements = {
        "THEME_NUMBER": html.escape(
            str(theme_number),
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


def wrap_hero(hero: str) -> str:
    """Plaats herkenbare commentaren rond de hero."""

    return (
        "<!-- CHAPTER_HERO_START -->\n"
        + hero
        + "\n<!-- CHAPTER_HERO_END -->"
    )


# ============================================================
# STYLESHEET TOEVOEGEN
# ============================================================

def ensure_hero_stylesheet(document: str) -> str:
    """Voeg chapter-hero.css automatisch toe."""

    if "chapter-hero.css" in document:
        return document

    stylesheet_link = (
        '    <link rel="stylesheet" '
        'href="../../assets/css/chapter-hero.css">\n'
    )

    head_close = HEAD_CLOSE_PATTERN.search(
        document
    )

    if head_close:
        return (
            document[:head_close.start()]
            + stylesheet_link
            + document[head_close.start():]
        )

    body_open = BODY_OPEN_PATTERN.search(
        document
    )

    if body_open:
        return (
            document[:body_open.start()]
            + stylesheet_link
            + document[body_open.start():]
        )

    return stylesheet_link + document


# ============================================================
# OUDE TITEL EN ABSTRACT VERWIJDEREN
# ============================================================

def remove_old_abstract(
    document: str,
    abstract_span: tuple[int, int] | None,
) -> str:
    """Verwijder de oude losse abstracttekst."""

    if abstract_span is None:
        return document

    start, end = abstract_span

    return (
        document[:start]
        + document[end:]
    )


def remove_matching_heading(
    document: str,
    expected_title: str,
) -> str:
    """Verwijder de heading die overeenkomt met de hero-titel."""

    expected = normalize_title(
        expected_title
    ).casefold()

    for match in HEADING_PATTERN.finditer(document):
        found = normalize_title(
            match.group("title")
        ).casefold()

        if not found:
            continue

        titles_match = (
            found == expected
            or (
                len(found) >= 5
                and found in expected
            )
            or (
                len(expected) >= 5
                and expected in found
            )
        )

        if titles_match:
            return (
                document[:match.start()]
                + document[match.end():]
            )

    return document


# ============================================================
# HERO INVOEGEN
# ============================================================

def insert_after_match(
    document: str,
    match: re.Match[str],
    block: str,
) -> str:
    """Plaats een blok direct na een gevonden HTML-element."""

    position = match.end()

    return (
        document[:position]
        + "\n"
        + block
        + "\n"
        + document[position:]
    )


def inject_hero(
    document: str,
    hero: str,
) -> str:
    """Vervang een bestaande hero of voeg een nieuwe hero in."""

    generated_block = wrap_hero(
        hero
    )

    if EXISTING_HERO_PATTERN.search(document):
        return EXISTING_HERO_PATTERN.sub(
            lambda _match: generated_block,
            document,
            count=1,
        )

    main_match = MAIN_OPEN_PATTERN.search(
        document
    )

    if main_match:
        return insert_after_match(
            document,
            main_match,
            generated_block,
        )

    article_match = ARTICLE_OPEN_PATTERN.search(
        document
    )

    if article_match:
        return insert_after_match(
            document,
            article_match,
            generated_block,
        )

    body_match = BODY_OPEN_PATTERN.search(
        document
    )

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

def html_candidates(
    module_dir: Path,
    stem: str,
) -> list[Path]:
    """Zoek gewone en online HTML-versies."""

    paths = [
        module_dir / f"{stem}.html",
        module_dir / f"{stem}.online.html",
    ]

    return [
        path
        for path in paths
        if path.is_file()
    ]


def fallback_html_files(
    module_dir: Path,
) -> list[Path]:
    """Zoek hoofdstukbestanden als index.tex niets oplevert."""

    return [
        path
        for path in sorted(
            module_dir.glob("*.html")
        )
        if path.name != "index.html"
        and not path.name.endswith(".online.html")
    ]


# ============================================================
# ÉÉN HTML-BESTAND VERWERKEN
# ============================================================

def process_html_file(
    html_path: Path,
    template: str,
    theme_number: str,
    theme_title: str,
    chapter_number: int,
    fallback_title: str,
) -> None:
    """Maak en plaats de hero in één hoofdstukbestand."""

    document = read_text(
        html_path
    )

    title = extract_title(
        document=document,
        fallback=fallback_title,
        theme_title=theme_title,
    )

    abstract, abstract_span = extract_abstract(
        document=document,
        title=title,
    )

    hero = create_hero(
        template=template,
        theme_number=theme_number,
        theme_title=theme_title,
        chapter_number=chapter_number,
        chapter_title=title,
        chapter_abstract=abstract,
    )

    if EXISTING_HERO_PATTERN.search(document):
        result = inject_hero(
            document,
            hero,
        )
    else:
        result = remove_old_abstract(
            document,
            abstract_span,
        )

        result = remove_matching_heading(
            result,
            title,
        )

        result = inject_hero(
            result,
            hero,
        )

    result = ensure_hero_stylesheet(
        result
    )

    write_text(
        html_path,
        result,
    )

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
    """Verwerk alle hoofdstukken van één module."""

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

    template = read_text(
        template_path
    )

    theme_number, theme_title = get_theme(
        module_dir
    )

    chapter_order = read_chapter_order(
        course_file
    )

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
            "Waarschuwing: geen activiteiten gevonden in index.tex. "
            "De HTML-bestanden worden alfabetisch verwerkt.",
            file=sys.stderr,
        )

        files = fallback_html_files(
            module_dir
        )

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
            f"Geen hoofdstukbestanden verwerkt in {module_dir}"
        )

    return processed_count


# ============================================================
# COMMANDOLIJN
# ============================================================

def main() -> int:
    """Lees argumenten en verwerk één module."""

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

    module_dir = Path(
        sys.argv[1]
    )

    course_file = Path(
        sys.argv[2]
    )

    template_path = Path(
        sys.argv[3]
    )

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