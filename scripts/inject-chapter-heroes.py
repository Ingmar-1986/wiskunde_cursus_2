
#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import sys
from pathlib import Path


# ============================================================
# CONFIGURATIE
# ============================================================

THEMES: dict[str, tuple[str, str]] = {
    "basiswiskunde": ("1", "Basiswiskunde"),
    "algebra": ("2", "Algebra"),
    "vergelijkingen": ("3", "Vergelijkingen"),
    "functies": ("4", "Functies"),
    "vectoren": ("5", "Vectoren"),
    "coordinaten": ("6", "Coördinaten"),
    "coördinaten": ("6", "Coördinaten"),
    "3d-meetkunde": ("7", "3D-meetkunde"),
    "goniometrie": ("8", "Goniometrie"),
    "logaritmen": ("9", "Logaritmen"),
    "transformaties": ("10", "Transformaties"),
}

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

ACTIVITY_PATTERN = re.compile(
    r"""
    \\(?:activity|include|input)
    (?:\s*\[[^\]]*\])?
    \s*\{
        (?P<path>[^}]+)
    \}
    """,
    re.VERBOSE,
)

TEX_TITLE_PATTERN = re.compile(
    r"\\title\s*\{(?P<title>[^{}]*)\}",
    re.IGNORECASE | re.DOTALL,
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
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def clean_html_text(value: str) -> str:
    value = TAG_PATTERN.sub(" ", value)
    value = html.unescape(value)
    value = WHITESPACE_PATTERN.sub(" ", value)

    return value.strip()


def humanize_slug(value: str) -> str:
    result = value.replace("_", " ").replace("-", " ")
    result = WHITESPACE_PATTERN.sub(" ", result).strip()

    if not result:
        return "Wiskunde"

    return result[0].upper() + result[1:]


def normalize_stem(raw_path: str) -> str:
    value = raw_path.strip().replace("\\", "/")

    if value.endswith(".tex"):
        value = value[:-4]

    return Path(value).name


# ============================================================
# THEMA EN HOOFDSTUKKEN
# ============================================================

def get_theme(module_dir: Path) -> tuple[str, str]:
    module_name = module_dir.name.casefold()

    if module_name in THEMES:
        return THEMES[module_name]

    return "", humanize_slug(module_dir.name)


def read_chapter_order(index_tex: Path) -> list[str]:
    document = read_text(index_tex)
    chapters: list[str] = []

    for match in ACTIVITY_PATTERN.finditer(document):
        stem = normalize_stem(
            match.group("path")
        )

        if not stem:
            continue

        if stem.casefold() in IGNORED_TEX_FILES:
            continue

        if stem not in chapters:
            chapters.append(stem)

    return chapters


# ============================================================
# TITEL UIT TEX
# ============================================================

def extract_title_from_tex(
    module_dir: Path,
    stem: str,
) -> str:
    tex_path = module_dir / f"{stem}.tex"

    if not tex_path.is_file():
        return humanize_slug(stem)

    document = read_text(tex_path)
    match = TEX_TITLE_PATTERN.search(document)

    if not match:
        return humanize_slug(stem)

    title = match.group("title")

    title = re.sub(
        r"\\(?:textbf|textit|emph|textrm|textsf)\s*\{([^{}]*)\}",
        r"\1",
        title,
    )

    title = re.sub(
        r"\\[A-Za-z@]+",
        " ",
        title,
    )

    title = title.replace("{", " ").replace("}", " ")
    title = WHITESPACE_PATTERN.sub(" ", title).strip()

    return title or humanize_slug(stem)


# ============================================================
# ABSTRACT UIT HTML
# ============================================================

def extract_abstract(
    document: str,
    title: str,
) -> tuple[str, tuple[int, int] | None]:
    for pattern in (
        ABSTRACT_CLASS_PATTERN,
        ABSTRACT_PARAGRAPH_PATTERN,
    ):
        match = pattern.search(document)

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
            return abstract, match.span()

    fallback = (
        f"In dit hoofdstuk leer je de belangrijkste begrippen, "
        f"methodes en toepassingen van {title.lower()}."
    )

    return fallback, None


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
    replacements = {
        "THEME_NUMBER": theme_number,
        "THEME_TITLE": theme_title,
        "CHAPTER_NUMBER": str(chapter_number),
        "CHAPTER_TITLE": chapter_title,
        "CHAPTER_ABSTRACT": chapter_abstract,
    }

    result = template

    for placeholder, value in replacements.items():
        result = result.replace(
            "{{" + placeholder + "}}",
            html.escape(value, quote=False),
        )

    return result.strip()


def wrap_hero(hero: str) -> str:
    return (
        "<!-- CHAPTER_HERO_START -->\n"
        f"{hero}\n"
        "<!-- CHAPTER_HERO_END -->"
    )


# ============================================================
# HERO EN CSS INVOEGEN
# ============================================================

def ensure_stylesheet(document: str) -> str:
    if "chapter-hero.css" in document:
        return document

    stylesheet = (
        '    <link rel="stylesheet" '
        'href="../../assets/css/chapter-hero.css">\n'
    )

    match = HEAD_CLOSE_PATTERN.search(document)

    if match:
        return (
            document[:match.start()]
            + stylesheet
            + document[match.start():]
        )

    return stylesheet + document


def insert_after(
    document: str,
    match: re.Match[str],
    content: str,
) -> str:
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
    block = wrap_hero(hero)

    if EXISTING_HERO_PATTERN.search(document):
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
        match = pattern.search(document)

        if match:
            return insert_after(
                document,
                match,
                block,
            )

    return block + "\n" + document


# ============================================================
# BESTAND VERWERKEN
# ============================================================

def process_html_file(
    html_path: Path,
    module_dir: Path,
    stem: str,
    template: str,
    theme_number: str,
    theme_title: str,
    chapter_number: int,
) -> None:
    document = read_text(html_path)

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

    document = ensure_stylesheet(
        document
    )

    write_text(
        html_path,
        document,
    )

    print(
        f"Hero ingevoegd: {html_path} "
        f"(hoofdstuk {chapter_number}: {title})"
    )


# ============================================================
# MODULE VERWERKEN
# ============================================================

def html_candidates(
    module_dir: Path,
    stem: str,
) -> list[Path]:
    candidates = [
        module_dir / f"{stem}.html",
        module_dir / f"{stem}.online.html",
    ]

    return [
        path
        for path in candidates
        if path.is_file()
    ]


def process_module(
    module_dir: Path,
    index_tex: Path,
    template_path: Path,
) -> int:
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

    theme_number, theme_title = get_theme(
        module_dir
    )

    chapter_order = read_chapter_order(
        index_tex
    )

    if not chapter_order:
        raise ValueError(
            f"Geen hoofdstukken gevonden in {index_tex}"
        )

    processed_count = 0

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
                module_dir=module_dir,
                stem=stem,
                template=template,
                theme_number=theme_number,
                theme_title=theme_title,
                chapter_number=chapter_number,
            )

            processed_count += 1

    if processed_count == 0:
        raise ValueError(
            f"Geen HTML-bestanden verwerkt in {module_dir}"
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
    index_tex = Path(sys.argv[2])
    template_path = Path(sys.argv[3])

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
        f"Klaar: {count} hoofdstukbestand(en) verwerkt "
        f"in {module_dir}."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())