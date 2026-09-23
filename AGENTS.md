# Mr. Koi Skills maintenance

This repository is a personal fork of KKKKhazix/khazix-skills. Keep upstream
attribution and commit history; `origin` is the personal fork and `upstream`
is the source repository. Do not push to upstream.

- Runtime skills live in the six `mrkoi-*` folders. Keep their folder names,
  frontmatter names, invocation examples and `agents/openai.yaml` consistent.
- Prefer clear Chinese, concrete outcomes and proportionate verification.
  Preserve user choices and current authorization. Avoid forced ceremonies.
- Local research and implementation do not imply release review. Only load
  release, legal or platform-policy checks when requested or needed for an
  explicitly authorized external release action.
- Never include personal paths, credentials, private project content or local
  news caches in public commits. Examples should be synthetic.
- Do not rewrite installed third-party skills or global memory as part of
  maintaining this repo. Installation must preserve any existing destination.
- Validate changed instructions and run the relevant script tests. Use temporary
  fixtures for disk tools; do not test against real user files or run cleanup.
- Sync upstream by inspecting its diff first; do not blindly overwrite the
  personalized skill directories with their former upstream names.
