# Repo Copy Assets

这份文档整理了可复用的仓库首页文案、项目标签和亮点描述，适合放在 GitHub 仓库简介、项目主页、简历附件或投递材料中。

## GitHub 仓库简介短句

企业级 RAG 知识问答系统，支持多格式文档异步入库、Milvus + Elasticsearch 混合检索、本地化部署与可运维落地。

## 仓库标签建议

- `RAG`
- `LLM`
- `FastAPI`
- `Next.js`
- `Kafka`
- `Elasticsearch`
- `Milvus`
- `Hybrid Retrieval`
- `Docker Compose`
- `Private Deployment`

## 项目亮点短文案

### 版本一

面向企业知识库场景的 RAG 问答平台，支持 PDF / Word / Markdown / HTML 等多格式文档异步入库，采用 Kafka Worker 流水线处理解析、切片和向量化，并通过 Milvus 与 Elasticsearch 混合检索提升召回准确率。

### 版本二

这不是一个只调用大模型接口的 Demo，而是一套完整的 RAG 工程系统：文档处理、混合检索、问答生成、数据库迁移、容器编排和本地集成验证都已经成型。

### 版本三

围绕企业内部知识管理与私有化部署需求打造的 RAG 平台，强调异步链路可靠性、检索准确率和多组件环境下的可运维性。

## README / 首页可复用卖点

- 多格式文档异步入库
- Kafka 驱动的三段式处理流水线
- Milvus + Elasticsearch 混合检索
- 支持死信队列、回放和幂等治理
- Alembic 迁移体系
- Docker Compose 全栈统一编排
- 本地集成脚本验证 ES / Milvus / MySQL 一致落库

## 对外展示时的注意点

- 强调“工程化落地”，不要只说接了大模型
- 强调“混合检索”，这比单纯向量库更有说服力
- 强调“可部署、可运维、可恢复”，这会明显提升项目可信度
- 如果需要写成果描述，优先写架构演进和问题解决方式，而不是堆功能列表
