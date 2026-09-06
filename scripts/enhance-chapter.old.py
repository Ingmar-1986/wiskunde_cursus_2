#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chapter:
    activity: str
    theme: str
    theme_number: int
    chapter_number: int
    html_file: Path

    @property
    def number(self) -> str:
        return f"{self.theme_number}.{self.chapter_number}"


def remove_comments(source: str) -> str:
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


def clean_latex_text(value: str) -> str:
    value = value.strip()

    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\#": "#",
        r"\_": "_",
        "~": " ",
        "---": "—",
        "--": "–",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    for command in (
        "textbf",
        "textit",
        "emph",
        "mathrm",
        "mathbf",
        "mathit",
        "textrm",
        "textsf",
        "texttt",
    ):
        value = re.sub(
            rf"\\{command}\s*\{{([^{{}}]*)\}}",
            r"\1",
            value,
        )

    value = value.replace(r"\(", "").replace(r"\)", "")
    value = value.replace("$", "")
    value = re.sub(r"\\[a-zA-Z@]+\*?", "", value)
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def parse_index(index_file: Path, module_dir: Path) -> list[Chapter]:
    source = remove_comments(index_file.read_text(encoding="utf-8"))

    token_pattern = re.compile(
        r"""
        \\part\s*\{(?P<part>[^{}]*)\}
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

        if activity is not None:
            if theme_number == 0:
                theme_number = 1

            chapter_number += 1

            activity = activity.strip()

            if activity.endswith(".tex"):
                activity = activity[:-4]

            html_file = module_dir / f"{activity}.html"

            chapters.append(
                Chapter(
                    activity=activity,
                    theme=current_theme,
                    theme_number=theme_number,
                    chapter_number=chapter_number,
                    html_file=html_file,
                )
            )

    return chapters


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent

    module_arg = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "modules/basiswiskunde"
    )

    module_dir = project_root / module_arg
    index_file = module_dir / "index.tex"

    print()
    print("Ximera hoofdstukken verwerken")
    print("────────────────────────────")
    print(f"Project: {project_root}")
    print(f"Module:  {module_dir}")
    print()

    if not module_dir.is_dir():
        print("Fout: modulemap bestaat niet.")
        return 1

    if not index_file.is_file():
        print("Fout: index.tex werd niet gevonden.")
        return 1

    chapters = parse_index(index_file, module_dir)

    if not chapters:
        print("Fout: geen hoofdstukken gevonden in index.tex.")
        return 1

    print(f"Hoofdstukken in index.tex: {len(chapters)}")
    print()

    missing_files: list[Path] = []

    for chapter in chapters:
        status = "OK" if chapter.html_file.is_file() else "ONTBREEKT"

        print(
            f"  {chapter.number:<5} "
            f"{chapter.theme} → "
            f"{chapter.activity}.html [{status}]"
        )

        if not chapter.html_file.is_file():
            missing_files.append(chapter.html_file)

    print()

    if missing_files:
        print("Deze HTML-bestanden ontbreken:")

        for path in missing_files:
            print(f"  - {path}")

        print()
        print("Voer eerst xmlatex uit.")
        return 1

    print("Volgorde en bestanden zijn correct.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())