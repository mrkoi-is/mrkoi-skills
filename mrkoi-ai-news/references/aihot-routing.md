# AIHOT 查询路由

本文件保留上游 API 语义，只在选择具体端点时读取。数据服务的实时契约优先；失败时按错误参考处理。个人额度与账户状态用宿主工具，不能用 AIHOT 的公共重置消息代替。

## 核心工作流

1. 根据意图选择下面唯一的默认入口。
2. 使用服务端参数表达范围；不要先拉大列表再用本地关键词代替 `q`。
3. 按 API 时间顺序展示用户所需数量的最近条目，用 `links.aihot` 作为标题主链接；若另行筛选重点，说明筛选依据，不能把时间顺序叫热度排名。
4. 只基于返回内容总结；证据不足就明说，不用训练记忆补成“实时结果”。
5. 请求失败时按 [错误与重试](errors.md) 降级，不得切换到其它新闻来源冒充 AIHOT。

| 用户意图 | 默认请求 |
|---|---|
| “今天／过去 24 小时有什么” | `/api/v1/items?mode=selected&window=24h` |
| “最近／最近一周有什么” | `/api/v1/items?mode=selected&window=7d&limit=10` |
| “Tibo 重置／发卡／下一次重置” | `/api/v1/codex-resets`；时间、阶段和空值含义见 [API 参考](api.md)，不猜下一次时间 |
| “当前最热／最近在爆什么” | `/api/v1/hot-topics` |
| “这件事的来龙去脉／后续进展” | 先查 hot-topics；若实际返回 `links.story`，从其 `/story/{publicId}` 路径提取 `publicId`，再调用 `/api/v1/stories/{publicId}`；否则用 items 的 `q` 查询 |
| 明确说“最新／今天的日报” | 先 `/api/v1/dailies?limit=1`，再请求返回日期对应的 `/api/v1/dailies/{YYYY-MM-DD}` |
| 明确指定日期的日报 | `/api/v1/dailies/{YYYY-MM-DD}` |
| “有哪些日报／日报归档” | `/api/v1/dailies?limit=N` |
| 模型／产品／论文／行业／技巧 | `/api/v1/items?mode=selected&category=<slug>&window=<24h|7d>` |
| 公司、产品或主题关键词 | `/api/v1/items?mode=selected&q=<关键词>&window=<24h|7d>` |
| “全部／所有公开动态” | `/api/v1/items?mode=all&window=<24h|7d>&limit=10` |
| 当前全部精选或私有完整副本 | 读取 [完整精选同步](sync.md) |

重置查询使用事件 `url` 和帖子 `url`，不要套用资讯的 `links.aihot`、7 天窗口或 limit 参数。先区分全员重置和发重置卡，再说明明确预告或已确认的事实；未公布就回答未知。

路由规则：

- 宽问题默认 `mode=selected`。只有用户明确要全部公开动态时才用 `mode=all`。
- **关键词查询精选池返回空集时，用完全相同的参数再查一次 `mode=all`**，并在输出里注明这些「未进入精选」。两次都空才回答未找到。精选池是高门槛策展，冷门公司或早期产品常常只在全量池里有；直接报「没有」会让用户以为 AIHOT 没覆盖，而实际上站内有内容。这条只适用于带 `q` 的查询，不要拿它扩大「今天有什么」这类宽问题的范围。
- 时间窗默认按 AIHOT 时间轴（`by=timeline`），与网站看到的一致：慢推信源（官方博客、公众号、HuggingFace Daily）原文两三天前发、今天才收录的，仍算「今天」；三天以上的历史回填则归位到原发布日，不会冒充最近。需要严格按第三方原文发布时间对账时才显式加 `by=published`，并向用户说明口径不同。
- 只取用户需要的条数：默认 `limit=50` 是给客户端用的，做简报时 7 天窗口传 `limit=10` 就够，不要默认拉满。
- 只有用户明确说“日报”才用 dailies；日报是固定日切成品，不等同滚动时间窗。
- 最新或今天的日报先查询一次 `/api/v1/dailies?limit=1`；索引有结果时，只使用其中实际返回的日期请求 `/api/v1/dailies/{date}`，索引为空就停止。不要把稳定 URL `/api/v1/dailies/latest` 作为 Agent 的默认入口：部分第三方工具可能在 HTTP 缓存之外长期复用同一 URL 的旧结果。`/latest` 仍是兼容的公开 REST 端点。绝不猜“今天”“昨天”或自行拼日期。
- “现在最热／热点榜”只用 hot-topics；items 按时间倒序，不能替代热点榜。按 `rank` 从小到大展示「第 N 名」，不得展示、推算或索要内部热度值，也不得拿信源数冒充热度。
- 用户追问某个热点的来龙去脉、时间线或最新进展时，只有 hot-topics 条目实际含 `links.story` 才继续：确认 URL 属于 `https://aihot.news/story/{publicId}` 或 `https://aihot.virxact.com/story/{publicId}`，从路径末段提取实际 `publicId`，再请求 `/api/v1/stories/{publicId}`。`links.story` 本身是给人阅读的 HTML 网页，不得直接请求，也不得把网页响应当 API 数据。事件 API 响应含逆序报道时间线、AI 综述（`digest`，随事件演化更新，矛盾会显式标注）与最新进展一句话（`latest`）。字段缺失、URL 不符合上述格式或事件 API 返回 404，表示事件层当前不可用；改用标题关键词查询 items。除此之外没有获取 story id 的检索端点，不得猜测或拼造 id。
- v1 原生时间窗是 `24h` 或 `7d`。用户指定其它七天内范围时，取最小覆盖窗后本地收窄，并如实写明范围。收窄要用与服务端一致的时间轴值，可由返回字段直接算出：`publishedAt` 为空时取 `discoveredAt`；`discoveredAt - publishedAt > 72 小时`（历史回填）时取 `publishedAt`；其余取 `discoveredAt`。直接拿 `publishedAt` 收窄会把慢推信源误删。
- “最近一周资讯”是滚动 7 天查询，不等同 AIHOT 的编辑成品周报。用户明确要 AIHOT 周报或月报时，如实说明当前只有 `https://aihot.news/weekly` 与 `https://aihot.news/monthly` 网页，尚无 Skill／API／RSS 端点；不得调用猜测的 weeklies／monthlies 路径。
- 当前 v1 没有按条目 ID 获取正文的端点。用户要深入阅读时，只能提供 items 已返回的 `summary`、`reason`、`links.aihot` 与 `links.original`；不得绕过 API 抓网页或把混合权限的全文 RSS 冒充单篇正文接口。
- items 的 `reason` 就是网页「推荐理由」。非空时用它写「为什么值得关注」，不要改写成更强的判断；为 null 或缺失时不要编造。
- 普通资讯问答不得下载 selected snapshot；它是给私有完整副本使用的高级同步能力。
- 原公众号爆文榜来源（`mp_hot`）、未审内容、低相关条目和已合并重复条目不在公开池；正常参与精选的官方／媒体公众号来源（`mp_account`）仍可能出现。不得笼统声称“所有公众号内容都被排除”。

完整参数、字段、分页与调用示例只在需要时读取 [API 参考](api.md)。
