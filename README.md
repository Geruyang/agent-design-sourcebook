<p align="center"><img src="assets/banner.svg" alt="Agent Design Sourcebook — 35 pinned source snapshots" /></p>

<p align="center"><strong>想做自己的 Agent？从真实项目的实现开始。</strong><br/>35 个固定版本的源码/公开资料快照，附原始官网、出处、版本与阅读路线。</p>

<p align="center"><b>中文</b> · <a href="README.en.md">English</a> · <a href="SOURCES.md">全部 35 个来源</a> · <a href="docs/READING_PATHS.md">源码阅读路线</a> · <a href="https://github.com/Geruyang/agent-skills-library">配套技能库</a></p>

Agent 的难点往往出现在第一次工具调用之后：状态放在哪里？失败后怎么恢复？工具权限由谁控制？前端如何显示执行过程？这个仓库把相关实现放在同一张地图上，方便你比较、学习，并为自己的项目作出设计选择。

## 这里有什么

| 你正在解决的问题 | 可以先看的项目 |
|---|---|
| 编码 Agent 的运行循环、工具执行与审批 | [Codex](code/openai/codex)、[TRAE Agent](code/bytedance/trae-agent)、[OpenCode](code/anomalyco/opencode)、[Gemini CLI](code/google-gemini/gemini-cli)、[Cline](code/cline/cline) |
| 如何把 Agent 嵌入应用 | [OpenAI Agents Python](code/openai/openai-agents-python)、[Agents JS](code/openai/openai-agents-js)、[Claude Agent SDK](code/anthropics/claude-agent-sdk-python)、[OpenHands SDK](code/OpenHands/software-agent-sdk) |
| 自托管服务、状态与执行环境如何组织 | [Agent Foundation](code/converge-ai-labs/agent-foundation)、[Goose](code/aaif-goose/goose)、[Pi](code/earendil-works/pi) |
| 聊天产品、桌面端与前端事件怎么组织 | [LibreChat](code/LibreChat-AI/LibreChat)、[Cherry Studio](code/CherryHQ/cherry-studio)、[AG-UI](code/ag-ui-protocol/ag-ui)、[ChatKit samples](code/openai/openai-chatkit-advanced-samples) |
| 如何接工具、定义技能、管理上下文 | [MCP SDK](code/modelcontextprotocol/typescript-sdk)、[MCP servers](code/modelcontextprotocol/servers)、[Agent Skills](code/agentskills/agentskills)、[Context Engineering](code/muratcankoylan/Agent-Skills-for-Context-Engineering) |

完整项目、官网、版本及条款见 **[SOURCES.md](SOURCES.md)**。这里直接包含源码文件，下载 ZIP 也能阅读，不需要逐一打开 35 个网页。

## 为什么做这个合集

- **从问题找实现**：按运行时、SDK、工具协议、UI 和技能组织，而不是只列项目名。
- **固定版本，方便比较**：每个快照有上游提交号，研究结果可以回到同一个版本核对。
- **源码就在仓库里**：35 个主项目，保留已有的 Cline benchmark 子模块内容与原始声明。
- **中英文导航**：可以分享给不同语言的团队成员，从同一套材料开始讨论。
- **技能和源码互相配合**：配套 [Agent Skills Library](https://github.com/Geruyang/agent-skills-library) 中的 `agent-designer` 提供架构设计方法，本仓库提供实现参考。

## 下载与使用

点击 **Code → Download ZIP**，或使用：

```bash
git clone --depth 1 https://github.com/Geruyang/agent-design-sourcebook.git
cd agent-design-sourcebook
```

Windows 遇到长路径问题时，可在克隆时指定仓库级选项：

```bash
git -c core.longpaths=true clone --depth 1 https://github.com/Geruyang/agent-design-sourcebook.git
```

源码与上游资源展开约 2.36 GB，下载前留出空间。每个项目的依赖、启动方式和系统要求不同，请阅读对应目录的原始 README。这个合集没有统一的一键运行命令。

## 推荐的第一条阅读路线

1. 从 [Agent Foundation](code/converge-ai-labs/agent-foundation/README.md) 区分运行时、服务与交互层。
2. 用 [OpenAI Agents Python](code/openai/openai-agents-python/README.md) 理解工具与运行循环。
3. 看 [MCP TypeScript SDK](code/modelcontextprotocol/typescript-sdk/README.md) 的工具连接边界。
4. 对照 [AG-UI](code/ag-ui-protocol/ag-ui/README.md)，理解执行事件如何到达前端。
5. 回到你自己的项目，只实现一条“输入 → 工具 → 结果”的最小流程，再加入状态恢复与评估。

还可以按目标选择 [编码助手、研究 Agent、自托管产品三条路线](docs/READING_PATHS.md)。

## 来源、范围与贡献

这里是第三方公开源码/资料的固定快照合集，原作者保留贡献与权利；每个组件继续适用自身许可证。部分项目采用社区或商业条款，不能将整个合集理解为统一的 MIT 开源项目。具体见 [NOTICE.md](NOTICE.md)。

特别说明：Claude Code 的公开仓库不等于完整产品源码；TRAE Agent 不等于 TRAE 客户端源码；第三方 ChatGPT 客户端不等于 OpenAI 官方客户端源码。本库也未包含个人配置、账号密钥、迁移备份或内部插件包。

欢迎提交阅读路线、版本更新建议或来源纠错。为了保留可核对的快照，请先在上游讨论产品代码改动。**如果这份地图帮你少走弯路，欢迎 Star 收藏，也支持你借鉴的原始项目。**
