# External Delivery Kit

这份文档用于对外投递、项目介绍和简历项目经历撰写，内容基于当前仓库的实际实现整理。

## 项目一句话介绍

企业级 RAG 知识问答系统，支持多格式文档上传、异步解析切片、向量化入库、Milvus + Elasticsearch 混合检索、机器人配置与多轮对话，面向本地化部署和可运维落地场景。

## 项目定位

- 面向企业内部知识管理、制度查询、产品文档问答、交付资料检索等场景
- 强调本地部署、知识隔离、异步处理可靠性和混合检索准确率
- 不只是大模型接入，而是完整的文档处理、检索、问答和运维工程体系

## 简历项目版

项目名称：企业级 RAG 知识问答系统

角色：后端 / 全栈研发（RAG 方向）

技术栈：`FastAPI`、`Next.js`、`MySQL`、`Redis`、`Kafka`、`Elasticsearch`、`Milvus`、`Docker Compose`

项目描述：

构建面向企业知识库场景的 RAG 问答平台，支持文档上传、解析、切片、向量化、混合检索、问答生成、后台管理与本地化部署，重点解决文档处理链路可靠性、检索准确率和多组件运维复杂度问题。

## 简历亮点条目

- 负责设计并实现完整 RAG 链路，覆盖文档上传、解析、切片、向量化、检索融合、问答生成和后台管理能力
- 将文档处理拆分为 `parse / split / vectorize` 三段 Kafka Worker 流水线，提升吞吐与故障隔离能力
- 重构消息模型为 `document_id / file_path / task metadata` 轻量消息，避免大文本和整批 chunk 穿过消息队列
- 设计 `Milvus` 语义召回与 `Elasticsearch` 关键词召回并行执行的混合检索方案，并引入 RRF 融合、阈值过滤和可选 rerank
- 落地 Alembic 迁移体系，替换应用启动期 `create_all`，补齐数据库迁移和初始化治理
- 为 Kafka 消费链路增加手动提交 offset、死信队列、消息回放、阶段幂等与失败闭环，降低重复消费和状态错乱风险
- 将前后端与 MySQL、Redis、ES、Milvus、Kafka 等依赖统一纳入 Docker Compose，形成标准化本地运维闭环
- 编写一键启动、状态检查、日志查看、定向重启、停机和本地集成校验脚本，提升环境一致性与排障效率

## 面向招聘方的成果表述

- 做成了可联调、可恢复、可运维的 RAG 工程系统，而不是单纯的大模型 Demo
- 支撑多格式知识入库和混合检索问答，适合企业内知识管理与私有化部署场景
- 补齐了异步链路可靠性、迁移体系、容器编排和本地集成验证能力，降低后续演进成本

## 适合投递的岗位方向

- RAG 工程师
- AI 应用工程师
- 大模型应用后端工程师
- AI 平台工程师
- 搜索 / 检索增强问答方向后端工程师

## 项目介绍短讲稿

我做的是一个企业级 RAG 知识问答系统，核心不是只把大模型接起来，而是把文档处理、混合检索、可靠性治理和本地化部署都做成了完整工程体系。系统支持 PDF、Word、Markdown、HTML 等多格式文档异步入库，使用 Kafka 拆分解析、切片和向量化阶段，最终把向量写入 Milvus、全文写入 Elasticsearch，在在线问答阶段做向量召回和关键词召回融合，再交给大模型生成答案。

## 投递时推荐保留的关键词

- `RAG`
- `Hybrid Retrieval`
- `Milvus`
- `Elasticsearch`
- `Kafka`
- `FastAPI`
- `Docker Compose`
- `DLQ`
- `Idempotency`
- `Private Deployment`

## 延伸材料

- [candidate-resume-template.md](./candidate-resume-template.md)
- [project-pitch-scripts.md](./project-pitch-scripts.md)
- [repo-copy-assets.md](./repo-copy-assets.md)

## English Materials

- [english-delivery-kit.md](./english-delivery-kit.md)
- [english-project-pitch-scripts.md](./english-project-pitch-scripts.md)
- [english-repo-copy-assets.md](./english-repo-copy-assets.md)

## Showcase Materials

- [showcase-architecture-workflow.md](./showcase-architecture-workflow.md)
- [showcase-demo-walkthrough.md](./showcase-demo-walkthrough.md)
- [showcase-capture-checklist.md](./showcase-capture-checklist.md)

## Case Study Materials

- [case-study-problem-solution-impact.md](./case-study-problem-solution-impact.md)
- [case-study-business-technical-challenges.md](./case-study-business-technical-challenges.md)
- [case-study-portfolio-summary.md](./case-study-portfolio-summary.md)
