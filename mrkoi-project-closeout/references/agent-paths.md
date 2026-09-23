# 平台规则与记忆边界

路径是探测线索，不是当前平台一定支持的接口。先读当前会话的指令与本机配置；需要版本相关结论时再查当前官方资料。不要携带其他平台的尺寸阈值、命令或自动记忆写入规则。

## Codex 优先

- 从当前仓库和工作目录定位实际加载的 `AGENTS.md`、`AGENTS.override.md` 及配置的 fallback；核对上级适用范围。文件存在不等于实际加载。
- 用户级目录可能由 `CODEX_HOME` 指定；使用会话给出的 skill 路径，不把 `~/.codex/skills`、`.agents/skills` 或项目目录写死为唯一安装位置。
- 多独立仓库分别遵守各自规则；根级规则不要塞入单个项目的流水账。
- 机器生成的 `MEMORY.md`、`memory_summary.md`、原始记忆及 rollout 索引默认只读。只有用户直接要求更新记忆且当前宿主允许时，使用宿主指定入口；能力存在不等于授权。
- 当前宿主若明确要求写一个 `extensions/ad_hoc/notes/<timestamp>-<slug>.md` 小更新说明，就按该指令执行；不直接改生成文件。不把此路径、`/memories` 或某配置项宣传为普适功能。
- 报告记忆问题时说明过期事实与来源；没有受支持写入口则保留 `generated-read-only`，不自造压缩候选或修改索引。

## Claude Code 与其他 Agent Skills 平台

`CLAUDE.md`、`.claude/CLAUDE.md`、`.claude/rules` 以及 `~/.claude/projects/.../memory` 可以作为 Claude 项目的查找线索；其他平台可能用 AGENTS.md、专属规则目录或设置。先核对当前宿主，不据目录名断定平台正在使用它们。

每份文件分为：人工规则、自动记忆、机器生成历史/索引。类型不明默认只读。人工规则按当前任务授权维护；任何平台记忆都要用户直接要求更新后才写，并遵循本平台机制。

如果 AGENTS.md 与 CLAUDE.md 共存，查项目声明和 readlink/import。只改实际权威源，不强制谁必须是真身；复制安装也不会自动同步。

## 降级用法

宿主不支持技能发现时，可在对话明确引用本 skill 文本，按需要读取 references；不会因此获得任何额外权限。脚本不可用时采用等价只读检查。诊断入口或命令只使用当前环境已经验证存在的形式。

需要核实时可查官方入口：

- [Agent Skills specification](https://agentskills.io/specification)
- [Claude Code memory](https://code.claude.com/docs/en/memory)
- [Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md/)
