# Skills Bootstrap Slice

## What This Slice Delivered

Bootstrap slice 解决的是 `skills` 从零到一可用的问题。

已落地内容：
- 本地文件型 skill 注册表
- `installed.json` 作为安装元数据索引
- Skills 列表与详情 API
- 本地 zip skill 安装入口
- 机器人 skill 绑定表与绑定 API
- `/skills` 与 `/skills/[slug]` 前端页面
- 仓库内置 demo skill：`rag-citation-guide`

## Bootstrap Slice Boundary

这一阶段的重点是“能安装、能查看、能绑定”，不是“运行时已经接入”。

因此 bootstrap 阶段的边界是：
- skill 元数据和包内容来自文件系统
- 绑定关系持久化到 MySQL
- 远端安装默认拒绝
- 不处理运行时 prompt 注入

## What Happened Next

运行时接入已经在下一阶段完成，继续阅读：
- [skills-runtime-integration.md](./skills-runtime-integration.md)
