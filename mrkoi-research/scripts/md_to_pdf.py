#!/usr/bin/env python3
"""Optional Mr. Koi Markdown-to-PDF export; see references/pdf-export.md."""

import argparse
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import sys

CSS_TEMPLATE = """
@page {
    size: A4;
    margin: 25mm 20mm 20mm 20mm;

    @top-center {
        content: HEADER_TEXT;
        font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "Droid Sans Fallback", sans-serif;
        font-size: 8pt;
        color: #95a5a6;
        border-bottom: 0.5pt solid #ecf0f1;
        padding-bottom: 3mm;
    }

    @bottom-center {
        content: "第 " counter(page) " 页";
        font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "Droid Sans Fallback", sans-serif;
        font-size: 8pt;
        color: #95a5a6;
        border-top: 0.8pt solid #1a5276;
        padding-top: 2mm;
    }
}

@page :first {
    @top-center { content: none; }
    @bottom-center { content: none; }
}

body {
    font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", "Droid Sans Fallback", sans-serif;
    font-size: 10.5pt;
    line-height: 1.75;
    color: #2c3e50;
    text-align: justify;
}

/* 封面 */
.cover {
    page-break-after: always;
    text-align: center;
    padding-top: 45%;
}
.cover h1 {
    font-size: 28pt;
    color: #1a5276;
    margin-bottom: 8mm;
    font-weight: bold;
    letter-spacing: 2pt;
}
.cover .subtitle {
    font-size: 14pt;
    color: #95a5a6;
    margin-bottom: 6mm;
}
.cover .meta {
    font-size: 11pt;
    color: #95a5a6;
    margin-bottom: 4mm;
}
.cover .divider {
    width: 60%;
    margin: 8mm auto;
    border: none;
    border-top: 1.5pt solid #1a5276;
}

/* 一级标题 */
h1 {
    font-size: 20pt;
    color: #1a5276;
    margin-top: 16mm;
    margin-bottom: 6mm;
    padding-bottom: 3mm;
    border-bottom: 2pt solid #1a5276;
    page-break-before: always;
    font-weight: bold;
}

/* 二级标题 */
h2 {
    font-size: 14pt;
    color: #1e8449;
    margin-top: 10mm;
    margin-bottom: 5mm;
    font-weight: bold;
}

/* 三级标题 */
h3 {
    font-size: 12pt;
    color: #2e86c1;
    margin-top: 6mm;
    margin-bottom: 3mm;
    font-weight: bold;
}

h4 {
    font-size: 11pt;
    color: #5b2c6f;
    margin-top: 5mm;
    margin-bottom: 2mm;
    font-weight: bold;
}

/* 段落 */
p {
    margin-top: 1.5mm;
    margin-bottom: 1.5mm;
    orphans: 3;
    widows: 3;
}

/* 引用块 */
blockquote {
    margin: 4mm 0;
    padding: 4mm 4mm 4mm 10mm;
    background: #f8f9fa;
    border-left: 3pt solid #1a5276;
    color: #5d6d7e;
    font-size: 10pt;
}
blockquote p {
    margin: 1mm 0;
}

/* 粗体 */
strong, b {
    font-weight: bold;
    color: #1a252f;
}

/* 行内代码 */
code {
    font-family: "Courier New", Courier, monospace;
    background: #fdf2e9;
    color: #c0392b;
    padding: 0.5mm 1.5mm;
    border-radius: 2pt;
    font-size: 9.5pt;
}

/* 表格 */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 4mm 0;
    font-size: 9.5pt;
}
thead th {
    background: #1a5276;
    color: white;
    padding: 3mm;
    text-align: left;
    font-weight: bold;
}
tbody td {
    padding: 2.5mm 3mm;
    border-bottom: 0.5pt solid #bdc3c7;
}
tbody tr:nth-child(even) {
    background: #f8f9fa;
}

/* 分隔线 */
hr {
    border: none;
    border-top: 0.5pt solid #bdc3c7;
    margin: 4mm 0;
}

/* 列表 */
ul, ol {
    margin: 2mm 0;
    padding-left: 8mm;
}
li {
    margin-bottom: 1mm;
}

img { max-width: 100%; height: auto; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
td, th { overflow-wrap: anywhere; }

/* 链接 */
a {
    color: #2e86c1;
    text-decoration: none;
}
"""


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(fragment):
    """Keep title text without copying Markdown-generated HTML to CSS."""
    parser = _TextExtractor()
    parser.feed(fragment)
    return "".join(parser.parts)


def css_string(value):
    """Quote a CSS string, including characters that could close a style tag."""
    escaped = []
    for char in value:
        if char == "\\":
            escaped.append("\\\\")
        elif char == '"':
            escaped.append('\\"')
        elif ord(char) < 32 or char in "<>":
            escaped.append(f"\\{ord(char):x} ")
        else:
            escaped.append(char)
    return '"' + "".join(escaped) + '"'


def extract_meta(md_text):
    """Extract only a leading metadata quote, leaving ordinary body quotes alone."""
    lines = md_text.splitlines()
    first_content = True
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if first_content and stripped.startswith("# "):
            first_content = False
            continue
        if stripped.startswith(">"):
            value = stripped.lstrip(">").strip()
            if value.startswith(("研究时间：", "研究时间:", "所属领域：", "研究对象类型：")):
                del lines[index]
                return "\n".join(lines), value
        break
    return md_text, ""


def output_paths(input_path, output_path):
    source = Path(input_path).expanduser().resolve()
    pdf = Path(output_path).expanduser().resolve()
    if pdf.suffix.lower() != ".pdf":
        raise ValueError("输出文件必须以 .pdf 结尾")
    html = pdf.with_suffix(".html")
    if source in (pdf, html):
        raise ValueError("输出文件不能覆盖输入源文件")
    return source, pdf, html


def md_to_html(md_text, title=None, subtitle="横纵研究报告", meta_line="", author="Mr. Koi"):
    """Convert trusted Markdown and escaped cover metadata into printable HTML."""
    import markdown

    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"], output_format="html5")
    # Only the leading title is moved onto the cover; later H1s remain body content.
    first_h1 = re.match(r"\s*<h1>(.*?)</h1>", html_body, flags=re.DOTALL)
    if first_h1:
        title = title or plain_text(first_h1.group(1))
        html_body = html_body[first_h1.end():]
    title = title or "研究报告"
    css = CSS_TEMPLATE.replace("HEADER_TEXT", css_string(f"{title}  |  {subtitle}"))
    meta_html = f'<div class="meta">{escape(meta_line)}</div>' if meta_line else ""
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>{escape(title)}</title><style>{css}</style></head>
<body>
<div class="cover">
<h1 style="page-break-before: avoid; border: none;">{escape(title)}</h1>
<div class="subtitle">{escape(subtitle)}</div>
{meta_html}<hr class="divider"><div class="meta">作者：{escape(author)}</div>
</div>
{html_body}
</body></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mr. Koi Markdown → PDF（可选导出）")
    parser.add_argument("input", help="UTF-8 Markdown 文件")
    parser.add_argument("output", help="PDF 输出路径，必须以 .pdf 结尾")
    parser.add_argument("--title", help="封面标题，默认使用开头的一级标题")
    parser.add_argument("--subtitle", default="横纵研究报告", help="封面副标题")
    parser.add_argument("--author", default="Mr. Koi", help="作者名")
    args = parser.parse_args(argv)
    try:
        source, pdf_path, html_path = output_paths(args.input, args.output)
        md_text = source.read_text(encoding="utf-8")
        md_text, meta_line = extract_meta(md_text)
        html = md_to_html(md_text, title=args.title, subtitle=args.subtitle, meta_line=meta_line, author=args.author)
        from weasyprint import HTML

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        # Resolve images and relative links relative to the source Markdown folder.
        document = HTML(string=html, base_url=str(source.parent))
        pdf_bytes = document.write_pdf()
        pdf_path.write_bytes(pdf_bytes)
        html_path.write_text(html, encoding="utf-8")
    except (ImportError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        print("依赖与平台运行库说明见 references/pdf-export.md；请勿修改系统 Python。", file=sys.stderr)
        return 1
    print(f"[OK] PDF 已生成: {pdf_path} ({len(pdf_bytes) / 1024:.1f} KB)")
    print(f"[OK] 调试 HTML 已生成: {html_path}")
    print("尚需检查中文字体、图表和分页；命令成功不等于版面已验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
