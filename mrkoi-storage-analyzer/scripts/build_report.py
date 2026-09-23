#!/usr/bin/env python3
"""Inject an analysis JSON into the HTML template -> a standalone report.

Usage:
    build_report.py <analysis.json> [output.html]

The analysis JSON is produced by an agent after interpreting scan.py output.
Schema (all sections optional except system):

{
  "generated_at": "2026-05-28 12:00:00",
  "scan_seconds": 42.1,
  "scope": ["/explicit/scanned/path"],
  "notes": ["measurement limits"],
  "system": {os, build, arch, user, home, filesystem,
             disk_total, disk_used, disk_free, purgeable},
  "top5": [{rank, tier(green|yellow|red), size, type, name, path, note}],
  "green":  [{name, path, size_estimate, kill_processes:[], trash_paths:[...]?, commands:[{label,cmd}]}],
  "yellow": [{name, path, size, content_profile, why_manual, disposal, risk, trash_paths:[...]?, open_note?}],
  "red":    [{name, path, size, why_keep, indirect_release, auto_reclaim, app_paths:[...]?}],
  "denied": ["/path/one", ...],
  "summary": {overview, tier_stats:{green,yellow,red}, priority:[...], long_term:[...]}
}
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "report_template.html")


def script_json(value):
    # JSON is embedded in HTML script context: literal </script> terminates it
    # even inside a JavaScript string. Paths/content are untrusted report data.
    return (json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")
            .replace(">", "\\u003e").replace("&", "\\u0026")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def render_report(template, data, config=None):
    if not isinstance(data, dict) or not isinstance(data.get("system"), dict):
        raise ValueError("analysis must contain a system object")
    # Replace template markers in a single pass; never reprocess report data
    # that happens to contain the text of a marker.
    import re
    values = {"__REPORT_DATA__": script_json(data), "__DELETE_CONFIG__": script_json(config)}
    return re.sub(r"__REPORT_DATA__|__DELETE_CONFIG__", lambda m: values[m.group()], template)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser(
        "~/Desktop/storage-report.html")

    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        tpl = f.read()

    html = render_report(tpl, data)

    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已生成: {out}")
    print(f"打开: open '{out}'")


if __name__ == "__main__":
    main()
