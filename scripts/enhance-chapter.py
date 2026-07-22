#!/usr/bin/env python3

from __future__ import annotations

import html
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, Comment, NavigableString, Tag


# ============================================================
# MODELLEN
# ============================================================


@dataclass
class Chapter:
    activity: str
    theme: str
    theme_number: int
    chapter_number: int
    tex_file: Path
    source_html_file: Path
    output_html_file: Path
    title: str
    abstract: str

    @property
    def number(self) -> str:
        return f"{self.theme_number}.{self.chapter_number}"

    @property
    def url(self) -> str:
        return self.output_html_file.name


@dataclass
class Module:
    directory: Path
    index_file: Path
    title: str
    chapters: list[Chapter]


# ============================================================
# ALGEMENE HULPFUNCTIES
# ============================================================


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    """
    Schrijf UTF-8 veilig via een tijdelijk bestand.

    De uiteindelijke uitvoer wordt pas vervangen nadat het tijdelijke
    bestand volledig is geschreven. Wanneer een bestaand doelbestand
    door Docker als root werd aangemaakt, geeft deze functie een duidelijke
    foutmelding. Het buildscript hoort zulke gewone .html-bestanden vooraf
    te verwijderen; de .online.html-bestanden blijven als bron behouden.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_name(f".{path.name}.tmp")

    try:
        temporary_path.write_text(content, encoding="utf-8")
        temporary_path.replace(path)

    except PermissionError as error:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise PermissionError(
            f"Geen schrijfrechten voor {path}. "
            "Het doelbestand is vermoedelijk door Docker als root aangemaakt. "
            "Verwijder eerst alleen de gewone hoofdstuk-HTML-bestanden; "
            "behoud de .online.html-bestanden als bron."
        ) from error

    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def remove_latex_comments(source: str) -> str:
    """
    Verwijdert LaTeX-commentaar, maar behoudt escaped procenttekens zoals \\%.
    """
    cleaned_lines: list[str] = []

    for line in source.splitlines():
        result: list[str] = []
        escaped = False

        for character in line:
            if character == "%" and not escaped:
                break

            result.append(character)

            if character == "\\":
                escaped = not escaped
            else:
                escaped = False

        cleaned_lines.append("".join(result))

    return "\n".join(cleaned_lines)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_latex_text(value: str) -> str:
    """
    Zet eenvoudige LaTeX-tekst om naar leesbare tekst voor HTML-metadata.
    Dit is niet bedoeld als volledige LaTeX-parser.
    """
    value = value.strip()

    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\#": "#",
        r"\_": "_",
        r"\{": "{",
        r"\}": "}",
        r"\ldots": "…",
        r"\dots": "…",
        r"\textendash": "–",
        r"\textemdash": "—",
        "~": " ",
        "---": "—",
        "--": "–",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    formatting_commands = (
        "textbf",
        "textit",
        "emph",
        "mathrm",
        "mathbf",
        "mathit",
        "textrm",
        "textsf",
        "texttt",
        "mbox",
    )

    previous = None

    while previous != value:
        previous = value

        for command in formatting_commands:
            value = re.sub(
                rf"\\{command}\s*\{{([^{{}}]*)\}}",
                r"\1",
                value,
            )

    value = re.sub(r"\\url\s*\{([^{}]*)\}", r"\1", value)
    value = re.sub(r"\\href\s*\{[^{}]*\}\s*\{([^{}]*)\}", r"\1", value)

    value = value.replace(r"\(", "")
    value = value.replace(r"\)", "")
    value = value.replace(r"\[", "")
    value = value.replace(r"\]", "")
    value = value.replace("$", "")

    value = re.sub(r"\\[a-zA-Z@]+\*?", "", value)
    value = value.replace("{", "").replace("}", "")

    return normalize_whitespace(value)


def extract_braced_argument(
    source: str,
    command_names: Iterable[str],
) -> str | None:
    """
    Leest het eerste accolade-argument van een LaTeX-commando.

    Voorbeelden:
        \title{Rekenen}
        \fvdtitle{Basiswiskunde}
    """
    command_pattern = "|".join(re.escape(name) for name in command_names)

    match = re.search(
        rf"\\(?:{command_pattern})\s*\{{",
        source,
    )

    if not match:
        return None

    start = match.end()
    depth = 1
    position = start

    while position < len(source):
        character = source[position]

        if character == "\\":
            position += 2
            continue

        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1

            if depth == 0:
                return source[start:position]

        position += 1

    return None


def extract_environment(source: str, environment: str) -> str | None:
    pattern = re.compile(
        rf"\\begin\s*\{{{re.escape(environment)}\}}"
        rf"(?P<content>.*?)"
        rf"\\end\s*\{{{re.escape(environment)}\}}",
        re.DOTALL,
    )

    match = pattern.search(source)

    if not match:
        return None

    return match.group("content").strip()


def fallback_title(activity: str) -> str:
    name = Path(activity).name
    name = name.replace("-", " ").replace("_", " ")
    name = normalize_whitespace(name)

    if not name:
        return "Hoofdstuk"

    return name[:1].upper() + name[1:]


def relative_web_path(from_directory: Path, target: Path) -> str:
    relative = os.path.relpath(target, start=from_directory)
    return Path(relative).as_posix()


# ============================================================
# LATEX EN MODULESTRUCTUUR
# ============================================================


def resolve_tex_file(module_dir: Path, activity: str) -> Path:
    activity = activity.strip()
    activity_path = Path(activity)

    candidates: list[Path] = []

    if activity_path.suffix == ".tex":
        candidates.append(module_dir / activity_path)
    else:
        candidates.extend(
            [
                module_dir / f"{activity}.tex",
                module_dir / activity / f"{activity_path.name}.tex",
                module_dir / activity / "index.tex",
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    # Geef een logisch verwacht pad terug voor de foutmelding.
    return candidates[0]


def activity_base_path(activity: str) -> str:
    activity = activity.strip().replace("\\", "/")

    if activity.endswith(".tex"):
        activity = activity[:-4]

    if activity.endswith("/index"):
        activity = activity[:-6]

    return activity


def resolve_html_files(
    module_dir: Path,
    activity: str,
) -> tuple[Path, Path]:
    base = activity_base_path(activity)

    output_file = module_dir / f"{base}.html"
    online_file = module_dir / f"{base}.online.html"

    # De online-versie is de voorkeur omdat die telkens een schone bron is.
    if online_file.is_file():
        source_file = online_file
    else:
        source_file = output_file

    return source_file, output_file


def extract_chapter_metadata(
    tex_file: Path,
    activity: str,
) -> tuple[str, str]:
    if not tex_file.is_file():
        return fallback_title(activity), ""

    source = remove_latex_comments(read_text(tex_file))

    title_raw = extract_braced_argument(
        source,
        (
            "title",
            "fvdtitle",
            "activitytitle",
            "chaptertitle",
        ),
    )

    title = (
        clean_latex_text(title_raw)
        if title_raw
        else fallback_title(activity)
    )

    abstract_raw = extract_environment(source, "abstract")

    if abstract_raw:
        abstract = clean_latex_text(abstract_raw)
    else:
        abstract_command = extract_braced_argument(
            source,
            (
                "abstract",
                "fvdabstract",
                "chapterabstract",
            ),
        )

        abstract = (
            clean_latex_text(abstract_command)
            if abstract_command
            else ""
        )

    return title, abstract


def parse_module(module_dir: Path) -> Module:
    index_file = module_dir / "index.tex"

    if not index_file.is_file():
        raise FileNotFoundError(
            f"index.tex werd niet gevonden: {index_file}"
        )

    source = remove_latex_comments(read_text(index_file))

    module_title_raw = extract_braced_argument(
        source,
        (
            "fvdtitle",
            "title",
        ),
    )

    module_title = (
        clean_latex_text(module_title_raw)
        if module_title_raw
        else fallback_title(module_dir.name)
    )

    token_pattern = re.compile(
        r"""
        \\(?:FVDpart|part)\s*\{(?P<part>[^{}]*)\}
        |
        \\activity\s*\{(?P<activity>[^{}]*)\}
        """,
        re.VERBOSE,
    )

    chapters: list[Chapter] = []

    current_theme = "Inleiding"
    theme_number = 0
    chapter_number = 0

    for match in token_pattern.finditer(source):
        part = match.group("part")
        activity = match.group("activity")

        if part is not None:
            theme_number += 1
            chapter_number = 0
            current_theme = clean_latex_text(part)
            continue

        if activity is None:
            continue

        if theme_number == 0:
            theme_number = 1

        chapter_number += 1
        activity = activity.strip()

        tex_file = resolve_tex_file(module_dir, activity)
        source_html_file, output_html_file = resolve_html_files(
            module_dir,
            activity,
        )

        title, abstract = extract_chapter_metadata(
            tex_file,
            activity,
        )

        chapters.append(
            Chapter(
                activity=activity_base_path(activity),
                theme=current_theme,
                theme_number=theme_number,
                chapter_number=chapter_number,
                tex_file=tex_file,
                source_html_file=source_html_file,
                output_html_file=output_html_file,
                title=title,
                abstract=abstract,
            )
        )

    if not chapters:
        raise ValueError(
            f"Geen \\activity{{...}} gevonden in {index_file}"
        )

    return Module(
        directory=module_dir,
        index_file=index_file,
        title=module_title,
        chapters=chapters,
    )


# ============================================================
# TEMPLATES
# ============================================================


class TemplateLoader:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.template_dir = project_root / "assets" / "html"

    def path(self, filename: str) -> Path:
        return self.template_dir / filename

    def load(self, filename: str) -> str:
        path = self.path(filename)

        if not path.is_file():
            raise FileNotFoundError(
                f"Template werd niet gevonden: {path}"
            )

        return read_text(path)

    def render(
        self,
        filename: str,
        replacements: dict[str, str],
    ) -> str:
        content = self.load(filename)

        for placeholder, value in replacements.items():
            content = content.replace(
                "{{" + placeholder + "}}",
                value,
            )

        return content


def parse_fragment(fragment_html: str) -> list[Tag | NavigableString]:
    fragment_soup = BeautifulSoup(fragment_html, "html.parser")
    return list(fragment_soup.contents)


def append_fragment(parent: Tag, fragment_html: str) -> None:
    for node in parse_fragment(fragment_html):
        parent.append(node)


def insert_fragment(
    parent: Tag,
    position: int,
    fragment_html: str,
) -> int:
    nodes = parse_fragment(fragment_html)

    for offset, node in enumerate(nodes):
        parent.insert(position + offset, node)

    return len(nodes)


# ============================================================
# DOCUMENTBEWERKING
# ============================================================


def ensure_document_structure(soup: BeautifulSoup) -> tuple[Tag, Tag]:
    if soup.html is None:
        html_tag = soup.new_tag("html")

        existing = list(soup.contents)

        for node in existing:
            html_tag.append(node.extract())

        soup.append(html_tag)

    if soup.head is None:
        head = soup.new_tag("head")
        soup.html.insert(0, head)

    if soup.body is None:
        body = soup.new_tag("body")

        movable = [
            node
            for node in list(soup.html.contents)
            if node is not soup.head
        ]

        for node in movable:
            body.append(node.extract())

        soup.html.append(body)

    return soup.head, soup.body


def ensure_stylesheet(
    soup: BeautifulSoup,
    head: Tag,
    href: str,
) -> None:
    for link in head.find_all("link", href=True):
        if link.get("href") == href:
            return

    link = soup.new_tag("link")
    link["rel"] = "stylesheet"
    link["href"] = href
    link["media"] = "screen"

    head.append(link)


def ensure_script(
    soup: BeautifulSoup,
    body: Tag,
    src: str,
) -> None:
    for script in soup.find_all("script", src=True):
        if script.get("src") == src:
            return

    script = soup.new_tag("script")
    script["src"] = src
    body.append(script)


def set_document_title(
    soup: BeautifulSoup,
    head: Tag,
    chapter: Chapter,
    module_title: str,
) -> None:
    title_text = f"{chapter.title} – {module_title}"

    if soup.title is None:
        title_tag = soup.new_tag("title")
        title_tag.string = title_text
        head.append(title_tag)
    else:
        soup.title.string = title_text


def extract_body_content(body: Tag) -> tuple[list, list[Tag]]:
    """
    Verplaatst de oorspronkelijke Ximera-inhoud later naar chapter-body.

    Scripts blijven buiten de inhoud en worden onderaan opnieuw geplaatst.
    """
    content_nodes: list = []
    script_nodes: list[Tag] = []

    for node in list(body.contents):
        extracted = node.extract()

        if isinstance(extracted, Tag) and extracted.name == "script":
            script_nodes.append(extracted)
        else:
            content_nodes.append(extracted)

    return content_nodes, script_nodes


def make_menu_button(soup: BeautifulSoup) -> Tag:
    button = soup.new_tag("button")
    button["class"] = ["course-menu-button"]
    button["id"] = "courseMenuButton"
    button["type"] = "button"
    button["aria-controls"] = "courseSidebar"
    button["aria-expanded"] = "false"
    button.string = "☰ Toon cursusinhoud"

    return button


def make_sidebar_overlay(soup: BeautifulSoup) -> Tag:
    overlay = soup.new_tag("div")
    overlay["class"] = ["course-sidebar-overlay"]
    overlay["id"] = "courseSidebarOverlay"

    return overlay


def mark_active_sidebar_link(
    sidebar_html: str,
    chapter: Chapter,
) -> str:
    sidebar_soup = BeautifulSoup(sidebar_html, "html.parser")

    current_names = {
        chapter.url,
        f"./{chapter.url}",
        chapter.activity,
        f"{chapter.activity}.html",
    }

    active_link: Tag | None = None

    for link in sidebar_soup.find_all("a", href=True):
        href = str(link.get("href", "")).strip()

        if href in current_names or Path(href).name == chapter.url:
            active_link = link
            break

    if active_link is not None:
        classes = list(active_link.get("class", []))

        if "is-active" not in classes:
            classes.append("is-active")

        active_link["class"] = classes
        active_link["aria-current"] = "page"

        section = active_link.find_parent(class_="course-section")

        if section is not None:
            section_classes = list(section.get("class", []))

            if "is-open" not in section_classes:
                section_classes.append("is-open")

            section["class"] = section_classes

            toggle = section.find(
                class_="course-section-toggle"
            )

            if toggle is not None:
                toggle["aria-expanded"] = "true"

    return str(sidebar_soup)


def render_previous_next(
    loader: TemplateLoader,
    module: Module,
    chapter_index: int,
) -> str:
    chapter = module.chapters[chapter_index]

    previous = (
        module.chapters[chapter_index - 1]
        if chapter_index > 0
        else None
    )

    next_chapter = (
        module.chapters[chapter_index + 1]
        if chapter_index + 1 < len(module.chapters)
        else None
    )

    replacements = {
        "PREVIOUS_URL": (
            html.escape(previous.url, quote=True)
            if previous
            else "#"
        ),
        "PREVIOUS_TITLE": (
            html.escape(previous.title)
            if previous
            else ""
        ),
        "HAS_PREVIOUS": "true" if previous else "false",
        "NEXT_URL": (
            html.escape(next_chapter.url, quote=True)
            if next_chapter
            else "#"
        ),
        "NEXT_TITLE": (
            html.escape(next_chapter.title)
            if next_chapter
            else ""
        ),
        "HAS_NEXT": "true" if next_chapter else "false",
        "OVERVIEW_URL": "index.html",
        "MODULE_TITLE": html.escape(module.title),
        "MODULE": html.escape(module.title),
    }

    return loader.render(
        "PreviousNext.html",
        replacements,
    )


def render_chapter_hero(
    loader: TemplateLoader,
    module: Module,
    chapter: Chapter,
    asset_prefix: str,
) -> str:
    replacements = {
        "THEME": html.escape(chapter.theme),
        "THEME_NUMBER": str(chapter.theme_number),

        "NUMBER": html.escape(chapter.number),
        "CHAPTER_NUMBER": str(chapter.chapter_number),
        "CHAPTER_LOCAL_NUMBER": str(chapter.chapter_number),

        "TITLE": html.escape(chapter.title),
        "ABSTRACT": html.escape(chapter.abstract),

        "MODULE_TITLE": html.escape(module.title),
        "MODULE": html.escape(module.title),

        "ASSET_PREFIX": html.escape(
            asset_prefix,
            quote=True,
        ),
    }

    return loader.render(
        "ChapterHero.html",
        replacements,
    )


def replace_common_placeholders(
    content: str,
    module: Module,
    chapter: Chapter,
    asset_prefix: str,
) -> str:
    replacements = {
        "{{MODULE_TITLE}}": html.escape(module.title),
        "{{MODULE}}": html.escape(module.title),
        "{{CHAPTER_TITLE}}": html.escape(chapter.title),
        "{{CHAPTER_NUMBER}}": html.escape(chapter.number),
        "{{THEME}}": html.escape(chapter.theme),
        "{{ASSET_PREFIX}}": html.escape(
            asset_prefix,
            quote=True,
        ),
    }

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    return content


# ============================================================
# HOOFDSTUK OPBOUWEN
# ============================================================


def enhance_chapter(
    project_root: Path,
    module: Module,
    chapter: Chapter,
    chapter_index: int,
    loader: TemplateLoader,
    sidebar_template: str,
) -> None:
    if not chapter.source_html_file.is_file():
        raise FileNotFoundError(
            "HTML-bron ontbreekt voor "
            f"{chapter.activity}: {chapter.source_html_file}"
        )

    source_html = read_text(chapter.source_html_file)
    soup = BeautifulSoup(source_html, "lxml")

    head, body = ensure_document_structure(soup)

    asset_prefix = relative_web_path(
        chapter.output_html_file.parent,
        project_root / "assets",
    )

    css_directory = project_root / "assets" / "css"

    stylesheet_names = (
        "base.css",
        "global.css",
        "Header_Footer.css",
        "ChapterLayout.css",
        "chapter-hero.css",
        "learning-boxes.css",
        "CourseOverview.css",
    )

    for stylesheet_name in stylesheet_names:
        stylesheet_file = css_directory / stylesheet_name

        if stylesheet_file.is_file():
            ensure_stylesheet(
                soup,
                head,
                f"{asset_prefix}/css/{stylesheet_name}",
            )

    set_document_title(
        soup,
        head,
        chapter,
        module.title,
    )

    original_content, original_scripts = extract_body_content(body)

    body.append(
        Comment(" XIMERA-HEADER-START ")
    )

    header_html = loader.load("Header.html")
    header_html = replace_common_placeholders(
        header_html,
        module,
        chapter,
        asset_prefix,
    )
    append_fragment(body, header_html)

    body.append(
        Comment(" XIMERA-HEADER-END ")
    )

    body.append(
        Comment(" XIMERA-CHAPTER-HERO-START ")
    )

    append_fragment(
        body,
        render_chapter_hero(
            loader,
            module,
            chapter,
            asset_prefix,
        ),
    )

    body.append(
        Comment(" XIMERA-CHAPTER-HERO-END ")
    )

    body.append(make_menu_button(soup))
    body.append(make_sidebar_overlay(soup))

    body.append(
        Comment(" XIMERA-CHAPTER-LAYOUT-START ")
    )

    main = soup.new_tag("main")
    main["class"] = ["chapter-layout"]

    active_sidebar = mark_active_sidebar_link(
        sidebar_template,
        chapter,
    )

    append_fragment(main, active_sidebar)

    article = soup.new_tag("article")
    article["class"] = ["chapter-content"]

    chapter_body = soup.new_tag("div")
    chapter_body["class"] = ["chapter-body"]

    for node in original_content:
        chapter_body.append(node)

    article.append(chapter_body)

    article.append(
        Comment(" XIMERA-PREVIOUS-NEXT-START ")
    )

    append_fragment(
        article,
        render_previous_next(
            loader,
            module,
            chapter_index,
        ),
    )

    article.append(
        Comment(" XIMERA-PREVIOUS-NEXT-END ")
    )

    main.append(article)
    body.append(main)

    body.append(
        Comment(" XIMERA-CHAPTER-LAYOUT-END ")
    )

    footer_clear = soup.new_tag("div")
    footer_clear["class"] = ["course-footer-clear"]
    body.append(footer_clear)

    body.append(
        Comment(" XIMERA-FOOTER-START ")
    )

    footer_html = loader.load("Footer.html")
    footer_html = replace_common_placeholders(
        footer_html,
        module,
        chapter,
        asset_prefix,
    )

    append_fragment(body, footer_html)

    body.append(
        Comment(" XIMERA-FOOTER-END ")
    )

    # Bestaande Ximera-scripts terugplaatsen.
    for script in original_scripts:
        body.append(script)

    # Ondersteunt zowel assets/javascripts als het oudere assets/js.
    javascript_candidates = (
        project_root
        / "assets"
        / "javascripts"
        / "chapter-layout.js",
        project_root
        / "assets"
        / "js"
        / "chapter-layout.js",
    )

    for javascript_file in javascript_candidates:
        if javascript_file.is_file():
            script_relative = relative_web_path(
                chapter.output_html_file.parent,
                javascript_file,
            )

            ensure_script(
                soup,
                body,
                script_relative,
            )
            break

    rendered = str(soup)

    # Mooie consistente HTML-afsluiting.
    if not rendered.endswith("\n"):
        rendered += "\n"

    write_text(
        chapter.output_html_file,
        rendered,
    )


# ============================================================
# CONTROLES
# ============================================================


def validate_required_files(
    project_root: Path,
    module: Module,
    loader: TemplateLoader,
) -> list[str]:
    errors: list[str] = []

    required_templates = (
    "Header.html",
    "Footer.html",
    "ChapterHero.html",
    "PreviousNext.html",
    "CourseCard.html",
    "CourseOverview.html",
)

    for filename in required_templates:
        path = loader.path(filename)

        if not path.is_file():
            errors.append(
                f"Template ontbreekt: {path}"
            )

    sidebar_file = (
        module.directory
        / "CourseSidebar.generated.html"
    )

    if not sidebar_file.is_file():
        errors.append(
            f"Sidebar ontbreekt: {sidebar_file}"
        )

    for chapter in module.chapters:
        if not chapter.tex_file.is_file():
            errors.append(
                f"TeX-bestand ontbreekt: {chapter.tex_file}"
            )

        if not chapter.source_html_file.is_file():
            errors.append(
                "HTML-bron ontbreekt: "
                f"{chapter.source_html_file}"
            )

    return errors


# ============================================================
# COMMANDOLIJN
# ============================================================


def resolve_module_directory(
    project_root: Path,
    argument: str,
) -> Path:
    candidate = Path(argument)

    if candidate.is_absolute():
        return candidate.resolve()

    return (project_root / candidate).resolve()


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent

    module_argument = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "modules/basiswiskunde"
    )

    module_dir = resolve_module_directory(
        project_root,
        module_argument,
    )

    print()
    print("Ximera hoofdstukken verwerken")
    print("────────────────────────────────────────")
    print(f"Project: {project_root}")
    print(f"Module:  {module_dir}")
    print()

    if not module_dir.is_dir():
        print("Fout: modulemap bestaat niet.")
        return 1

    try:
        module = parse_module(module_dir)
    except (FileNotFoundError, ValueError) as error:
        print(f"Fout: {error}")
        return 1

    loader = TemplateLoader(project_root)

    errors = validate_required_files(
        project_root,
        module,
        loader,
    )

    if errors:
        print("De verwerking kan niet starten:")
        print()

        for error in errors:
            print(f"  - {error}")

        print()
        print("Voer eerst xmlatex en generate-sidebar.sh uit.")
        return 1

    sidebar_file = (
        module.directory
        / "CourseSidebar.generated.html"
    )

    sidebar_html = read_text(sidebar_file)

    print(f"Moduletitel:  {module.title}")
    print(f"Hoofdstukken: {len(module.chapters)}")
    print()

    failed = False

    for index, chapter in enumerate(module.chapters):
        print(
            f"[{chapter.number}] "
            f"{chapter.title}"
        )
        print(
            f"    bron:   {chapter.source_html_file.name}"
        )
        print(
            f"    uitvoer: {chapter.output_html_file.name}"
        )

        try:
            enhance_chapter(
                project_root=project_root,
                module=module,
                chapter=chapter,
                chapter_index=index,
                loader=loader,
                sidebar_template=sidebar_html,
            )
        except Exception as error:
            failed = True
            print(f"    FOUT: {error}")
        else:
            print("    OK")

        print()

    if failed:
        print("Niet alle hoofdstukken konden worden verwerkt.")
        return 1

    print("Alle hoofdstukken zijn succesvol verwerkt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

def render_course_card(
    loader: TemplateLoader,
    chapter: Chapter,
) -> str:
    return loader.render(
        "CourseCard.html",
        {
            "URL": html.escape(chapter.url, quote=True),
            "NUMBER": html.escape(chapter.number),
            "THEME": html.escape(chapter.theme),
            "TITLE": html.escape(chapter.title),
            "ABSTRACT": html.escape(chapter.abstract),
        },
    )
    
def render_course_overview(
    loader: TemplateLoader,
    module: Module,
) -> str:
    theme_groups: dict[
        tuple[int, str],
        list[Chapter],
    ] = {}

    for chapter in module.chapters:
        key = (
            chapter.theme_number,
            chapter.theme,
        )

        theme_groups.setdefault(key, []).append(chapter)

    theme_sections: list[str] = []

    for (theme_number, theme_name), chapters in theme_groups.items():
        cards = "".join(
            render_course_card(
                loader,
                chapter,
            )
            for chapter in chapters
        )

        theme_sections.append(
            f"""
            <section class="course-theme">

                <header class="course-theme-header">
                    <span class="course-theme-number">
                        Thema {theme_number}
                    </span>

                    <h2 class="course-theme-title">
                        {html.escape(theme_name)}
                    </h2>
                </header>

                <div class="course-card-grid">
                    {cards}
                </div>

            </section>
            """
        )

    return loader.render(
        "CourseOverview.html",
        {
            "MODULE_TITLE": html.escape(module.title),
            "THEME_SECTIONS": "".join(theme_sections),
        },
    )