# MiniMax Anthropic-Compatible Setup

这份文档说明如何在当前项目里，把 MiniMax 通过 Anthropic 兼容接口接入为 RAG 聊天模型。

## 适用范围

当前仓库已经实测支持：

- `provider = anthropic`
- `model_type = chat`
- `base_url = https://api.minimaxi.com/anthropic`

后端会自动把上面的基础地址归一化到：

```text
https://api.minimaxi.com/anthropic/v1/messages
```

同时会按 Anthropic 原生格式包装消息体，也就是把 `user/assistant` 消息转换成 `content: [{ type: "text", text: "..." }]` 的结构。

## 管理后台配置步骤

### 1. 新建聊天模型

在 `管理后台 -> LLM 配置` 中新增一条记录：

- `name`: `MiniMax M2.5 Anthropic`
- `model_type`: `chat`
- `provider`: `anthropic`
- `model_name`: `MiniMax-M2.5`
- `base_url`: `https://api.minimaxi.com/anthropic`
- `description`: 可以写成“MiniMax Anthropic-compatible chat model”

如果你需要，也可以使用 MiniMax 兼容返回的 Claude 别名模型。

### 2. 绑定 API Key

在 `管理后台 -> API Keys` 中为上面的 LLM 新增一条密钥记录。

说明：

- 仓库不会提交真实密钥
- API Key 会在后端加密后存储
- 运行时会在请求前解密并注入到厂商适配器

### 3. 绑定机器人

在 `机器人` 页面创建或编辑机器人：

- 把 `chat_llm_id` 指向上面创建的 MiniMax LLM
- 绑定至少一个知识库
- 根据需要设置 `top_k`、`similarity_threshold`、`temperature`

完成后，普通用户就可以在聊天页直接使用这个机器人进行 RAG 问答。

## 当前实现细节

本次接入补齐了这几个兼容点：

1. `AnthropicProvider` 允许把 `base_url` 配成厂商根地址，而不是必须手动写完整的 `/v1/messages`。
2. 请求消息会按 Anthropic 规范转换成内容块格式，而不是直接传纯字符串。
3. 非流式响应会同时解析：
   - `text`
   - `thinking`
4. 流式响应会识别：
   - `text_delta`
   - `thinking_delta`

核心代码在：

- [backend/app/core/llm/providers/anthropic.py](../backend/app/core/llm/providers/anthropic.py)

## 已验证结果

2026-03-27 在本地 compose 环境完成了真实验证：

- 前端：`http://localhost:33004`
- 后端：`http://localhost:38084`
- 知识库文档：`03-hybrid-retrieval.md`
- 聊天模型：`MiniMax-M2.5`
- 接口路径：`https://api.minimaxi.com/anthropic/v1/messages`

验证通过的内容包括：

- 真实 MiniMax API 请求返回 `200`
- 本地 `POST /api/v1/chat/ask` 成功返回答案
- RAG 检索上下文正常拼装
- 聊天结果已经在前端页面展示并截图

## 截图

### 知识库总览

![知识库总览](./assets/readme/rag-knowledge-overview.png)

### 文档入库完成

![文档入库完成](./assets/readme/rag-document-completed.png)

### MiniMax RAG 对话

![MiniMax RAG 对话](./assets/readme/rag-chat-minimax-answer.png)

## 当前限制

这条 Anthropic 兼容接入目前主要用于 `chat` 能力。

当前不支持通过 `AnthropicProvider` 直接做：

- embedding
- rerank

因此如果知识库向量化和重排需要外部模型，仍然建议分别使用当前项目已经支持的 embedding/rerank 方案。

## 排障建议

如果 MiniMax 聊天没有工作，优先检查：

1. `provider` 是否填成了 `anthropic`
2. `base_url` 是否填成了 `https://api.minimaxi.com/anthropic`
3. API Key 是否绑定到了正确的 LLM
4. 机器人是否真的绑定了这个 chat LLM
5. 知识库文档状态是否已经到 `completed`

如果需要进一步看系统链路，可继续参考：

- [rag-workflow-hybrid-retrieval.md](./rag-workflow-hybrid-retrieval.md)
- [teaching/03-hybrid-retrieval.md](./teaching/03-hybrid-retrieval.md)
- [local-integration.md](./local-integration.md)
- [demo-data-utf8-repair.md](./demo-data-utf8-repair.md)
