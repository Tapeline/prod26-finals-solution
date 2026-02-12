import re
import textwrap
import json
from collections import defaultdict
from pathlib import Path
from typing import Final

_GLOSSARY: Final = "docs/glossary.md"
_LINE_REGEX = "\\*\\*\\w+:(.+?)\\*\\*"


def _read_glossary(glossary_path: str) -> dict[str, dict[str, str]]:
    md_text = Path(glossary_path).read_text(encoding="utf-8")
    lines = md_text.splitlines()
    terms = defaultdict(dict)
    i = 0
    current_term = None
    current_group = None
    current_term_lines = []
    while i < len(lines):
        #if lines[i].startswith("**term:"):
        if re.fullmatch(string=lines[i], pattern=_LINE_REGEX):
            if current_term_lines:
                terms[current_group][current_term] = "\n".join(current_term_lines)
                current_term = None
                current_group = None
                current_term_lines.clear()
            current_group, current_term = lines[i].removeprefix("**") \
                .removesuffix("**").split(":", maxsplit=1)
        elif lines[i] == "" or lines[i].startswith(" "):
            current_term_lines.append(lines[i].strip())
        elif lines[i].startswith(":"):
            current_term_lines.append(lines[i][1:].strip())
        else:
            if current_term_lines:
                terms[current_group][current_term] = "\n".join(current_term_lines)
                current_term = None
                current_group = None
                current_term_lines.clear()
        i += 1
    if current_term_lines:
        terms[current_group][current_term] = "\n".join(current_term_lines)
    return terms


def define_env(env):
    terms = _read_glossary(_GLOSSARY)

    @env.macro
    def indent_snippet(path, indent):
        contents = Path(path).read_text()
        return textwrap.indent(contents, indent)

    @env.macro
    def definition(group: str, term: str, indent: str = ""):
        if group not in terms:
            return textwrap.indent("Group not found.", indent)
        if term not in terms:
            return textwrap.indent("Definition not found.", indent)
        return textwrap.indent(terms[group][term], indent)

    @env.macro
    def decorated_definition(group: str, term: str, indent: str = ""):
        if group not in terms:
            return textwrap.indent("> Group not found.", indent)
        if term not in terms[group]:
            return textwrap.indent("> Definition not found.", indent)
        md = textwrap.indent(
            f"**{term}**\n\n{terms[group][term]}",
            "> "
        )
        return textwrap.indent(md, indent)
