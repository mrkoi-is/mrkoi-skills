#!/usr/bin/env python3
"""Opt-in local cleanup UI for explicitly authorized report paths.

Default output is build_report.py's static report. This service requires
--enable-cleanup and one or more --allow-path arguments matching reviewed
trash_paths. Permanent deletion additionally requires --allow-permanent-delete.
A classification in generated JSON never grants cleanup authority by itself.
"""
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from build_report import render_report

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "report_template.html")
HOME = os.path.realpath(os.path.expanduser("~"))
TOKEN = secrets.token_urlsafe(24)

DATA = {}
TPL = ""
RM_ALLOW = set()
TRASH_ALLOW = set()
OPEN_ALLOW = set()
PERMANENT_DELETE = False


def expand(p):
    return os.path.realpath(os.path.expanduser(p))


def deletion_target(path):
    """A precise child of HOME, never a broad mixed data/toolchain root."""
    protected = {HOME, *(os.path.join(HOME, p) for p in (
        "Workspace", "Library", "Library/Caches", "Library/Application Support",
        "Library/Containers", "Library/Group Containers", "Library/Developer",
        "Library/Developer/CoreSimulator", "Downloads", "Documents", "Desktop",
        ".cargo", ".gradle", ".m2", ".docker", "Library/pnpm"))}
    return path.startswith(HOME + os.sep) and path not in protected


def load(src, approved_paths=(), allow_permanent=False):
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    # 三套白名单，权限从严到宽：
    #   rm    = 仅绿灯 trash_paths（可直接删的纯缓存）
    #   trash = 绿灯 + 橙灯 trash_paths（橙灯只准移废纸篓，不准直接删）
    #   open  = trash 全集 + 橙灯 path + 红灯 app_paths（仅"在文件管理器打开"，非破坏性）
    approved = {expand(p) for p in approved_paths}
    rejected = [p for p in approved if not deletion_target(p)]
    if rejected:
        raise ValueError("清理目标必须为用户目录内的具体子目录，不能是混合数据根目录：" + repr(rejected))
    rm_allow, trash_allow, open_allow = set(), set(), set()
    for it in data.get("green", []):
        for p in (it.get("trash_paths") or []):
            rp = expand(p)
            if rp in approved:
                if allow_permanent:
                    rm_allow.add(rp)
                trash_allow.add(rp)
                open_allow.add(rp)
    for it in data.get("yellow", []):
        for p in (it.get("trash_paths") or []):
            rp = expand(p)
            if rp in approved:
                trash_allow.add(rp)
                open_allow.add(rp)
        if it.get("path"):
            rp = expand(it["path"])
            if os.path.exists(rp):
                open_allow.add(rp)
    # 红灯只允许"打开"（应用本体在 /Applications，删除让用户在访达里自己卸）
    for it in data.get("red", []):
        for p in (it.get("app_paths") or []):
            rp = expand(p)
            if os.path.exists(rp):
                open_allow.add(rp)
    unknown = approved - trash_allow
    if unknown:
        raise ValueError("授权路径未在报告的 trash_paths 中：" + repr(sorted(unknown)))
    for tier in ("green", "yellow"):
        for item in data.get(tier, []):
            item["trash_paths"] = [p for p in (item.get("trash_paths") or []) if expand(p) in trash_allow]
    return data, tpl, rm_allow, trash_allow, open_allow


def move_to_trash(path):
    if sys.platform == "darwin":
        _trash_macos(path)
    elif sys.platform.startswith("win"):
        _trash_windows(path)
    else:
        raise OSError("移到废纸篓仅支持 macOS / Windows")


def _trash_macos(path):
    # Finder owns Trash semantics. Do not bypass a cancellation or failure by
    # silently moving files ourselves (which could overwrite an existing item).
    script = 'tell application "Finder" to delete (POSIX file %s as alias)' % json.dumps(path)
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise OSError((r.stderr or "Finder 未完成废纸篓操作").strip())


def _trash_windows(path):
    # Send to Recycle Bin via SHFileOperationW with FOF_ALLOWUNDO (stdlib ctypes).
    # UNTESTED on this build — verify on a real Windows machine.
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_uint16),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    FO_DELETE = 3
    FOF_ALLOWUNDO = 0x0040
    FOF_NOCONFIRMATION = 0x0010
    FOF_SILENT = 0x0004
    op = SHFILEOPSTRUCTW()
    op.wFunc = FO_DELETE
    op.pFrom = os.path.abspath(path) + "\x00\x00"  # double-null terminated list
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if rc != 0 or op.fAnyOperationsAborted:
        raise OSError("SHFileOperation failed or cancelled (code %d)" % rc)


def hard_delete(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def open_in_file_manager(path):
    # 非破坏性：在访达 / 资源管理器里打开该位置，方便用户自己审查删除
    target = path if os.path.isdir(path) else os.path.dirname(path)
    if sys.platform == "darwin":
        # .app 是 bundle，对它用 open 会"启动应用"而非显示；必须用 open -R 在访达里选中。
        if target.rstrip("/").endswith(".app"):
            r = subprocess.run(["open", "-R", target], capture_output=True, text=True)
            if r.returncode != 0:
                raise OSError((r.stderr or "open -R 失败").strip())
            return
        # 普通文件夹：先试直接打开看内容；沙盒容器（如微信）open 会报 -10814，
        # 退回 open -R 在父目录里选中它。两者都失败才算错。
        r = subprocess.run(["open", target], capture_output=True, text=True)
        if r.returncode != 0:
            r2 = subprocess.run(["open", "-R", target], capture_output=True, text=True)
            if r2.returncode != 0:
                raise OSError((r.stderr or r2.stderr or "open 失败").strip())
    elif sys.platform.startswith("win"):
        subprocess.run(["explorer", target])  # explorer 退出码不可靠，不据此判成败
    else:
        raise OSError("打开文件夹仅支持 macOS / Windows")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            if (self.headers.get("Host") or "").split(":")[0] not in ("127.0.0.1", "localhost"):
                self._send(403, "host 不被允许", "text/plain; charset=utf-8")
                return
            cfg = {"token": TOKEN, "endpoint": "/action", "allow_rm": PERMANENT_DELETE}
            html = render_report(TPL, DATA, cfg)
            self._send(200, html, "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/action":
            self._send(404, json.dumps({"ok": False, "error": "not found"}))
            return
        # DNS-rebinding guard: only accept local Host
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self._send(403, json.dumps({"ok": False, "error": "host 不被允许"}))
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n < 1 or n > 65536:
                raise ValueError("invalid request size")
            req = json.loads(self.rfile.read(n))
            if not isinstance(req, dict):
                raise ValueError("request must be an object")
        except Exception:
            self._send(400, json.dumps({"ok": False, "error": "请求格式错误"}))
            return
        if req.get("token") != TOKEN:
            self._send(403, json.dumps({"ok": False, "error": "token 校验失败"}))
            return
        mode = req.get("mode")
        allow = {"rm": RM_ALLOW, "trash": TRASH_ALLOW, "open": OPEN_ALLOW}.get(mode)
        if allow is None:
            self._send(400, json.dumps({"ok": False, "error": "未知操作"}))
            return
        paths = req.get("paths")
        if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and os.path.isabs(p) for p in paths):
            self._send(400, json.dumps({"ok": False, "error": "需要非空的绝对路径列表"}))
            return
        # Validate the complete batch before doing anything: a bad second path
        # must not leave the first one already moved/deleted.
        resolved = list(dict.fromkeys(expand(p) for p in paths))
        for rp in resolved:
            if rp not in allow:
                self._send(403, json.dumps({"ok": False, "error": "路径不在白名单：%s" % rp}))
                return
            valid_root = (rp == HOME or rp.startswith(HOME + os.sep) or
                          rp == "/Applications" or rp.startswith("/Applications/")) if mode == "open" else deletion_target(rp)
            if not valid_root:
                self._send(403, json.dumps({"ok": False, "error": "路径越界或为受保护根目录：%s" % rp}))
                return
        done = []
        for rp in resolved:
            try:
                if mode == "open":
                    open_in_file_manager(rp)
                elif not os.path.exists(rp):
                    pass  # already gone, treat as success
                elif mode == "trash":
                    move_to_trash(rp)
                else:
                    hard_delete(rp)
                done.append(rp)
            except Exception as e:
                self._send(500, json.dumps({"ok": False, "error": str(e), "done": done}))
                return
        self._send(200, json.dumps({"ok": True, "done": done}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis")
    parser.add_argument("--enable-cleanup", action="store_true")
    parser.add_argument("--allow-path", action="append", default=[])
    parser.add_argument("--allow-permanent-delete", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not args.enable_cleanup or not args.allow_path:
        parser.error("默认请用 build_report.py；清理服务需要 --enable-cleanup 和具体 --allow-path")
    global DATA, TPL, RM_ALLOW, TRASH_ALLOW, OPEN_ALLOW, PERMANENT_DELETE
    PERMANENT_DELETE = args.allow_permanent_delete
    DATA, TPL, RM_ALLOW, TRASH_ALLOW, OPEN_ALLOW = load(args.analysis, args.allow_path, PERMANENT_DELETE)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    url = "http://127.0.0.1:%d/" % port
    print("报告服务已启动：" + url)
    print("已授权废纸篓路径 %d 项 | 已授权永久删除路径 %d 项" % (len(TRASH_ALLOW), len(RM_ALLOW)))
    print("用完按 Ctrl+C 停止服务（服务关掉后按钮即失效）")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止服务。")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
