#!/usr/bin/env python3
"""Read-only storage scanner (macOS + Windows).

Collects disk usage, system info, and per-directory size breakdowns for the
hot spots that typically eat disk, and emits one JSON blob to stdout for an agent
to interpret and classify. Auto-detects the OS and scans the right locations.

STRICTLY READ-ONLY: only sizes/lists/reads metadata. Never creates, moves, or
deletes anything.

Output shape (same on both OSes):
{
  "generated_at", "scan_seconds",
  "system": {os, build, arch, user, home, filesystem,
             disk_total, disk_used, disk_free, purgeable,
             disks: [{name, total, used, free}]},   # all volumes/drives
  "groups": { "<group>": [{name, path, size_kb, size_h}], ... }
}
"""
import argparse
import json
import os
import shutil
import sys
import time

HOME = os.path.expanduser("~")


def human(kb):
    """KB number -> human string like '12.3 GB'."""
    n = float(kb) * 1024
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit not in ("B", "KB") else f"{int(n)} {unit}"
        n /= 1024


# ======================================================================
# macOS
# ======================================================================
import re
import subprocess


def run(cmd, timeout=180):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def du_entry(path, timeout=120):
    """Preserve errors and partial lower bounds instead of silently omitting them."""
    item = {"name": os.path.basename(path.rstrip(os.sep)) or path, "path": path}
    try:
        result = subprocess.run(["du", "-sk", path], capture_output=True,
                                text=True, timeout=timeout)
        match = re.match(r"\s*(\d+)", result.stdout)
        kb = int(match.group(1)) if match else None
        item.update(size_kb=kb, size_h=human(kb) if kb is not None else "?")
        if result.returncode != 0 or kb is None:
            error = result.stderr.strip() or "du produced no size"
            item.update(incomplete=True, error=error)
            if "permission denied" in error.lower() or "operation not permitted" in error.lower():
                item["denied"] = True
    except (subprocess.TimeoutExpired, OSError) as exc:
        item.update(size_kb=None, size_h="?", incomplete=True, error=str(exc))
    return item


def limited_results(results, limit):
    # Always retain errors, including those below the display floor or top-N.
    valid = sorted((r for r in results if not r.get("incomplete")),
                   key=lambda r: r["size_kb"], reverse=True)
    errors = [r for r in results if r.get("incomplete")]
    return valid[:limit] + errors


def du_children(path, min_kb=51200, limit=40):
    """Size immediate children; no follow of child symlinks. macOS/POSIX."""
    if not os.path.isdir(path):
        return [{"name": "(unavailable)", "path": path, "size_kb": None,
                 "size_h": "?", "incomplete": True, "error": "not an accessible directory"}]
    try:
        entries = sorted(os.listdir(path))
    except OSError as exc:
        return [{"name": "(unreadable)", "path": path, "size_kb": None,
                 "size_h": "?", "incomplete": True,
                 "denied": isinstance(exc, PermissionError), "error": str(exc)}]
    results = []
    for name in entries:
        child = os.path.join(path, name)
        if os.path.islink(child):
            continue
        item = du_entry(child)
        if item.get("incomplete") or item["size_kb"] >= min_kb:
            results.append(item)
    return limited_results(results, limit)


MAC_TARGETS = [
    ("home", HOME, 102400),
    ("library", os.path.join(HOME, "Library"), 51200),
    ("caches", os.path.join(HOME, "Library/Caches"), 51200),
    ("containers", os.path.join(HOME, "Library/Containers"), 51200),
    ("group_containers", os.path.join(HOME, "Library/Group Containers"), 51200),
    ("app_support", os.path.join(HOME, "Library/Application Support"), 51200),
    ("applications", "/Applications", 102400),
    ("downloads", os.path.join(HOME, "Downloads"), 51200),
    ("dev_storage", None, 51200),
]

MAC_DEV_CACHE_PATHS = [
    "~/Library/Caches/pip", "~/Library/Caches/uv", "~/.cache", "~/.cargo",
    "~/.npm", "~/.pnpm-store", "~/.gradle", "~/.m2",
    "~/Library/Developer/Xcode/DerivedData", "~/Library/Developer/CoreSimulator",
    "~/Library/Developer/Xcode/iOS DeviceSupport", "~/Library/pnpm",
    "~/go/pkg", "~/.docker",
]


def dev_caches_macos():
    # Inventory only: several roots mix caches, toolchains and user data.
    results = []
    for p in MAC_DEV_CACHE_PATHS:
        path = os.path.expanduser(p)
        if not os.path.isdir(path) or os.path.islink(path):
            continue
        item = du_entry(path, timeout=180)
        if item.get("incomplete") or item["size_kb"] >= 51200:
            results.append(item)
    return limited_results(results, len(results))


def system_info_macos():
    info = {}
    info["os"] = "macOS " + run(["sw_vers", "-productVersion"]).strip()
    info["build"] = run(["sw_vers", "-buildVersion"]).strip()
    arch = run(["uname", "-m"]).strip()
    brand = run(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
    info["arch"] = (f"Apple Silicon (arm64){' / ' + brand if brand else ''}"
                    if arch == "arm64" else f"{arch}{' / ' + brand if brand else ''}")
    info["user"] = os.environ.get("USER", "") or run(["whoami"]).strip()
    info["home"] = HOME
    total, used, free = "?", "?", "?"
    try:
        t, u, f = shutil.disk_usage(HOME)
        total, used, free = human(t // 1024), human(u // 1024), human(f // 1024)
    except Exception:
        pass
    info["disk_total"], info["disk_used"], info["disk_free"] = total, used, free
    dinfo = run(["diskutil", "info", HOME])
    fs = re.search(r"File System Personality:\s*(.+)", dinfo)
    info["filesystem"] = fs.group(1).strip() if fs else "APFS"
    pm = re.search(r"Purgeable Space:\s*([\d.,]+ \w+)", dinfo)
    info["purgeable"] = pm.group(1).strip() if pm else ""
    volume = re.search(r"Volume Name:\s*(.+)", dinfo)
    info["disk_name"] = volume.group(1).strip() if volume else HOME
    info["disks"] = [{"name": info["disk_name"], "total": total, "used": used, "free": free}]
    return info


def scan_macos():
    system = system_info_macos()
    groups = {}
    for key, path, floor in MAC_TARGETS:
        groups[key] = dev_caches_macos() if key == "dev_storage" else du_children(path, min_kb=floor)
    return system, groups


# ======================================================================
# Windows  (UNTESTED on this build — stdlib only: os, shutil, ctypes)
# ======================================================================
def dir_size_bytes(path, errors=None):
    """Recursive size in bytes via os.scandir. Skips symlinks and unreadable."""
    errors = errors if errors is not None else []
    total = 0
    try:
        with os.scandir(path) as it:
            for e in it:
                try:
                    if e.is_symlink():
                        continue
                    if e.is_file(follow_symlinks=False):
                        total += e.stat(follow_symlinks=False).st_size
                    elif e.is_dir(follow_symlinks=False):
                        total += dir_size_bytes(e.path, errors)
                except OSError as exc:
                    errors.append(str(exc))
    except OSError as exc:
        errors.append(str(exc))
    return total


def scandir_children(path, min_kb=51200, limit=40):
    """Windows logical sizes, retaining unreadable/partial results."""
    try:
        entries = sorted(os.listdir(path))
    except OSError as exc:
        return [{"name": "(unreadable)", "path": path, "size_kb": None,
                 "size_h": "?", "incomplete": True,
                 "denied": isinstance(exc, PermissionError), "error": str(exc)}]
    results = []
    for name in entries:
        child = os.path.join(path, name)
        if os.path.islink(child):
            continue
        errors = []
        try:
            kb = (os.path.getsize(child) if os.path.isfile(child)
                  else dir_size_bytes(child, errors)) // 1024
        except OSError as exc:
            kb = 0
            errors.append(str(exc))
        if kb < min_kb and not errors:
            continue
        item = {"name": name, "path": child, "size_kb": kb, "size_h": human(kb)}
        if errors:
            item.update(incomplete=True, error="; ".join(errors),
                        denied=any("denied" in e.lower() for e in errors))
        results.append(item)
    return limited_results(results, limit)


def list_drives_windows():
    drives = []
    import string
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            try:
                t, u, f = shutil.disk_usage(root)
                drives.append({"name": root, "total": human(t // 1024),
                               "used": human(u // 1024), "free": human(f // 1024)})
            except Exception:
                continue
    return drives


def system_info_windows():
    import platform
    info = {}
    info["os"] = platform.system() + " " + platform.release()
    info["build"] = platform.version()
    info["arch"] = os.environ.get("PROCESSOR_ARCHITECTURE", platform.machine())
    info["user"] = os.environ.get("USERNAME", "")
    info["home"] = os.environ.get("USERPROFILE", HOME)
    sysdrive = os.environ.get("SystemDrive", "C:") + "\\"
    total, used, free = "?", "?", "?"
    try:
        t, u, f = shutil.disk_usage(sysdrive)
        total, used, free = human(t // 1024), human(u // 1024), human(f // 1024)
    except Exception:
        pass
    info["disk_total"], info["disk_used"], info["disk_free"] = total, used, free
    info["filesystem"] = "NTFS"
    info["purgeable"] = ""
    info["disk_name"] = sysdrive
    info["disks"] = list_drives_windows()
    return info


def scan_windows():
    profile = os.environ.get("USERPROFILE", HOME)
    local = os.environ.get("LOCALAPPDATA", os.path.join(profile, "AppData", "Local"))
    roaming = os.environ.get("APPDATA", os.path.join(profile, "AppData", "Roaming"))
    targets = [
        ("user_profile", profile, 102400),
        ("appdata_local", local, 51200),
        ("appdata_roaming", roaming, 51200),
        ("temp", os.environ.get("TEMP", os.path.join(local, "Temp")), 51200),
        ("downloads", os.path.join(profile, "Downloads"), 51200),
        ("program_files", os.environ.get("ProgramFiles", r"C:\Program Files"), 102400),
        ("program_files_x86", os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), 102400),
    ]
    groups = {}
    for key, path, floor in targets:
        groups[key] = scandir_children(path, min_kb=floor)

    dev_paths = [
        os.path.join(profile, ".cache"), os.path.join(profile, ".npm"),
        os.path.join(profile, ".gradle"), os.path.join(profile, ".m2"),
        os.path.join(profile, ".nuget", "packages"), os.path.join(profile, ".cargo"),
        os.path.join(local, "pip", "Cache"), os.path.join(local, "Yarn"),
        os.path.join(local, "uv"), os.path.join(local, "ms-playwright"),
        os.path.join(local, "go-build"),
    ]
    dev = []
    for path in dev_paths:
        if not os.path.isdir(path):
            continue
        try:
            errors = []
            kb = dir_size_bytes(path, errors) // 1024
        except (PermissionError, OSError):
            continue
        if kb < 51200 and not errors:
            continue
        item = {"name": os.path.basename(path.rstrip("\\/")) or path,
                "path": path, "size_kb": kb, "size_h": human(kb)}
        if errors:
            item.update(incomplete=True, error="; ".join(errors))
        dev.append(item)
    dev.sort(key=lambda r: r["size_kb"], reverse=True)
    groups["dev_storage"] = dev
    return system_info_windows(), groups


# ======================================================================
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--path", action="append", help="Scan children of this explicit directory (repeatable)")
    scope.add_argument("--system", action="store_true", help="Scan common system/home locations")
    parser.add_argument("--min-kb", type=int, default=51200)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()
    if args.min_kb < 0 or args.limit < 1:
        parser.error("--min-kb must be nonnegative and --limit positive")
    started = time.time()
    if args.path:
        paths = list(dict.fromkeys(os.path.abspath(os.path.expanduser(p)) for p in args.path))
        scanner = scandir_children if sys.platform.startswith("win") else du_children
        groups = {path: scanner(path, args.min_kb, args.limit) for path in paths}
        # Explicit directory scans do not invoke machine inventory commands.
        system = {"os": sys.platform, "home": HOME, "scope": paths,
                  "disk_total": "?", "disk_used": "?", "disk_free": "?"}
    elif sys.platform == "darwin":
        system, groups = scan_macos()
    elif sys.platform.startswith("win"):
        system, groups = scan_windows()
    else:
        parser.error("--system supports macOS and Windows only")
    data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system": system,
        "groups": groups,
        "scan_seconds": round(time.time() - started, 1),
        "scope": args.path or "common-system-locations",
        "limits": {"min_kb": args.min_kb if args.path else "per-group 51200/102400",
                   "max_complete_items_per_group": args.limit if args.path else 40,
                   "overlapping_groups": True, "follow_child_symlinks": False},
        "notes": ["Groups can overlap; do not sum parent and child paths.",
                  "Incomplete sizes are lower bounds, not complete measurements.",
                  "Top-N and size floors omit small complete entries; this is not a full disk inventory."],
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
