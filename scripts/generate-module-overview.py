
#!/usr/bin/env python3
r"""
Genereert automatisch een module-openingspagina met een overzicht
van de thema's uit een Ximera-indexbestand.

De modulegegevens worden gelezen uit:

    \fvdtitle{...}
    of
    \title{...}

    \begin{abstract}
    ...
    \end{abstract}

Thema's worden gelezen uit:

    \FVDpart{...}

De uitvoer wordt opgeslagen als:

    module-opening.generated.tex
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModuleData:
    title: str
    abstract: str
    themes: list[str]


def remove_latex_comments(text: str) -> str:
    cleaned_lines: list[str] = []

    for line in text.splitlines():
        output: list[str] = []
        index = 0

        while index < len(line):
            character = line[index]

            if character == "%":
                backslashes = 0
                check_index = index - 1

                while check_index >= 0 and line[check_index] == "\\":
                    backslashes += 1
                    check_index -= 1

                if backslashes % 2 == 0:
                    break

            output.append(character)
            index += 1

        cleaned_lines.append("".join(output))

    return "\n".join(cleaned_lines)


def extract_braced_argument(
    text: str,
    command_start: int,
) -> tuple[str, int] | None:
    opening_brace = text.find("{", command_start)

    if opening_brace == -1:
        return None

    depth = 0

    for index in range(opening_brace, len(text)):
        character = text[index]

        if character == "{":
            depth += 1

        elif character == "}":
            depth -= 1

            if depth == 0:
                return text[opening_brace + 1:index], index + 1

    return None


def extract_command_argument(
    text: str,
    command: str,
) -> str | None:
    cleaned = remove_latex_comments(text)

    pattern = re.compile(
        rf"\\{re.escape(command)}\s*\{{"
    )

    match = pattern.search(cleaned)

    if not match:
        return None

    result = extract_braced_argument(
        cleaned,
        match.start(),
    )

    if result is None:
        return None

    argument, _ = result
    return argument.strip()


def extract_environment(
    text: str,
    environment: str,
) -> str | None:
    cleaned = remove_latex_comments(text)

    pattern = re.compile(
        rf"\\begin\s*\{{{re.escape(environment)}\}}"
        rf"(.*?)"
        rf"\\end\s*\{{{re.escape(environment)}\}}",
        flags=re.DOTALL,
    )

    match = pattern.search(cleaned)

    if not match:
        return None

    content = match.group(1)
    content = re.sub(r"\s+", " ", content)

    return content.strip()


def extract_all_command_arguments(
    text: str,
    command: str,
) -> list[str]:
    cleaned = remove_latex_comments(text)

    pattern = re.compile(
        rf"\\{re.escape(command)}\s*\{{"
    )

    arguments: list[str] = []
    search_position = 0

    while True:
        match = pattern.search(
            cleaned,
            search_position,
        )

        if not match:
            break

        result = extract_braced_argument(
            cleaned,
            match.start(),
        )

        if result is None:
            break

        argument, end_position = result
        argument = re.sub(r"\s+", " ", argument).strip()

        arguments.append(argument)
        search_position = end_position

    return arguments


def read_module_data(index_file: Path) -> ModuleData:
    source = index_file.read_text(
        encoding="utf-8",
        errors="replace",
    )

    title = extract_command_argument(
        source,
        "fvdtitle",
    )

    if title is None:
        title = extract_command_argument(
            source,
            "title",
        )

    if title is None:
        title = index_file.parent.name

    abstract = extract_environment(
        source,
        "abstract",
    )

    if abstract is None:
        abstract = (
            "In deze module bouwen we stap voor stap de "
            "nodige wiskundige basis op."
        )

    themes = extract_all_command_arguments(
        source,
        "FVDpart",
    )

    return ModuleData(
        title=title,
        abstract=abstract,
        themes=themes,
    )


def build_generated_tex(data: ModuleData) -> str:
    theme_lines: list[str] = []

    if data.themes:
        for number, theme in enumerate(
            data.themes,
            start=1,
        ):
            theme_lines.append(
                rf"    \FVDmodulethemetile{{{number}}}{{{theme}}}"
            )
    else:
        theme_lines.append(
            r"    \emph{Er zijn nog geen thema's toegevoegd.}"
        )

    theme_overview = "\n".join(theme_lines)

    return (
        "% ============================================================\n"
        "% AUTOMATISCH GEGENEREERD BESTAND\n"
        "% Niet handmatig aanpassen.\n"
        "% ============================================================\n"
        "\n"
        r"\ifdefined\HCode" "\n"
        "  % Geen afzonderlijke module-openingspagina in HTML.\n"
        r"\else" "\n"
        r"  \FVDmoduleopening" "\n"
        f"    {{{data.title}}}\n"
        f"    {{{data.abstract}}}\n"
        "    {%\n"
        f"{theme_overview}\n"
        "    }\n"
        r"\fi" "\n"
    )


def generate(index_file: Path) -> Path:
    if not index_file.is_file():
        raise FileNotFoundError(
            f"Indexbestand niet gevonden: {index_file}"
        )

    data = read_module_data(index_file)

    output_file = (
        index_file.parent
        / "module-opening.generated.tex"
    )

    output_file.write_text(
        build_generated_tex(data),
        encoding="utf-8",
    )

    print(f"Modulepagina gegenereerd: {output_file}")
    print(f"Moduletitel: {data.title}")
    print(f"Aantal thema's: {len(data.themes)}")

    for number, theme in enumerate(
        data.themes,
        start=1,
    ):
        print(f"  Thema {number}: {theme}")

    return output_file


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Genereer een module-openingspagina "
            "met een overzicht van de thema's."
        )
    )

    parser.add_argument(
        "index_file",
        type=Path,
        help="Het index.tex-bestand van de module.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    try:
        generate(
            arguments.index_file.resolve()
        )
    except Exception as exc:
        print(
            f"Fout: {exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY