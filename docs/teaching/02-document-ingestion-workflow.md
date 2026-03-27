# 02 文档入库链路

## 这条链路解决什么问题

文档上传不是“收个文件就结束”，而是要把文件变成：

- 可搜索的正文
- 可语义召回的向量
- 可追踪状态的知识库记录

所以这个项目把入库链路拆成多阶段。

## 整体流程

```text
上传文件
-> 保存原文件和文档记录
-> Kafka 投递轻量任务
-> parser 解析
-> splitter 切片
-> vectorizer 向量化
-> 写入 Elasticsearch / Milvus
-> 更新完成状态
```

## 第 1 步：上传文件

上传发生后，系统会先做三件事：

- 保存原始文件
- 创建 `rag_document` 记录
- 把状态初始化为 `uploading`

然后系统会发一条 Kafka 消息，但消息里不传全文，只传：

- `document_id`
- `file_path`
- `task_metadata`

## 为什么 Kafka 不传全文

因为全文和整批 chunks 都属于重内容：

- 消息会变大
- 失败重试成本高
- 回放和幂等更难做

所以当前设计是：

- Kafka 传任务指针
- 真正的大文本放在文件和中间 artifact 里

## 第 2 步：parser 解析

`parser worker` 的职责是把原始文件变成标准文本。

它会处理：

- PDF
- DOCX
- TXT
- Markdown
- HTML

输出结果不会继续塞进 Kafka，而是先落到 pipeline artifact。

同时文档状态会进入：

```text
parsing
```

## 第 3 步：splitter 切片

`splitter worker` 会读取 parser 产物，再按知识库配置的：

- `chunk_size`
- `chunk_overlap`

进行切片。

这里不是简单按字数硬切，而是尽量保留结构：

- 标题
- 段落边界
- PDF 页码
- heading metadata

状态会更新为：

```text
splitting
```

## 第 4 步：vectorizer 向量化

`vectorizer worker` 会读取 chunks，完成两件事：

1. 生成 embedding，写入 Milvus
2. 把 chunk 正文和 metadata 写入 Elasticsearch

状态会更新为：

```text
embedding
```

## 第 5 步：完成与失败

如果两边都写成功，状态会变成：

```text
completed
```

同时会更新：

- 文档的 `chunk_count`
- 知识库的 `document_count`
- 知识库的 `total_chunks`

如果中途任一阶段失败，状态会进入：

```text
failed
```

## 当前状态机

整个文档处理状态机是：

```text
uploading -> parsing -> splitting -> embedding -> completed / failed
```

## 为什么要拆成三段 worker

这样设计的好处是：

- 每段职责更单一
- 出问题更容易定位
- 可以针对不同阶段单独扩容
- 更容易接入重试、DLQ、回放和幂等控制

## 这一章的重点

入库链路的核心不是“把文件传给模型”，而是“把文件稳定地加工成可检索数据”。

## 下一步看什么

接下来建议看在线问答最核心的部分：

- [03-hybrid-retrieval.md](./03-hybrid-retrieval.md)
