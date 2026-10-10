#!/usr/bin/env python3
"""Build the Skill ZIP without tests, run outputs, caches, or credentials."""

from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "github-project-guide"
ALLOWED = {"scripts", "references", "templates"}


def build():
    definition = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---(?:\n|$)", definition, re.S)
    if not match:
        raise ValueError("SKILL.md must start with YAML frontmatter.")
    metadata = match.group(1)
    for key in ("description", "description_zh", "description_en", "version", "author"):
        if not re.search(r"^" + key + r":\s*\S.+$", metadata, re.M):
            raise ValueError("Missing required metadata: " + key)
    version = re.search(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", metadata, re.M)
    if not version:
        raise ValueError("Use an unquoted major.minor.patch version.")
    output = ROOT / "dist" / ("github-project-guide-" + version.group(1) + ".zip")
    output.parent.mkdir(exist_ok=True)
    files = [SKILL / "SKILL.md"]
    for folder in sorted(ALLOWED):
        for path in sorted((SKILL / folder).rglob("*")):
            relative = path.relative_to(SKILL)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError("Do not ship symlinks: " + str(relative))
            if path.is_file() and path.suffix in {".py", ".md", ".json", ".txt"}:
                files.append(path)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "github-project-guide/" + path.relative_to(SKILL).as_posix())
        archive.write(ROOT / "LICENSE", "github-project-guide/LICENSE")
    return output


if __name__ == "__main__":
    print(build())
