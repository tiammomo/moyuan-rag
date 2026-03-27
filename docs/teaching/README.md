# RAG Teaching Guide

这个目录专门用于讲清楚当前项目里的 RAG 全流程，目标不是只解释概念，而是把“这个仓库里实际怎么做的”讲明白。

## 推荐阅读顺序

1. [01-rag-overview.md](./01-rag-overview.md)
2. [02-document-ingestion-workflow.md](./02-document-ingestion-workflow.md)
3. [03-hybrid-retrieval.md](./03-hybrid-retrieval.md)
4. [04-answer-generation.md](./04-answer-generation.md)
5. [05-system-components.md](./05-system-components.md)
6. [06-debug-and-validation.md](./06-debug-and-validation.md)
7. [07-architecture-and-sequence-diagrams.md](./07-architecture-and-sequence-diagrams.md)
8. [08-simplified-data-flow.md](./08-simplified-data-flow.md)

## 这套教学内容会回答什么

- 这个项目的 RAG 到底分成哪些阶段
- 文档为什么要拆成 `parse / split / vectorize`
- Kafka 为什么只传 `document_id / file_path / task metadata`
- Milvus 和 Elasticsearch 为什么要一起用
- 混合检索的融合、重排、阈值过滤是怎么串起来的
- 生成答案时上下文是怎么组装的
- 出问题时应该从哪里排查
- 怎么用图把整个 RAG 结构讲给别人
- 怎么用最简单的数据流图解释“文档变知识、问题变答案”

## 适合谁看

- 刚接触 RAG，想把整体链路看清楚的人
- 想基于这个仓库做二次开发的人
- 面试、汇报、分享时需要一套结构化讲法的人
