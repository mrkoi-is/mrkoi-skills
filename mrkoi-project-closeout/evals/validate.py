#!/usr/bin/env python3
"""Validate packaging and exercise the inventory in isolated synthetic projects.

Behavior scenarios in evals.json need a separate agent run; this script does not
claim that checking fixture structure proves correct agent decisions.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob('*'):
        if path.is_symlink():
            result[str(path.relative_to(root))] = 'link:' + str(path.readlink())
        elif path.is_file():
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main() -> None:
    text = (ROOT / 'SKILL.md').read_text()
    parts = text.split('---', 2)
    assert len(parts) == 3, 'missing frontmatter'
    assert 'name: mrkoi-project-closeout' in parts[1], 'wrong skill name'
    description = parts[1].split('description: >-', 1)[1].split('\nmetadata:', 1)[0]
    assert 1 <= len(description) <= 1024
    assert len(text.splitlines()) < 500
    for relative in re.findall(r'\]\((references/[^)]+)\)', text):
        assert (ROOT / relative).is_file(), f'missing reference {relative}'
    assert (ROOT / 'agents/openai.yaml').is_file()
    eval_data = json.loads((ROOT / 'evals/evals.json').read_text())
    assert eval_data['skill_name'] == ROOT.name
    evals = eval_data['evals']
    assert len(evals) >= 11
    assert len({item['id'] for item in evals}) == len(evals)
    for item in evals:
        assert item.get('expectations')
        for relative in item.get('files', []):
            assert not Path(relative).is_absolute()
            assert (ROOT / relative).exists(), f'missing fixture {relative}'
    triggers = json.loads((ROOT / 'evals/trigger-eval.json').read_text())
    assert len(triggers) >= 20
    assert any(item['should_trigger'] for item in triggers)
    assert any(not item['should_trigger'] for item in triggers)

    script = ROOT / 'scripts/audit-inventory.sh'
    assert script.stat().st_mode & stat.S_IXUSR
    subprocess.run(['bash', '-n', str(script)], check=True)
    with tempfile.TemporaryDirectory(prefix='mrkoi-closeout-eval-') as temporary:
        sandbox = Path(temporary)
        project = sandbox / 'project with spaces'
        fixture = ROOT / 'evals/fixtures/eval-10-vibe-project/project'
        shutil.copytree(fixture, project, symlinks=True)
        (project / 'CLAUDE.md').write_text('SYNTHETIC_PRIVATE_TEXT_MUST_NOT_BE_PRINTED\n')
        (project / 'AGENTS.md').symlink_to('CLAUDE.md')
        (project / 'AGENTS.override.md').symlink_to('missing-rule.md')
        (project / 'node_modules').mkdir()
        (project / 'node_modules/ignored.md').write_text('ignored')
        # An ancestor rule must not appear in --local-only output.
        (sandbox / 'AGENTS.md').write_text('ancestor fixture\n')
        before = snapshot(sandbox)
        result = subprocess.run(['bash', str(script), '--local-only', str(project)],
                                text=True, capture_output=True, check=True)
        assert 'git_root=none' in result.stdout
        assert 'state=valid' in result.stdout and 'state=broken' in result.stdout
        assert str(project / 'README.md') in result.stdout
        assert str(project / 'node_modules/ignored.md') not in result.stdout
        assert str(sandbox / 'AGENTS.md') not in result.stdout
        assert 'SYNTHETIC_PRIVATE_TEXT_MUST_NOT_BE_PRINTED' not in result.stdout
        assert 'platform-directories' not in result.stdout
        assert snapshot(sandbox) == before, 'inventory mutated its inputs'
        if shutil.which('git'):
            subprocess.run(['git', 'init', '-q', str(project)], check=True)
            before = snapshot(sandbox)
            result = subprocess.run(['bash', str(script), '--local-only', str(project)],
                                    text=True, capture_output=True, check=True)
            assert 'head=unborn' in result.stdout, result.stdout
            assert snapshot(sandbox) == before, 'git inventory mutated its inputs'
        invalid = subprocess.run(['bash', str(script), str(sandbox / 'missing')],
                                 text=True, capture_output=True)
        assert invalid.returncode == 66
    print(f'[OK] package and isolated read-only inventory checks passed; '
          f'{len(evals)} behavior scenarios and {len(triggers)} trigger scenarios present (not executed)')


if __name__ == '__main__':
    main()
