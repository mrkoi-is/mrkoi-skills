# Mr. Koi Skills

面向中文研究、内容创作和个人工程协作的 6 个 Agent Skills。由 [Khazix Skills](https://github.com/KKKKhazix/khazix-skills) fork 而来，保留方法与历史，按 Mr. Koi 的工作方式维护。

个人仓库：[mrkoi-is/mrkoi-skills](https://github.com/mrkoi-is/mrkoi-skills) · [English](README.en.md) · [分析与改造说明](docs/analysis.md)

## 有什么

| 个人版 | 原技能 | 适合解决的问题 | 本版重点 |
|---|---|---|---|
| [mrkoi-goal-planner](mrkoi-goal-planner/SKILL.md) | leader | 把复杂想法变成可执行、可验收的目标 | 先查事实，保留用户选择，按宿主能力输出任务书 |
| [mrkoi-storage-analyzer](mrkoi-storage-analyzer/SKILL.md) | storage-analyzer | 查清磁盘占用，形成清理决策 | 默认静态只读报告，区分工具链、缓存与用户数据 |
| [mrkoi-ai-news](mrkoi-ai-news/SKILL.md) | aihot | AI 新闻、热点、日报与选题线索 | 聚合发现线索，重要事实核对一手来源 |
| [mrkoi-project-closeout](mrkoi-project-closeout/SKILL.md) | neat-freak | 对齐本次工作与文档、规则和交接状态 | 当前项目收尾，发布与记忆写入按实际请求 |
| [mrkoi-research](mrkoi-research/SKILL.md) | hv-analysis | 研究产品、公司、技术或概念 | 横向对比与纵向演化，按问题控制篇幅和格式 |
| [mrkoi-writer](mrkoi-writer/SKILL.md) | khazix-writer | 把资料、观点和经历整理成中文文章 | 使用自己的材料，不借用原作者身份和经历 |

所有 Skill 使用独立的 `mrkoi-` 名称，不覆盖原版或已有 `human-writing`。这份仓库也不宣称已经学会你的个人文风；写作样文和明确反馈可以继续帮助校准。

## 本地使用

需要 Python 3.10+。把 fork 克隆到你自己的代码目录，先预览安装：

```bash
git clone https://github.com/mrkoi-is/mrkoi-skills.git
cd mrkoi-skills
python3 scripts/install_local.py
python3 scripts/install_local.py --apply
```

安装器将六个目录链接到 `${CODEX_HOME:-~/.codex}/skills`。只创建软链接，仓库是唯一维护源；目标位置存在其他文件、目录或链接就停止，绝不覆盖。支持只安装部分：

```bash
python3 scripts/install_local.py mrkoi-research mrkoi-writer --apply
```

安装后在下一轮或新会话中调用；若客户端尚未刷新列表，重新打开会话。其他支持 Agent Skills 的客户端可通过 `--dest` 指定其技能目录，实际发现与调用需在目标客户端验证。

```text
使用 $mrkoi-goal-planner 把这个想法整理成目标任务书。
使用 $mrkoi-storage-analyzer 分析这个目录的磁盘占用，只生成报告。
使用 $mrkoi-ai-news 整理过去 24 小时的 AI 重点消息。
使用 $mrkoi-project-closeout 核对本次改动和项目文档是否一致。
使用 $mrkoi-research 对比这几个方案，给出有来源的判断。
使用 $mrkoi-writer 把这些材料整理成一篇适合公众号的文章。
```

磁盘分析和 PDF 导出各自的参数、依赖以对应 Skill 和脚本 `--help` 为准。安装不会扫描磁盘、清理文件、拉取新闻全文、创建定时任务或修改记忆。

## 维护与验证

```bash
python3 -m unittest discover -s tests -v
```

各技能的脚本测试与验证范围见 [分析与改造说明](docs/analysis.md)。说明文档通过结构检查，不等于已在所有模型和客户端上完成行为验收。

原始目录已经个人化改名。同步上游时先审阅差异，再把相关变更移植到对应目录：

```bash
git remote add upstream https://github.com/KKKKhazix/khazix-skills.git
git fetch upstream
git diff 4f2db09802736ac8130ddf8dd6121435b5a41b55 upstream/main
```

`upstream` 已存在时跳过 `remote add`。不要直接将上游整个技能目录覆盖回来，也不要用 AIHOT 网站的安装脚本更新本 fork。

## 来源

基于上游提交 `4f2db09802736ac8130ddf8dd6121435b5a41b55`（2026-09-23 拉取）。原项目与个人版适配采用 [MIT License](LICENSE)，保留原作者版权。AIHOT 技能及参考另保留 [Virxact 的 MIT 许可](mrkoi-ai-news/LICENSE)。新闻数据和第三方文章不随代码许可转移。
