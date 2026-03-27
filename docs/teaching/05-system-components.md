# 05 系统组件与数据路径

## 先看组件分层

这个项目可以按三层理解：

### 1. 产品层

- `front`：前端页面，负责登录、知识库、聊天、管理界面
- `backend`：后端 API，负责鉴权、业务逻辑、检索与问答编排

### 2. 数据与检索层

- `MySQL`：业务元数据
- `Redis`：会话上下文和运行时缓存
- `Elasticsearch`：全文与 chunk 正文检索
- `Milvus`：向量存储与语义召回

### 3. 异步处理层

- `Kafka`：任务投递和解耦
- `parser worker`
- `splitter worker`
- `vectorizer worker`

## 谁存什么

### MySQL

存：

- 用户
- 知识库
- 文档
- 机器人
- 会话
- 状态和元数据

### Elasticsearch

存：

- chunk 正文
- chunk metadata
- knowledge_id / document_id / chunk_index

### Milvus

存：

- chunk vector
- chunk 标识
- 与检索相关的必要字段

### 文件与 pipeline artifact

存：

- 原始上传文件
- parser 产物
- splitter 产物

## 数据是怎么流动的

### 离线入库

```text
用户上传
-> backend 落文件和数据库记录
-> Kafka 发任务
-> parser 产出标准文本
-> splitter 产出 chunks
-> vectorizer 写 ES / Milvus
```

### 在线问答

```text
用户提问
-> backend 加载机器人和知识库
-> Milvus / Elasticsearch 并行召回
-> 融合 / rerank / 过滤
-> 交给大模型生成答案
```

## 为什么一个知识库对应一个向量 collection

这样做有几个好处：

- 隔离更清晰
- 删除或重建知识库更方便
- 不同知识库可以独立管理向量数据

## 为什么 ES 和 Milvus 不能互相替代

因为它们解决的不是同一个问题：

- ES 强在词项、短语、标题、全文
- Milvus 强在语义相似度

所以它们在这个系统里是互补关系，而不是二选一。

## 这一章的重点

看懂组件分工之后，就能更容易理解：

- 某个问题应该去哪个系统查
- 某个故障大概率落在哪一层

## 下一步看什么

最后一章讲“怎么验证系统真的跑通，以及出问题时怎么排查”：

- [06-debug-and-validation.md](./06-debug-and-validation.md)
