# 可选 PDF 导出

只有用户需要 PDF 时运行。Markdown 是保留的源稿，PDF 是派生交付物。

## 依赖

需要 Python 3、`markdown`、`weasyprint`，以及当前 WeasyPrint 平台要求的原生运行库。先检查已有运行时；在 Codex 桌面环境可用 `load_workspace_dependencies` 查找可用依赖。缺失时使用项目或临时虚拟环境，不加 `--break-system-packages`，不修改系统 Python。

依赖安装应遵循当前任务授权；如果本次只要求分析，不需要为可选 PDF 安装软件。所需平台组件以实际 WeasyPrint 报错和官方安装说明为准，不承诺仅 `pip install` 就能解决原生库问题。

## 命令

```bash
python /path/to/mrkoi-research/scripts/md_to_pdf.py report.md report.pdf --author "Mr. Koi"
```

输出必须使用 `.pdf` 后缀（大小写均可）；同目录生成 `.html` 供调试。输出文件可能被覆盖，运行前选择本次交付路径。相对图片与链接以输入 Markdown 所在目录解析，Markdown 中的原始 HTML 按原样传给渲染器，仅用于可信本地稿件。

开头的 `# 标题` 自动用于封面；`--title` 可覆盖标题，`--subtitle` 可改副标题。紧接开头标题的 `> 研究时间：... | 所属领域：...` 元信息可移到封面，正文普通引用保持原状。

默认字体依次寻找 Noto Sans CJK SC、PingFang SC、Microsoft YaHei 等；字体名称写进 CSS 不代表机器已安装可用字体。缺字时应选择当前系统已有的中文字体或补齐项目依赖后重新验证。

## 验证

确认 PDF 能打开、中文可见且可复制、标题与作者正确、相对图片存在；渲染页面检查长表格、代码、图片、分页及页眉。内容较长时尤其查看首尾页和跨页表格。

记录实际状态：未运行、命令生成成功、或生成并完成版面检查。缺依赖时交付完整 Markdown 并说明 PDF 未生成，不能把语法检查或 HTML 检查算作 PDF 验收。
