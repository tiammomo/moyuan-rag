# Candidate Resume Template

这是一版基于当前项目整理的中文简历模板，可以直接按你的工作年限和真实经历替换个人信息后使用。

## 个人简介模板

具备 `RAG`、大模型应用工程和企业级后端落地经验，熟悉文档解析、异步流水线、混合检索、向量数据库和本地化部署。能够独立把 AI Demo 推进到可联调、可恢复、可运维的工程系统，重点关注链路可靠性、检索准确率和多组件环境治理。

## 核心技能模板

- 后端：`Python`、`FastAPI`、`SQLAlchemy`、`MySQL`、`Redis`
- 检索与 AI：`RAG`、`Milvus`、`Elasticsearch`、`Hybrid Retrieval`、`Rerank`
- 异步与可靠性：`Kafka`、`DLQ`、`Idempotency`、`Retry`、`State Machine`
- 工程化：`Docker Compose`、`Alembic`、本地集成验证、脚本化运维
- 前端：`Next.js`、`React`、`TypeScript`、`Zustand`

## 项目经历模板

项目名称：企业级 RAG 知识问答系统

项目角色：后端 / 全栈研发（RAG 方向）

技术栈：`FastAPI`、`Next.js`、`MySQL`、`Redis`、`Kafka`、`Elasticsearch`、`Milvus`、`Docker Compose`

项目描述：

面向企业内部知识库场景构建 RAG 问答平台，支持多格式文档上传、异步解析切片、向量化入库、Milvus 与 Elasticsearch 混合检索、机器人配置与多轮问答，重点解决文档处理可靠性、混合检索准确率与私有化部署运维复杂度问题。

项目亮点：

- 负责设计并实现完整 RAG 链路，覆盖文档上传、解析、切片、向量化、检索融合、问答生成和后台管理能力
- 将文档处理拆分为 `parse / split / vectorize` 三段 Kafka Worker 流水线，提升吞吐与故障隔离能力
- 重构消息模型为 `document_id / file_path / task metadata` 轻量消息，避免大文本和整批 chunk 穿过消息队列
- 设计 `Milvus` 语义召回与 `Elasticsearch` 关键词召回并行执行的混合检索方案，并引入 `RRF` 融合、阈值过滤和可选 rerank
- 落地 `Alembic` 迁移体系，替换应用启动期 `create_all`，补齐数据库迁移和初始化治理
- 为 Kafka 消费链路增加手动提交 offset、死信队列、消息回放、阶段幂等与失败闭环，降低重复消费和状态错乱风险
- 将前后端与 MySQL、Redis、ES、Milvus、Kafka 等依赖统一纳入 Docker Compose，形成标准化本地运维闭环
- 编写一键启动、状态检查、日志查看、定向重启、停机和本地集成校验脚本，提升环境一致性与排障效率

## 业务难点模板

- 企业文档格式复杂，结构信息容易在解析和切片阶段丢失
- 用户问法和文档原文表述差异大，单一路径检索难以兼顾召回率和精确度
- 文档入库链路长，涉及解析、切片、向量化、ES/Milvus 落库多个阶段，失败点多
- 私有化部署依赖组件多，环境不一致时联调和恢复成本高

## 技术难点模板

- Kafka 只传轻量任务消息，不传全文与整批 chunk，解决大消息和回放成本问题
- 通过手动提交 offset、DLQ、幂等控制和先删后写，控制重复消费和重复索引风险
- 通过混合检索与排序融合，兼顾语义相似和关键词精确命中
- 通过 Compose 和集成脚本，降低多组件系统的联调和排障复杂度

## 面试时可直接复述的总结

这个项目最有价值的地方，不是只把大模型接上，而是把 RAG 做成了一个可联调、可恢复、可部署、可运维的工程系统。
