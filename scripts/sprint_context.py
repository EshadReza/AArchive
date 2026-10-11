#!/usr/bin/env python3
"""Print one sprint and its referenced Markdown context; no external dependencies."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "TASKS.md"
SRS = ROOT / "docs/requirements.md"
DECISIONS = ROOT / "docs/decisions/README.md"
PROGRESS = ROOT / "docs/progress.md"
SPRINT_ID = r"S\d{3}[A-Z]?"
PHASES = ("MVP", "Phase 2", "Future")


@dataclass(frozen=True)
class Section:
    key: str
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Sprint:
    key: str
    title: str
    text: str

    def field(self, name: str) -> str:
        match = re.search(rf"^\*\*{re.escape(name)}:\*\* (.+)$", self.text, re.M)
        if not match:
            raise ValueError(f"{self.key}: missing metadata field {name}")
        return match.group(1).strip()

    def values(self, name: str) -> list[str]:
        value = self.field(name)
        return [] if value == "None" else [part.strip() for part in value.split(",")]


def read_sprints() -> dict[str, Sprint]:
    text = PLAN.read_text(encoding="utf-8")
    pattern = re.compile(
        rf'^### (?P<key>{SPRINT_ID}) - (?P<title>[^\n]+)\n'
        r'(?P<body>.*?)(?=^<a id="s|^## |\Z)', re.M | re.S
    )
    result: dict[str, Sprint] = {}
    for match in pattern.finditer(text):
        key = match.group("key")
        if key in result:
            raise ValueError(f"Duplicate sprint ID: {key}")
        result[key] = Sprint(key, match.group("title"), match.group(0).strip())
    if not result:
        raise ValueError("No sprint cards found in TASKS.md")
    return result


def read_sections(path: Path, kind: str) -> dict[str, Section]:
    text = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^(#{1,6}) ([^\n]+)$", text, re.M))
    result: dict[str, Section] = {}
    for i, heading in enumerate(headings):
        title = heading.group(2)
        if kind == "srs":
            match = re.match(r"(\d+(?:\.\d+)*)(?:\.)?\s", title)
            if not match:
                match = re.match(r"(Appendix [A-Z])(?:\s|:)", title)
        else:
            match = re.match(r"(D\d{2})\s+-\s+", title)
        if not match:
            continue
        key = match.group(1)
        end = len(text)
        for following in headings[i + 1:]:
            if len(following.group(1)) <= len(heading.group(1)):
                end = following.start()
                break
        if key in result:
            raise ValueError(f"Duplicate section {key} in {path.name}")
        result[key] = Section(key, heading.start(), end, text[heading.start():end].strip())
    return result


def read_progress() -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for match in re.finditer(
        rf"^\| ({SPRINT_ID}) \| ([^|]+) \| (.*?) \|$",
        PROGRESS.read_text(encoding="utf-8"), re.M,
    ):
        key, status, evidence = (part.strip() for part in match.groups())
        if key in result:
            raise ValueError(f"Duplicate progress row: {key}")
        result[key] = (status, evidence)
    return result


def selected_sections(keys: list[str], sections: dict[str, Section]) -> list[Section]:
    selected = [sections[key] for key in keys]
    # A parent section already includes its children; do not print both.
    return sorted(
        [section for section in selected if not any(
            other.key != section.key and other.start <= section.start
            and other.end >= section.end for other in selected
        )], key=lambda section: section.start,
    )


def select_next(sprints, progress) -> tuple[str | None, str | None]:
    """Select from a validated ledger without mutating it or claiming work."""
    for phase in PHASES:
        unfinished = sorted(
            key for key, sprint in sprints.items()
            if sprint.field("Phase") == phase and progress[key][0] != "DONE"
        )
        if not unfinished:
            continue
        for status in ("IN_PROGRESS", "TODO"):
            for key in unfinished:
                if progress[key][0] == status and all(
                    progress[dep][0] == "DONE"
                    for dep in sprints[key].values("Prerequisites")
                ):
                    return key, phase
        # Do not jump ahead to a later phase just because it has a ready card.
        return None, phase
    return None, None


def validate(sprints, srs, decisions, progress) -> list[str]:
    errors: list[str] = []
    for key, sprint in sprints.items():
        try:
            for name in ("Phase", "Prerequisites", "SRS sections", "Decisions", "Work areas"):
                sprint.field(name)
            if sprint.field("Phase") not in PHASES:
                errors.append(f"{key}: unknown phase {sprint.field('Phase')}")
            for dependency in sprint.values("Prerequisites"):
                if dependency not in sprints:
                    errors.append(f"{key}: unknown prerequisite {dependency}")
                elif dependency == key:
                    errors.append(f"{key}: depends on itself")
            for ref in sprint.values("SRS sections"):
                if ref not in srs:
                    errors.append(f"{key}: unknown SRS section {ref}")
            for ref in sprint.values("Decisions"):
                if ref not in decisions:
                    errors.append(f"{key}: unknown decision {ref}")
            for marker in ("**Implementation steps**", "**Acceptance checks**", "**Boundary:**"):
                if marker not in sprint.text:
                    errors.append(f"{key}: missing {marker}")
        except ValueError as exc:
            errors.append(str(exc))
        if key not in progress:
            errors.append(f"{key}: missing progress row")
    for key, (status, evidence) in progress.items():
        if key not in sprints:
            errors.append(f"Progress row has no sprint card: {key}")
        if status not in {"TODO", "IN_PROGRESS", "BLOCKED", "DONE"}:
            errors.append(f"{key}: invalid status {status}")
        if status in {"DONE", "BLOCKED"} and not evidence:
            errors.append(f"{key}: {status} requires evidence or a blocker")
        if status == "DONE" and key in sprints:
            for dep in sprints[key].values("Prerequisites"):
                if progress.get(dep, ("MISSING", ""))[0] != "DONE":
                    errors.append(f"{key}: DONE while prerequisite {dep} is not DONE")

    seen: set[str] = set()
    active: set[str] = set()

    def visit(key: str) -> None:
        if key in active:
            errors.append(f"Dependency cycle includes {key}")
            return
        if key in seen:
            return
        active.add(key)
        try:
            deps = sprints[key].values("Prerequisites")
        except ValueError:
            deps = []
        for dep in deps:
            if dep in sprints:
                visit(dep)
        active.remove(key)
        seen.add(key)

    for key in sprints:
        visit(key)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sprint", nargs="?", help="Sprint ID, e.g. S042")
    parser.add_argument("--next", action="store_true", help="Select the next ready sprint")
    parser.add_argument("--list", action="store_true", help="Print the compact index")
    parser.add_argument("--brief", action="store_true", help="Print only the selected card")
    parser.add_argument("--check", action="store_true", help="Validate the plan and references")
    args = parser.parse_args()
    if sum(bool(x) for x in (args.sprint, args.next, args.list, args.check)) != 1:
        parser.error("Choose a sprint ID, --next, --list, or --check")
    if args.brief and not (args.sprint or args.next):
        parser.error("--brief requires a sprint ID or --next")
    try:
        sprints = read_sprints()
        srs = read_sections(SRS, "srs")
        decisions = read_sections(DECISIONS, "decisions")
        progress = read_progress()
        if args.check or args.next:
            errors = validate(sprints, srs, decisions, progress)
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 1
            if args.check:
                print(f"OK: {len(sprints)} sprint cards; dependency graph, SRS/decision references, "
                      f"and {len(progress)} progress rows are consistent.")
                return 0
        if args.list:
            for key, sprint in sprints.items():
                state = progress.get(key, ("MISSING", ""))[0]
                print(f"{key} [{state}] {sprint.title} | needs {sprint.field('Prerequisites')}")
            return 0
        if args.next:
            key, phase = select_next(sprints, progress)
            if key is None:
                if phase is None:
                    print("All planned sprints are DONE. No next sprint remains.")
                    return 0
                print(f"No ready sprint in {phase}. Later phases remain gated.\n")
                for blocked_key, card in sprints.items():
                    state, evidence = progress[blocked_key]
                    if card.field("Phase") != phase or state == "DONE":
                        continue
                    unmet = [dep for dep in card.values("Prerequisites")
                             if progress[dep][0] != "DONE"]
                    detail = evidence if state == "BLOCKED" else ""
                    if unmet:
                        detail += ("; " if detail else "") + "needs " + ", ".join(unmet)
                    print(f"- {blocked_key} [{state}]: {detail or 'Inspect the progress ledger.'}")
                return 3
            print(f"Selected {key} [{progress[key][0]}] in {phase}. "
                  "The agent should implement/resume this sprint after verifying evidence.\n")
        else:
            key = args.sprint.upper()
        if key not in sprints:
            parser.error(f"Unknown sprint {key}; use --list")
        sprint = sprints[key]
        print(sprint.text)
        if args.brief:
            return 0
        print("\n## Current prerequisite status\n")
        for dependency in sprint.values("Prerequisites"):
            state, evidence = progress.get(dependency, ("MISSING", ""))
            print(f"- {dependency}: {state}" + (f" - {evidence}" if evidence else ""))
        if not sprint.values("Prerequisites"):
            print("No implementation prerequisites.")
        print("\n## Working contract\n")
        print("Read AGENTS.md and docs/progress.md. Implement only this card; inspect actual "
              "code, honor prerequisite gates, and record real verification evidence. "
              "No complete application exists merely because it is planned here.")
        print("\n## Referenced decisions (docs/decisions/README.md)\n")
        for section in selected_sections(sprint.values("Decisions"), decisions):
            print(section.text, "\n")
        print("\n## Referenced SRS excerpts (docs/requirements.md)\n")
        for section in selected_sections(sprint.values("SRS sections"), srs):
            print(section.text, "\n")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Context error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
