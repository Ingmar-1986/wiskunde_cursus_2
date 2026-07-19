#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import sys
from pathlib import Path


# ============================================================
# CONFIGURATIE
# ============================================================

IGNORED_TEX_FILES = {
    "index",
    "preamble",
    "header",
    "footer",
    "macros",
    "commands",
}


# ============================================================
# REGULIERE EXPRESSIES
# ============================================================

INDEX_ITEM_PATTERN = re.compile(
    r"""
    \\part\s*\{
        (?P<theme>[^{}]+)
    \}
    |
    \\(?:activity|include|input)
    (?:\s*\[[^\]]*\])?
    \s*\{
        (?P<path>[^}]+)
    \}
    """,
    re.VERBOSE | re.DOTALL,
)

TEX_TITLE_PATTERN = re.compile(
    r"""
    \\title
    \s*
    \{
        (?P<title>[^{}]*)
    \}
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

CHAPTER_DATA_PATTERN = re.compile(
    r"""
    %\s*FVD_CHAPTER_DATA_START\s*
    .*?
    %\s*FVD_CHAPTER_DATA_END\s*
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

DOCUMENT_PATTERN = re.compile(
    r"""
    \\begin\s*\{\s*document\s*\}
    """,
    re.IGNORECASE | re.VERBOSE,
)

EXISTING_HERO_PATTERN = re.compile(
    r"""
    <!--\s*CHAPTER_HERO_START\s*-->
    .*?
    <!--\s*CHAPTER_HERO_END\s*-->
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

ABSTRACT_CLASS_PATTERN = re.compile(
    r"""
    <(?P<tag>div|section|p)\b
    (?=[^>]*class=["'][^"']*\babstract\b[^"']*["'])
    [^>]*>
    (?P<content>.*?)
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
    (?P<content>.*?)
    </p>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

MAIN_PATTERN = re.compile(
    r"<main\b[^>]*>",
    re.IGNORECASE,
)

ARTICLE_PATTERN = re.compile(
    r"<article\b[^>]*>",
    re.IGNORECASE,
)

BODY_PATTERN = re.compile(
    r"<body\b[^>]*>",
    re.IGNORECASE,
)

HEAD_CLOSE_PATTERN = re.compile(
    r"</head>",
    re.IGNORECASE,
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

    return path.read_text(
        encoding="utf-8"
    )


def write_text(
    path: Path,
    content: str,
) -> None:
    """Schrijf een UTF-8-bestand."""

    path.write_text(
        content,
        encoding="utf-8",
    )


def clean_html_text(value: str) -> str:
    """Verwijder HTML-tags en normaliseer witruimte."""

    value = TAG_PATTERN.sub(
        " ",
        value,
    )

    value = html.unescape(
        value
    )

    value = WHITESPACE_PATTERN.sub(
        " ",
        value,
    )

    return value.strip()


def clean_tex_text(value: str) -> str:
    """Verwijder eenvoudige LaTeX-opmaak uit een titel."""

    value = re.sub(
        r"""
        \\(?:textbf|textit|emph|textrm|textsf)
        \s*
        \{
            ([^{}]*)
        \}
        """,
        r"\1",
        value,
        flags=re.VERBOSE,
    )

    value = re.sub(
        r"\\[A-Za-z@]+",
        " ",
        value,
    )

    value = value.replace(
        "{",
        " ",
    ).replace(
        "}",
        " ",
    )

    value = WHITESPACE_PATTERN.sub(
        " ",
        value,
    )

    return value.strip()


def humanize_slug(value: str) -> str:
    """Zet een bestandsnaam om naar een leesbare titel."""

    result = value.replace(
        "_",
        " ",
    ).replace(
        "-",
        " ",
    )

    result = WHITESPACE_PATTERN.sub(
        " ",
        result,
    ).strip()

    if not result:
        return "Wiskunde"

    return result[0].upper() + result[1:]


def normalize_stem(raw_path: str) -> str:
    """Zet een LaTeX-pad om naar een bestandsstam."""

    value = raw_path.strip().replace(
        "\\",
        "/",
    )

    if value.endswith(".tex"):
        value = value[:-4]

    return Path(value).name


# ============================================================
# CURSUSSTRUCTUUR UIT INDEX.TEX
# ============================================================

def read_course_structure(
    index_tex: Path,
) -> list[dict[str, str | int]]:
    """
    Lees thema's en hoofdstukken uit index.tex.

    Elke \\part{...} start:
    - een nieuw thema;
    - de hoofdstuknummering opnieuw vanaf 1.
    """

    document = read_text(
        index_tex
    )

    structure: list[dict[str, str | int]] = []

    current_theme_number = 0
    current_theme_title = ""
    current_chapter_number = 0

    for match in INDEX_ITEM_PATTERN.finditer(
        document
    ):
        theme_title = match.group(
            "theme"
        )

        activity_path = match.group(
            "path"
        )

        if theme_title is not None:
            current_theme_number += 1

            current_theme_title = clean_tex_text(
                theme_title
            )

            current_chapter_number = 0

            continue

        if activity_path is None:
            continue

        stem = normalize_stem(
            activity_path
        )

        if not stem:
            continue

        if stem.casefold() in IGNORED_TEX_FILES:
            continue

        if current_theme_number == 0:
            current_theme_number = 1

            current_theme_title = humanize_slug(
                index_tex.parent.name
            )

            current_chapter_number = 0

        current_chapter_number += 1

        structure.append(
            {
                "stem": stem,
                "theme_number": current_theme_number,
                "theme_title": current_theme_title,
                "chapter_number": current_chapter_number,
            }
        )

    return structure


# ============================================================
# TITEL UIT TEX
# ============================================================

def extract_title_from_tex(
    module_dir: Path,
    stem: str,
) -> str:
    """Lees de hoofdstuktitel uit het bijbehorende TeX-bestand."""

    tex_path = module_dir / f"{stem}.tex"

    if not tex_path.is_file():
        return humanize_slug(
            stem
        )

    document = read_text(
        tex_path
    )

    match = TEX_TITLE_PATTERN.search(
        document
    )

    if not match:
        return humanize_slug(
            stem
        )

    title = clean_tex_text(
        match.group("title")
    )

    return title or humanize_slug(
        stem
    )


# ============================================================
# PDF-HOOFDSTUKGEGEVENS IN TEX
# ============================================================

def escape_tex_argument(value: str) -> str:
    """
    Maak gewone tekst veilig genoeg voor gebruik als argument
    van \\fvdchapterdata.

    Bestaande LaTeX-commando's in de thematitel blijven behouden.
    Alleen tekens die de argumentstructuur kunnen verstoren,
    worden beschermd.
    """

    return (
        value
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("&", r"\&")
    )


def create_chapter_data_block(
    theme_number: int,
    theme_title: str,
    chapter_number: int,
) -> str:
    """Maak het automatisch beheerde PDF-metadatablok."""

    safe_theme_title = escape_tex_argument(
        theme_title
    )

    return (
        "% FVD_CHAPTER_DATA_START\n"
        "% Automatisch gegenereerd uit index.tex.\n"
        "% Niet handmatig aanpassen.\n"
        "\\fvdchapterdata"
        f"{{{theme_number}}}"
        f"{{{safe_theme_title}}}"
        f"{{{chapter_number}}}\n"
        "% FVD_CHAPTER_DATA_END"
    )


def inject_chapter_data(
    document: str,
    block: str,
) -> str:
    """
    Vervang bestaande hoofdstukmetadata of voeg ze toe.

    Het blok wordt bij voorkeur direct na \\begin{document}
    geplaatst. Daardoor is Opmaak.tex al geladen en bestaat
    \\fvdchapterdata zeker.
    """

    if CHAPTER_DATA_PATTERN.search(
        document
    ):
        return CHAPTER_DATA_PATTERN.sub(
            lambda _match: block,
            document,
            count=1,
        )

    match = DOCUMENT_PATTERN.search(
        document
    )

    if not match:
        raise ValueError(
            "Geen \\begin{document} gevonden."
        )

    position = match.end()

    return (
        document[:position]
        + "\n\n"
        + block
        + "\n"
        + document[position:]
    )


def process_tex_file(
    tex_path: Path,
    theme_number: int,
    theme_title: str,
    chapter_number: int,
) -> None:
    """Plaats of actualiseer de PDF-hoofdstukgegevens."""

    if not tex_path.is_file():
        raise ValueError(
            f"Hoofdstukbestand niet gevonden: {tex_path}"
        )

    document = read_text(
        tex_path
    )

    block = create_chapter_data_block(
        theme_number=theme_number,
        theme_title=theme_title,
        chapter_number=chapter_number,
    )

    updated_document = inject_chapter_data(
        document,
        block,
    )

    if updated_document != document:
        write_text(
            tex_path,
            updated_document,
        )

        print(
            f"PDF-gegevens bijgewerkt: {tex_path} "
            f"(thema {theme_number}; hoofdstuk {chapter_number})"
        )
    else:
        print(
            f"PDF-gegevens zijn actueel: {tex_path}"
        )

# ============================================================
# ABSTRACT UIT HTML
# ============================================================

def extract_abstract(
    document: str,
    title: str,
) -> tuple[str, tuple[int, int] | None]:
    """
    Zoek het abstract in de gegenereerde HTML.

    Geeft ook de positie terug, zodat de oude losse abstracttekst
    verwijderd kan worden.
    """

    for pattern in (
        ABSTRACT_CLASS_PATTERN,
        ABSTRACT_PARAGRAPH_PATTERN,
    ):
        match = pattern.search(
            document
        )

        if not match:
            continue

        abstract = clean_html_text(
            match.group("content")
        )

        abstract = re.sub(
            r"^\s*Abstract\.?\s*",
            "",
            abstract,
            flags=re.IGNORECASE,
        ).strip()

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
    theme_number: int,
    theme_title: str,
    chapter_number: int,
    chapter_title: str,
    chapter_abstract: str,
) -> str:
    """Vul de placeholders in chapter-hero.html."""

    replacements = {
        "THEME_NUMBER": str(
            theme_number
        ),
        "THEME_TITLE": theme_title,
        "CHAPTER_NUMBER": str(
            chapter_number
        ),
        "CHAPTER_TITLE": chapter_title,
        "CHAPTER_ABSTRACT": chapter_abstract,
    }

    result = template

    for placeholder, value in replacements.items():
        result = result.replace(
            "{{" + placeholder + "}}",
            html.escape(
                value,
                quote=False,
            ),
        )

    return result.strip()


def wrap_hero(hero: str) -> str:
    """Plaats herkenbare commentaren rond de hero."""

    return (
        "<!-- CHAPTER_HERO_START -->\n"
        f"{hero}\n"
        "<!-- CHAPTER_HERO_END -->"
    )


# ============================================================
# CSS EN HERO INVOEGEN
# ============================================================

def ensure_chapter_css(document: str) -> str:
    """
    Voeg de CSS voor de chapter hero en pedagogische blokken toe
    als die nog ontbreken.
    """

    css_files = [
        "chapter-hero.css",
        "learning-boxes.css",
    ]

    missing_links = []

    for css_file in css_files:
        if css_file not in document:
            missing_links.append(
                f'  <link rel="stylesheet" '
                f'href="../../assets/css/{css_file}">\n'
            )

    if not missing_links:
        return document

    return document.replace(
        "</head>",
        "".join(missing_links) + "</head>",
        1,
    )

def insert_after(
    document: str,
    match: re.Match[str],
    content: str,
) -> str:
    """Plaats content direct na een gevonden HTML-element."""

    position = match.end()

    return (
        document[:position]
        + "\n"
        + content
        + "\n"
        + document[position:]
    )


def inject_hero(
    document: str,
    hero: str,
) -> str:
    """Vervang een bestaande hero of voeg een nieuwe hero toe."""

    block = wrap_hero(
        hero
    )

    if EXISTING_HERO_PATTERN.search(
        document
    ):
        return EXISTING_HERO_PATTERN.sub(
            lambda _match: block,
            document,
            count=1,
        )

    for pattern in (
        MAIN_PATTERN,
        ARTICLE_PATTERN,
        BODY_PATTERN,
    ):
        match = pattern.search(
            document
        )

        if match:
            return insert_after(
                document,
                match,
                block,
            )

    return block + "\n" + document


# ============================================================
# HTML-BESTAND VERWERKEN
# ============================================================

def process_html_file(
    html_path: Path,
    module_dir: Path,
    stem: str,
    template: str,
    theme_number: int,
    theme_title: str,
    chapter_number: int,
) -> None:
    """Maak en plaats de hero in één hoofdstukbestand."""

    document = read_text(
        html_path
    )

    title = extract_title_from_tex(
        module_dir,
        stem,
    )

    abstract, abstract_span = extract_abstract(
        document,
        title,
    )

    if abstract_span is not None:
        start, end = abstract_span

        document = (
            document[:start]
            + document[end:]
        )

    hero = create_hero(
        template=template,
        theme_number=theme_number,
        theme_title=theme_title,
        chapter_number=chapter_number,
        chapter_title=title,
        chapter_abstract=abstract,
    )

    document = inject_hero(
        document,
        hero,
    )

    document = ensure_chapter_css(
        document
    )

    write_text(
        html_path,
        document,
    )

    print(
        f"Hero ingevoegd: {html_path} "
        f"(thema {theme_number}: {theme_title}; "
        f"hoofdstuk {chapter_number}: {title})"
    )


# ============================================================
# HTML-BESTANDEN ZOEKEN
# ============================================================

def html_candidates(
    module_dir: Path,
    stem: str,
) -> list[Path]:
    """Zoek de gewone en online HTML-versie."""

    candidates = [
        module_dir / f"{stem}.html",
        module_dir / f"{stem}.online.html",
    ]

    return [
        path
        for path in candidates
        if path.is_file()
    ]


# ============================================================
# MODULE VERWERKEN
# ============================================================

def process_module(
    module_dir: Path,
    index_tex: Path,
    template_path: Path,
) -> int:
    """
    Verwerk alle hoofdstukken van één module.

    Voor ieder hoofdstuk:
    - werk de PDF-metadata in het TeX-bestand bij;
    - werk de hero in bestaande HTML-bestanden bij.
    """

    if not module_dir.is_dir():
        raise ValueError(
            f"Modulemap niet gevonden: {module_dir}"
        )

    if not index_tex.is_file():
        raise ValueError(
            f"index.tex niet gevonden: {index_tex}"
        )

    if not template_path.is_file():
        raise ValueError(
            f"Hero-template niet gevonden: {template_path}"
        )

    template = read_text(
        template_path
    )

    course_structure = read_course_structure(
        index_tex
    )

    if not course_structure:
        raise ValueError(
            f"Geen thema's of hoofdstukken gevonden in {index_tex}"
        )

    processed_tex_count = 0
    processed_html_count = 0

    for item in course_structure:
        stem = str(
            item["stem"]
        )

        theme_number = int(
            item["theme_number"]
        )

        theme_title = str(
            item["theme_title"]
        )

        chapter_number = int(
            item["chapter_number"]
        )

        # ----------------------------------------------------
        # TEX: PDF-METADATA BIJWERKEN
        # ----------------------------------------------------

        tex_path = module_dir / f"{stem}.tex"

        process_tex_file(
            tex_path=tex_path,
            theme_number=theme_number,
            theme_title=theme_title,
            chapter_number=chapter_number,
        )

        processed_tex_count += 1

        # ----------------------------------------------------
        # HTML: HERO BIJWERKEN
        # ----------------------------------------------------

        candidates = html_candidates(
            module_dir,
            stem,
        )

        if not candidates:
            print(
                f"Waarschuwing: geen HTML gevonden voor "
                f"thema {theme_number}, hoofdstuk "
                f"{chapter_number}: {stem}",
                file=sys.stderr,
            )

            continue

        for html_path in candidates:
            process_html_file(
                html_path=html_path,
                module_dir=module_dir,
                stem=stem,
                template=template,
                theme_number=theme_number,
                theme_title=theme_title,
                chapter_number=chapter_number,
            )

            processed_html_count += 1

    if processed_tex_count == 0:
        raise ValueError(
            f"Geen hoofdstukbestanden verwerkt in {module_dir}"
        )

    print()
    print(
        f"PDF-metadata bijgewerkt in "
        f"{processed_tex_count} TeX-bestand(en)."
    )

    print(
        f"HTML-hero bijgewerkt in "
        f"{processed_html_count} HTML-bestand(en)."
    )

    return processed_tex_count + processed_html_count


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

    index_tex = Path(
        sys.argv[2]
    )

    template_path = Path(
        sys.argv[3]
    )

    try:
        count = process_module(
            module_dir=module_dir,
            index_tex=index_tex,
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
        f"Klaar: {count} bewerking(en) uitgevoerd "
        f"in {module_dir}."
    )
    
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )