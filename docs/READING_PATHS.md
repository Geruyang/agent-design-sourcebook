# 源码阅读路线 / Guided reading paths

不用按 35 个项目的顺序读。先明确你要做的产品，再选一个最小流程。
Do not read all 35 projects in order. Pick your product goal and trace one small execution path.

## 1. 编码助手 / Coding assistant

Start: [TRAE Agent](../code/bytedance/trae-agent) → [Codex](../code/openai/codex) → [Cline](../code/cline/cline).

追踪一次请求如何组装上下文、调用工具、处理结果、结束任务。比较文件修改、终端执行和审批分别由谁负责。先实现一个可回滚的文件编辑任务。

Trace context assembly, tool calls, results and termination. Compare ownership of edits, shell execution and approvals. Start with a reversible file-edit task.

## 2. 研究 Agent / Research agent

Start: [OpenAI Agents Python](../code/openai/openai-agents-python) → [MCP servers](../code/modelcontextprotocol/servers) → [Context Engineering](../code/muratcankoylan/Agent-Skills-for-Context-Engineering).

先用一个只读工具返回可引用的资料，再加入来源记录、上下文压缩和结果评估。多 Agent 只在拆分任务确有收益时加入。

Begin with one read-only retrieval tool and citable output. Add provenance, context management and evaluation. Add multiple agents only when decomposition helps the task.

## 3. 自托管 Agent 产品 / Self-hosted product

Start: [Agent Foundation](../code/converge-ai-labs/agent-foundation) → [LibreChat](../code/LibreChat-AI/LibreChat) → [AG-UI](../code/ag-ui-protocol/ag-ui).

区分会话状态、后台执行状态和前端展示状态。记录重连、取消、失败恢复、权限与租户隔离的边界。先完成一个用户的一条可恢复任务，再扩展并发与多租户。

Separate conversation, execution and presentation state. Identify reconnection, cancellation, recovery, permissions and tenant boundaries. Complete one resumable task for one user before expanding concurrency and tenancy.

## 每次阅读记下这 5 个问题 / Five questions to keep

1. State: 状态由谁持有，何时落盘？ Who owns and persists state?
2. Tools: 工具输入、输出与失败如何表示？ How are inputs, outputs and failures represented?
3. Authority: 哪些动作需要用户授权？ Which actions need authorization?
4. Recovery: 中断后能从哪里恢复？ Where can execution resume?
5. Evidence: 什么测试能证明目标行为？ Which test demonstrates the intended behavior?

这些是阅读建议，不表示每个项目都实现了同一种机制。按固定版本源码与实际测试判断。
These are study prompts, not claims that every project implements the same mechanism. Use the pinned source and actual tests as evidence.
