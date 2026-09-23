#!/usr/bin/env python3
"""Link the reviewed checkout into Codex without replacing existing skills."""
import argparse
import os
from pathlib import Path

SKILLS = (
    "mrkoi-goal-planner", "mrkoi-storage-analyzer", "mrkoi-ai-news",
    "mrkoi-project-closeout", "mrkoi-research", "mrkoi-writer",
)
REPO = Path(__file__).resolve().parents[1]


def install(repo, dest, names, apply=False):
    """Preflight the whole selection, then link; never replace a destination."""
    repo, dest = Path(repo).resolve(), Path(dest).expanduser().absolute()
    pending = []
    for name in names:
        if name not in SKILLS:
            raise ValueError(f"Unknown skill: {name}")
        source, target = repo / name, dest / name
        if not (source / "SKILL.md").is_file():
            raise ValueError(f"Missing source: {source / 'SKILL.md'}")
        if target.is_symlink() and target.resolve() == source.resolve():
            print(f"Already linked: {name}")
            continue
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Preserving existing destination: {target}")
        pending.append((source, target))
    created = []
    if apply:
        dest.mkdir(parents=True, exist_ok=True)
        try:
            for source, target in pending:
                target.symlink_to(source, target_is_directory=True)
                created.append((source, target))
        except OSError:
            for source, target in reversed(created):
                if target.is_symlink() and target.readlink() == source:
                    target.unlink()
            raise
    for source, target in pending:
        print(f"{'Linked' if apply else 'Would link'}: {target} -> {source}")
    return len(pending)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", help="Skill names; defaults to all six")
    codex_dir = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    parser.add_argument("--dest", type=Path, default=codex_dir / "skills")
    parser.add_argument("--apply", action="store_true", help="Create links (default: preview)")
    args = parser.parse_args()
    try:
        install(REPO, args.dest, list(dict.fromkeys(args.skills or SKILLS)), args.apply)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Installation stopped: {exc}\n")


if __name__ == "__main__":
    main()
