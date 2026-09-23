# Mr. Koi Skills

A personal fork of [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills), adapted for Chinese research, writing, goal planning, project closeout and local storage analysis. See the [Chinese README](README.md) for the maintained guide and the [assessment](docs/analysis.md) for scope and validation.

| Skill | Purpose |
|---|---|
| `mrkoi-goal-planner` | Turn a complex request into an evidence-backed execution brief |
| `mrkoi-storage-analyzer` | Analyze storage with a static, read-only report by default |
| `mrkoi-ai-news` | Gather current AI news and verify important claims against primary sources |
| `mrkoi-project-closeout` | Reconcile project documentation and actual implementation within the requested scope |
| `mrkoi-research` | Compare alternatives and trace their development with explicit evidence |
| `mrkoi-writer` | Develop Chinese articles from the user's materials without assuming another author's identity |

## Install from the reviewed local checkout

Python 3.10+ is required.

```bash
python3 scripts/install_local.py
python3 scripts/install_local.py --apply
```

The first command previews; the second creates links in `$CODEX_HOME/skills` (or `~/.codex/skills`). Existing destinations are preserved. To install a subset, pass the skill directory names. Use `--dest` for another agent's skill directory and verify discovery in that client. The checkout remains the single maintained source.

Invoke a skill by its `$mrkoi-...` name on the next turn or in a new conversation. Installation does not scan disks, delete files, start scheduled tasks or edit agent memory.

## Attribution

Forked from upstream commit `4f2db09802736ac8130ddf8dd6121435b5a41b55`. Original copyright and Git history are retained under the [MIT license](LICENSE). The AIHOT-derived skill retains [Virxact's MIT license](mrkoi-ai-news/LICENSE). Code licensing does not transfer third-party news content rights.
