#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag


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


# Gegevens voor de modulebanner.
# Pas hier later eenvoudig titel, beschrijving en lesuren aan.
MODULE_INFO = {
    1: {
        "title": "Basiswiskunde",
        "description": (
            "De fundering voor programmeren, 3D, vectoren "
            "en digitale creatie."
        ),
        "lesson_hours": 18,
    },
    2: {
        "title": "Objecten beschrijven",
        "description": (
            "Coördinaten, meetkunde en vergelijkingen gebruiken "
            "om digitale objecten nauwkeurig te beschrijven."
        ),
        "lesson_hours": 24,
    },
    3: {
        "title": "Verbanden modelleren",
        "description": (
            "Functies en modellen gebruiken om verbanden in "
            "digitale toepassingen te begrijpen."
        ),
        "lesson_hours": 30,
    },
    4: {
        "title": "Objecten bewegen en transformeren",
        "description": (
            "Goniometrie, vectoren en transformaties toepassen "
            "op beweging en animatie."
        ),
        "lesson_hours": 28,
    },
    5: {
        "title": "Een digitale wereld creëren",
        "description": (
            "3D-vectoren, matrices en geïntegreerde modellen "
            "gebruiken voor digitale creatie."
        ),
        "lesson_hours": 20,
    },
}


# ============================================================
# REGULIERE EXPRESSIES
# ============================================================

INDEX_ITEM_PATTERN = re.compile(
    r"""
    \\(?:FVDpart|part)\s*\{
        (?P<theme>[^{}]+)
    \}
    |
    \\activity
    (?:\s*\[[^\]]*\])?
    \s*\{
        (?P<path>[^}]+)
    \}
    """,
    re.VERBOSE | re.DOTALL,
)


MODULE_TITLE_PATTERN = re.compile(
    r"""
    \\(?:fvdtitle|title)
    \s*
    \{
        (?P<title>[^{}]*)
    \}
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

MODULE_ABSTRACT_PATTERN = re.compile(
    r"""
    \\begin\s*\{\s*abstract\s*\}
    (?P<abstract>.*?)
    \\end\s*\{\s*abstract\s*\}
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
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
    %\s*FVD_CHAPTER_DATA_END[^\S\r\n]*
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


EXISTING_MODULE_BANNER_PATTERN = re.compile(
    r"""
    <!--\s*MODULE_BANNER_START\s*-->
    .*?
    <!--\s*MODULE_BANNER_END\s*-->
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

COURSE_CONTENT_HEADING_PATTERN = re.compile(
    r"""
    <h(?P<level>[1-6])\b[^>]*>
    (?P<content>.*?Cursusinhoud.*?)
    </h(?P=level)>
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
    """Zet een LaTeX-pad om naar een relatief pad zonder .tex-extensie."""

    value = raw_path.strip().replace(
        "\\",
        "/",
    )

    if value.endswith(".tex"):
        value = value[:-4]

    return value

# ============================================================
# CURSUSSTRUCTUUR UIT INDEX.TEX
# ============================================================

def read_course_structure(
    index_tex: Path,
) -> list[dict[str, str | int]]:
    r"""
    Lees thema's en hoofdstukken uit index.tex.

    Elke \FVDpart{...} of \part{...} start:
    - een nieuw thema;
    - de hoofdstuknummering opnieuw vanaf 1.

    \FVDchapterpair{theorie}{oefeningen} wordt voor deze parser
    omgezet naar één of twee gewone \activity{...}-items.
    Een leeg tweede argument wordt overgeslagen.
    """

    document = read_text(index_tex)

    # Maak \FVDchapterpair begrijpelijk voor de bestaande activity-parser.
    # Theorie en oefeningen blijven aparte online activities.
    document = re.sub(
        r"\\FVDchapterpair\s*"
        r"\{([^{}]*)\}\s*"
        r"\{([^{}]*)\}",
        lambda match: (
            f"\\activity{{{match.group(1).strip()}}}\n"
            + (
                f"\\activity{{{match.group(2).strip()}}}"
                if match.group(2).strip()
                else ""
            )
        ),
        document,
    )

    structure: list[dict[str, str | int]] = []

    current_theme_number = 0
    current_theme_title = ""
    current_chapter_number = 0
    current_theory_number = 0

    for match in INDEX_ITEM_PATTERN.finditer(document):
        theme_title = match.group("theme")
        activity_path = match.group("path")

        if theme_title is not None:
            current_theme_number += 1
            current_theme_title = clean_tex_text(theme_title)
            current_chapter_number = 0
            current_theory_number = 0
            continue

        if activity_path is None:
            continue

        activity_path = activity_path.strip()

        # Deze placeholders komen alleen voor in de macrodefinitie zelf.
        if activity_path in {"#1", "#2"}:
            continue

        stem = normalize_stem(activity_path)

        if not stem:
            continue

        if stem.casefold() in IGNORED_TEX_FILES:
            continue

        if current_theme_number == 0:
            current_theme_number = 1
            current_theme_title = humanize_slug(index_tex.parent.name)
            current_chapter_number = 0

        current_chapter_number += 1

        activity_name = Path(stem).name.casefold()
        is_exercises = (
        activity_name.startswith("oefeningen-")
        or activity_name.endswith("-oefeningen")
        )

        if is_exercises:
            display_number = f"{current_theory_number}.OEF"
            pdf_chapter_number = current_theory_number
        else:
            current_theory_number += 1
            display_number = str(current_theory_number)
            pdf_chapter_number = current_theory_number

        structure.append(
            {
                "stem": stem,
                "theme_number": current_theme_number,
                "theme_title": current_theme_title,
                "chapter_number": current_chapter_number,
                "display_number": display_number,
                "pdf_chapter_number": pdf_chapter_number,
            }
        )

    return structure



def extract_module_metadata(
    index_tex: Path,
    module_dir: Path,
    module_number: int,
) -> tuple[str, str]:
    r"""
    Lees de moduletitel en modulebeschrijving rechtstreeks uit index.tex.

    De titel komt uit:
        \fvdtitle{...}
        of \title{...}

    De beschrijving komt uit:
        \begin{abstract}
        ...
        \end{abstract}

    Alleen wanneer die gegevens ontbreken, wordt MODULE_INFO als reserve gebruikt.
    """

    source = read_text(index_tex)

    title_match = MODULE_TITLE_PATTERN.search(source)
    abstract_match = MODULE_ABSTRACT_PATTERN.search(source)

    fallback_data = MODULE_INFO.get(module_number, {})

    if title_match:
        module_title = clean_tex_text(
            title_match.group("title")
        )
    else:
        module_title = str(
            fallback_data.get(
                "title",
                humanize_slug(module_dir.name),
            )
        )

    if abstract_match:
        module_description = clean_tex_text(
            abstract_match.group("abstract")
        )
    else:
        module_description = str(
            fallback_data.get(
                "description",
                "De wiskundige basis voor digitale creatie.",
            )
        )

    return module_title, module_description


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
        return humanize_slug(stem)

    document = read_text(tex_path)

    match = TEX_TITLE_PATTERN.search(document)

    if not match:
        return humanize_slug(stem)

    title = clean_tex_text(match.group("title"))

    return title or humanize_slug(stem)


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
        "% FVD_CHAPTER_DATA_END\n\n"
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
# OUDE MODULE-INTRO VERWIJDEREN
# ============================================================

def remove_old_module_intro(
    document: str,
    module_number: int,
    module_title: str,
) -> str:
    """
    Verwijder het volledige oude module-introblok boven de nieuwe banner.

    Dit verwijdert onder meer:
    - "MOD1 Basiswiskunde";
    - de titel "Cursusinhoud";
    - de begeleidende zin "Kies hieronder een thema ...".

    De functie werkt generiek voor MOD1, MOD2, MOD3, enzovoort.
    De nieuwe modulebanner en de eigenlijke themakaarten blijven behouden.
    """

    soup = BeautifulSoup(document, "lxml")

    # 1. Verwijder bekende introcontainers volledig.
    for selector in (
        ".module-overview-intro",
        ".course-overview-intro",
        ".xourse-intro",
    ):
        for element in soup.select(selector):
            element.decompose()

    removable_texts = {
        "cursusinhoud",
        (
            "kies hieronder een thema en open het hoofdstuk "
            "waarmee je wilt starten."
        ),
    }

    module_labels = {
        f"mod{module_number} {module_title}".casefold(),
        f"module {module_number} {module_title}".casefold(),
        f"mod {module_number} {module_title}".casefold(),
    }

    # 2. Verwijder losse koppen en tekstregels die samen het oude blok vormen.
    candidates = soup.find_all(
        ["h1", "h2", "h3", "p", "div", "span", "header", "section"]
    )

    for element in candidates:
        if element.parent is None:
            continue

        # Containers met andere structurele onderdelen niet verwijderen.
        if element.find(
            [
                "article",
                "details",
                "nav",
                "footer",
                "main",
            ]
        ):
            continue

        text_value = " ".join(
            element.get_text(" ", strip=True).split()
        )
        folded = text_value.casefold()

        if folded in removable_texts or folded in module_labels:
            element.decompose()
            continue

        # Ondersteun maplabels zoals "MOD1 Basiswiskunde" of "MOD2 ...".
        if re.fullmatch(
            rf"mod(?:ule)?\s*0*{module_number}\s+{re.escape(module_title)}",
            text_value,
            flags=re.IGNORECASE,
        ):
            element.decompose()

    # 3. Verwijder lege wrappers die na bovenstaande bewerking overblijven.
    changed = True

    while changed:
        changed = False

        for element in soup.find_all(["div", "section", "header"]):
            if element.parent is None:
                continue

            classes = " ".join(element.get("class", []))
            element_classes = element.get("class", [])

            # Decoratieve onderdelen van de algemene FVD-header
            # mogen nooit als "lege wrappers" verwijderd worden.
            if any(
                class_name.startswith("fvd-hero__")
                for class_name in element_classes
            ):
                continue

            if "module-banner" in classes:
                continue

            has_visible_text = bool(
                element.get_text(" ", strip=True)
            )

            has_meaningful_child = element.find(
                [
                    "img",
                    "svg",
                    "article",
                    "details",
                    "nav",
                    "footer",
                    "main",
                ]
            )

            if not has_visible_text and has_meaningful_child is None:
                element.decompose()
                changed = True

    return str(soup)


# ============================================================
# MODULEBANNER OPBOUWEN EN INVOEGEN
# ============================================================

def extract_module_number(module_dir: Path) -> int:
    """Lees het modulenummer uit een mapnaam zoals MOD1-Basiswiskunde."""

    match = re.search(
        r"MOD\s*0*(\d+)",
        module_dir.name,
        flags=re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return 1


def create_module_banner(
    template: str,
    module_number: int,
    module_title: str,
    module_description: str,
    lesson_hours: int,
    theme_count: int,
) -> str:
    """Vul de placeholders in module-banner.html."""

    replacements = {
        "MODULE_NUMBER": str(module_number),
        "MODULE_TITLE": module_title,
        "MODULE_DESCRIPTION": module_description,
        "LESSON_HOURS": str(lesson_hours),
        "THEME_COUNT": str(theme_count),
    }

    result = template

    for placeholder, value in replacements.items():
        result = result.replace(
            "{{" + placeholder + "}}",
            html.escape(value, quote=False),
        )

    return result.strip()


def wrap_module_banner(banner: str) -> str:
    """Plaats herkenbare commentaren rond de modulebanner."""

    return (
        "<!-- MODULE_BANNER_START -->\n"
        f"{banner}\n"
        "<!-- MODULE_BANNER_END -->"
    )


def inject_module_banner(
    document: str,
    banner: str,
) -> str:
    """
    Plaats de modulebanner na de volledige Ximera-header/introsectie.

    Een bestaande banner wordt eerst verwijderd, zodat hij ook
    werkelijk naar de juiste positie wordt verplaatst.
    """

    block = wrap_module_banner(
        banner
    )

    # Verwijder eerst een bestaande banner.
    # Anders wordt ze alleen op haar oude, verkeerde plaats vervangen.
    document = EXISTING_MODULE_BANNER_PATTERN.sub(
        "",
        document,
        count=1,
    )

    # Beste invoegpositie: onmiddellijk na de volledige websiteheader.
    # De oude module-intro wordt niet langer gegenereerd, waardoor
    # XIMERA-INTRO-END niet altijd bestaat.
    header_marker = "<!-- XIMERA-HEADER-END -->"

    if header_marker in document:
        return document.replace(
            header_marker,
            header_marker + "\n\n" + block,
            1,
        )

    # Compatibiliteit met oudere pagina's die nog een introblok bevatten.
    intro_marker = "<!-- XIMERA-INTRO-END -->"

    if intro_marker in document:
        return document.replace(
            intro_marker,
            intro_marker + "\n\n" + block,
            1,
        )

    # Reservepositie: vóór de Ximera-preamble.
    preamble_marker = '<div class="preamble">'

    if preamble_marker in document:
        return document.replace(
            preamble_marker,
            block + "\n\n" + preamble_marker,
            1,
        )

    # Laatste noodoplossing: direct na <body>.
    match = BODY_PATTERN.search(
        document
    )

    if match:
        return insert_after(
            document,
            match,
            block,
        )

    return block + "\n" + document

def module_html_candidates(
    module_dir: Path,
) -> list[Path]:
    """Zoek de gewone HTML-versie van de module-index."""

    candidates = [
        module_dir / "index.html",
    ]

    return [
        path
        for path in candidates
        if path.is_file()
    ]
    
def ensure_module_css(
    document: str,
) -> str:
    """Voeg module-banner.css toe als die link nog ontbreekt."""

    if "module-banner.css" in document:
        return document

    match = HEAD_CLOSE_PATTERN.search(
        document
    )

    if not match:
        return document

    css_link = (
        '  <link rel="stylesheet" '
        'href="../../assets/css/module-banner.css">\n'
    )

    position = match.start()

    return (
        document[:position]
        + css_link
        + document[position:]
    )
def process_module_banner(
    module_dir: Path,
    index_tex: Path,
    template_path: Path,
    course_structure: list[dict[str, str | int]],
) -> int:
    """Plaats de modulebanner in de module-overzichtspagina."""

    if not template_path.is_file():
        raise ValueError(
            f"Modulebanner-template niet gevonden: {template_path}"
        )

    candidates = module_html_candidates(module_dir)

    if not candidates:
        print(
            f"Waarschuwing: geen index.html gevonden in {module_dir}",
            file=sys.stderr,
        )
        return 0

    module_number = extract_module_number(module_dir)
    module_data = MODULE_INFO.get(module_number, {})

    module_title, module_description = extract_module_metadata(
        index_tex=index_tex,
        module_dir=module_dir,
        module_number=module_number,
    )

    lesson_hours = int(
        module_data.get("lesson_hours", 0)
    )
    theme_count = len(
        {int(item["theme_number"]) for item in course_structure}
    )

    template = read_text(template_path)
    banner = create_module_banner(
        template=template,
        module_number=module_number,
        module_title=module_title,
        module_description=module_description,
        lesson_hours=lesson_hours,
        theme_count=theme_count,
    )

    processed_count = 0

    for html_path in candidates:
        document = read_text(html_path)

        document = remove_old_module_intro(
            document=document,
            module_number=module_number,
            module_title=module_title,
        )

        document = inject_module_banner(
            document,
            banner,
        )

        document = ensure_module_css(
            document
        )

        write_text(
            html_path,
            document,
        )

        print(
            f"Modulebanner ingevoegd: {html_path} "
            f"(module {module_number}: {module_title})"
        )
        processed_count += 1

    return processed_count


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
    "exercise-hero.css",
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
    """Zoek de gewone HTML-versie."""

    candidates = [
        module_dir / f"{stem}.html",
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
    module_template_path: Path,
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

    processed_module_count = process_module_banner(
        module_dir=module_dir,
        index_tex=index_tex,
        template_path=module_template_path,
        course_structure=course_structure,
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
        
        display_number = str(
            item["display_number"]
        )
        
        pdf_chapter_number = int(
            item["pdf_chapter_number"]
        )

        # ----------------------------------------------------
        # TEX: PDF-METADATA BIJWERKEN
        # ----------------------------------------------------

        tex_path = module_dir / f"{stem}.tex"

        process_tex_file(
            tex_path=tex_path,
            theme_number=theme_number,
            theme_title=theme_title,
            chapter_number=pdf_chapter_number,
        )

        processed_tex_count += 1

        # ----------------------------------------------------
        # HTML-HERO
        # ----------------------------------------------------
        # Wordt volledig beheerd door enhance-chapter.py.
        # Hier niets meer injecteren om dubbele hero's te vermijden.

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

    print(
        f"Modulebanner bijgewerkt in "
        f"{processed_module_count} HTML-bestand(en)."
    )

    return (
        processed_tex_count
        + processed_html_count
        + processed_module_count
    )


# ============================================================
# COMMANDOLIJN
# ============================================================

def main() -> int:
    """Lees argumenten en verwerk één module."""

    if len(sys.argv) != 5:
        print(
            "Gebruik:\n"
            "  python3 scripts/inject-chapter-heroes.py "
            "<modulemap> <index.tex> <chapter-hero.html> "
            "<module-banner.html>\n\n"
            "Voorbeeld:\n"
            "  python3 scripts/inject-chapter-heroes.py "
            "modules/basiswiskunde "
            "modules/basiswiskunde/index.tex "
            "assets/html/chapter-hero.html "
            "assets/html/module-banner.html",
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

    module_template_path = Path(
        sys.argv[4]
    )

    try:
        count = process_module(
            module_dir=module_dir,
            index_tex=index_tex,
            template_path=template_path,
            module_template_path=module_template_path,
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