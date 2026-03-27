# 06 调试与验证

## 为什么 RAG 项目一定要有联调验证

因为它不是单体应用，而是一整套多组件系统：

- 前端
- 后端
- worker
- MySQL
- Redis
- Kafka
- Elasticsearch
- Milvus

如果只看单个接口是否返回 `200`，并不能证明整条链路可用。

## 最先看什么

先看服务是否健康：

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\status-rag-stack.ps1
```

还可以直接看：

- 前端：`http://localhost:33004`
- 后端健康检查：`http://localhost:38084/health`
- Swagger：`http://localhost:38084/docs`

## 如何验证完整入库链路

推荐直接跑本地集成脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\local-integration.ps1 -StartInfra
```

它会验证：

- 基础服务是否可用
- 迁移是否执行
- 上传到向量化是否跑通
- MySQL、Elasticsearch、Milvus 是否一致落库

## 上传卡住时先看哪里

### 停在 `uploading`

优先排查：

- backend 是否成功发出 Kafka 消息
- Kafka / worker 是否正常运行

### 停在 `parsing`

优先排查：

- parser worker 日志
- 文件解析是否失败
- 原文件路径是否可读

### 停在 `splitting`

优先排查：

- splitter worker 日志
- parser artifact 是否存在

### 停在 `embedding`

优先排查：

- vectorizer worker 日志
- embedding 模型是否可用
- Elasticsearch / Milvus 是否正常写入

## 看日志怎么做

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\logs-rag-stack.ps1 -Services backend,parser,splitter,vectorizer -Tail 50
```

## 重启单个服务怎么做

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-rag-stack.ps1 -Services backend
```

## Kafka 相关问题怎么处理

这个项目已经做了：

- 手动提交 offset
- DLQ
- replay 工具

所以当消息失败时，不是简单丢掉，而是可以继续追踪和回放。

## 如何理解“测试通过”

对这个项目来说，真正的“通过”至少意味着：

- 前后端可访问
- 文档能完成入库
- ES 有 chunk
- Milvus 有向量
- 文档状态能进入 `completed`

## 最后记住一句话

RAG 项目的验证不是看某个函数跑没跑，而是看“从上传到答案”的整条链路有没有闭环。
