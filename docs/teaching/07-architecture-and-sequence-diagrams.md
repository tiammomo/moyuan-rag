# 07 架构图与时序图

这一章专门用图的方式，把整个 RAG 系统怎么协作讲清楚。适合 onboarding、分享、面试白板讲解和做项目汇报时快速说明系统结构。

## 1. 系统总架构图

```mermaid
flowchart LR
    U["用户"] --> F["前端<br/>Next.js"]
    F --> B["后端 API<br/>FastAPI"]

    B --> DB["MySQL"]
    B --> R["Redis"]
    B --> K["Kafka"]
    B --> ES["Elasticsearch"]
    B --> MV["Milvus"]

    K --> P["Parser Worker"]
    K --> S["Splitter Worker"]
    K --> V["Vectorizer Worker"]

    P --> FS["文件与 Pipeline Artifact"]
    S --> FS
    V --> FS

    V --> ES
    V --> MV
```

## 这张图要怎么讲

可以按三层来讲：

- 产品层：前端和后端，负责用户操作、业务编排和问答入口。
- 数据与检索层：MySQL、Redis、Elasticsearch、Milvus，负责状态、上下文、全文和向量数据。
- 异步处理层：Kafka 和三个 worker，负责把文档加工成可检索知识。

## 2. 文档入库时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant B as 后端 API
    participant K as Kafka
    participant P as Parser
    participant S as Splitter
    participant V as Vectorizer
    participant ES as Elasticsearch
    participant MV as Milvus

    U->>B: 上传文档
    B->>B: 保存文件 + 创建文档记录
    B->>K: 发布轻量任务消息
    K->>P: 消费上传任务
    P->>P: 解析原文件
    P->>K: 发布 parsed 阶段任务
    K->>S: 消费 parsed 任务
    S->>S: 切片 + 生成 chunk metadata
    S->>K: 发布 split 阶段任务
    K->>V: 消费 split 任务
    V->>MV: 写入向量
    V->>ES: 写入 chunk 正文
    V->>B: 更新文档状态 completed
```

## 这张图的重点

- 上传不是同步做完所有事，而是异步流水线。
- Kafka 在这里负责解耦，不负责传大文本。
- 每个 worker 只做自己那一段职责。
- 最终是 ES 和 Milvus 一起构成检索底座。

## 3. 在线问答时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant B as 后端 API
    participant MV as Milvus
    participant ES as Elasticsearch
    participant L as LLM

    U->>F: 提问
    F->>B: 发起问答请求
    B->>B: 加载机器人与知识库配置
    par 混合召回
        B->>MV: 向量检索
        B->>ES: 关键词/短语检索
    end
    B->>B: 融合、重排、阈值过滤
    B->>L: 发送问题 + 检索上下文
    L-->>B: 返回答案
    B-->>F: 返回答案与引用
    F-->>U: 展示结果
```

## 这张图要怎么讲

- 先讲“召回不是单路，是并行两路”。
- 再讲“生成不是直接回答，而是基于检索上下文回答”。
- 最后强调“答案质量依赖检索质量，不只是依赖模型本身”。

## 4. 为什么图解比文字更重要

因为 RAG 项目很容易被误解成：

- 一个聊天框
- 一个向量库
- 一个模型调用

但实际上这里是完整工程系统。图解能快速说明：

- 数据在哪里流动
- 哪些组件在协作
- 哪个阶段出了问题应该查哪一层

## 5. 这一章的使用方式

这份文档最适合拿来做：

- 项目汇报的结构图
- 面试白板讲解的底稿
- 内部 onboarding 的快速说明
- 仓库文档里的视觉补充材料
