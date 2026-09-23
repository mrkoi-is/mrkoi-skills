# macOS 存储归属参考

目录名只能提供线索，不能代替当前内容和使用方核实。

| 目录 | 常见内容 | 默认处理 |
|---|---|---|
| `~/Library/Caches/<app>`、`~/.cache/<tool>` | 可再生成缓存，也可能是下载的模型/离线内容 | 核实子目录、应用状态和再生成条件后列候选 |
| `~/.npm/_cacache`、Xcode `DerivedData/<project>` | 下载缓存、项目构建产物 | 按具体项目/缓存清单处理，说明重建成本 |
| `~/.cargo`、`~/.gradle`、`~/.m2`、`~/Library/pnpm` | 工具、配置、缓存、仓库混合 | 不整目录清理；先区分 bin/config/缓存 |
| `~/Library/Developer/CoreSimulator` | 运行时、设备和模拟器用户数据 | 通过 Xcode/simctl 查询并选择明确不用的设备/运行时 |
| `~/.docker`、Docker 应用数据目录 | 配置、凭据、镜像、持久化卷 | 不手动删除；先区分镜像/容器/卷及使用方 |
| `~/Library/Containers/<UUID 或 bundleid>` | 聊天、离线视频、设置等应用数据 | 用户数据；先识别应用，优先应用内管理 |
| `~/Library/Application Support/*` | 应用配置、资料、虚拟机等 | 用户数据或应用资产，不能按名称自动清理 |
| `~/Downloads/*` | 安装包、文档、唯一存档、交付产物 | 核实可再获取性和使用方，再建议归档或清理 |
| `/Applications/*.app` | 应用本体 | 仅在用户需要时建议正常卸载 |
| 系统文件、APFS 快照 | 系统管理空间 | 说明观测限制，不自动改快照策略 |

## Mr. Koi 工作区

`~/Workspace` 是混合工作区。定位独立仓库、嵌套仓库、worktree 和普通资料目录后，再检查 Git 状态、依赖/SDK 声明、固定路径使用方。不要把 Android/Flutter/FVM、Xcode、Node 版本目录或 `node_modules` 仅按体积判为垃圾。文档、Obsidian Vault、NAS 同步目录和下载交付包视为用户数据。

## 不明容器

只读列出 `Data/Documents`、`Data/Library` 的目录元信息，结合 bundle ID 判断应用归属。归属不明时保留不确定性，不读取无关聊天/文档内容来凑证据。

## 计量限制

`du -sk` 是已分配块的观测值，可能包含快照/克隆与共享块影响；`disk_usage` 是卷级空间。跨层级、跨卷以及重复扫描的数据不能直接求和。`incomplete`/`denied` 必须显示在报告中。

## 废纸篓

只有明确的清理任务才启用服务。macOS 使用 Finder 废纸篓 API，失败则报告失败，不绕过失败结果静默改为移动/永久删除。移入废纸篓不代表物理空间立即释放。
