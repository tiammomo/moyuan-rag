# RAG Workflow And Hybrid Retrieval

这份文档是当前项目里 RAG 主链路的总览版，适合项目汇报、技术讲解和快速建立整体认知。

如果你想按教学顺序系统阅读，建议直接从：

- [teaching/README.md](./teaching/README.md)

开始。

## 一句话理解这个项目的 RAG

这个项目的 RAG 可以概括成两条主线：

1. 离线入库链路：把文档加工成“可全文检索 + 可语义召回”的知识数据。
2. 在线问答链路：把用户问题转成检索任务，拿到最相关上下文，再交给大模型生成答案。

## 两条主线

### 离线入库

```text
文件 -> 解析 -> 切片 -> 向量化 -> 写入 Elasticsearch / Milvus
```

### 在线问答

```text
问题 -> 查询准备 -> 混合召回 -> 融合 / 重排 -> 生成答案
```

## 离线入库 Workflow

### 第 1 步：上传与建档

- 用户上传 PDF、DOCX、TXT、Markdown、HTML 等文档
- 后端保存原文件并创建文档记录
- 文档状态初始化为 `uploading`
- Kafka 只发送轻量任务消息

当前 Kafka 消息的关键字段是：

- `document_id`
- `file_path`
- `task_metadata`

### 第 2 步：parser 解析

- `parser worker` 读取原文件
- 做格式解析和标准文本抽取
- 把解析结果落到 pipeline artifact
- 状态进入 `parsing`

### 第 3 步：splitter 切片

- `splitter worker` 读取解析结果
- 按知识库配置做 chunk 切片
- 尽量保留标题、页码、段落边界等结构信息
- 状态进入 `splitting`

### 第 4 步：vectorizer 向量化

- `vectorizer worker` 读取切片结果
- 生成 embedding
- 向量写入 `Milvus`
- 正文和 metadata 写入 `Elasticsearch`
- 状态进入 `embedding`

### 第 5 步：完成或失败

- 全部成功后状态变成 `completed`
- 任一阶段失败则进入 `failed`
- 同步更新知识库的文档数和 chunk 数

当前的文档状态机是：

```text
uploading -> parsing -> splitting -> embedding -> completed / failed
```

## 为什么入库链路要拆成三段 worker

因为真实文档处理不是一个轻量操作：

- 文件格式复杂
- 解析和向量化耗时不同
- 每个阶段的失败方式不一样
- 重试、回放、幂等都需要更细粒度控制

拆成 `parse / split / vectorize` 之后，可以获得：

- 更清晰的职责边界
- 更容易的故障定位
- 更自然的扩容方式
- 更可靠的 DLQ 和回放治理

## 在线问答 Workflow

### 第 1 步：加载机器人与知识库

- 用户提问
- 系统加载机器人配置
- 找到机器人绑定的知识库列表
- 读取会话历史和检索配置

### 第 2 步：查询准备

- 根据当前问题构造 retrieval query
- 如果是追问，会把最近一轮上下文拼入查询

### 第 3 步：并行混合召回

系统会并行执行两路检索：

- `Milvus` 向量召回
- `Elasticsearch` 关键词 / 短语 / 标题召回

### 第 4 步：融合与重排

项目当前的融合逻辑分三层看：

1. 先拿到两边候选集
2. 用 `RRF` 进行融合排序
3. 生成 blended score，并按需做 rerank

### 第 5 步：过滤与生成

- 根据阈值过滤不相关 chunk
- 取最终 topK 上下文
- 与 `system_prompt`、历史消息、用户问题一起交给大模型
- 返回最终答案和引用来源

## 为什么一定要做混合检索

单独做向量检索的问题是：

- 语义相关，但可能不够精确
- 专有名词、制度标题、缩写容易命中不稳

单独做关键词检索的问题是：

- 用户问法一变，召回率可能明显下降
- 自然语言问题和原文术语不一致时表现差

所以这个项目把两者结合：

- `Milvus` 负责“像不像”
- `Elasticsearch` 负责“是不是这个词、这个短语、这个标题”

## 当前工程化重点

- Kafka 只传轻量任务消息，不传大文本
- worker 在成功或进入 DLQ 后才提交 offset
- 支持 DLQ 查看与回放
- 向量阶段支持更安全的重建逻辑
- 有本地集成脚本验证 MySQL、ES、Milvus 三端结果一致

## 推荐配套阅读

- [teaching/01-rag-overview.md](./teaching/01-rag-overview.md)
- [teaching/02-document-ingestion-workflow.md](./teaching/02-document-ingestion-workflow.md)
- [teaching/03-hybrid-retrieval.md](./teaching/03-hybrid-retrieval.md)
- [teaching/04-answer-generation.md](./teaching/04-answer-generation.md)
- [teaching/05-system-components.md](./teaching/05-system-components.md)
- [teaching/06-debug-and-validation.md](./teaching/06-debug-and-validation.md)

## 最简短的对外讲法

这个项目的 RAG 不是单路检索，而是一套“异步文档处理 + 混合检索 + 生成答案”的完整工程链路。离线侧用 Kafka 把文档处理拆成解析、切片、向量化三段；在线侧并行执行 Milvus 语义召回和 Elasticsearch 关键词召回，再融合结果交给大模型生成最终回答。
